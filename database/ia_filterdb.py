import logging
import re
import base64
from struct import pack
from pymongo import MongoClient, TEXT
from pymongo.errors import DuplicateKeyError
from hydrogram.file_id import FileId

from info import (
    PRIMARY_DB_URL,
    CLOUD_DB_URL,
    ARCHIVE_DB_URL,
    DATABASE_NAME,
    COLLECTION_NAME,
    USE_CAPTION_FILTER,
    MAX_BTN
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────
# 🔌 DATABASE CONNECTIONS
# ─────────────────────────────────────

# Primary DB
primary_client = MongoClient(PRIMARY_DB_URL)
primary_db = primary_client[DATABASE_NAME]
primary_col = primary_db[COLLECTION_NAME]

# Cloud DB
cloud_col = None
if CLOUD_DB_URL:
    cloud_client = MongoClient(CLOUD_DB_URL)
    cloud_db = cloud_client[DATABASE_NAME]
    cloud_col = cloud_db[COLLECTION_NAME]

# Archive DB
archive_col = None
if ARCHIVE_DB_URL:
    archive_client = MongoClient(ARCHIVE_DB_URL)
    archive_db = archive_client[DATABASE_NAME]
    archive_col = archive_db[COLLECTION_NAME]

# ─────────────────────────────────────
# 📌 CREATE TEXT INDEX (SAME FOR ALL)
# ─────────────────────────────────────
for col in (primary_col, cloud_col, archive_col):
    if col:
        try:
            col.create_index([("file_name", TEXT)])
        except Exception as e:
            logger.warning(f"Index creation skipped: {e}")

# ─────────────────────────────────────
# 🧠 HELPERS
# ─────────────────────────────────────

def get_collection(db_type: str):
    if db_type == "primary":
        return primary_col
    if db_type == "cloud":
        return cloud_col
    if db_type == "archive":
        return archive_col
    return None


def unpack_new_file_id(new_file_id: str) -> str:
    decoded = FileId.decode(new_file_id)
    return base64.urlsafe_b64encode(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    ).decode().rstrip("=")

# ─────────────────────────────────────
# 💾 SAVE FILE (PRIMARY / CLOUD / ARCHIVE)
# ─────────────────────────────────────
async def save_file(media, db_type: str = "primary"):
    collection = get_collection(db_type)
    if not collection:
        return "err"

    file_id = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"@\w+|[_\-.+]", " ", str(media.file_name))
    caption = re.sub(r"@\w+|[_\-.+]", " ", str(media.caption or ""))

    document = {
        "_id": file_id,
        "file_name": file_name,
        "file_size": media.file_size,
        "caption": caption,
        "db": db_type
    }

    try:
        collection.insert_one(document)
        logger.info(f"[{db_type.upper()}] Indexed → {file_name}")
        return "suc"
    except DuplicateKeyError:
        return "dup"
    except Exception as e:
        logger.error(e)
        return "err"

# ─────────────────────────────────────
# 🔍 SEARCH (ALL DBs or SINGLE DB)
# ─────────────────────────────────────
async def get_search_results(
    query: str,
    db_type: str | None = None,
    max_results: int = MAX_BTN,
    offset: int = 0
):
    query = query.strip()
    if not query:
        pattern = re.compile(".", re.IGNORECASE)
    else:
        pattern = re.compile(query.replace(" ", ".*"), re.IGNORECASE)

    if USE_CAPTION_FILTER:
        flt = {"$or": [{"file_name": pattern}, {"caption": pattern}]}
    else:
        flt = {"file_name": pattern}

    results = []

    collections = (
        [get_collection(db_type)]
        if db_type
        else [primary_col, cloud_col, archive_col]
    )

    for col in collections:
        if col:
            results.extend(list(col.find(flt)))

    total = len(results)
    files = results[offset: offset + max_results]
    next_offset = offset + max_results if offset + max_results < total else ""

    return files, next_offset, total

# ─────────────────────────────────────
# 📊 COUNTS (STATS PANEL)
# ─────────────────────────────────────
def count_files(db_type: str) -> int:
    col = get_collection(db_type)
    return col.count_documents({}) if col else 0


def count_all_files() -> int:
    return (
        count_files("primary")
        + count_files("cloud")
        + count_files("archive")
    )

# ─────────────────────────────────────
# 📦 FILE DETAILS (PM / STREAM)
# ─────────────────────────────────────
async def get_file_details(file_id: str):
    for col in (primary_col, cloud_col, archive_col):
        if col:
            doc = col.find_one({"_id": file_id})
            if doc:
                return doc
    return None

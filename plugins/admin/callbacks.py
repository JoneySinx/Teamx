# plugins/admin/callbacks.py
import time
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from info import ADMINS, TOTAL_DB_SIZE_MB
from utils import get_readable_time, temp
from database.ia_filterdb import (
    db_count_documents,
    second_db_count_documents,
)
from database.users_chats_db import db


# ─────────────────────────────────────
# 🔐 ADMIN FILTER
# ─────────────────────────────────────
async def admin_only(_, __, query: CallbackQuery):
    return query.from_user and query.from_user.id in ADMINS

admin_filter = filters.create(admin_only)


# ─────────────────────────────────────
# 📊 DB PROGRESS BAR
# ─────────────────────────────────────
def db_progress_bar(used, total, size=10):
    if total <= 0:
        return "□" * size
    percent = min(used / total, 1)
    filled = int(size * percent)
    return "■" * filled + "□" * (size - filled)


# ─────────────────────────────────────
# 📥 INDEX PANEL
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^admin_index$") & admin_filter)
async def admin_index_panel(client, query: CallbackQuery):
    text = "<b>📥 Index Management</b>\n\nChoose what you want to do 👇"

    buttons = [
        [
            InlineKeyboardButton("➕ Start Indexing", callback_data="admin_index_start"),
            InlineKeyboardButton("📄 Indexed Channels", callback_data="admin_index_channels"),
        ],
        [InlineKeyboardButton("⏹ Cancel Indexing", callback_data="admin_index_cancel")],
        [InlineKeyboardButton("« Back", callback_data="admin_home")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )


# ─────────────────────────────────────
# 🔍 ADMIN SEARCH (PLACEHOLDER)
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^admin_search$") & admin_filter)
async def admin_search_panel(client, query: CallbackQuery):
    await query.edit_message_text(
        "<b>🔍 Admin Search</b>\n\n"
        "Send search query in chat.\n"
        "(Advanced DB grouping coming next)",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Back", callback_data="admin_home")]
        ])
    )


# ─────────────────────────────────────
# 📊 STATS PANEL (UPDATED)
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^admin_stats$") & admin_filter)
async def admin_stats(client, query: CallbackQuery):

    start = time.time()

    users = await db.total_users_count()
    chats = await db.total_chat_count()

    primary_files = db_count_documents()
    cloud_files = second_db_count_documents()

    # archive (safe fallback)
    try:
        from database.ia_filterdb import archive_db_count_documents
        archive_files = archive_db_count_documents()
    except Exception:
        archive_files = 0

    total_files = primary_files + cloud_files + archive_files

    # DB SIZE (MB)
    used_bytes = (
        await db.get_files_db_size() +
        await db.get_second_files_db_size()
    )

    try:
        used_bytes += await db.get_archive_files_db_size()
    except Exception:
        pass

    used_mb = used_bytes / (1024 * 1024)
    total_mb = TOTAL_DB_SIZE_MB

    bar = db_progress_bar(used_mb, total_mb)
    percent = round((used_mb / total_mb) * 100, 2)

    uptime = get_readable_time(time.time() - temp.START_TIME)

    text = (
        "<b>📊 Bot Statistics</b>\n\n"
        f"👤 Users : <code>{users}</code>\n"
        f"👥 Chats : <code>{chats}</code>\n\n"

        f"🗂 Primary  : <code>{primary_files}</code>\n"
        f"☁️ Cloud    : <code>{cloud_files}</code>\n"
        f"📦 Archive  : <code>{archive_files}</code>\n\n"

        f"📊 Total Files : <code>{total_files}</code>\n\n"

        f"💾 Total DB Size : <code>{total_mb} MB</code>\n"
        f"📈 Used DB Size  : <code>{used_mb:.2f} MB</code>\n\n"

        f"📉 DB Usage : {bar} <code>{percent}%</code>\n\n"

        f"⏱ Uptime : <code>{uptime}</code>"
    )

    await query.edit_message_text(
        text,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Back", callback_data="admin_home")]
        ])
    )

    await query.answer(f"Updated in {round(time.time() - start, 2)}s ⚡")


# ─────────────────────────────────────
# ⚙️ SETTINGS PANEL
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^admin_settings$") & admin_filter)
async def admin_settings(client, query: CallbackQuery):
    await query.edit_message_text(
        "<b>⚙️ Admin Settings</b>\n\nGlobal bot settings will appear here.",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Back", callback_data="admin_home")]
        ])
    )


# ─────────────────────────────────────
# 📢 BROADCAST PANEL
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^admin_broadcast$") & admin_filter)
async def admin_broadcast(client, query: CallbackQuery):
    await query.edit_message_text(
        "<b>📢 Broadcast Panel</b>\n\nUse /broadcast or /grp_broadcast commands.",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Back", callback_data="admin_home")]
        ])
    )


# ─────────────────────────────────────
# 🧠 DATABASE MANAGER
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^admin_databases$") & admin_filter)
async def admin_databases(client, query: CallbackQuery):
    text = (
        "<b>🧠 Database Manager</b>\n\n"
        "Select database 👇\n\n"
        "• Primary DB\n"
        "• Cloud DB\n"
        "• Archive DB"
    )

    buttons = [
        [
            InlineKeyboardButton("🗂 Primary", callback_data="db_primary"),
            InlineKeyboardButton("☁️ Cloud", callback_data="db_cloud"),
        ],
        [InlineKeyboardButton("📦 Archive", callback_data="db_archive")],
        [InlineKeyboardButton("« Back", callback_data="admin_home")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )


# ─────────────────────────────────────
# 🏠 BACK TO ADMIN HOME
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^admin_home$") & admin_filter)
async def admin_home(client, query: CallbackQuery):
    from plugins.admin.start import admin_start
    fake_msg = query.message
    fake_msg.from_user = query.from_user
    await admin_start(client, fake_msg)

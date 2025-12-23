# plugins/admin/search.py

from hydrogram import Client, filters, enums
from hydrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

from info import ADMINS, MAX_BTN
from utils import temp
from database.ia_filterdb import (
    admin_search_count,
    admin_search_results
)


# ─────────────────────────────────────
# 🔐 ADMIN FILTER
# ─────────────────────────────────────
async def admin_only(_, __, obj):
    return obj.from_user and obj.from_user.id in ADMINS

admin_filter = filters.create(admin_only)


# ─────────────────────────────────────
# 🔍 ADMIN SEARCH ENTRY
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^admin_search$") & admin_filter)
async def admin_search_entry(client, query: CallbackQuery):
    await query.edit_message_text(
        "<b>🔍 Admin Search</b>\n\n"
        "Send your search keyword in chat.\n"
        "Example: <code>Avatar 2022</code>",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Back", callback_data="admin_home")]
        ])
    )

    # wait for query
    msg = await client.listen(query.message.chat.id, query.from_user.id)
    search_key = msg.text.strip()

    await msg.delete()
    await show_grouped_results(client, query, search_key)


# ─────────────────────────────────────
# 📊 GROUPED SEARCH RESULT
# ─────────────────────────────────────
async def show_grouped_results(client, query, keyword):
    primary = await admin_search_count(keyword, db_type="primary")
    cloud = await admin_search_count(keyword, db_type="cloud")
    archive = await admin_search_count(keyword, db_type="archive")

    total = primary + cloud + archive

    text = (
        "<b>📊 Search Results</b>\n\n"
        f"🔎 Query : <code>{keyword}</code>\n\n"
        f"🗂 Primary : <code>{primary}</code>\n"
        f"☁️ Cloud : <code>{cloud}</code>\n"
        f"📦 Archive : <code>{archive}</code>\n\n"
        f"📁 Total Files : <code>{total}</code>\n\n"
        "Select database 👇"
    )

    buttons = [
        [
            InlineKeyboardButton(
                f"🗂 Primary ({primary})",
                callback_data=f"admin_search_db#primary#0#{keyword}"
            ),
            InlineKeyboardButton(
                f"☁️ Cloud ({cloud})",
                callback_data=f"admin_search_db#cloud#0#{keyword}"
            )
        ],
        [
            InlineKeyboardButton(
                f"📦 Archive ({archive})",
                callback_data=f"admin_search_db#archive#0#{keyword}"
            )
        ],
        [
            InlineKeyboardButton("« Back", callback_data="admin_home")
        ]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )


# ─────────────────────────────────────
# 📂 FETCH RESULTS FROM SELECTED DB
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^admin_search_db#") & admin_filter)
async def admin_search_db(client, query: CallbackQuery):
    _, db_type, offset, keyword = query.data.split("#")
    offset = int(offset)

    files, next_offset, total = await admin_search_results(
        keyword=keyword,
        db_type=db_type,
        offset=offset,
        limit=MAX_BTN
    )

    if not files:
        return await query.answer("No more results", show_alert=True)

    text = (
        f"<b>📂 {db_type.upper()} Results</b>\n\n"
        f"🔎 Query : <code>{keyword}</code>\n"
        f"📁 Total : <code>{total}</code>\n\n"
    )

    buttons = []

    for file in files:
        text += f"• {file['file_name']}\n"

    # pagination
    if next_offset < total:
        buttons.append([
            InlineKeyboardButton(
                "➡️ Next",
                callback_data=f"admin_search_db#{db_type}#{next_offset}#{keyword}"
            )
        ])

    buttons.append([
        InlineKeyboardButton("« Back", callback_data="admin_search")
    ])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )

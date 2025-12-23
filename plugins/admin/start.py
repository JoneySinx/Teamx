# plugins/admin/start.py

from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from info import ADMINS
from utils import temp


@Client.on_message(filters.private & filters.command("start") & filters.user(ADMINS))
async def admin_start(client, message):
    """
    Admin-only /start handler
    Private chat only
    """

    # Save bot start time if not set
    if not temp.START_TIME:
        import time
        temp.START_TIME = time.time()

    user = message.from_user
    mention = user.mention if user else "Admin"

    text = (
        f"<b>👑 Admin Control Panel</b>\n\n"
        f"Welcome {mention} 👋\n\n"
        "Choose an option below 👇"
    )

    buttons = [
        [
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton("📥 Index", callback_data="admin_index"),
        ],
        [
            InlineKeyboardButton("🔍 Search", callback_data="admin_search"),
            InlineKeyboardButton("🧠 Databases", callback_data="admin_databases"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
        ]
    ]

    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )

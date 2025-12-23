# plugins/admin/start.py
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from info import ADMINS
from utils import temp, get_wish
from database.users_chats_db import db


# ─────────────────────────────────────
# 🔐 ADMIN-ONLY /start (PRIVATE CHAT)
# ─────────────────────────────────────
@Client.on_message(
    filters.command("start")
    & filters.private
    & filters.user(ADMINS)
)
async def admin_start(client, message):
    """
    Admin dashboard start
    Visible ONLY to ADMINS in private chat
    """

    # Save admin as user (optional but useful for stats)
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)

    wish = get_wish()

    text = (
        f"<b>👋 Hey {message.from_user.mention}, {wish}\n\n"
        f"⚙️ Admin AutoFilter Control Panel</b>\n\n"
        f"• Manage Indexing\n"
        f"• Search Database\n"
        f"• Broadcast\n"
        f"• Premium & Settings\n"
        f"• Database Stats\n"
    )

    buttons = [
        [
            InlineKeyboardButton("📥 Index", callback_data="admin_index"),
            InlineKeyboardButton("🔍 Search", callback_data="admin_search"),
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("👥 Groups", callback_data="admin_groups"),
        ],
        [
            InlineKeyboardButton("🧠 Databases", callback_data="admin_databases"),
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="close_data"),
        ],
    ]

    await message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )


# ─────────────────────────────────────
# 🚫 NON-ADMIN /start (PRIVATE CHAT)
# (Handled later in public_start.py)
# ─────────────────────────────────────
@Client.on_message(filters.command("start") & filters.private)
async def non_admin_start(client, message):
    """
    Non-admin private start
    Temporary placeholder until public_start.py
    """
    await message.reply_text(
        "👋 Hello!\n\n"
        "This bot is currently running in admin-only mode.\n"
        "Please add me to a group for group management features."
    )

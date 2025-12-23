import re
import time
import asyncio

from hydrogram import Client, filters, enums
from hydrogram.errors import FloodWait
from hydrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

from info import ADMINS, INDEX_EXTENSIONS
from utils import temp, get_readable_time
from database.ia_filterdb import save_file


# ─────────────────────────────────────
# 🔐 ADMIN FILTER
# ─────────────────────────────────────
async def admin_only(_, __, obj):
    return obj.from_user and obj.from_user.id in ADMINS

admin_filter = filters.create(admin_only)

lock = asyncio.Lock()


# ─────────────────────────────────────
# 📥 START INDEX COMMAND (ADMIN)
# ─────────────────────────────────────
@Client.on_message(filters.command("index") & filters.private & admin_filter)
async def admin_index_start(bot, message):
    if lock.locked():
        return await message.reply("⏳ Index already running. Please wait.")

    ask = await message.reply("📩 Forward last channel message or send channel message link.")
    msg = await bot.listen(message.chat.id, message.from_user.id)
    await ask.delete()

    # ── Extract message id & chat id ──
    if msg.text and msg.text.startswith("https://t.me"):
        try:
            parts = msg.text.split("/")
            last_msg_id = int(parts[-1])
            chat_id = parts[-2]
            if chat_id.isnumeric():
                chat_id = int("-100" + chat_id)
        except Exception:
            return await message.reply("❌ Invalid message link.")
    elif msg.forward_from_chat and msg.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = msg.forward_from_message_id
        chat_id = msg.forward_from_chat.username or msg.forward_from_chat.id
    else:
        return await message.reply("❌ Not a valid forwarded message or link.")

    try:
        chat = await bot.get_chat(chat_id)
    except Exception as e:
        return await message.reply(f"❌ Error: {e}")

    if chat.type != enums.ChatType.CHANNEL:
        return await message.reply("❌ I can index only channels.")

    ask_skip = await message.reply("⏩ Send skip message count (0 if none).")
    skip_msg = await bot.listen(message.chat.id, message.from_user.id)
    await ask_skip.delete()

    try:
        skip = int(skip_msg.text)
    except ValueError:
        return await message.reply("❌ Skip value must be a number.")

    # ── DB Selection Panel ──
    text = (
        "<b>📥 Select Database for Indexing</b>\n\n"
        f"📺 Channel : <code>{chat.title}</code>\n"
        f"📦 Last Message ID : <code>{last_msg_id}</code>\n"
        f"⏩ Skip : <code>{skip}</code>\n\n"
        "Choose where to index 👇"
    )

    buttons = [
        [
            InlineKeyboardButton(
                "🗂 Primary DB",
                callback_data=f"index_db#primary#{chat_id}#{last_msg_id}#{skip}"
            ),
            InlineKeyboardButton(
                "☁️ Cloud DB",
                callback_data=f"index_db#cloud#{chat_id}#{last_msg_id}#{skip}"
            ),
        ],
        [
            InlineKeyboardButton(
                "📦 Archive DB",
                callback_data=f"index_db#archive#{chat_id}#{last_msg_id}#{skip}"
            )
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="index_cancel")
        ]
    ]

    await message.reply(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )


# ─────────────────────────────────────
# ❌ CANCEL INDEX
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^index_cancel$") & admin_filter)
async def cancel_index(bot, query: CallbackQuery):
    temp.CANCEL = True
    await query.edit_message_text("⛔ Indexing cancelled.")


# ─────────────────────────────────────
# ▶️ CONFIRM DB & START INDEXING
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^index_db#") & admin_filter)
async def index_with_db(bot, query: CallbackQuery):
    _, db_type, chat_id, last_msg_id, skip = query.data.split("#")

    chat_id = int(chat_id)
    last_msg_id = int(last_msg_id)
    skip = int(skip)

    await query.edit_message_text(
        "<b>🚀 Indexing Started</b>\n\n"
        f"🗄 Database : <code>{db_type.upper()}</code>\n"
        "⏳ Please wait...",
        parse_mode=enums.ParseMode.HTML
    )

    await run_indexing(
        bot=bot,
        msg=query.message,
        chat_id=chat_id,
        last_msg_id=last_msg_id,
        skip=skip,
        db_type=db_type
    )


# ─────────────────────────────────────
# ⚙️ CORE INDEX LOGIC
# ─────────────────────────────────────
async def run_indexing(bot, msg, chat_id, last_msg_id, skip, db_type):
    start_time = time.time()

    total = duplicate = deleted = no_media = unsupported = errors = 0
    current = skip

    async with lock:
        try:
            async for message in bot.iter_messages(chat_id, last_msg_id, skip):
                if temp.CANCEL:
                    temp.CANCEL = False
                    break

                current += 1

                if message.empty:
                    deleted += 1
                    continue

                if not message.media:
                    no_media += 1
                    continue

                if message.media not in (
                    enums.MessageMediaType.VIDEO,
                    enums.MessageMediaType.DOCUMENT
                ):
                    unsupported += 1
                    continue

                media = getattr(message, message.media.value, None)
                if not media or not media.file_name:
                    unsupported += 1
                    continue

                if not str(media.file_name).lower().endswith(tuple(INDEX_EXTENSIONS)):
                    unsupported += 1
                    continue

                media.caption = message.caption
                status = await save_file(media, db_type=db_type)

                if status == "suc":
                    total += 1
                elif status == "dup":
                    duplicate += 1
                else:
                    errors += 1

                if current % 30 == 0:
                    await msg.edit(
                        "<b>📊 Indexing Progress</b>\n\n"
                        f"🗄 DB : <code>{db_type.upper()}</code>\n"
                        f"📥 Saved : <code>{total}</code>\n"
                        f"♻️ Duplicate : <code>{duplicate}</code>\n"
                        f"❌ Errors : <code>{errors}</code>\n"
                        f"⏳ Time : <code>{get_readable_time(time.time() - start_time)}</code>",
                        parse_mode=enums.ParseMode.HTML
                    )

        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            return await msg.reply(f"❌ Index failed: {e}")

    # ── Final Report ──
    await msg.edit(
        "<b>✅ Index Completed</b>\n\n"
        f"🗄 Database : <code>{db_type.upper()}</code>\n"
        f"📥 Total Saved : <code>{total}</code>\n"
        f"♻️ Duplicate : <code>{duplicate}</code>\n"
        f"🗑 Deleted : <code>{deleted}</code>\n"
        f"🚫 Unsupported : <code>{unsupported}</code>\n"
        f"❌ Errors : <code>{errors}</code>\n\n"
        f"⏱ Time Taken : <code>{get_readable_time(time.time() - start_time)}</code>",
        parse_mode=enums.ParseMode.HTML
    )

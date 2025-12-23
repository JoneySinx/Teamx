# plugins/admin/index.py

import asyncio
import time
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from hydrogram.errors import FloodWait

from info import ADMINS, INDEX_EXTENSIONS
from utils import temp, get_readable_time
from database.ia_filterdb import save_file


# ─────────────────────────────────────
# 🔐 ADMIN FILTER
# ─────────────────────────────────────
async def admin_only(_, __, query: CallbackQuery):
    return query.from_user and query.from_user.id in ADMINS

admin_filter = filters.create(admin_only)

lock = asyncio.Lock()


# ─────────────────────────────────────
# ▶️ START INDEXING (ENTRY)
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^admin_index_start$") & admin_filter)
async def admin_index_start(client, query: CallbackQuery):
    text = (
        "<b>➕ Start Indexing</b>\n\n"
        "📌 Forward last message from channel\n"
        "OR send channel message link\n\n"
        "<i>Only channels are supported</i>"
    )

    await query.edit_message_text(
        text,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("« Back", callback_data="admin_index")]
        ])
    )

    # Wait for admin input
    try:
        msg = await client.listen(
            chat_id=query.from_user.id,
            user_id=query.from_user.id,
            timeout=120
        )
    except asyncio.TimeoutError:
        return await query.message.reply("⏳ Timeout. Try again.")

    # ── Extract channel & message id
    chat_id = None
    last_msg_id = None

    if msg.text and msg.text.startswith("https://t.me"):
        try:
            parts = msg.text.split("/")
            last_msg_id = int(parts[-1])
            raw_chat = parts[-2]
            chat_id = int("-100" + raw_chat) if raw_chat.isnumeric() else raw_chat
        except Exception:
            return await query.message.reply("❌ Invalid message link.")

    elif msg.forward_from_chat and msg.forward_from_chat.type == enums.ChatType.CHANNEL:
        chat_id = msg.forward_from_chat.id
        last_msg_id = msg.forward_from_message_id

    else:
        return await query.message.reply("❌ Invalid input. Send channel link or forwarded message.")

    # Ask skip value
    ask = await query.message.reply("🔢 Send skip count (0 recommended)")
    try:
        skip_msg = await client.listen(
            chat_id=query.from_user.id,
            user_id=query.from_user.id,
            timeout=60
        )
        skip = int(skip_msg.text)
    except Exception:
        return await ask.edit("❌ Invalid skip number.")

    buttons = [
        [
            InlineKeyboardButton(
                "✅ Confirm Index",
                callback_data=f"admin_index_confirm#{chat_id}#{last_msg_id}#{skip}"
            )
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="admin_index")
        ]
    ]

    await ask.edit(
        f"<b>Confirm Indexing?</b>\n\n"
        f"Channel: <code>{chat_id}</code>\n"
        f"Last Msg ID: <code>{last_msg_id}</code>\n"
        f"Skip: <code>{skip}</code>",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ─────────────────────────────────────
# ✅ CONFIRM & RUN INDEXING
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^admin_index_confirm") & admin_filter)
async def admin_index_confirm(client, query: CallbackQuery):
    if lock.locked():
        return await query.answer("⚠️ Indexing already running", show_alert=True)

    _, chat_id, last_msg_id, skip = query.data.split("#")

    try:
        chat_id = int(chat_id)
        last_msg_id = int(last_msg_id)
        skip = int(skip)
    except ValueError:
        return await query.answer("❌ Invalid data", show_alert=True)

    msg = await query.edit_message_text("⏳ Indexing started...")

    asyncio.create_task(
        run_indexing(client, msg, chat_id, last_msg_id, skip)
    )


# ─────────────────────────────────────
# ⏹ CANCEL INDEXING
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^admin_index_cancel$") & admin_filter)
async def admin_index_cancel(client, query: CallbackQuery):
    temp.CANCEL = True
    await query.edit_message_text("⛔ Trying to cancel indexing...")


# ─────────────────────────────────────
# ⚙️ CORE INDEX LOOP
# ─────────────────────────────────────
async def run_indexing(client, msg, chat_id, last_msg_id, skip):
    async with lock:
        start_time = time.time()

        total = saved = dup = deleted = unsupported = errors = 0
        temp.CANCEL = False

        try:
            async for message in client.iter_messages(chat_id, last_msg_id, skip):
                if temp.CANCEL:
                    break

                total += 1

                if not message.media:
                    continue

                if message.media not in [
                    enums.MessageMediaType.DOCUMENT,
                    enums.MessageMediaType.VIDEO
                ]:
                    unsupported += 1
                    continue

                media = getattr(message, message.media.value, None)
                if not media or not media.file_name:
                    continue

                if not media.file_name.lower().endswith(tuple(INDEX_EXTENSIONS)):
                    unsupported += 1
                    continue

                media.caption = message.caption
                status = await save_file(media)

                if status == "suc":
                    saved += 1
                elif status == "dup":
                    dup += 1
                else:
                    errors += 1

                if total % 25 == 0:
                    await msg.edit_text(
                        f"<b>📥 Indexing...</b>\n\n"
                        f"Processed: <code>{total}</code>\n"
                        f"Saved: <code>{saved}</code>\n"
                        f"Duplicates: <code>{dup}</code>\n"
                        f"Unsupported: <code>{unsupported}</code>\n"
                        f"Errors: <code>{errors}</code>",
                        parse_mode=enums.ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("⏹ Cancel", callback_data="admin_index_cancel")]
                        ])
                    )

        except FloodWait as e:
            await asyncio.sleep(e.value)

        uptime = get_readable_time(time.time() - start_time)

        await msg.edit_text(
            "<b>✅ Indexing Finished</b>\n\n"
            f"Total Processed: <code>{total}</code>\n"
            f"Saved: <code>{saved}</code>\n"
            f"Duplicates: <code>{dup}</code>\n"
            f"Unsupported: <code>{unsupported}</code>\n"
            f"Errors: <code>{errors}</code>\n\n"
            f"⏱ Time Taken: <code>{uptime}</code>",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Back", callback_data="admin_index")]
            ])
        )

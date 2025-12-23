# plugins/admin/filters.py

from hydrogram import filters
from hydrogram.types import Message, CallbackQuery
from info import ADMINS
from utils import temp


# ─────────────────────────────────────
# 🔐 ADMIN USER FILTER
# ─────────────────────────────────────
async def is_admin(_, __, obj):
    """
    Works for both Message & CallbackQuery
    """
    user = None

    if isinstance(obj, Message):
        user = obj.from_user
    elif isinstance(obj, CallbackQuery):
        user = obj.from_user

    return bool(user and user.id in ADMINS)


admin_filter = filters.create(is_admin)


# ─────────────────────────────────────
# 🚫 BANNED USER FILTER (ADMIN SIDE SAFE)
# ─────────────────────────────────────
async def is_banned(_, __, obj):
    user = None

    if isinstance(obj, Message):
        user = obj.from_user
    elif isinstance(obj, CallbackQuery):
        user = obj.from_user

    return bool(user and user.id in temp.BANNED_USERS)


banned_filter = filters.create(is_banned)


# ─────────────────────────────────────
# 🧠 NO-OP CALLBACK (PAGE COUNTER ETC.)
# ─────────────────────────────────────
@filters.create
async def noop_callback(_, __, query: CallbackQuery):
    """
    Used for buttons like:
    📄 1 / 10
    """
    return False

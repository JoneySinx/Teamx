# plugins/admin/pagination.py

from hydrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_pagination(
    *,
    page: int,
    total_pages: int,
    callback_prefix: str,
    extra_data: str = ""
):
    """
    Generic pagination builder for admin panels

    Args:
        page (int): current page number (1-based)
        total_pages (int): total pages
        callback_prefix (str): callback prefix (e.g. "admin_search")
        extra_data (str): extra callback data (query/db_type/etc)

    Returns:
        InlineKeyboardMarkup | None
    """

    if total_pages <= 1:
        return None

    buttons = []

    nav_buttons = []

    # ◀ Prev
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                "◀ Prev",
                callback_data=f"{callback_prefix}#{page-1}#{extra_data}"
            )
        )

    # Page indicator
    nav_buttons.append(
        InlineKeyboardButton(
            f"📄 {page}/{total_pages}",
            callback_data="noop"
        )
    )

    # Next ▶
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                "Next ▶",
                callback_data=f"{callback_prefix}#{page+1}#{extra_data}"
            )
        )

    buttons.append(nav_buttons)

    # Back button (standard admin UX)
    buttons.append([
        InlineKeyboardButton("« Back", callback_data="admin_home")
    ])

    return InlineKeyboardMarkup(buttons)

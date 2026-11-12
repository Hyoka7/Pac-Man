"""Shared calculations for positioning rendered content."""


def centered_start(area_size: int, content_size: int) -> int:
    """Return the start coordinate that centers content within an area.

    Args:
        area_size: Size of the containing area.
        content_size: Size of the content to center.

    Returns:
        The start coordinate; negative when the content is larger.
    """
    return (area_size - content_size) // 2

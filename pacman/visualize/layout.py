"""Shared calculations for positioning rendered content."""


def centered_start(area_size: int, content_size: int) -> int:
    """Return the start coordinate that centers content within an area."""
    return (area_size - content_size) // 2

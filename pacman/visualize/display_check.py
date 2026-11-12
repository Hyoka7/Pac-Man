"""Check the X display before MLX, which crashes when none is reachable."""

import ctypes
import ctypes.util
import os


def ensure_display_available() -> None:
    """Raise RuntimeError unless an X server accepts an XCB connection."""
    display = os.environ.get("DISPLAY")
    if not display:
        raise RuntimeError("no graphical display (DISPLAY is not set)")
    library = ctypes.util.find_library("xcb")
    if library is None:
        return
    try:
        xcb = ctypes.CDLL(library)
    except OSError:
        return
    xcb.xcb_connect.restype = ctypes.c_void_p
    xcb.xcb_connect.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
    xcb.xcb_connection_has_error.restype = ctypes.c_int
    xcb.xcb_connection_has_error.argtypes = [ctypes.c_void_p]
    xcb.xcb_disconnect.restype = None
    xcb.xcb_disconnect.argtypes = [ctypes.c_void_p]
    connection = xcb.xcb_connect(None, None)
    try:
        failed = connection is None or xcb.xcb_connection_has_error(connection)
    finally:
        if connection is not None:
            xcb.xcb_disconnect(connection)
    if failed:
        raise RuntimeError(f"cannot connect to display {display!r}")

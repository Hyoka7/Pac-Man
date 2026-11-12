"""Type stubs for the bundled MLX wrapper (mlx 2.2), which ships none.

Pointers are ctypes ``c_void_p`` values, which Python exposes as ``int``
or ``None`` (NULL). Methods mirror ``mlx/mlx.py``; the package itself is
used as-is.
"""

from collections.abc import Callable
from typing import Any

Pointer = int | None


class Mlx:
    SYNC_IMAGE_WRITABLE: int
    SYNC_WIN_FLUSH: int
    SYNC_WIN_COMPLETED: int

    def __init__(self) -> None: ...

    def mlx_init(self) -> Pointer: ...

    def mlx_release(self, mlx_ptr: Pointer) -> int: ...

    def mlx_new_window(
        self, mlx_ptr: Pointer, width: int, height: int, title: str
    ) -> Pointer: ...

    def mlx_clear_window(self, mlx_ptr: Pointer, win_ptr: Pointer) -> int: ...

    def mlx_pixel_put(
        self, mlx_ptr: Pointer, win_ptr: Pointer, x: int, y: int, color: int
    ) -> int: ...

    def mlx_destroy_window(
        self, mlx_ptr: Pointer, win_ptr: Pointer
    ) -> int: ...

    def mlx_new_image(
        self, mlx_ptr: Pointer, width: int, height: int
    ) -> Pointer: ...

    def mlx_get_data_addr(
        self, img_ptr: Pointer
    ) -> tuple[memoryview, int, int, int]: ...

    def mlx_put_image_to_window(
        self,
        mlx_ptr: Pointer,
        win_ptr: Pointer,
        img_ptr: Pointer,
        x: int,
        y: int,
    ) -> int: ...

    def mlx_destroy_image(self, mlx_ptr: Pointer, img_ptr: Pointer) -> int: ...

    def mlx_loop(self, mlx_ptr: Pointer) -> int: ...

    def mlx_loop_exit(self, mlx_ptr: Pointer) -> int: ...

    def mlx_mouse_hook(
        self,
        win_ptr: Pointer,
        callback: Callable[[int, int, int, Any], object] | None,
        param: Any,
    ) -> int: ...

    def mlx_key_hook(
        self,
        win_ptr: Pointer,
        callback: Callable[[int, Any], object] | None,
        param: Any,
    ) -> int: ...

    def mlx_expose_hook(
        self,
        win_ptr: Pointer,
        callback: Callable[[Any], object] | None,
        param: Any,
    ) -> int: ...

    def mlx_loop_hook(
        self,
        mlx_ptr: Pointer,
        callback: Callable[[Any], object] | None,
        param: Any,
    ) -> int: ...

    # The callback arity depends on x_event (key, mouse, motion or other).
    def mlx_hook(
        self,
        win_ptr: Pointer,
        x_event: int,
        x_mask: int,
        callback: Callable[..., object] | None,
        param: Any,
    ) -> int: ...

    def mlx_string_put(
        self,
        mlx_ptr: Pointer,
        win_ptr: Pointer,
        x: int,
        y: int,
        color: int,
        string: str,
    ) -> int: ...

    def mlx_xpm_file_to_image(
        self, mlx_ptr: Pointer, filename: str
    ) -> tuple[Pointer, int, int]: ...

    def mlx_png_file_to_image(
        self, mlx_ptr: Pointer, filename: str
    ) -> tuple[Pointer, int, int]: ...

    def mlx_mouse_hide(self, mlx_ptr: Pointer) -> int: ...

    def mlx_mouse_show(self, mlx_ptr: Pointer) -> int: ...

    def mlx_mouse_move(self, mlx_ptr: Pointer, x: int, y: int) -> int: ...

    def mlx_mouse_get_pos(self, mlx_ptr: Pointer) -> tuple[int, int, int]: ...

    def mlx_do_key_autorepeatoff(self, mlx_ptr: Pointer) -> int: ...

    def mlx_do_key_autorepeaton(self, mlx_ptr: Pointer) -> int: ...

    def mlx_get_screen_size(
        self, mlx_ptr: Pointer
    ) -> tuple[int, int, int]: ...

    def mlx_do_sync(self, mlx_ptr: Pointer) -> int: ...

    def mlx_sync(
        self, mlx_ptr: Pointer, cmd: int, img_or_win_ptr: Pointer
    ) -> int: ...

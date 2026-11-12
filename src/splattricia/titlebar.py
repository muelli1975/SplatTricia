"""Shared Stereo-Tools policy for native title bars."""
from __future__ import annotations

import ctypes
from functools import lru_cache
import sys

CAPTION_RGB = (0x20, 0x20, 0x20)
CAPTION_TEXT_RGB = (0xF2, 0xF2, 0xF2)


@lru_cache(maxsize=1)
def _windows_functions():
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", winmode=0x00000800)  # System32
    dwm = ctypes.WinDLL("dwmapi", winmode=0x00000800)
    ancestor = user32.GetAncestor
    ancestor.argtypes = (wintypes.HWND, wintypes.UINT)
    ancestor.restype = wintypes.HWND
    set_attribute = dwm.DwmSetWindowAttribute
    set_attribute.argtypes = (wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD)
    set_attribute.restype = ctypes.c_long
    redraw = user32.RedrawWindow
    redraw.argtypes = (wintypes.HWND, ctypes.c_void_p, wintypes.HRGN, wintypes.UINT)
    redraw.restype = wintypes.BOOL
    return ancestor, set_attribute, redraw


def _colorref(rgb):
    red, green, blue = rgb
    return red | (green << 8) | (blue << 16)


def _apply_windows_titlebar(window_id):
    from ctypes import wintypes

    try:
        ancestor, set_attribute, redraw = _windows_functions()
        hwnd = ancestor(window_id, 2)  # GA_ROOT also resolves Tk's child HWND.
        if not hwnd:
            return False

        def set_value(attribute, value):
            return set_attribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)) == 0

        immersive = wintypes.BOOL(1)
        dark = set_value(20, immersive) or set_value(19, immersive)
        # Explicit caption and text colors are supported on Windows 11.
        caption = set_value(35, wintypes.DWORD(_colorref(CAPTION_RGB)))
        text = set_value(36, wintypes.DWORD(_colorref(CAPTION_TEXT_RGB)))
        applied = dark or caption or text
        if applied:
            # Repaint the frame in place, without hiding or activating it.
            redraw(hwnd, None, None, 0x0001 | 0x0400 | 0x0100)
        return applied
    except (AttributeError, OSError):
        return False


def _apply_macos_appearance():
    """Select Dark Aqua for this AppKit application, on the GUI thread."""
    try:
        objc = ctypes.CDLL("/usr/lib/libobjc.A.dylib")
        pointer = ctypes.c_void_p
        objc.objc_getClass.argtypes = (ctypes.c_char_p,)
        objc.objc_getClass.restype = pointer
        objc.sel_registerName.argtypes = (ctypes.c_char_p,)
        objc.sel_registerName.restype = pointer
        send = ctypes.CFUNCTYPE(pointer, pointer, pointer)(("objc_msgSend", objc))
        send_string = ctypes.CFUNCTYPE(pointer, pointer, pointer, ctypes.c_char_p)(("objc_msgSend", objc))
        send_object = ctypes.CFUNCTYPE(pointer, pointer, pointer, pointer)(("objc_msgSend", objc))
        set_object = ctypes.CFUNCTYPE(None, pointer, pointer, pointer)(("objc_msgSend", objc))
        get_class, selector = objc.objc_getClass, objc.sel_registerName
        application = send(get_class(b"NSApplication"), selector(b"sharedApplication"))
        name = send_string(get_class(b"NSString"), selector(b"stringWithUTF8String:"), b"NSAppearanceNameDarkAqua")
        appearance = send_object(get_class(b"NSAppearance"), selector(b"appearanceNamed:"), name)
        if application and appearance:
            set_object(application, selector(b"setAppearance:"), appearance)
    except (AttributeError, OSError):
        pass


def restyle_tk_titlebar(window):
    """Apply the shared colors to a Tk window whose native frame may be new."""
    if sys.platform != "win32":
        return False
    from tkinter import TclError

    try:
        if window.winfo_exists() and not window.overrideredirect() and not window.attributes("-fullscreen"):
            return _apply_windows_titlebar(window.winfo_id())
    except TclError:
        pass
    return False


def install_tk_titlebars(root):
    if sys.platform == "darwin":
        _apply_macos_appearance()
    elif sys.platform == "win32":
        from tkinter import Tk, Toplevel

        def mapped(event):
            window = event.widget
            if isinstance(window, (Tk, Toplevel)):
                restyle_tk_titlebar(window)
                root.after(100, restyle_tk_titlebar, window)

        root.bind_all("<Map>", mapped, add="+")
        restyle_tk_titlebar(root)


def install_qt_titlebars(application):
    if sys.platform == "darwin":
        _apply_macos_appearance()
    elif sys.platform == "win32":
        from PySide6.QtCore import QEvent, QObject, Qt
        from PySide6.QtWidgets import QWidget

        class TitleBars(QObject):
            def eventFilter(self, widget, event):
                if (event.type() in (QEvent.Type.Show, QEvent.Type.WindowStateChange)
                        and isinstance(widget, QWidget) and widget.isWindow()
                        and widget.windowType() in (Qt.WindowType.Window, Qt.WindowType.Dialog,
                                                    Qt.WindowType.Tool, Qt.WindowType.Sheet)
                        and not widget.isFullScreen() and widget.windowHandle() is not None):
                    _apply_windows_titlebar(int(widget.winId()))
                return False

        event_filter = TitleBars(application)
        application.installEventFilter(event_filter)
        application._stereo_tools_titlebars = event_filter

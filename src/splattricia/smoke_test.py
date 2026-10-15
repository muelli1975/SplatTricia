"""Developer checks for the assembled portable application, without model weights.

This validates GUI layout, encoders and camera/export integration. It is not a
claim that SHARP inference or CUDA rendering has been run on a build server.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import tempfile
import time
import traceback

import customtkinter as ctk
import numpy as np
from PIL import Image

from . import __version__
from .depth_export import save_depth_png
from .export_options import WiggleOptions
from .settings import save_settings, load_settings
from .wiggle_export import export_wiggle, ffmpeg_path


def _settle(widget):
    for _ in range(15):
        widget.update()
        time.sleep(0.02)


def _check_children(parent):
    for child in parent.winfo_children():
        if child.__class__.__name__ == 'CTkButton' and child._text_label is not None:
            assert child._text_label.winfo_reqwidth() <= child._text_label.winfo_width(), ('button text clipped',str(child))
        if child.__class__.__name__.startswith('CTk'):
            assert child.winfo_x() >= -2 and child.winfo_y() >= -2, ('control origin', str(child))
            assert child.winfo_x() + child.winfo_width() <= parent.winfo_width() + 2, ('control width', str(child), child.winfo_x(), child.winfo_width(), parent.winfo_width())
            assert child.winfo_y() + child.winfo_height() <= parent.winfo_height() + 2, ('control height', str(child), child.winfo_y(), child.winfo_height(), parent.winfo_height())
        _check_children(child)


def _layout_geometry(parent):
    result = {}
    for child in parent.winfo_children():
        if child.__class__.__name__.startswith('CTk'):
            result[str(child)] = (child.winfo_x(),child.winfo_y(),
                                  child.winfo_width(),child.winfo_height())
        result.update(_layout_geometry(child))
    return result


def _assert_layout_unchanged(app, expected):
    _settle(app)
    actual = _layout_geometry(app)
    changed = [(key,value,actual.get(key)) for key,value in expected.items()
               if actual.get(key) != value]
    assert not changed, ('layout moved during state change',changed)


def _screenshot(widget, path):
    import sys
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        user = ctypes.windll.user32
        user.GetParent.restype = wintypes.HWND
        user.GetParent.argtypes = [wintypes.HWND]
        hwnd = user.GetParent(widget.winfo_id()) or widget.winfo_id()
        gdi = ctypes.windll.gdi32
        user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
        user.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
        gdi.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
        gdi.DeleteObject.argtypes = [wintypes.HGDIOBJ]
        gdi.DeleteDC.argtypes = [wintypes.HDC]
        user.GetWindowDC.restype = wintypes.HDC
        user.GetWindowDC.argtypes = [wintypes.HWND]
        gdi.CreateCompatibleDC.restype = wintypes.HDC
        gdi.CreateCompatibleDC.argtypes = [wintypes.HDC]
        gdi.CreateCompatibleBitmap.restype = wintypes.HBITMAP
        gdi.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
        gdi.SelectObject.restype = wintypes.HGDIOBJ
        gdi.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
        class Header(ctypes.Structure):
            _fields_ = [('size',wintypes.DWORD),('width',wintypes.LONG),('height',wintypes.LONG),
                        ('planes',wintypes.WORD),('bits',wintypes.WORD),('compression',wintypes.DWORD),
                        ('sizeimage',wintypes.DWORD),('x',wintypes.LONG),('y',wintypes.LONG),
                        ('used',wintypes.DWORD),('important',wintypes.DWORD)]
        rectangle = wintypes.RECT()
        user.GetWindowRect(hwnd,ctypes.byref(rectangle))
        width,height=rectangle.right-rectangle.left,rectangle.bottom-rectangle.top
        hdc=user.GetWindowDC(hwnd)
        memory=gdi.CreateCompatibleDC(hdc)
        bitmap=gdi.CreateCompatibleBitmap(hdc,width,height)
        previous=gdi.SelectObject(memory,bitmap)
        try:
            assert user.PrintWindow(hwnd,memory,2), 'PrintWindow failed'
            header=Header(ctypes.sizeof(Header),width,-height,1,32,0,width*height*4,0,0,0,0)
            pixels=ctypes.create_string_buffer(width*height*4)
            gdi.SelectObject(memory,previous)
            assert gdi.GetDIBits(memory,bitmap,0,height,pixels,ctypes.byref(header),0)==height
            Image.frombytes('RGB',(width,height),pixels.raw,'raw','BGRX').save(path)
        finally:
            gdi.SelectObject(memory,previous)
            gdi.DeleteObject(bitmap)
            gdi.DeleteDC(memory)
            user.ReleaseDC(hwnd,hdc)
    else:
        from PIL import ImageGrab
        x, y = widget.winfo_rootx(), widget.winfo_rooty()
        ImageGrab.grab(bbox=(x, y, x+widget.winfo_width(), y+widget.winfo_height())).save(path)


def _main_screenshot(app, path):
    # Hosted Windows desktops can be fixed at 1024x768. Tk does not paint the
    # off-screen canvas area, even for PrintWindow. Capture a temporarily scaled
    # view; all layout checks still run at their requested 100/125/150% scale.
    scale = min(1.0, (app.winfo_screenwidth()-24)/app.winfo_width(),
                (app.winfo_screenheight()-90)/app.winfo_height())
    try:
        ctk.set_widget_scaling(scale)
        ctk.set_window_scaling(scale)
        app.geometry('+0+0')
        _settle(app)
        _check_children(app)
        _screenshot(app,path)
    finally:
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)
        _settle(app)


def run(output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir/'failure.txt').unlink(missing_ok=True)
    (output_dir/'report.json').unlink(missing_ok=True)
    try:
        report = _run_checks(output_dir)
        (output_dir/'report.json').write_text(json.dumps(report, indent=2),encoding='utf-8')
        return 0
    except BaseException:
        (output_dir/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8')
        return 1


def _run_checks(output_dir):
    from .gui import SplatTriciaApp
    from .wiggle_dialog import WiggleDialog
    from .theme import BG_MAIN, TEXT_DISABLED
    import splattricia.gui as gui
    layouts = []
    for locale in ('de', 'en'):
        for scale in (1.0, 1.25, 1.5):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                save_settings(root/'settings.json', {'language':locale})
                ctk.set_widget_scaling(scale)
                ctk.set_window_scaling(scale)
                app = SplatTriciaApp(root)
                try:
                    _settle(app)
                    assert app.wiggle_button.cget('state') == 'disabled'
                    _check_children(app)
                    initial_geometry = _layout_geometry(app)
                    app.save_wiggle_check.toggle()
                    assert app.wiggle_button.cget('state') == 'normal'
                    _assert_layout_unchanged(app,initial_geometry)
                    app.save_wiggle_check.toggle()
                    _assert_layout_unchanged(app,initial_geometry)
                    app.save_wiggle_check.toggle()
                    _assert_layout_unchanged(app,initial_geometry)
                    if scale == 1.0:
                        _main_screenshot(app, output_dir/f'gui-{locale}.png')
                    def apply(options):
                        app.wiggle_options = options
                        app._save_paths()
                    dialog = WiggleDialog(app, app.wiggle_options, apply)
                    try:
                        _settle(app)
                        assert dialog.cget('fg_color') == BG_MAIN
                        _check_children(dialog)
                        assert dialog.size_menu.cget('values') == ['720','1080','2160']
                        dialog.size_menu.set('720')
                        if scale == 1.0:
                            _screenshot(dialog, output_dir/f'wiggle-{locale}.png')
                        dialog.fps_menu.set('60')
                        dialog._format_changed('GIF')
                        assert dialog.fps_menu.cget('values') == ['10','15','20','25']
                        assert dialog.fps_menu.get() == '15'
                        dialog.fps_menu.set('25')
                        dialog.size_menu.set('640')
                        dialog._save()
                    finally:
                        if dialog.winfo_exists():
                            dialog.destroy()
                    _settle(app)
                    saved = WiggleOptions.from_settings(load_settings(root/'settings.json')['wiggle'])
                    assert saved.format == 'gif' and saved.gif_fps == 25 and saved.video_fps == 60
                    assert saved.video_height == 720
                    # Exercise the actual Start callback without SHARP/model
                    # execution. Placeholders live only in this disposable root.
                    (root/'models').mkdir()
                    (root/'models/sharp_2572gikvuh.pt').write_bytes(b'GUI test placeholder')
                    (root/'input.png').write_bytes(b'GUI test placeholder')
                    app.input_file.set(str(root/'input.png'))
                    app._processing_worker = lambda *args: None
                    before_start = _layout_geometry(app)
                    app.start_button.invoke()
                    assert app.is_running
                    _assert_layout_unchanged(app,before_start)
                    app.status_text.set('Processing / ' + 'long_filename_' * 30 + '.jpg')
                    _assert_layout_unchanged(app,before_start)
                    assert app.save_wiggle_check.cget('state') == 'disabled'
                    assert app.wiggle_button.cget('state') == 'disabled'
                    app.is_running = False
                    app._set_processing_controls(False)
                    _assert_layout_unchanged(app,before_start)
                    assert app.wiggle_button.cget('state') == 'normal'
                    # Existing slider values and mutual locks retain their defaults.
                    assert app.deviation.get() == 20 and app.window_position.get() == 100
                    assert app.window_backshift_slider.cget('state') == 'normal'
                    assert not app.error_log_lines, app.error_log_lines
                    layouts.append({'locale':locale,'scale':scale,'width':app.winfo_width(),'height':app.winfo_height()})
                    app.geometry('1200x880')
                    _settle(app)
                    _check_children(app)
                finally:
                    app.destroy()
    ctk.set_widget_scaling(1.0)
    ctk.set_window_scaling(1.0)
    with tempfile.TemporaryDirectory() as folder:
        work = Path(folder)
        def view(weight):
            rgb = np.zeros((47,64,3),dtype=np.uint8)
            rgb[...,1] = np.arange(64,dtype=np.uint8)*4
            rgb[:,round(weight*50):round(weight*50)+10,0] = 255
            return rgb
        for fps in (30,60):
            options = WiggleOptions(video_fps=fps,cycle_seconds=.5)
            path = work/f'video-{fps}.mp4'
            export_wiggle(view,(64,47),options,path,work/'_temp')
            decoded = subprocess.run([ffmpeg_path(),'-hide_banner','-loglevel','error','-i',str(path),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            assert len(decoded.stdout) == options.frame_count*5*64*48*3
        for fps in (10,15,20,25):
            options = WiggleOptions(format='gif',gif_fps=fps,cycle_seconds=1)
            path = work/f'animation-{fps}.gif'
            export_wiggle(view,(64,47),options,path,work/'_temp')
            with Image.open(path) as image:
                assert image.info['loop']==0
                duration=0
                for frame_index in range(image.n_frames):
                    image.seek(frame_index)
                    duration+=image.info['duration']
                assert duration==1000
        export_wiggle(view,(64,47),WiggleOptions(format='png',cycle_seconds=1),work/'frames',work/'_temp')
        assert len(list((work/'frames').glob('*.png'))) == 30
        path = work/'depth.png'
        save_depth_png(np.array([[1.,2.,4.]]),np.ones((1,3)),path)
        with Image.open(path) as image:
            assert np.asarray(image).tolist()==[[65535,21845,0]]
    return {'version':__version__,'application_code':str(Path(gui.__file__).resolve()),
            'gui_layouts':layouts,'layout_transitions':'wiggle on/off, Start, busy, long status, idle',
            'encoder_tests':'MP4 30/60, GIF 10/15/20/25, PNG sequence, 16-bit depth PNG',
            'cuda_inference_tested':False}

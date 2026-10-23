from __future__ import annotations

from dataclasses import replace
import customtkinter as ctk

from .export_options import WiggleOptions
from .theme import (BG_MAIN, INPUT_BG, PANEL, PANEL_HOVER, BORDER, TEXT,
                    TEXT_MUTED, TEXT_DISABLED, BUTTON_BG, BUTTON_HOVER,
                    FONT_FAMILY, RADIUS_CONTROL)


class WiggleDialog(ctk.CTkToplevel):
    """A modal, themed editor. Only Apply persists the complete draft."""
    def __init__(self, owner, options: WiggleOptions, apply) -> None:
        super().__init__(owner)
        self.tr = owner.tr
        self.options = options
        self.apply = apply
        self.title(self.tr("wiggle.title"))
        self.geometry("480x405")
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)
        self.transient(owner)
        self.grid_columnconfigure(1, weight=1)
        self.formats = {"mp4": "MP4", "gif": "GIF", "avif": "AVIF", "png": self.tr("wiggle.png_sequence")}
        self.labels = []
        for row, key in enumerate(("wiggle.format", "wiggle.size_height", "wiggle.fps", "wiggle.duration", "wiggle.cycles")):
            label = ctk.CTkLabel(self, text=self.tr(key), text_color=TEXT,
                                 font=ctk.CTkFont(family=FONT_FAMILY, size=13))
            label.grid(row=row, column=0, sticky="w", padx=(20, 14), pady=(20 if row == 0 else 8, 0))
            self.labels.append(label)
        style = dict(fg_color=PANEL, button_color=PANEL_HOVER, button_hover_color=BORDER,
                     dropdown_fg_color=INPUT_BG, dropdown_hover_color=PANEL_HOVER,
                     text_color=TEXT, dropdown_text_color=TEXT, text_color_disabled=TEXT_DISABLED,
                     corner_radius=RADIUS_CONTROL)
        self.format_menu = ctk.CTkOptionMenu(self, values=list(self.formats.values()),
                                            command=self._format_changed, **style)
        self.size_menu = ctk.CTkOptionMenu(self, values=[], **style)
        self.fps_menu = ctk.CTkOptionMenu(self, values=[], **style)
        self.duration = ctk.CTkEntry(self, fg_color=INPUT_BG, border_color=BORDER, text_color=TEXT)
        self.duration.insert(0, f"{options.cycle_seconds:g}")
        self.cycles = ctk.CTkEntry(self, fg_color=INPUT_BG, border_color=BORDER, text_color=TEXT)
        self.cycles.insert(0, str(options.video_cycles))
        for row, widget in enumerate((self.format_menu, self.size_menu, self.fps_menu, self.duration, self.cycles)):
            widget.grid(row=row, column=1, sticky="ew", padx=(0, 20), pady=(20 if row == 0 else 8, 0))
        self.hint = ctk.CTkLabel(self, text="", text_color=TEXT_MUTED, wraplength=440, justify="left", anchor="w")
        self.hint.grid(row=5, column=0, columnspan=2, sticky="ew", padx=20, pady=(14, 0))
        self.error = ctk.CTkLabel(self, text="", text_color=TEXT, wraplength=440, justify="left")
        self.error.grid(row=6, column=0, columnspan=2, sticky="ew", padx=20, pady=(4, 0))
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=7, column=0, columnspan=2, sticky="e", padx=20, pady=16)
        for col, key, command in [(0, "wiggle.cancel", self.destroy), (1, "wiggle.apply", self._save)]:
            button = ctk.CTkButton(buttons, text=self.tr(key), command=command, width=110,
                                   fg_color=BUTTON_BG, hover_color=BUTTON_HOVER, text_color=TEXT,
                                   border_width=1, border_color=BORDER, corner_radius=RADIUS_CONTROL)
            button.grid(row=0, column=col, padx=(8, 0))
        self.format_menu.set(self.formats[options.format])
        self._refresh()
        self.after(100, self._activate)

    def _activate(self):
        if self.winfo_exists():
            owner = self.master
            x = owner.winfo_rootx() + max(0, (owner.winfo_width() - self.winfo_width()) // 2)
            y = owner.winfo_rooty() + max(0, (owner.winfo_height() - self.winfo_height()) // 2)
            self.geometry(f"+{x}+{y}")
            self.grab_set()
            self.focus_set()

    def _capture(self):
        fmt = self.options.format
        updates = {f"{fmt if fmt != 'mp4' else 'video'}_fps": int(self.fps_menu.get())}
        updates[{"mp4": "video_height", "gif": "gif_long_side", "png": "png_height", "avif": "avif_height"}[fmt]] = int(self.size_menu.get())
        self.options = replace(self.options, **updates)

    def _format_changed(self, choice):
        self._capture()
        self.options = replace(self.options, format=next(key for key, text in self.formats.items() if text == choice))
        self._refresh()

    def _refresh(self):
        is_mp4 = self.options.format == "mp4"
        self.cycles.configure(state="normal" if is_mp4 else "disabled",
                              text_color=TEXT if is_mp4 else TEXT_DISABLED)
        self.labels[4].configure(text_color=TEXT if is_mp4 else TEXT_DISABLED)
        is_gif = self.options.format == "gif"
        self.labels[1].configure(text=self.tr("wiggle.size_long" if is_gif else "wiggle.size_height"))
        sizes = (["640", "800", "1024"] if is_gif else
                 ["720", "1080", "2160"] if self.options.format in {"mp4", "avif"} else ["1080", "2160"])
        self.size_menu.configure(values=sizes)
        self.size_menu.set(str({"mp4": self.options.video_height, "gif": self.options.gif_long_side,
                                "png": self.options.png_height,
                                "avif": self.options.avif_height}[self.options.format]))
        self.fps_menu.configure(values=["10", "15", "20", "25"] if is_gif else ["30", "60"])
        self.fps_menu.set(str(self.options.fps))
        self.hint.configure(text=self.tr("wiggle.hint_" + self.options.format))

    def _save(self):
        try:
            cycles = int(self.cycles.get().strip())
            if cycles < 1:
                raise ValueError
        except ValueError:
            self.error.configure(text=self.tr("wiggle.invalid_cycles"))
            return
        try:
            self._capture()
            draft = replace(self.options, cycle_seconds=float(self.duration.get().strip().replace(",", ".")),
                            video_cycles=cycles)
            draft.validate()
        except (ValueError, TypeError):
            self.error.configure(text=self.tr("wiggle.invalid_duration"))
            return
        self.apply(draft)
        self.destroy()

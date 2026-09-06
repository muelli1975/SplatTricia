from __future__ import annotations

import queue
import sys
import threading
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox

try:
    import customtkinter as ctk
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "customtkinter ist nicht installiert. Bitte im SplatTricia-venv installieren."
    ) from exc

from . import __version__
from .cache import clear_temporary_files
from .config import ProcessingConfig
from .i18n import Translator
from .models import ProgressEvent
from .settings import load_settings, save_settings
from .path_logic import preferred_dialog_directory, resolve_output_dir
from .theme import (
    BG_MAIN, BG_SOFT, PANEL, BORDER,
    TEXT, TEXT_MUTED, TEXT_DISABLED,
    GOLD, GOLD_LIGHT,
    INPUT_BG, BUTTON_BG, BUTTON_HOVER,
    SLIDER_TRACK, SLIDER_PROGRESS, SLIDER_BUTTON, SLIDER_BUTTON_HOVER,
    SLIDER_DISABLED_PROGRESS, SLIDER_DISABLED_BUTTON, CHECKBOX_DISABLED,
    PROGRESS_TRACK,
    START_BG, START_HOVER_BG, START_TEXT, START_HOVER_TEXT,
    START_BORDER, START_HOVER_BORDER,
    START_DISABLED_BG, START_DISABLED_TEXT, START_DISABLED_BORDER,
    LANGUAGE_BG, LANGUAGE_BUTTON_BG, LANGUAGE_HOVER,
    LANGUAGE_DROPDOWN_BG, LANGUAGE_DROPDOWN_HOVER,
    DANGER, DANGER_HOVER, FONT_FAMILY, RADIUS_CONTROL, RADIUS_PANEL, BORDER_WIDTH,
)

APP_NAME = "SplatTricia"
DEFAULT_MODEL_NAME = "sharp_2572gikvuh.pt"
ERROR_LOG_NAME = "splattricia_error.log"


class SplatTriciaApp(ctk.CTk):
    def __init__(self, app_dir: Path) -> None:
        super().__init__()
        self.app_dir = app_dir
        self.settings_path = app_dir / "settings.json"
        self.settings = load_settings(self.settings_path)
        self.translator = Translator(str(self.settings.get("language", "de")))
        self.tr = self.translator.tr

        ctk.set_appearance_mode("dark")
        self.title(f"{APP_NAME} – {__version__}")
        self.geometry("1280x800")
        self.minsize(1100, 700)
        self.configure(fg_color=BG_MAIN)
        icon_path = self.app_dir / "assets" / "splattricia.ico"
        if icon_path.is_file():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.input_file = ctk.StringVar(value=str(self.settings.get("last_input_file", "")))
        self.input_folder = ctk.StringVar(value=str(self.settings.get("last_input_folder", "")))
        self.output_folder = ctk.StringVar(value=str(self.settings.get("last_output_folder", "")))
        self.use_input_subfolder = ctk.BooleanVar(
            value=bool(self.settings.get("use_input_subfolder", True))
        )
        self.use_ply_cache = ctk.BooleanVar(value=True)
        self.append_settings_to_filename = ctk.BooleanVar(value=False)
        self.gray_anaglyph = ctk.BooleanVar(value=False)
        self.deviation = ctk.DoubleVar(value=20)
        self.window_position = ctk.DoubleVar(value=100)
        self.window_backshift = ctk.DoubleVar(value=0)
        self.float_lr_symmetric = ctk.BooleanVar(value=True)
        self.float_left = ctk.DoubleVar(value=0)
        self.float_right = ctk.DoubleVar(value=0)
        self.float_top = ctk.DoubleVar(value=0)
        self.float_bottom = ctk.DoubleVar(value=0)
        self._syncing_float_sliders = False
        self.status_text = ctk.StringVar(value=self.tr("status.ready"))
        self.progress_value = ctk.DoubleVar(value=0)
        self.worker_thread: threading.Thread | None = None
        self.cancel_event = threading.Event()
        self.ui_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.is_running = False
        self.error_log_lines: list[str] = []
        self._last_progress_value = 0.0
        self._build_layout()
        self._apply_widget_style()
        self._set_processing_controls(running=False)
        self._update_window_position_label()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._poll_ui_queue)

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_main_area()
        self._build_footer()

    def _apply_widget_style(self) -> None:
        """Wendet die zentrale Palette auf alle Standard-Bedienelemente an."""

        def walk(widget):
            try:
                name = widget.__class__.__name__
                if name == "CTkButton":
                    widget.configure(
                        fg_color=BUTTON_BG,
                        hover_color=BUTTON_HOVER,
                        text_color=TEXT,
                        text_color_disabled=TEXT_DISABLED,
                        border_width=BORDER_WIDTH,
                        border_color=BORDER,
                        corner_radius=RADIUS_CONTROL,
                    )
                elif name == "CTkCheckBox":
                    widget.configure(
                        fg_color=GOLD,
                        hover_color=GOLD_LIGHT,
                        border_color=BORDER,
                        text_color=TEXT,
                        text_color_disabled=TEXT_DISABLED,
                        corner_radius=4,
                    )
                elif name == "CTkSlider":
                    widget.configure(
                        fg_color=SLIDER_TRACK,
                        progress_color=SLIDER_PROGRESS,
                        button_color=SLIDER_BUTTON,
                        button_hover_color=SLIDER_BUTTON_HOVER,
                    )
                elif name == "CTkProgressBar":
                    widget.configure(fg_color=PROGRESS_TRACK, progress_color=GOLD)
                elif name == "CTkEntry":
                    widget.configure(
                        fg_color=INPUT_BG,
                        border_color=BORDER,
                        text_color=TEXT,
                        placeholder_text_color=TEXT_MUTED,
                        corner_radius=RADIUS_CONTROL,
                    )
            except Exception as exc:
                self.error_log_lines.append(
                    f"UI-Stil konnte für {name} nicht angewendet werden: {exc}\n"
                    f"{traceback.format_exc()}"
                )
            for child in widget.winfo_children():
                walk(child)

        warning_count_before = len(self.error_log_lines)
        walk(self)
        if len(self.error_log_lines) > warning_count_before:
            self._write_error_log()

        # Eindeutige Aktionshierarchie nach dem allgemeinen Styling.
        self.start_button.configure(
            fg_color=START_BG,
            hover_color=START_HOVER_BG,
            text_color=START_TEXT,
            text_color_disabled=TEXT_DISABLED,
            border_width=BORDER_WIDTH,
            border_color=START_BORDER,
        )
        self.start_button.bind("<Enter>", self._on_start_button_enter, add="+")
        self.start_button.bind("<Leave>", self._on_start_button_leave, add="+")
        self.cancel_button.configure(
            fg_color=BUTTON_BG,
            hover_color=BUTTON_HOVER,
            text_color=TEXT,
            border_width=BORDER_WIDTH,
            border_color=BORDER,
        )
        self.clear_temp_button.configure(
            fg_color=BUTTON_BG,
            hover_color=DANGER_HOVER,
            text_color=TEXT,
            border_width=BORDER_WIDTH,
            border_color=DANGER,
        )

    def _set_slider_enabled(self, slider, enabled: bool) -> None:
        slider.configure(
            state="normal" if enabled else "disabled",
            fg_color=SLIDER_TRACK,
            progress_color=SLIDER_PROGRESS if enabled else SLIDER_DISABLED_PROGRESS,
            button_color=SLIDER_BUTTON if enabled else SLIDER_DISABLED_BUTTON,
            button_hover_color=(
                SLIDER_BUTTON_HOVER if enabled else SLIDER_DISABLED_BUTTON
            ),
        )

    def _set_checkbox_enabled(self, checkbox, enabled: bool) -> None:
        checkbox.configure(
            state="normal" if enabled else "disabled",
            fg_color=GOLD if enabled else CHECKBOX_DISABLED,
            hover_color=GOLD_LIGHT if enabled else CHECKBOX_DISABLED,
        )

    def _set_start_button_disabled(self) -> None:
        self.start_button.configure(
            fg_color=START_DISABLED_BG,
            hover_color=START_DISABLED_BG,
            text_color=START_DISABLED_TEXT,
            border_color=START_DISABLED_BORDER,
        )

    def _set_processing_controls(self, running: bool) -> None:
        state = "disabled" if running else "normal"

        for widget in (
            self.language_menu,
            self.input_file_button,
            self.input_folder_button,
            self.output_button,
            self.defaults_button,
            self.clear_temp_button,
        ):
            widget.configure(state=state)

        for entry in (self.input_file_entry, self.input_folder_entry):
            entry.configure(
                state=state,
                text_color=TEXT_DISABLED if running else TEXT,
            )

        for checkbox in (
            self.input_subfolder_check,
            self.gray_anaglyph_check,
            self.use_ply_cache_check,
            self.append_settings_check,
        ):
            self._set_checkbox_enabled(checkbox, not running)

        self._set_slider_enabled(self.deviation_slider, not running)
        self._set_slider_enabled(self.window_position_slider, not running)

        if running:
            self.start_button.configure(state="disabled")
            self._set_start_button_disabled()
            self.cancel_button.configure(state="normal")
        else:
            self.start_button.configure(state="normal")
            self._set_start_button_normal()
            self.cancel_button.configure(state="disabled")

        self._update_output_state()
        self._update_backshift_state()
        self._update_floating_window_state()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=BG_SOFT)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header, text=APP_NAME, font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=GOLD_LIGHT,
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(18, 2))
        ctk.CTkLabel(
            header, text=self.tr("app.subtitle"), font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 16))
        language_values = ["Deutsch", "English"]
        current = "English" if self.translator.locale == "en" else "Deutsch"
        self.language_menu = ctk.CTkOptionMenu(
            header,
            values=language_values,
            command=self._on_language_changed,
            width=120,
            fg_color=LANGUAGE_BG,
            button_color=LANGUAGE_BUTTON_BG,
            button_hover_color=LANGUAGE_HOVER,
            text_color=TEXT,
            dropdown_fg_color=LANGUAGE_DROPDOWN_BG,
            dropdown_hover_color=LANGUAGE_DROPDOWN_HOVER,
            dropdown_text_color=TEXT,
            corner_radius=RADIUS_CONTROL,
        )
        self.language_menu.set(current)
        self.language_menu.grid(row=0, column=1, rowspan=2, padx=24, pady=18)

    def _build_main_area(self) -> None:
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=1, column=0, sticky="nsew", padx=18, pady=18)
        main.grid_columnconfigure((0, 1, 2), weight=1)
        main.grid_rowconfigure(0, weight=1)
        left = ctk.CTkFrame(main, fg_color=PANEL, border_width=BORDER_WIDTH, border_color=BORDER, corner_radius=RADIUS_PANEL)
        center = ctk.CTkFrame(main, fg_color=PANEL, border_width=BORDER_WIDTH, border_color=BORDER, corner_radius=RADIUS_PANEL)
        right = ctk.CTkFrame(main, fg_color=PANEL, border_width=BORDER_WIDTH, border_color=BORDER, corner_radius=RADIUS_PANEL)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        center.grid(row=0, column=1, sticky="nsew", padx=9)
        right.grid(row=0, column=2, sticky="nsew", padx=(9, 0))
        for frame in (left, center, right):
            frame.grid_columnconfigure(0, weight=1)
        self._build_input_output_card(left)
        self._build_stereo_card(center)
        self._build_options_card(right)

    def _section_title(self, parent, key: str, row: int):
        label = ctk.CTkLabel(
            parent, text=self.tr(key), font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT,
        )
        label.grid(row=row, column=0, sticky="w", padx=20, pady=(20, 10))
        return label

    def _hint(self, parent, key: str, row: int, pady=(0, 14)):
        label = ctk.CTkLabel(
            parent, text=self.tr(key), text_color=TEXT_MUTED,
            wraplength=340, justify="left", anchor="w",
        )
        label.grid(row=row, column=0, sticky="ew", padx=20, pady=pady)
        return label

    def _separator(self, parent, row: int, pady=(8, 4)):
        separator = ctk.CTkFrame(parent, height=2, fg_color=BORDER, corner_radius=0)
        separator.grid(row=row, column=0, sticky="ew", padx=20, pady=pady)
        return separator

    def _path_row(self, parent, row: int, label_key: str, variable, command):
        label = ctk.CTkLabel(parent, text=self.tr(label_key), anchor="w")
        label.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 6))
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row + 1, column=0, sticky="ew", padx=20, pady=(0, 14))
        frame.grid_columnconfigure(0, weight=1)
        entry = ctk.CTkEntry(frame, textvariable=variable)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        button = ctk.CTkButton(
            frame, text=self.tr("button.choose"), width=110, command=command
        )
        button.grid(row=0, column=1, sticky="e")
        return label, entry, button

    def _build_input_output_card(self, parent) -> None:
        self._section_title(parent, "section.input", 0)
        (
            self.input_file_label,
            self.input_file_entry,
            self.input_file_button,
        ) = self._path_row(
            parent, 1, "label.single_image", self.input_file, self.choose_input_file
        )
        (
            self.input_folder_label,
            self.input_folder_entry,
            self.input_folder_button,
        ) = self._path_row(
            parent, 3, "label.image_folder", self.input_folder, self.choose_input_folder
        )
        self._separator(parent, 5, pady=(12, 4))
        self._section_title(parent, "section.output", 6)
        self.input_subfolder_check = ctk.CTkCheckBox(
            parent, text=self.tr("option.input_subfolder"),
            variable=self.use_input_subfolder, command=self._on_output_mode_changed,
        )
        self.input_subfolder_check.grid(
            row=7, column=0, sticky="w", padx=20, pady=(0, 10)
        )
        self.output_path_label = ctk.CTkLabel(
            parent, text=self.tr("label.output_folder"), anchor="w"
        )
        self.output_path_label.grid(row=8, column=0, sticky="ew", padx=20, pady=(0, 6))
        output_row = ctk.CTkFrame(parent, fg_color="transparent")
        output_row.grid(row=9, column=0, sticky="ew", padx=20, pady=(0, 12))
        output_row.grid_columnconfigure(0, weight=1)
        self.output_entry = ctk.CTkEntry(output_row, textvariable=self.output_folder)
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.output_button = ctk.CTkButton(
            output_row, text=self.tr("button.choose"), width=110,
            command=self.choose_output_folder,
        )
        self.output_button.grid(row=0, column=1, sticky="e")
        self.gray_anaglyph_check = ctk.CTkCheckBox(
            parent, text=self.tr("option.gray_anaglyph"), variable=self.gray_anaglyph
        )
        self.gray_anaglyph_check.grid(row=10, column=0, sticky="w", padx=20, pady=(4, 14))
        self._separator(parent, 11, pady=(12, 4))
        self._section_title(parent, "section.options", 12)
        self.use_ply_cache_check = ctk.CTkCheckBox(
            parent, text=self.tr("option.reuse_ply"), variable=self.use_ply_cache
        )
        self.use_ply_cache_check.grid(
            row=13, column=0, sticky="w", padx=20, pady=(0, 12)
        )
        self.append_settings_check = ctk.CTkCheckBox(
            parent, text=self.tr("option.append_settings"),
            variable=self.append_settings_to_filename,
        )
        self.append_settings_check.grid(
            row=14, column=0, sticky="w", padx=20, pady=(0, 20)
        )

    def _build_stereo_card(self, parent) -> None:
        self._section_title(parent, "section.stereo", 0)
        self.deviation_label = ctk.CTkLabel(parent, text="", width=340, anchor="w")
        self.deviation_label.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 6))
        self.deviation_slider = ctk.CTkSlider(
            parent, from_=5, to=30, variable=self.deviation,
            number_of_steps=5, command=self._on_deviation_changed,
        )
        self.deviation_slider.grid(
            row=2, column=0, sticky="ew", padx=20, pady=(0, 8)
        )
        self._hint(parent, "hint.deviation", 3, pady=(0, 18))
        self._separator(parent, 4, pady=(6, 4))
        self._section_title(parent, "section.window", 5)
        self.window_position_label = ctk.CTkLabel(parent, text="", width=340, anchor="w")
        self.window_position_label.grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 2))
        self.window_position_info_label = ctk.CTkLabel(
            parent, text="", width=340, anchor="w", text_color=TEXT_MUTED
        )
        self.window_position_info_label.grid(row=7, column=0, sticky="ew", padx=20, pady=(0, 6))
        self.window_position_slider = ctk.CTkSlider(
            parent, from_=0, to=100, variable=self.window_position,
            number_of_steps=20, command=self._on_window_position_changed,
        )
        self.window_position_slider.grid(
            row=8, column=0, sticky="ew", padx=20, pady=(0, 8)
        )
        self._hint(parent, "hint.window_position", 9, pady=(0, 18))
        self.window_backshift_label = ctk.CTkLabel(parent, text="", width=340, anchor="w")
        self.window_backshift_label.grid(row=10, column=0, sticky="ew", padx=20, pady=(0, 6))
        self.window_backshift_slider = ctk.CTkSlider(
            parent, from_=0, to=10, variable=self.window_backshift,
            number_of_steps=10, command=self._on_window_backshift_changed,
        )
        self.window_backshift_slider.grid(row=11, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.backshift_hint = self._hint(parent, "hint.window_back", 12, pady=(0, 18))
        self.defaults_button = ctk.CTkButton(
            parent, text=self.tr("button.defaults"), command=self.reset_defaults
        )
        self.defaults_button.grid(
            row=13, column=0, sticky="ew", padx=20, pady=(6, 20)
        )

    def _build_options_card(self, parent) -> None:
        self._section_title(parent, "section.floating_window", 0)
        self._hint(parent, "hint.floating_window", 1, pady=(0, 12))
        self.float_symmetry_check = ctk.CTkCheckBox(
            parent, text=self.tr("option.symmetric"),
            variable=self.float_lr_symmetric, command=self._on_float_symmetry_changed,
        )
        self.float_symmetry_check.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 10))
        self.float_left_label = ctk.CTkLabel(parent, text="", width=340, anchor="w")
        self.float_left_label.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 4))
        self.float_left_slider = ctk.CTkSlider(
            parent, from_=0, to=30, variable=self.float_left,
            number_of_steps=30, command=self._on_float_left_changed,
        )
        self.float_left_slider.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 8))
        self.float_right_label = ctk.CTkLabel(parent, text="", width=340, anchor="w")
        self.float_right_label.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 4))
        self.float_right_slider = ctk.CTkSlider(
            parent, from_=0, to=30, variable=self.float_right,
            number_of_steps=30, command=self._on_float_right_changed,
        )
        self.float_right_slider.grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.float_top_label = ctk.CTkLabel(parent, text="", width=340, anchor="w")
        self.float_top_label.grid(row=7, column=0, sticky="ew", padx=20, pady=(0, 4))
        self.float_top_slider = ctk.CTkSlider(
            parent, from_=0, to=30, variable=self.float_top,
            number_of_steps=30, command=self._on_float_top_changed,
        )
        self.float_top_slider.grid(row=8, column=0, sticky="ew", padx=20, pady=(0, 8))
        self.float_bottom_label = ctk.CTkLabel(parent, text="", width=340, anchor="w")
        self.float_bottom_label.grid(row=9, column=0, sticky="ew", padx=20, pady=(0, 4))
        self.float_bottom_slider = ctk.CTkSlider(
            parent, from_=0, to=30, variable=self.float_bottom,
            number_of_steps=30, command=self._on_float_bottom_changed,
        )
        self.float_bottom_slider.grid(row=10, column=0, sticky="ew", padx=20, pady=(0, 12))
        self._separator(parent, 11, pady=(10, 4))
        self._section_title(parent, "section.maintenance", 12)
        self.clear_temp_button = ctk.CTkButton(
            parent, text=self.tr("button.clear_temp"), command=self.clear_temp_files
        )
        self.clear_temp_button.grid(row=13, column=0, sticky="ew", padx=20, pady=(0, 8))
        self._hint(parent, "hint.clear_temp", 14, pady=(0, 20))
        self._refresh_dynamic_labels()

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, corner_radius=0, fg_color=BG_SOFT)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            footer, textvariable=self.status_text, anchor="w",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT,
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(14, 4))
        self.progress = ctk.CTkProgressBar(
            footer, variable=self.progress_value,
            fg_color=PROGRESS_TRACK, progress_color=GOLD,
        )
        self.progress.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 14))
        self.progress.set(0)
        buttons = ctk.CTkFrame(footer, fg_color="transparent")
        buttons.grid(row=0, column=1, rowspan=2, sticky="e", padx=24, pady=14)
        self.start_button = ctk.CTkButton(
            buttons, text=self.tr("button.start"), width=130, height=42,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"), command=self.start_processing,
        )
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        self.cancel_button = ctk.CTkButton(
            buttons, text=self.tr("button.cancel"), width=130, height=42,
            command=self.cancel_processing, state="disabled",
        )
        self.cancel_button.grid(row=0, column=1)

    def _set_start_button_normal(self) -> None:
        self.start_button.configure(
            fg_color=START_BG,
            hover_color=START_HOVER_BG,
            text_color=START_TEXT,
            border_color=START_BORDER,
        )

    def _set_start_button_hover(self) -> None:
        self.start_button.configure(
            fg_color=START_HOVER_BG,
            hover_color=START_HOVER_BG,
            text_color=START_HOVER_TEXT,
            border_color=START_HOVER_BORDER,
        )

    def _on_start_button_enter(self, _event=None) -> None:
        if self.start_button.cget("state") != "disabled":
            self.after_idle(self._set_start_button_hover)

    def _on_start_button_leave(self, _event=None) -> None:
        if self.start_button.cget("state") == "disabled":
            self.after_idle(self._set_start_button_disabled)
        else:
            self.after_idle(self._set_start_button_normal)

    def _on_language_changed(self, choice: str) -> None:
        if self.is_running:
            return
        locale = "en" if choice == "English" else "de"
        if locale == self.translator.locale:
            return
        self.settings["language"] = locale
        save_settings(self.settings_path, self.settings)
        messagebox.showinfo(
            self.tr("dialog.language_title"),
            self.tr("dialog.language_restart"),
        )

    def choose_input_file(self) -> None:
        if self.is_running:
            return
        path = filedialog.askopenfilename(
            title=self.tr("dialog.choose_image"),
            initialdir=str(self._input_dialog_directory()),
            filetypes=[
                (self.tr("dialog.image_files"), "*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp *.heic *.heif"),
                (self.tr("dialog.all_files"), "*.*"),
            ],
        )
        if path:
            self.input_file.set(path)
            self.input_folder.set("")
            self.status_text.set(self.tr("status.image_selected"))
            self._save_paths()

    def choose_input_folder(self) -> None:
        if self.is_running:
            return
        path = filedialog.askdirectory(
            title=self.tr("dialog.choose_folder"),
            initialdir=str(self._input_dialog_directory()),
        )
        if path:
            self.input_folder.set(path)
            self.input_file.set("")
            self.status_text.set(self.tr("status.folder_selected"))
            self._save_paths()

    def choose_output_folder(self) -> None:
        if self.is_running:
            return
        path = filedialog.askdirectory(
            title=self.tr("dialog.choose_output"),
            initialdir=str(self._output_dialog_directory()),
        )
        if path:
            self.output_folder.set(path)
            self.use_input_subfolder.set(False)
            self._update_output_state()
            self.status_text.set(self.tr("status.output_selected"))
            self._save_paths()

    def _input_dialog_directory(self) -> Path:
        return preferred_dialog_directory(
            self.input_file.get(),
            self.input_folder.get(),
            str(self.settings.get("last_input_file", "")),
            str(self.settings.get("last_input_folder", "")),
            fallback=Path.home(),
        )

    def _output_dialog_directory(self) -> Path:
        input_path = self._get_input_path()
        input_candidate = ""
        if input_path is not None:
            input_candidate = str(input_path.parent if input_path.is_file() else input_path)
        return preferred_dialog_directory(
            self.output_folder.get(),
            input_candidate,
            fallback=Path.home(),
        )

    def _save_paths(self) -> None:
        self.settings.update(
            {
                "last_input_file": self.input_file.get(),
                "last_input_folder": self.input_folder.get(),
                "last_output_folder": self.output_folder.get(),
                "use_input_subfolder": bool(self.use_input_subfolder.get()),
            }
        )
        try:
            save_settings(self.settings_path, self.settings)
        except OSError:
            pass

    def _on_output_mode_changed(self) -> None:
        self._update_output_state()
        self._save_paths()

    def _update_output_state(self) -> None:
        uses_input_subfolder = bool(self.use_input_subfolder.get())
        entry_state = "disabled" if uses_input_subfolder or self.is_running else "normal"
        text_color = TEXT_DISABLED if uses_input_subfolder else TEXT
        self.output_entry.configure(state=entry_state, text_color=text_color)
        self.output_path_label.configure(text_color=text_color)
        self.output_button.configure(state="disabled" if self.is_running else "normal")

    def _format_permille(self, value: float) -> str:
        if abs(value - round(value)) < 0.05:
            return str(int(round(value)))
        text = f"{value:.1f}"
        return text.replace(".", ",") if self.translator.locale == "de" else text

    def _refresh_dynamic_labels(self) -> None:
        deviation = round(float(self.deviation.get()) / 5) * 5
        position = round(float(self.window_position.get()) / 5) * 5
        near_front = deviation * (100.0 - position) / 100.0
        self.deviation_label.configure(text=self.tr("label.deviation", value=deviation))
        self.window_position_label.configure(text=self.tr("label.window_position", value=position))
        self.window_position_info_label.configure(
            text=self.tr("label.near_front", value=self._format_permille(near_front))
        )
        self.window_backshift_label.configure(
            text=self.tr("label.window_back", value=round(float(self.window_backshift.get())))
        )
        self.float_left_label.configure(text=self.tr("label.left", value=round(float(self.float_left.get()))))
        self.float_right_label.configure(text=self.tr("label.right", value=round(float(self.float_right.get()))))
        self.float_top_label.configure(text=self.tr("label.top", value=round(float(self.float_top.get()))))
        self.float_bottom_label.configure(text=self.tr("label.bottom", value=round(float(self.float_bottom.get()))))

    def _update_window_position_label(self) -> None:
        self._refresh_dynamic_labels()

    def _on_deviation_changed(self, value) -> None:
        self.deviation.set(round(float(value) / 5) * 5)
        self._refresh_dynamic_labels()

    def _on_window_position_changed(self, value) -> None:
        self.window_position.set(round(float(value) / 5) * 5)
        self._update_backshift_state()
        self._refresh_dynamic_labels()

    def _on_window_backshift_changed(self, value) -> None:
        self.window_backshift.set(round(float(value)))
        self._refresh_dynamic_labels()

    def _update_backshift_state(self) -> None:
        available = round(float(self.window_position.get())) == 100
        if not available:
            self.window_backshift.set(0)

        self._set_slider_enabled(
            self.window_backshift_slider,
            enabled=available and not self.is_running,
        )
        self.window_backshift_label.configure(
            text_color=TEXT if available else TEXT_DISABLED
        )
        self.backshift_hint.configure(
            text_color=TEXT_MUTED if available else TEXT_DISABLED
        )
        self._refresh_dynamic_labels()

    def _on_float_symmetry_changed(self) -> None:
        if self.float_lr_symmetric.get():
            self.float_right.set(round(float(self.float_left.get())))
        self._refresh_dynamic_labels()
        self._update_floating_window_state()

    def _on_float_left_changed(self, value) -> None:
        if self._syncing_float_sliders:
            return
        rounded = round(float(value))
        self.float_left.set(rounded)
        if self.float_lr_symmetric.get():
            self._syncing_float_sliders = True
            self.float_right.set(rounded)
            self._syncing_float_sliders = False
        if rounded > 0:
            self.float_top.set(0)
            self.float_bottom.set(0)
        self._refresh_dynamic_labels()
        self._update_floating_window_state()

    def _on_float_right_changed(self, value) -> None:
        if self._syncing_float_sliders:
            return
        rounded = round(float(value))
        self.float_right.set(rounded)
        if self.float_lr_symmetric.get():
            self._syncing_float_sliders = True
            self.float_left.set(rounded)
            self._syncing_float_sliders = False
        if rounded > 0:
            self.float_top.set(0)
            self.float_bottom.set(0)
        self._refresh_dynamic_labels()
        self._update_floating_window_state()

    def _on_float_top_changed(self, value) -> None:
        rounded = round(float(value))
        self.float_top.set(rounded)
        if rounded > 0:
            self.float_bottom.set(0)
            self.float_left.set(0)
            self.float_right.set(0)
        self._refresh_dynamic_labels()
        self._update_floating_window_state()

    def _on_float_bottom_changed(self, value) -> None:
        rounded = round(float(value))
        self.float_bottom.set(rounded)
        if rounded > 0:
            self.float_top.set(0)
            self.float_left.set(0)
            self.float_right.set(0)
        self._refresh_dynamic_labels()
        self._update_floating_window_state()

    def _update_floating_window_state(self) -> None:
        top = round(float(self.float_top.get()))
        bottom = round(float(self.float_bottom.get()))
        vertical = top > 0 or bottom > 0

        left_right_available = not vertical
        top_available = bottom == 0
        bottom_available = top == 0

        self._set_slider_enabled(
            self.float_left_slider, left_right_available and not self.is_running
        )
        self._set_slider_enabled(
            self.float_right_slider, left_right_available and not self.is_running
        )
        self._set_slider_enabled(
            self.float_top_slider, top_available and not self.is_running
        )
        self._set_slider_enabled(
            self.float_bottom_slider, bottom_available and not self.is_running
        )
        self._set_checkbox_enabled(
            self.float_symmetry_check, left_right_available and not self.is_running
        )

        self.float_left_label.configure(
            text_color=TEXT if left_right_available else TEXT_DISABLED
        )
        self.float_right_label.configure(
            text_color=TEXT if left_right_available else TEXT_DISABLED
        )
        self.float_top_label.configure(
            text_color=TEXT if top_available else TEXT_DISABLED
        )
        self.float_bottom_label.configure(
            text_color=TEXT if bottom_available else TEXT_DISABLED
        )

    def reset_defaults(self) -> None:
        if self.is_running:
            return
        self.deviation.set(20)
        self.window_position.set(100)
        self.window_backshift.set(0)
        self.float_left.set(0)
        self.float_right.set(0)
        self.float_top.set(0)
        self.float_bottom.set(0)
        self.float_lr_symmetric.set(True)
        self.gray_anaglyph.set(False)
        self.append_settings_to_filename.set(False)
        self.use_ply_cache.set(True)
        self._update_backshift_state()
        self._update_floating_window_state()
        self._refresh_dynamic_labels()
        self.status_text.set(self.tr("status.defaults_restored"))

    def _get_input_path(self) -> Path | None:
        if self.input_file.get().strip():
            return Path(self.input_file.get().strip())
        if self.input_folder.get().strip():
            return Path(self.input_folder.get().strip())
        return None

    def _get_output_dir(self) -> Path | None:
        return resolve_output_dir(
            input_path=self._get_input_path(),
            use_input_subfolder=bool(self.use_input_subfolder.get()),
            custom_output_folder=self.output_folder.get(),
        )

    def start_processing(self) -> None:
        if self.is_running:
            return
        input_path = self._get_input_path()
        output_dir = self._get_output_dir()
        if input_path is None:
            messagebox.showwarning(self.tr("dialog.no_input_title"), self.tr("dialog.no_input"))
            return
        if not input_path.exists():
            messagebox.showwarning(
                self.tr("dialog.input_missing_title"),
                self.tr("dialog.input_missing", path=input_path),
            )
            return
        if output_dir is None:
            messagebox.showwarning(
                self.tr("dialog.no_output_title"), self.tr("dialog.no_output")
            )
            return
        model_path = self.app_dir / "models" / DEFAULT_MODEL_NAME
        if not model_path.is_file():
            messagebox.showerror(
                self.tr("dialog.model_missing_title"),
                self.tr("dialog.model_missing", path=model_path, model=DEFAULT_MODEL_NAME),
            )
            return

        config = ProcessingConfig(
            checkpoint_path=model_path,
            exiftool_path=(self.app_dir / "tools" / "exiftool.exe"),
            target_height=2160,
            fixed_focal_length_mm=30.0,
            deviation_permille=round(float(self.deviation.get())),
            window_position_percent=round(float(self.window_position.get())),
            window_back_permille=round(float(self.window_backshift.get())),
            float_left_permille=round(float(self.float_left.get())),
            float_right_permille=round(float(self.float_right.get())),
            float_top_permille=round(float(self.float_top.get())),
            float_bottom_permille=round(float(self.float_bottom.get())),
            gray_anaglyph=bool(self.gray_anaglyph.get()),
            append_settings_to_filename=bool(self.append_settings_to_filename.get()),
        )
        self.cancel_event.clear()
        self.error_log_lines = []
        try:
            (self.app_dir / ERROR_LOG_NAME).unlink(missing_ok=True)
        except OSError:
            pass
        self.is_running = True
        self._set_processing_controls(running=True)
        self.progress.set(0)
        self._last_progress_value = 0.0
        self.status_text.set(self.tr("status.starting"))
        self._save_paths()
        self.worker_thread = threading.Thread(
            target=self._processing_worker,
            args=(config, input_path, output_dir, not bool(self.use_ply_cache.get())),
            daemon=True,
        )
        self.worker_thread.start()

    def _processing_worker(
        self,
        config: ProcessingConfig,
        input_path: Path,
        output_dir: Path,
        rebuild_ply: bool,
    ) -> None:
        try:
            from .controller import ProcessingCancelled, ProcessingController
        except Exception as exc:
            self.ui_queue.put(("error", (exc, traceback.format_exc())))
            return
        try:
            controller = ProcessingController(
                config=config,
                event_callback=self._on_controller_event,
                cancel_callback=self.cancel_event.is_set,
            )
            items = controller.run(
                input_path=input_path,
                output_dir=output_dir,
                rebuild_ply=rebuild_ply,
            )
            errors = [item for item in items if item.status != "ok"]
            self.ui_queue.put(("success", (len(items), len(errors))))
        except ProcessingCancelled:
            self.ui_queue.put(("cancelled", None))
        except Exception as exc:
            self.ui_queue.put(("error", (exc, traceback.format_exc())))

    def _on_controller_event(self, event: ProgressEvent) -> None:
        self.ui_queue.put(("event", event))

    def _poll_ui_queue(self) -> None:
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()
                if kind == "event":
                    self._apply_controller_event(payload)
                elif kind == "success":
                    total, errors = payload
                    self._finish_success(total, errors)
                elif kind == "cancelled":
                    self._finish_cancelled()
                elif kind == "error":
                    exc, details = payload
                    self.error_log_lines.append(details)
                    self._finish_error(exc)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(50, self._poll_ui_queue)

    def _apply_controller_event(self, event: ProgressEvent) -> None:
        values = dict(event.details)
        values.update(
            {
                "current": event.current,
                "total": event.total,
                "filename": values.get("filename", event.item_key),
            }
        )
        status = self.tr(event.message_key, **values)
        progress = None
        if event.stage == "start":
            progress = 0.02
        elif event.stage == "preparing" and event.total:
            progress = 0.02 + 0.04 * (event.current / event.total)
        elif event.stage == "model_loading":
            progress = 0.06
        elif event.stage == "model_ready":
            progress = 0.08
        elif event.stage in {"inference", "inference_done"} and event.total:
            fraction = event.current / event.total
            progress = 0.08 + 0.57 * fraction
        elif event.stage == "model_released":
            progress = 0.67
        elif event.stage == "inference_skipped":
            progress = 0.35
        elif event.stage == "rendering" and event.total:
            progress = 0.68 + 0.30 * ((event.current - 1) / event.total)
        elif event.stage == "render_step" and event.total:
            step_fraction = float(event.details.get("step_fraction", 0.0))
            image_fraction = ((event.current - 1) + step_fraction) / event.total
            progress = 0.68 + 0.30 * image_fraction
        elif event.stage == "metadata" and event.total:
            image_fraction = ((event.current - 1) + 0.96) / event.total
            progress = 0.68 + 0.30 * image_fraction
        elif event.stage == "rendering_done" and event.total:
            progress = 0.68 + 0.30 * (event.current / event.total)
        elif event.stage == "finished":
            progress = 1.0
        elif event.stage in {"item_error", "item_warning"}:
            self.error_log_lines.append(event.fallback_message)
            trace = event.details.get("traceback")
            if trace:
                self.error_log_lines.append(str(trace))
            if event.stage == "item_error":
                self._write_error_log()
        self._post_status(status, progress)

    def cancel_processing(self) -> None:
        if not self.is_running:
            return
        self.cancel_event.set()
        self.cancel_button.configure(state="disabled")
        self.status_text.set(self.tr("status.cancelling"))

    def _post_status(self, text: str, progress: float | None = None) -> None:
        self.status_text.set(text)
        if progress is not None:
            value = max(self._last_progress_value, min(1.0, max(0.0, progress)))
            self._last_progress_value = value
            self.progress.set(value)

    def _reset_running_state(self) -> None:
        self.is_running = False
        self._set_processing_controls(running=False)

    def _finish_success(self, total: int, error_count: int) -> None:
        self._reset_running_state()
        self.progress.set(1)
        if error_count:
            log_path = self._write_error_log()
            self.status_text.set(
                self.tr(
                    "status.finished_with_errors",
                    total=total,
                    errors=error_count,
                )
            )
            messagebox.showwarning(
                self.tr("dialog.completed_errors_title"),
                self.tr(
                    "dialog.completed_errors",
                    errors=error_count,
                    log=log_path or "-",
                ),
            )
        else:
            self.status_text.set(self.tr("status.finished", total=total))
            self._play_ready_sound()

    def _finish_cancelled(self) -> None:
        self._reset_running_state()
        self.progress.set(0)
        self._last_progress_value = 0.0
        self.status_text.set(self.tr("status.cancelled"))

    def _finish_error(self, exc: Exception) -> None:
        self._reset_running_state()
        self.progress.set(0)
        self._last_progress_value = 0.0
        log_path = self._write_error_log()
        self.status_text.set(self.tr("status.error"))
        messagebox.showerror(
            self.tr("dialog.error_title"),
            self.tr("dialog.error", error=exc, log=log_path or "-"),
        )

    def _write_error_log(self) -> Path | None:
        if not self.error_log_lines:
            return None
        try:
            path = self.app_dir / ERROR_LOG_NAME
            path.write_text("\n".join(self.error_log_lines) + "\n", encoding="utf-8")
            return path
        except OSError:
            return None

    def _play_ready_sound(self) -> None:
        path = self.app_dir / "assets" / "ready.wav"
        if not path.is_file() or not sys.platform.startswith("win"):
            return
        try:
            import winsound
            winsound.PlaySound(
                str(path),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
        except Exception:
            pass

    def clear_temp_files(self) -> None:
        if self.is_running:
            return
        output_dir = self._get_output_dir()
        if output_dir is None:
            messagebox.showwarning(self.tr("dialog.no_path_title"), self.tr("dialog.no_path"))
            return

        temp_dir = output_dir / "_temp"
        if not temp_dir.exists():
            self.status_text.set(self.tr("status.temp_not_found"))
            return
        if not messagebox.askyesno(
            self.tr("dialog.delete_temp_title"),
            self.tr("dialog.delete_temp_confirm", path=temp_dir),
        ):
            return
        try:
            clear_temporary_files(temp_dir)
            self.status_text.set(self.tr("status.temp_deleted"))
        except Exception as exc:
            messagebox.showerror(self.tr("dialog.error_title"), str(exc))

    def _on_close(self) -> None:
        if self.is_running:
            if not messagebox.askyesno(
                self.tr("dialog.close_title"), self.tr("dialog.close_running")
            ):
                return
            self.cancel_event.set()
        self._save_paths()
        self.destroy()


def main(app_dir: Path) -> int:
    app = SplatTriciaApp(app_dir)
    app.mainloop()
    return 0

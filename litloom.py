import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk, ImageDraw
import re
import threading
import os
import sys
import math

# --- Library Imports with User Guidance ---

# NEW: Added pyperclip for copy-to-clipboard functionality
try:
    import pyperclip
except ImportError:
    print(
        "Warning: 'pyperclip' library not found. Copy-to-clipboard functionality will be disabled. Please run: pip install pyperclip")
    pyperclip = None

try:
    from spellchecker import SpellChecker
except ImportError:
    print("Error: 'pyspellchecker' library not found. Please run: pip install pyspellchecker")
    sys.exit()
try:
    import pyttsx3
except ImportError:
    # On Windows, you might not need to specify the version.
    # If you face issues, try `pip install pyttsx3`.
    print("Error: 'pyttsx3' library not found. Please run: pip install pyttsx3")
    sys.exit()
try:
    import nltk
    import nltk.downloader as nl_downloader
except ImportError:
    print("Error: 'nltk' library not found. Please run: pip install nltk")
    sys.exit()
try:
    from deep_translator import GoogleTranslator, exceptions
except ImportError:
    # This is now only needed for the analysis page translation, not for TTS.
    print("Error: 'deep_translator' library not found. Please run: pip install deep-translator")
    sys.exit()
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    # Import font registration module
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print("Error: 'reportlab' library not found. Please run: pip install reportlab")
    sys.exit()

from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize, sent_tokenize


# --- One-time NLTK Data Download ---
def download_nltk_data():
    """Downloads required NLTK data if not already present."""
    required_data = [('tokenizers/punkt', 'punkt'),
                     ('taggers/averaged_perceptron_tagger', 'averaged_perceptron_tagger'),
                     ('sentiment/vader_lexicon', 'vader_lexicon')]

    print("Checking for necessary NLTK data...")
    all_present = True
    for path, pkg_id in required_data:
        try:
            nltk.data.find(path)
            print(f"  - {pkg_id} is already present.")
        except (getattr(nl_downloader, 'DownloadError', Exception)) as e:
            all_present = False
            print(f"  - {pkg_id} not found or download error: {e}. Attempting to download...")
            try:
                nltk.download(pkg_id, quiet=False)
            except Exception as download_e:
                print(
                    f"CRITICAL ERROR: Failed to download NLTK data '{pkg_id}'. Please try running `python -m nltk.downloader {pkg_id}` manually in your terminal.")
                print(f"Details: {download_e}")
                sys.exit(1)

    if all_present:
        print("\nAll NLTK data already present.")
    else:
        print("\nNLTK data download complete.")


download_nltk_data()

# --- Global Font Registration for ReportLab ---
try:
    # This path logic assumes the 'assets' folder is in the same directory as the script.
    # It's more robust than relying on a hardcoded path.
    base_dir_for_font = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir_for_font, 'assets', 'fonts', 'NotoSans-Regular.ttf')
    bold_font_path = os.path.join(base_dir_for_font, 'assets', 'fonts', 'NotoSans-Bold.ttf')

    # Check if fonts exist before registering
    if os.path.exists(font_path) and os.path.exists(bold_font_path):
        default_font_for_pdf = 'NotoSans'
        pdfmetrics.registerFont(TTFont(default_font_for_pdf, font_path))
        pdfmetrics.registerFont(TTFont(f'{default_font_for_pdf}-Bold', bold_font_path))
    else:
        raise FileNotFoundError("Custom font files not found in assets/fonts/ directory.")

except Exception as e:
    print(f"WARNING: Could not load custom font for PDF generation: {e}. Translated text in PDF may appear as boxes.")
    default_font_for_pdf = 'Helvetica'


# --- POPUP WINDOW CLASSES ---

class ExportPdfPopup(tk.Toplevel):
    """A custom-themed pop-up window for PDF export options."""

    def __init__(self, parent, pdf_content_func):
        super().__init__(parent)
        self.parent = parent
        self.pdf_content_func = pdf_content_func
        self.selected_path = tk.StringVar(value=os.path.expanduser("~"))

        self.withdraw()
        self.overrideredirect(True)
        self.geometry("500x250")
        self.attributes("-alpha", 0.98)

        self.bg_color = "#B48C68"
        self.main_color = "#C7B6A4"
        self.text_color = "#4A4A4A"
        self.button_color = "#E5E5E5"
        self.button_hover_color = "#DCDCDC"

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<B1-Motion>", self.move_window)
        self.canvas.bind("<ButtonPress-1>", self.start_move)

        self.setup_ui()
        self.center_window()
        self.deiconify()

    def start_move(self, event):
        self.x, self.y = event.x, event.y

    def move_window(self, event):
        deltax, deltay = event.x - self.x, event.y - self.y
        x, y = self.winfo_x() + deltax, self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def center_window(self):
        self.update_idletasks()
        px, py = self.parent.winfo_x(), self.parent.winfo_y()
        pw, ph = self.parent.winfo_width(), self.parent.winfo_height()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f'{w}x{h}+{px + (pw // 2) - (w // 2)}+{py + (ph // 2) - (h // 2)}')

    def setup_ui(self):
        self.canvas.configure(bg=self.bg_color)
        self.parent.draw_rounded_rectangle(self.canvas, 5, 5, 495, 245, radius=20, fill=self.main_color,
                                           tags="popup_bg")

        self.close_btn_id = self.canvas.create_text(480, 20, text="X", font=("Georgia", 14, "bold"),
                                                    fill=self.text_color, tags="close_btn")
        self.canvas.tag_bind("close_btn", "<Enter>",
                             lambda e: self.config(cursor="hand2") or self.canvas.itemconfig(self.close_btn_id,
                                                                                             fill="#C0392B"))
        self.canvas.tag_bind("close_btn", "<Leave>",
                             lambda e: self.config(cursor="") or self.canvas.itemconfig(self.close_btn_id,
                                                                                        fill=self.text_color))
        self.canvas.tag_bind("close_btn", "<Button-1>", lambda e: self.destroy())

        self.canvas.create_text(250, 40, text="Export PDF", font=("Georgia", 20, "bold"), fill=self.text_color,
                                anchor="center")
        self.canvas.create_text(100, 90, text="Save to:", font=("Georgia", 12), fill=self.text_color, anchor="w")

        self.path_entry = ttk.Entry(self, textvariable=self.selected_path, width=40, style='TEntry')
        self.canvas.create_window(100, 110, window=self.path_entry, anchor="w")

        self.parent.create_canvas_button(self.canvas, 400, 95, 470, 125, "Browse", "browse_btn", self.browse_directory,
                                         corner_radius=10, font_size=10,
                                         bg_color=self.button_color, hover_color=self.button_hover_color,
                                         text_color=self.text_color)
        self.parent.create_canvas_button(self.canvas, 120, 180, 240, 215, "Convert", "convert_final_btn",
                                         self.convert_and_save,
                                         corner_radius=20, font_size=14,
                                         bg_color=self.button_color, hover_color=self.button_hover_color,
                                         text_color=self.text_color)
        self.parent.create_canvas_button(self.canvas, 260, 180, 380, 215, "Cancel", "cancel_export_btn", self.destroy,
                                         corner_radius=20, font_size=14,
                                         bg_color=self.button_color, hover_color=self.button_hover_color,
                                         text_color=self.text_color)

    def browse_directory(self):
        directory = filedialog.askdirectory(parent=self)
        if directory:
            self.selected_path.set(directory)

    def convert_and_save(self):
        output_dir = self.selected_path.get()
        if not output_dir:
            self.parent.show_temp_message("Please select a directory to save the PDF.", 2000)
            return
        self.pdf_content_func(output_dir)
        self.destroy()


class SpellCheckPopup(tk.Toplevel):
    """A custom-themed pop-up window for spell checking."""

    def __init__(self, parent, misspelled_data, text_widget):
        super().__init__(parent)
        self.parent = parent
        self.misspelled_data = misspelled_data
        self.text_widget = text_widget
        self.current_word_index = 0

        self.withdraw()
        self.overrideredirect(True)
        self.geometry("400x350")
        self.attributes("-alpha", 0.98)

        self.bg_color = "#B48C68"
        self.main_color = "#C7B6A4"
        self.text_color = "#4A4A4A"
        self.button_color = "#E5E5E5"
        self.button_hover_color = "#DCDCDC"

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<B1-Motion>", self.move_window)
        self.canvas.bind("<ButtonPress-1>", self.start_move)

        self.setup_ui()
        self.display_next_error()
        self.center_window()
        self.deiconify()

    def start_move(self, event):
        self.x, self.y = event.x, event.y

    def move_window(self, event):
        deltax, deltay = event.x - self.x, event.y - self.y
        x, y = self.winfo_x() + deltax, self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def center_window(self):
        self.update_idletasks()
        px, py = self.parent.winfo_x(), self.parent.winfo_y()
        pw, ph = self.parent.winfo_width(), self.parent.winfo_height()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f'{w}x{h}+{px + (pw // 2) - (w // 2)}+{py + (ph // 2) - (h // 2)}')

    def setup_ui(self):
        self.canvas.configure(bg=self.bg_color)
        self.parent.draw_rounded_rectangle(self.canvas, 5, 5, 395, 345, radius=20, fill=self.main_color,
                                           tags="popup_bg")
        self.close_btn_id = self.canvas.create_text(380, 20, text="X", font=("Georgia", 14, "bold"),
                                                    fill=self.text_color, tags="close_btn")
        self.canvas.tag_bind("close_btn", "<Enter>",
                             lambda e: self.config(cursor="hand2") or self.canvas.itemconfig(self.close_btn_id,
                                                                                             fill="#C0392B"))
        self.canvas.tag_bind("close_btn", "<Leave>",
                             lambda e: self.config(cursor="") or self.canvas.itemconfig(self.close_btn_id,
                                                                                        fill=self.text_color))
        self.canvas.tag_bind("close_btn", "<Button-1>", lambda e: self.destroy())

    def display_next_error(self):
        self.canvas.delete("suggestion_elements")
        if self.current_word_index >= len(self.misspelled_data):
            self.canvas.create_text(200, 70, text="Spell check complete!", font=("Georgia", 16),
                                    fill=self.text_color, tags="suggestion_elements", anchor="center")
            self.after(1500, self.destroy)
            return

        data = self.misspelled_data[self.current_word_index]
        word, suggestions = data['word'], data['suggestions']

        self.canvas.create_text(200, 50, text="Misspelled Word:", font=("Georgia", 12),
                                fill=self.text_color, tags="suggestion_elements")
        self.canvas.create_text(200, 80, text=f"'{word}'", font=("Georgia", 18, "bold"),
                                fill="#C0392B", tags="suggestion_elements")

        y_pos = 120
        for i, sug in enumerate(suggestions[:5]):
            btn_tag = f"sug_{i}"
            self.parent.create_canvas_button(self.canvas, 100, y_pos, 300, y_pos + 30, text=sug, tag=btn_tag,
                                             command=lambda s=sug: self.replace_word(s), corner_radius=15,
                                             bg_color=self.button_color, hover_color=self.button_hover_color,
                                             text_color=self.text_color, font_size=12)
            y_pos += 40

        ignore_btn_width = 150
        ignore_btn_x1 = 200 - (ignore_btn_width / 2)
        ignore_btn_x2 = 200 + (ignore_btn_width / 2)
        self.parent.create_canvas_button(self.canvas, ignore_btn_x1, 300, ignore_btn_x2, 330, "Ignore", "ignore_btn",
                                         self.next_error, corner_radius=15, font_size=12,
                                         bg_color=self.button_color, hover_color=self.button_hover_color,
                                         text_color=self.text_color)

    def replace_word(self, suggestion):
        data = self.misspelled_data[self.current_word_index]
        self.parent.replace_text_at_index(data['index'], data['word'], suggestion)
        self.next_error()

    def next_error(self):
        self.current_word_index += 1
        self.display_next_error()


try:
    import win32com.client
    import pythoncom
except ImportError:
    print("CRITICAL ERROR: 'pywin32' library not found.")
    print("Please run: pip install pywin32")
    sys.exit()


class TextToSpeechPopup(tk.Toplevel):
    def __init__(self, parent, text_to_speak):
        super().__init__(parent)
        self.parent = parent
        self.full_text = text_to_speak.strip() if text_to_speak.strip() else "There is no text to read."
        self.is_paused = False
        self.is_stopped = True
        self.check_status_job = None
        try:
            pythoncom.CoInitialize()
            self.voice = win32com.client.Dispatch("SAPI.SpVoice")
            self.voice_map, self.default_rate = self._get_windows_voices()
            if not self.voice_map:
                raise RuntimeError("No SAPI5 TTS voices found on this system.")
            self.selected_voice_token = list(self.voice_map.values())[0]
        except Exception as e:
            print(f"Failed to initialize Windows SAPI5 engine: {e}")
            self.parent.show_temp_message(f"TTS Error: {e}", 3000)
            self.after(50, self.destroy)
            return

        self.speed_options = ["0.75x", "1.0x (Normal)", "1.25x", "1.5x", "1.75x", "2.0x"]
        self.sapi_rate_map = {"0.75x": -2, "1.0x (Normal)": 0, "1.25x": 2, "1.5x": 5, "1.75x": 8, "2.0x": 10}
        self.selected_speed_option = tk.StringVar(value="1.0x (Normal)")

        self.withdraw()
        self.overrideredirect(True)
        self.geometry("400x300")
        self.attributes("-alpha", 0.98)
        self.main_color, self.text_color = "#C7B6A4", "#4A4A4A"
        self.button_color, self.button_hover_color = "#E5E5E5", "#DCDCDC"
        self.main_frame = tk.Frame(self, bg=self.main_color)
        self.main_frame.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(self.main_frame, highlightthickness=0, bg=self.main_color)
        self.canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self.canvas.bind("<B1-Motion>", self.move_window)
        self.canvas.bind("<ButtonPress-1>", self.start_move)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.setup_ui()
        self.center_window()
        self.deiconify()

    def _get_windows_voices(self):
        voice_map = {}
        for token in self.voice.GetVoices():
            voice_map[token.GetDescription()] = token
        default_rate = self.voice.Rate
        return voice_map, default_rate

    def setup_ui(self):
        self.parent.draw_rounded_rectangle(self.canvas, 5, 5, 395, 295, radius=20, fill=self.main_color)
        self.close_btn_id = self.canvas.create_text(380, 20, text="X", font=("Georgia", 14, "bold"),
                                                    fill=self.text_color, tags="tts_close")
        self.canvas.tag_bind("tts_close", "<Button-1>", lambda e: self.on_close())
        self.canvas.tag_bind("tts_close", "<Enter>",
                             lambda e: self.config(cursor="hand2") or self.canvas.itemconfig(self.close_btn_id,
                                                                                             fill="#C0392B"))
        self.canvas.tag_bind("tts_close", "<Leave>",
                             lambda e: self.config(cursor="") or self.canvas.itemconfig(self.close_btn_id,
                                                                                        fill=self.text_color))

        self.canvas.create_text(70, 80, text="Voice:", font=("Georgia", 12), fill=self.text_color, anchor="w")
        self.voice_combo = ttk.Combobox(self.main_frame, values=list(self.voice_map.keys()), state='readonly', width=30,
                                        style='TCombobox')
        self.voice_combo.set(self.selected_voice_token.GetDescription())
        self.voice_combo.place(x=130, y=70)
        self.voice_combo.bind("<<ComboboxSelected>>", self.on_voice_change)

        self.canvas.create_text(70, 130, text="Speed:", font=("Georgia", 12), fill=self.text_color, anchor="w")
        self.speed_combo = ttk.Combobox(self.main_frame, textvariable=self.selected_speed_option,
                                        values=self.speed_options, state='readonly', width=15, style='TCombobox')
        self.speed_combo.place(x=130, y=120)
        self.speed_combo.bind("<<ComboboxSelected>>", self.on_speed_change)

        self.play_pause_button_id = self.parent.create_canvas_button(self.canvas, 100, 200, 200, 250, "Play",
                                                                     "play_pause_btn", self.toggle_play_pause,
                                                                     corner_radius=25, font_size=18,
                                                                     bg_color=self.button_color,
                                                                     hover_color=self.button_hover_color,
                                                                     text_color=self.text_color)
        self.stop_button_id = self.parent.create_canvas_button(self.canvas, 210, 200, 310, 250, "Stop", "stop_btn",
                                                               self.stop_playback, corner_radius=25, font_size=18,
                                                               bg_color=self.button_color,
                                                               hover_color=self.button_hover_color,
                                                               text_color=self.text_color)

    def on_voice_change(self, event=None):
        self.selected_voice_token = self.voice_map[self.voice_combo.get()]
        if not self.is_stopped: self.stop_playback()

    def on_speed_change(self, event=None):
        self.voice.Rate = self.sapi_rate_map[self.selected_speed_option.get()]
        if not self.is_stopped: self.stop_playback()

    def update_play_pause_button(self, text):
        text_item_id = self.canvas.find_withtag("play_pause_btn_text")
        if text_item_id: self.canvas.itemconfig(text_item_id, text=text)

    def toggle_play_pause(self):
        if self.is_stopped:
            self.start_playback()
        elif self.is_paused:
            self.resume_playback()
        else:
            self.pause_playback()

    def start_playback(self):
        self.is_stopped, self.is_paused = False, False
        self.update_play_pause_button("Pause")
        self.voice.Voice = self.selected_voice_token
        self.voice.Rate = self.sapi_rate_map[self.selected_speed_option.get()]
        self.voice.Speak(self.full_text, 1)  # SVSF_ASYNC
        self._check_playback_status()

    def pause_playback(self):
        if not self.is_stopped and not self.is_paused:
            self.is_paused = True
            self.voice.Pause()
            self.update_play_pause_button("Resume")

    def resume_playback(self):
        if self.is_paused:
            self.is_paused = False
            self.voice.Resume()
            self.update_play_pause_button("Pause")

    def stop_playback(self):
        if not self.is_stopped:
            self.is_stopped, self.is_paused = True, False
            self.voice.Speak("", 3)  # SVSF_PURGEBEFORESPEAK
        self.update_play_pause_button("Play")

    def _check_playback_status(self):
        if self.check_status_job: self.after_cancel(self.check_status_job)
        if not self.is_stopped and self.voice.Status.RunningState != 1:
            self.check_status_job = self.after(100, self._check_playback_status)
        elif not self.is_stopped:
            self.is_stopped, self.is_paused = True, False
            self.update_play_pause_button("Play")

    def on_close(self):
        self.stop_playback()
        if self.check_status_job: self.after_cancel(self.check_status_job)
        self.destroy()

    def start_move(self, event):
        self.x, self.y = event.x, event.y

    def move_window(self, event):
        self.geometry(f"+{self.winfo_x() + event.x - self.x}+{self.winfo_y() + event.y - self.y}")

    def center_window(self):
        self.update_idletasks()
        px, py, pw, ph = self.parent.winfo_x(), self.parent.winfo_y(), self.parent.winfo_width(), self.parent.winfo_height()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f'{w}x{h}+{px + (pw // 2) - (w // 2)}+{py + (ph // 2) - (h // 2)}')


class LitLoomApp(tk.Tk):
    """
 The main application window for Lit-Loom. This class manages the UI,
 state (which page is active), and all functional logic.
 """

    def __init__(self):
        super().__init__()
        self.title("◆ LitLoom")
        self.geometry("800x600")
        self.minsize(600, 450)
        self.configure(bg="#CBBFAC")

        self.current_page = "welcome"
        self.poem_text = ""
        self.current_font_size = 22 # Resetting to a more standard default
        self.active_analysis_button = "overview"
        self.resize_job_id = None
        self.last_width, self.last_height = 0, 0
        self.current_poem_index = 0

        # --- ADDED: State for storing translation for PDF export ---
        self.translated_text = ""
        self.translated_lang = ""

        self.button_bg_color = "#A6876D"
        self.button_hover_color = "#92755E"
        self.control_button_color = "#E5E5E5"
        self.control_button_hover_color = "#DCDCDC"

        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.spell = SpellChecker()
        self.editor_text_widget = None
        self.analysis_text_widget = None

        self.example_poems = [
            (
                "The rose is sick. Invisible worm,\nThat flies in the nyght, in the howling storm,\nHas found out thy bed of crimson joy,\nAnd his dark secret love does thy life destroy."),
            (
                "I wandered lonely as a clowd\nThat floats on high o'er vales and hills,\nWhen all at once I saw a crowd,\nA host, of golden daffodills."),
            (
                "Two roads diverged in a yellow wood,\nAnd sorry I could not travel both\nAnd be one traveler, long I stood\nAnd looked down one as far as I could\nTo where it bent in the undergrowth;\n\nThen took the other, as just as fair,\nAnd having perhaps the better claim,\nBecause it was grassy and wanted wear;\nThough as for that the passing there\nHad worn them really about the same.")
        ]

        self.original_fg_image = None
        self.original_bg_image = None
        self.original_logo_image = None
        self.original_title_image = None
        self.original_bottom_sound_icon_image = None
        self.original_top_sound_icon_image = None
        self.original_welcome_icon_image = None
        self.original_copy_icon_image = None

        self.fg_photo, self.bg_photo, self.logo_photo, self.title_photo, \
            self.bottom_sound_icon_photo, self.top_sound_icon_photo, self.welcome_icon_photo, \
            self.copy_icon_photo = [None] * 8

        self.load_images()
        self.setup_styles()

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.bind_events()
        self.after(50, self.redraw_canvas, True)

    # --- Methods for Right-Click Context Menu ---
    def _create_text_context_menu(self, text_widget):
        context_menu = tk.Menu(text_widget, tearoff=0, bg="#F0F0F0", fg="#333333",
                               activebackground=self.button_hover_color, activeforeground="white")
        context_menu.add_command(label="Cut", command=lambda: text_widget.event_generate("<<Cut>>"))
        context_menu.add_command(label="Copy", command=lambda: text_widget.event_generate("<<Copy>>"))
        context_menu.add_command(label="Paste", command=lambda: text_widget.event_generate("<<Paste>>"))
        context_menu.add_separator()
        context_menu.add_command(label="Select All", command=lambda: self._select_all_text(text_widget))
        text_widget.bind("<Button-3>", lambda event: self._show_text_context_menu(event, context_menu, text_widget))
        text_widget.bind("<Button-1>", lambda event: context_menu.unpost())

    def _select_all_text(self, text_widget):
        text_widget.focus_set()
        text_widget.tag_add(tk.SEL, "1.0", tk.END)
        text_widget.mark_set(tk.INSERT, "1.0")
        text_widget.see(tk.INSERT)
        return "break"

    def _show_text_context_menu(self, event, menu, text_widget):
        is_disabled = text_widget.cget("state") == tk.DISABLED
        has_selection = False
        try:
            if text_widget.tag_ranges(tk.SEL):
                has_selection = True
        except tk.TclError:
            has_selection = False
        if is_disabled or not has_selection:
            menu.entryconfig("Cut", state=tk.DISABLED)
        else:
            menu.entryconfig("Cut", state=tk.NORMAL)
        if not has_selection:
            menu.entryconfig("Copy", state=tk.DISABLED)
        else:
            menu.entryconfig("Copy", state=tk.NORMAL)
        try:
            self.clipboard_get()
            can_paste = True
        except tk.TclError:
            can_paste = False
        if is_disabled or not can_paste:
            menu.entryconfig("Paste", state=tk.DISABLED)
        else:
            menu.entryconfig("Paste", state=tk.NORMAL)
        menu.tk_popup(event.x_root, event.y_root)

    def draw_rounded_rectangle(self, canvas, x1, y1, x2, y2, radius=25, **kwargs):
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        radius = int(radius)
        fill_color = kwargs.get('fill', 'black')
        outline_color = kwargs.get('outline', fill_color)
        width = kwargs.get('width', 0)
        tags = kwargs.get('tags', '')

        item_ids = [
            canvas.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill_color, outline=outline_color,
                                    width=width, tags=tags),
            canvas.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill_color, outline=outline_color,
                                    width=width, tags=tags),
            canvas.create_arc(x1, y1, x1 + 2 * radius, y1 + 2 * radius, start=90, extent=90, style=tk.PIESLICE,
                              fill=fill_color, outline=outline_color, width=width, tags=tags),
            canvas.create_arc(x2 - 2 * radius, y1, x2, y1 + 2 * radius, start=0, extent=90, style=tk.PIESLICE,
                              fill=fill_color, outline=outline_color, width=width, tags=tags),
            canvas.create_arc(x2 - 2 * radius, y2 - 2 * radius, x2, y2, start=270, extent=90, style=tk.PIESLICE,
                              fill=fill_color, outline=outline_color, width=width, tags=tags),
            canvas.create_arc(x1, y2 - 2 * radius, x1 + 2 * radius, y2, start=180, extent=90, style=tk.PIESLICE,
                              fill=fill_color, outline=outline_color, width=width, tags=tags)
        ]
        return item_ids

    def load_images(self):
        image_info = {
            'fg': {'attr': 'original_fg_image', 'file': "background.jpeg", 'convert_rgba': False,
                   'apply_rounded': True},
            'bg': {'attr': 'original_bg_image', 'file': "bg.jpeg", 'convert_rgba': False, 'apply_rounded': False},
            'logo': {'attr': 'original_logo_image', 'file': "Quill With Ink.png", 'convert_rgba': False,
                     'apply_rounded': False},
            'title': {'attr': 'original_title_image', 'file': "LitLoom.png", 'convert_rgba': False,
                      'apply_rounded': False},
            'top_sound_icon': {'attr': 'original_top_sound_icon_image', 'file': "Sound I.png", 'convert_rgba': True,
                               'apply_rounded': False},
            'copy_icon': {'attr': 'original_copy_icon_image', 'file': "Copy.png", 'convert_rgba': True,
                          'apply_rounded': False}
        }
        base_dir = os.path.dirname(os.path.abspath(__file__))
        for key, info in image_info.items():
            filename = info['file']
            attr_name = info['attr']
            found_path = None
            asset_path = os.path.join(base_dir, 'assets', filename)
            if os.path.exists(asset_path):
                found_path = asset_path
            else:
                current_dir_path = os.path.join(base_dir, filename)
                if os.path.exists(current_dir_path): found_path = current_dir_path
            if found_path:
                try:
                    img = Image.open(found_path)
                    if info['convert_rgba']: img = img.convert('RGBA')
                    if info['apply_rounded']: img = self.add_rounded_corners_to_image(img, 30)
                    setattr(self, attr_name, img)
                except Exception as e:
                    print(f"ERROR: Could not load image '{filename}' from '{found_path}': {e}")
                    setattr(self, attr_name, None)
            else:
                print(f"WARNING: Image '{filename}' not found in 'assets/' or current directory.")
                setattr(self, attr_name, None)
        if not all([self.original_bg_image, self.original_fg_image, self.original_title_image]):
            print(
                "CRITICAL: One or more core images (background, foreground, title) could not be loaded. UI may appear incomplete.")

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TCombobox', fieldbackground='#F0F0F0', background='#F0F0F0', foreground='#4A4A4A',
                        arrowcolor='#4A4A4A', selectbackground='#D9CFC1', bordercolor="#CBBFAC")
        style.map('TCombobox', fieldbackground=[('readonly', '#F0F0F0')])
        style.configure("Vertical.TScrollbar", gripcount=0, background="#D9CFC1", troughcolor="#F0F0F0",
                        bordercolor="#F0F0F0", arrowcolor="#4A4A4A")

    def bind_events(self):
        self.bind("<Configure>", self.handle_resize)

    def _on_button_hover(self, event, tag, bg_color, hover_color):
        self.config(cursor="hand2")
        for item_id in self.canvas.find_withtag(f"{tag}_bg"): self.canvas.itemconfig(item_id, fill=hover_color)

    def _on_button_leave(self, event, tag, bg_color, hover_color):
        self.config(cursor="")
        for item_id in self.canvas.find_withtag(f"{tag}_bg"): self.canvas.itemconfig(item_id, fill=bg_color)

    def _on_icon_button_hover(self, event, tag, bg_color, hover_color):
        self.config(cursor="hand2")
        for item_id in self.canvas.find_withtag(f"{tag}_bg"): self.canvas.itemconfig(item_id, fill=hover_color)

    def _on_icon_button_leave(self, event, tag, bg_color, hover_color):
        self.config(cursor="")
        for item_id in self.canvas.find_withtag(f"{tag}_bg"): self.canvas.itemconfig(item_id, fill=bg_color)

    def handle_resize(self, event):
        if self.resize_job_id: self.after_cancel(self.resize_job_id)
        self.resize_job_id = self.after(50, self.redraw_canvas)

    def redraw_canvas(self, force_redraw=False):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10: return
        size_changed = (w != self.last_width or h != self.last_height)
        if not size_changed and not force_redraw: return
        editor_content = self.editor_text_widget.get("1.0",
                                                     tk.END).strip() if self.editor_text_widget and self.editor_text_widget.winfo_exists() else ""
        self.canvas.delete("all")
        for widget_id in self.canvas.find_all():
            if self.canvas.type(widget_id) == 'window':
                widget = self.canvas.itemcget(widget_id, 'window')
                if isinstance(widget, tk.Widget) and widget.winfo_exists(): widget.destroy()
        self.editor_text_widget, self.analysis_text_widget = None, None
        if self.current_page == "welcome":
            self.draw_welcome_page(w, h, size_changed)
        elif self.current_page == "editor":
            self.draw_poem_editor_page(w, h, size_changed)
            if editor_content: self.editor_text_widget.insert("1.0", editor_content)
        elif self.current_page == "analysis":
            self.draw_analysis_page(w, h, size_changed)
            getattr(self, f"_generate_{self.active_analysis_button}_content")()
        self.last_width, self.last_height = w, h

    def create_canvas_button(self, canvas, x1, y1, x2, y2, text, tag, command, **kwargs):
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        bg_color = kwargs.get('bg_color', self.control_button_color)
        hover_color = kwargs.get('hover_color', self.control_button_hover_color)
        self.draw_rounded_rectangle(canvas, x1, y1, x2, y2, radius=kwargs.get('corner_radius', 20), fill=bg_color,
                                    tags=(f"{tag}_bg", tag))
        canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=text,
                           font=("Georgia", kwargs.get('font_size', 12), "bold"),
                           fill=kwargs.get('text_color', "#4A4A4A"), tags=(f"{tag}_text", tag))
        canvas.tag_bind(tag, "<Button-1>", lambda e: command())
        canvas.tag_bind(tag, "<Enter>", lambda e: self._on_button_hover(e, tag, bg_color, hover_color))
        canvas.tag_bind(tag, "<Leave>", lambda e: self._on_button_leave(e, tag, bg_color, hover_color))

    def create_sidebar_button(self, x1, y1, x2, y2, label, tag, command, **kwargs):
        is_active = kwargs.get('is_active', tag == self.active_analysis_button)
        special_color = kwargs.get('special_color', False)
        if special_color:
            bg, hover = ("#F3D7CA", "#E2C6BA")
        else:
            bg, hover = ("#D4E2D4", "#C3D1C3") if is_active else ("#E5E5E5", "#DCDCDC")
        self.create_canvas_button(self.canvas, x1, y1, x2, y2, label, tag, command, corner_radius=15, font_size=14,
                                  bg_color=bg, hover_color=hover, text_color="#4A4A4A")

    def create_icon_button(self, x, y, image, tag, command, **kwargs):
        width, height = kwargs.get('width', 40), kwargs.get('height', 40)
        bg_color = kwargs.get('bg_color', self.control_button_color)
        hover_color = kwargs.get('hover_color', self.control_button_hover_color)
        self.draw_rounded_rectangle(self.canvas, x - width / 2, y - height / 2, x + width / 2, y + height / 2,
                                    radius=width / 2, fill=bg_color, tags=(f"{tag}_bg", tag))
        temp_img = image.copy() if hasattr(image, 'copy') else image
        if hasattr(temp_img, 'thumbnail'): temp_img.thumbnail((width * 0.7, height * 0.7), Image.Resampling.LANCZOS)
        photo_image = ImageTk.PhotoImage(temp_img) if not isinstance(temp_img, ImageTk.PhotoImage) else temp_img
        if not hasattr(self.canvas, 'image_references'): self.canvas.image_references = []
        self.canvas.image_references.append(photo_image)
        self.canvas.create_image(int(x), int(y), image=photo_image, anchor="center", tags=(f"{tag}_image", tag))
        self.canvas.tag_bind(tag, "<Button-1>", lambda e: command())
        self.canvas.tag_bind(tag, "<Enter>", lambda e: self._on_icon_button_hover(e, tag, bg_color, hover_color))
        self.canvas.tag_bind(tag, "<Leave>", lambda e: self._on_icon_button_leave(e, tag, bg_color, hover_color))

    def draw_welcome_page(self, w, h, size_changed):
        if (size_changed or not self.bg_photo) and self.original_bg_image:
            self.bg_photo = ImageTk.PhotoImage(self.original_bg_image.resize((w, h), Image.Resampling.LANCZOS))
        if self.bg_photo:
            self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")
        else:
            self.canvas.configure(bg="#FDFDFD")
        if (size_changed or not self.welcome_icon_photo) and self.original_welcome_icon_image:
            img_copy = self.original_welcome_icon_image.copy()
            img_copy.thumbnail((50, 50), Image.Resampling.LANCZOS)
            self.welcome_icon_photo = ImageTk.PhotoImage(img_copy)
        if self.welcome_icon_photo: self.create_icon_button(30, 30, self.welcome_icon_photo, "welcome_app_icon",
                                                            lambda: None, width=50, height=50, bg_color="#C7B6A4",
                                                            hover_color="#D9CFC1")
        if (size_changed or not self.fg_photo) and self.original_fg_image:
            img = self.original_fg_image.copy()
            img.thumbnail((w * 0.85, h * 0.75), Image.Resampling.LANCZOS)
            self.fg_photo = ImageTk.PhotoImage(self.add_rounded_corners_to_image(img, 30))
        if self.fg_photo: self.canvas.create_image(w / 2, h / 2 + h * 0.05, image=self.fg_photo)
        if (size_changed or not self.title_photo) and self.original_title_image:
            img = self.original_title_image.copy()
            img.thumbnail((w * 0.4, 100), Image.Resampling.LANCZOS)
            self.title_photo = ImageTk.PhotoImage(img)
        if self.title_photo:
            self.canvas.create_image(w / 2, h * 0.15, image=self.title_photo)
        else:
            self.canvas.create_text(w / 2, h * 0.15, text="Lit-Loom", font=("Georgia", 60, "bold"), fill="white")
        btn_w, btn_h, btn_cx, btn_cy = 200, 50, w / 2, h * 0.55
        self.create_canvas_button(self.canvas, btn_cx - btn_w / 2, btn_cy - btn_h / 2, btn_cx + btn_w / 2,
                                  btn_cy + btn_h / 2,
                                  text="Let's Go!", tag="start_btn", command=self.go_to_editor_page, corner_radius=25,
                                  font_size=16, bg_color=self.button_bg_color, hover_color=self.button_hover_color,
                                  text_color="white")

    def draw_poem_editor_page(self, w, h, size_changed):
        self.current_page = "editor"
        bg, sidebar, content, text_color = "#B48C68", "#C7B6A4", "#E5E5E5", "#4A4A4A"
        self.canvas.configure(bg=bg)
        border, sidebar_w, top_m, content_p = 20, 220, 80, 40
        self.draw_rounded_rectangle(self.canvas, border, border, w - border, h - border, radius=25, fill=sidebar)
        self.draw_rounded_rectangle(self.canvas, sidebar_w, top_m, w - content_p, h - content_p, radius=20,
                                    fill=content)
        heading_y = (top_m + border) / 2
        self.canvas.create_text((w + sidebar_w) / 2, heading_y, text="Write Your Poem", font=("Georgia", 22, "bold"),
                                fill=text_color)
        if (size_changed or not self.logo_photo) and self.original_logo_image:
            img_copy = self.original_logo_image.copy()
            img_copy.thumbnail((45, 45), Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(img_copy)
        if self.logo_photo: self.canvas.create_image(60, 60, image=self.logo_photo)
        text_frame = tk.Frame(self, bg=content, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", style="Vertical.TScrollbar")
        self.editor_text_widget = tk.Text(text_frame, bg=content, fg=text_color, font=("Georgia", 25), bd=0,
                                          highlightthickness=0,
                                          wrap="word", insertbackground=text_color, selectbackground=sidebar, undo=True,
                                          yscrollcommand=scrollbar.set, relief="flat")
        scrollbar.config(command=self.editor_text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        self.editor_text_widget.pack(side="left", fill="both", expand=True)
        self._create_text_context_menu(self.editor_text_widget)
        self.canvas.create_window(sidebar_w + 10, top_m + 10, window=text_frame, anchor="nw",
                                  width=w - sidebar_w - content_p - 20, height=h - top_m - content_p - 20)
        btn_w, btn_h, btn_cx = 150, 40, sidebar_w / 2 + 10
        buttons = {"example_btn": (120, "Add Example", self.show_example_poem),
                   "spell_btn": (180, "Spell Correct", self.run_spell_correct),
                   "clear_editor_btn": (240, "Clear", self.clear_editor_text),
                   "analyze_btn": (h - 100, "Analyze", self.run_analyze)}
        for tag, (y, text, cmd) in buttons.items():
            self.create_canvas_button(self.canvas, btn_cx - btn_w / 2, y, btn_cx + btn_w / 2, y + btn_h, text=text,
                                      tag=tag,
                                      command=cmd, corner_radius=20, font_size=12 if 'analyze' not in tag else 14,
                                      text_color=text_color)
        if (size_changed or not self.bottom_sound_icon_photo) and self.original_bottom_sound_icon_image:
            img_copy = self.original_bottom_sound_icon_image.copy()
            img_copy.thumbnail((60, 60), Image.Resampling.LANCZOS)
            self.bottom_sound_icon_photo = ImageTk.PhotoImage(img_copy)
        if self.bottom_sound_icon_photo: self.create_icon_button(w - content_p - 35, h - content_p - 35,
                                                                 self.bottom_sound_icon_photo, "sound_icon_bottom",
                                                                 self.open_tts_popup, width=60, height=60)
        if (size_changed or not self.top_sound_icon_photo) and self.original_top_sound_icon_image:
            img_copy = self.original_top_sound_icon_image.copy()
            img_copy.thumbnail((40, 40), Image.Resampling.LANCZOS)
            self.top_sound_icon_photo = ImageTk.PhotoImage(img_copy)
        if self.top_sound_icon_photo: self.create_icon_button(w - 70, heading_y, self.top_sound_icon_photo,
                                                              "sound_icon_top", self.open_tts_popup)
        if (size_changed or not self.copy_icon_photo) and self.original_copy_icon_image:
            img_copy = self.original_copy_icon_image.copy()
            img_copy.thumbnail((40, 40), Image.Resampling.LANCZOS)
            self.copy_icon_photo = ImageTk.PhotoImage(img_copy)
        if self.copy_icon_photo: self.create_icon_button(w - 120, heading_y, self.copy_icon_photo, "copy_editor_btn",
                                                         lambda: self.copy_text_to_clipboard(self.editor_text_widget))

    def draw_analysis_page(self, w, h, size_changed):
        self.current_page = "analysis"
        self.canvas.configure(bg="#CBBFAC")
        self.draw_rounded_rectangle(self.canvas, 240, 40, w - 40, h - 40, radius=20, fill="#F0F0F0", outline="")
        if (size_changed or not self.logo_photo) and self.original_logo_image:
            img_copy = self.original_logo_image.copy()
            img_copy.thumbnail((45, 45), Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(img_copy)
        if self.logo_photo: self.canvas.create_image(125, 55, image=self.logo_photo)
        btn_y, btn_config = 120, {"overview": "Overview", "parts_of_speech": "Parts of speech",
                                  "figure_of_speech": "Figure of speech", "tone": "Tone"}
        for tag, label in btn_config.items():
            self.create_sidebar_button(30, btn_y, 210, btn_y + 45, label, tag,
                                       lambda t=tag: self.switch_active_analysis(t))
            btn_y += 60
        self.create_sidebar_button(30, btn_y, 210, btn_y + 45, "Back to poem", "back_to_poem", self.go_back_to_editor,
                                   is_active=False)
        self.canvas.create_text(125, h - 190, text="Language", font=("Georgia", 14), fill="#5a5a5a")
        self.create_sidebar_button(30, h - 170, 210, h - 125, "Translation", "translation",
                                   lambda: self.switch_active_analysis("translation"), special_color=True)
        supported_langs_dict = GoogleTranslator().get_supported_languages(as_dict=True)
        self.all_langs_display_names, self.all_langs_codes = sorted(
            list(supported_langs_dict.keys())), supported_langs_dict
        self.lang_var = tk.StringVar(self)
        self.lang_dropdown = ttk.Combobox(self, textvariable=self.lang_var, values=self.all_langs_display_names,
                                          state='readonly', width=18, style='TCombobox', font=("Georgia", 10))
        self.lang_dropdown.set("Select Language...")
        self.lang_dropdown.bind("<<ComboboxSelected>>", self.translate_poem_for_display)
        self.canvas.create_window(125, h - 100, window=self.lang_dropdown)
        self.create_sidebar_button(30, h - 60, 210, h - 15, "Convert to PDF", "convert_pdf_btn",
                                   self.open_pdf_export_dialog, is_active=False)
        text_frame = tk.Frame(self, bg="#F0F0F0", bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", style="Vertical.TScrollbar")
        self.analysis_text_widget = tk.Text(text_frame, bg="#F0F0F0", fg="#4A4A4A",
                                            font=("Georgia", self.current_font_size), bd=0, highlightthickness=0,
                                            wrap="word", yscrollcommand=scrollbar.set, relief="flat", state='disabled')
        scrollbar.config(command=self.analysis_text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        self.analysis_text_widget.pack(side="left", fill="both", expand=True)
        self._create_text_context_menu(self.analysis_text_widget)
        self.canvas.create_window(250, 90, window=text_frame, anchor="nw", width=w - 300, height=h - 140)
        if (size_changed or not self.top_sound_icon_photo) and self.original_top_sound_icon_image:
            img_copy = self.original_top_sound_icon_image.copy()
            img_copy.thumbnail((35, 35), Image.Resampling.LANCZOS)
            self.top_sound_icon_photo = ImageTk.PhotoImage(img_copy)
        if self.top_sound_icon_photo: self.create_icon_button(w - 60, 60, self.top_sound_icon_photo, "audio_btn",
                                                              self.open_tts_popup, width=35, height=35)
        if (size_changed or not self.copy_icon_photo) and self.original_copy_icon_image:
            img_copy = self.original_copy_icon_image.copy()
            img_copy.thumbnail((35, 35), Image.Resampling.LANCZOS)
            self.copy_icon_photo = ImageTk.PhotoImage(img_copy)
        if self.copy_icon_photo: self.create_icon_button(w - 105, 60, self.copy_icon_photo, "copy_analysis_btn",
                                                         lambda: self.copy_text_to_clipboard(self.analysis_text_widget),
                                                         width=35, height=35)
        self.canvas.create_text(w - 260, h - 60, text="size:", font=("Georgia", 12), fill="#5a5a5a")
        self.create_canvas_button(self.canvas, w - 220, h - 75, w - 180, h - 45, "–", "font_dec", self.decrease_font,
                                  corner_radius=10, font_size=16)
        self.create_canvas_button(self.canvas, w - 170, h - 75, w - 130, h - 45, "+", "font_inc", self.increase_font,
                                  corner_radius=10, font_size=16)
        self.create_canvas_button(self.canvas, w - 110, h - 75, w - 50, h - 45, "Clear", "clear_an",
                                  self.clear_analysis_text, corner_radius=10, font_size=10)

    def add_rounded_corners_to_image(self, img, radius):
        mask = Image.new('L', img.size, 0)
        draw = ImageDraw.Draw(mask)
        safe_radius = min(radius, img.width // 2, img.height // 2)
        draw.rounded_rectangle((0, 0) + img.size, radius=safe_radius, fill=255)
        img.putalpha(mask)
        return img

    def go_to_editor_page(self, event=None):
        self.current_page = "editor"
        self.redraw_canvas(force_redraw=True)

    def run_analyze(self, event=None):
        text = self.editor_text_widget.get("1.0", tk.END).strip()
        if not text:
            self.show_temp_message("Please enter a poem to analyze.", 2000)
            return
        self.translated_text = ""
        self.translated_lang = ""
        self.poem_text, self.current_page, self.active_analysis_button = text, "analysis", "overview"
        self.redraw_canvas(force_redraw=True)

    def go_back_to_editor(self, event=None):
        self.current_page = "editor"
        self.redraw_canvas(force_redraw=True)

    def clear_editor_text(self, event=None):
        if self.editor_text_widget and self.editor_text_widget.winfo_exists():
            self.editor_text_widget.delete("1.0", tk.END)

    def show_example_poem(self, event=None):
        if self.editor_text_widget and self.editor_text_widget.winfo_exists():
            self.editor_text_widget.delete("1.0", tk.END)
            self.editor_text_widget.insert("1.0", self.example_poems[self.current_poem_index])
            self.current_poem_index = (self.current_poem_index + 1) % len(self.example_poems)

    def run_spell_correct(self, event=None):
        if not (self.editor_text_widget and self.editor_text_widget.winfo_exists()): return
        content = self.editor_text_widget.get("1.0", tk.END)
        if not content.strip():
            self.show_temp_message("No text to spell check.", 2000)
            return
        misspelled = self.spell.unknown(set(re.findall(r'\b\w+\b', content.lower())))
        misspelled_data = []
        if misspelled:
            for word_lower in sorted(list(misspelled)):
                start_pos = "1.0"
                while True:
                    idx = self.editor_text_widget.search(word_lower, start_pos, stopindex=tk.END, nocase=1,
                                                         regexp=False)
                    if not idx: break
                    end_idx = f"{idx}+{len(word_lower)}c"
                    actual_word = self.editor_text_widget.get(idx, end_idx)
                    misspelled_data.append(
                        {'word': actual_word, 'index': idx, 'suggestions': list(self.spell.candidates(word_lower))})
                    start_pos = end_idx
            if misspelled_data:
                SpellCheckPopup(self, misspelled_data, self.editor_text_widget)
            else:
                self.show_temp_message("No misspelled words found.", 2000)
        else:
            self.show_temp_message("Spell check complete, no errors found.", 2000)

    def replace_text_at_index(self, index, old, new):
        if self.editor_text_widget and self.editor_text_widget.winfo_exists():
            self.editor_text_widget.delete(index, f"{index}+{len(old)}c")
            self.editor_text_widget.insert(index, new)

    def open_tts_popup(self, event=None):
        widget = None
        if self.current_page == "editor":
            widget = self.editor_text_widget
        elif self.current_page == "analysis":
            widget = self.analysis_text_widget
        content = widget.get("1.0", tk.END).strip() if widget and widget.winfo_exists() else ""
        if content:
            TextToSpeechPopup(self, content)
        else:
            self.show_temp_message("No text to read aloud.", 2000)

    def copy_text_to_clipboard(self, text_widget):
        if not pyperclip:
            self.show_temp_message("Pyperclip library not found. Cannot copy text.", 2000)
            return
        if text_widget and text_widget.winfo_exists():
            content = text_widget.get("1.0", tk.END).strip()
            if content:
                pyperclip.copy(content)
                self.show_temp_message("Text copied to clipboard!", 1500)
            else:
                self.show_temp_message("No text to copy.", 1500)

    def increase_font(self):
        self.current_font_size = min(32, self.current_font_size + 2)
        self.redraw_canvas(force_redraw=True)

    def decrease_font(self):
        self.current_font_size = max(8, self.current_font_size - 2)
        self.redraw_canvas(force_redraw=True)

    def clear_analysis_text(self):
        self.update_analysis_widget("", "")

    def show_temp_message(self, message, duration_ms=2000):
        self.canvas.delete("temp_message")
        cx, cy = self.winfo_width() / 2, self.winfo_height() / 2
        bbox = self.canvas.create_rectangle(cx - 150, cy - 30, cx + 150, cy + 30, fill="#333333", outline="",
                                            tags="temp_message")
        self.canvas.create_text(cx, cy, text=message, font=("Georgia", 14, "bold"), fill="white", tags="temp_message",
                                justify="center")
        self.canvas.after(duration_ms, lambda: self.canvas.delete("temp_message"))

    def update_analysis_widget(self, content, title=""):
        if not (self.analysis_text_widget and self.analysis_text_widget.winfo_exists()): return
        self.analysis_text_widget.config(state='normal')
        self.analysis_text_widget.delete('1.0', tk.END)
        self.analysis_text_widget.tag_configure("h1", font=("Georgia", self.current_font_size + 4, "bold"), spacing3=15)
        self.analysis_text_widget.tag_configure("content", lmargin1=15, lmargin2=15)
        if title: self.analysis_text_widget.insert('1.0', title + "\n\n", "h1")
        self.analysis_text_widget.insert(tk.END, content, "content")
        self.analysis_text_widget.config(state='disabled')

    def switch_active_analysis(self, button_tag):
        self.active_analysis_button = button_tag
        self.redraw_canvas(force_redraw=True)

    def _generate_overview_content(self):
        lines = self.poem_text.strip().split('\n')
        num_lines, num_words = len(lines), len(word_tokenize(self.poem_text))
        scheme, rhymes = self.analyze_rhyme_scheme(lines)
        snippet = self.poem_text[:200] + "..." if len(self.poem_text) > 200 else self.poem_text
        content = (f"Content Snippet:\n  \"{snippet}\"\n\n"
                   f"The poem has {num_lines} lines and {num_words} words.\n\n"
                   f"Rhyme Scheme: {scheme if scheme else 'Not detected'}\n\n"
                   "Rhyming Word Groups:\n" + (
                       '\n'.join(f"  - {' / '.join(g)}" for g in rhymes) if rhymes else "  - None detected"))
        self.update_analysis_widget(content, "Poem Overview")

    def _generate_parts_of_speech_content(self):
        pos_map = {'CC': 'Coordinating Conjunction', 'CD': 'Cardinal Number', 'DT': 'Determiner',
                   'EX': 'Existential There', 'FW': 'Foreign Word', 'IN': 'Preposition/Subord. Conjunction',
                   'JJ': 'Adjective', 'JJR': 'Adjective, comparative', 'JJS': 'Adjective, superlative',
                   'LS': 'List Item Marker', 'MD': 'Modal Verb', 'NN': 'Noun, singular or mass', 'NNS': 'Noun, plural',
                   'NNP': 'Proper Noun, singular', 'NNPS': 'Proper Noun, plural', 'PDT': 'Predeterminer',
                   'POS': 'Possessive Ending', 'PRP': 'Personal Pronoun', 'PRP$': 'Possessive Pronoun', 'RB': 'Adverb',
                   'RBR': 'Adverb, comparative', 'RBS': 'Adverb, superlative', 'RP': 'Particle', 'SYM': 'Symbol',
                   'TO': 'To', 'UH': 'Interjection', 'VB': 'Verb, base form', 'VBD': 'Verb, past tense',
                   'VBG': 'Verb, gerund/present participle', 'VBN': 'Verb, past participle',
                   'VBP': 'Verb, non-3rd pers singular present', 'VBZ': 'Verb, 3rd pers singular present',
                   'WDT': 'Wh-determiner', 'WP': 'Wh-pronoun', 'WP$': 'Possessive Wh-pronoun', 'WRB': 'Wh-adverb'}
        pos_groups = {}
        for word, tag in nltk.pos_tag(word_tokenize(self.poem_text)):
            if re.match(r'[a-zA-Z0-9]', word):
                mapped_tag = pos_map.get(tag, 'Other')
                if mapped_tag not in pos_groups: pos_groups[mapped_tag] = set()
                pos_groups[mapped_tag].add(word.lower())
        content = '\n\n'.join(
            f"{name}:\n  - {', '.join(sorted(list(words)))}" for name, words in sorted(pos_groups.items()))
        self.update_analysis_widget(content, "Parts of Speech")

    def _generate_figure_of_speech_content(self):
        sentences = sent_tokenize(self.poem_text)
        similes, metaphors, alliterations = [], [], []
        for s in sentences:
            if " like " in f" {s.lower()} " or " as " in f" {s.lower()} ":
                if " as " in f" {s.lower()} ":
                    if not re.search(r'\bas\s+\w+\s+as\b', s.lower()):
                        continue
                similes.append(s.strip())
            words, tagged = word_tokenize(s.lower()), nltk.pos_tag(word_tokenize(s.lower()))
            for i in range(len(tagged) - 2):
                if tagged[i][1].startswith('NN') and tagged[i + 1][0] in ['is', 'are'] and tagged[i + 2][
                    1].startswith(
                    'NN') and tagged[i][0] != tagged[i + 2][0] and tagged[i + 2][0] not in ['man', 'woman',
                                                                                            'person', 'thing',
                                                                                            'animal', 'human',
                                                                                            'boy', 'girl']:
                    metaphors.append(s.strip());
                    break
            clean_words = [w.lower() for w in words if re.match(r'^[a-z]{2,}', w)]
            if len(clean_words) >= 3:
                consonants = {w[0]: [] for w in clean_words if w and w[0] not in 'aeiou'}
                for w in clean_words:
                    if w and w[0] in consonants: consonants[w[0]].append(w)
                for char, word_list in consonants.items():
                    if len(set(word_list)) >= 3: alliterations.append(
                        f"'{s.strip()}' (Words: {', '.join(sorted(list(set(word_list))))})"); break
        content = (f"Simile (comparison using 'like' or 'as'):\n" + (
            '\n'.join(f'  - "{s}"' for s in similes) if similes else "  - No clear similes detected.") +
                   f"\n\nBasic Metaphor Detection (e.g., 'X is Y'):\n" + ('\n'.join(
                    f'  - "{s}"' for s in sorted(
                        list(set(metaphors)))) if metaphors else "  - No simple metaphors detected.") +
                   f"\n\nBasic Alliteration Detection (repeated initial consonant sounds):\n" + ('\n'.join(
                    f'  - {a}' for a in
                    sorted(list(set(alliterations)))) if alliterations else "  - No clear alliterations detected.") +
                   "\n\nNote: Figure of speech detection is complex and these are basic heuristics.")
        self.update_analysis_widget(content, "Figures of Speech")

    def _generate_tone_content(self):
        scores = self.sentiment_analyzer.polarity_scores(self.poem_text)
        if scores['compound'] >= 0.05:
            tone, mood = "Positive", "This may suggest a mood of joy, love, or hope."
        elif scores['compound'] <= -0.05:
            tone, mood = "Negative", "This may suggest a mood of sadness, anger, or despair."
        else:
            tone, mood = "Neutral", "The language is balanced, suggesting an objective or descriptive mood."
        content = f"The overall tone appears to be {tone}.\n\n{mood}\n\nTechnical Scores:\n  - Positive: {scores['pos']:.1%}\n  - Neutral: {scores['neu']:.1%}\n  - Negative: {scores['neg']:.1%}"
        self.update_analysis_widget(content, "Sentimental Tone")

    def _generate_translation_content(self):
        self.translated_text = ""
        self.translated_lang = ""
        self.update_analysis_widget("Please select a language from the dropdown menu below to translate the poem.",
                                    "Translation")

    def translate_poem_for_display(self, event=None):
        lang_name = self.lang_var.get()
        lang_code = self.all_langs_codes.get(lang_name)
        if not lang_code: return

        def do_translate():
            try:
                self.after(0, self.update_analysis_widget, "Translating...", f"Translation to {lang_name}")
                translated = GoogleTranslator(source='auto', target=lang_code).translate(self.poem_text)
                self.translated_text = translated if translated else ""
                self.translated_lang = lang_name
                self.after(0, self.update_analysis_widget, translated, f"Translation to {lang_name}")
            except Exception as e:
                self.translated_text = ""
                self.translated_lang = ""
                self.after(0, self.update_analysis_widget,
                           f"Translation failed. Check internet connection.\n\nError: {e}", "Translation Error")

        threading.Thread(target=do_translate, daemon=True).start()

    def analyze_rhyme_scheme(self, lines):
        if not lines: return "", []
        end_words = [re.sub(r'[^\w\s]', '', w[-1]).lower() for l in lines if (w := l.strip().split())]
        if not end_words: return "", []
        labels, next_char, rhymes = {}, ord('A'), {}
        for i, word in enumerate(end_words):
            if word in labels: continue
            found_rhyme = False
            for j in range(i):
                if len(word) > 2 and len(end_words[j]) > 2 and end_words[j][-3:] == word[-3:]:
                    labels[word] = labels.get(end_words[j], chr(next_char))
                    found_rhyme = True
                    break
            if not found_rhyme:
                labels[word] = chr(next_char)
                next_char += 1
        scheme = "".join([labels.get(w, '?') for w in end_words])
        rhyme_groups = {}
        for word, label in labels.items():
            if label not in rhyme_groups: rhyme_groups[label] = set()
            rhyme_groups[label].add(word)
        final_rhymes = [sorted(list(rhyme_groups[key])) for key in sorted(rhyme_groups.keys())]
        return scheme, final_rhymes

    def open_pdf_export_dialog(self):
        if not self.poem_text.strip():
            self.show_temp_message("No poem text to convert to PDF.", 2000)
            return
        ExportPdfPopup(self, self._generate_pdf_content)

    def _generate_pdf_content(self, output_dir):
        # --- THIS IS THE FULLY CORRECTED PDF GENERATION METHOD ---
        pdf_filename = os.path.join(output_dir, "LitLoom_Analysis_Report.pdf")
        doc = SimpleDocTemplate(pdf_filename, pagesize=letter,
                                leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                                topMargin=0.75 * inch, bottomMargin=0.75 * inch)
        Story, styles = [], getSampleStyleSheet()

        # Define custom styles
        title_style = ParagraphStyle('TitleStyle', parent=styles['h1'], fontName=f'{default_font_for_pdf}-Bold',
                                     fontSize=18,
                                     alignment=1, spaceAfter=18)
        heading_style = ParagraphStyle('HeadingStyle', parent=styles['h2'], fontName=f'{default_font_for_pdf}-Bold',
                                       fontSize=14,
                                       leading=18, spaceBefore=12, spaceAfter=6)
        normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName=default_font_for_pdf,
                                      fontSize=10, leading=14, spaceAfter=6)
        code_style = ParagraphStyle('CodeStyle', parent=styles['Normal'], fontName=default_font_for_pdf,
                                    fontSize=10,
                                    leading=12, spaceAfter=12, borderPadding=8,
                                    borderColor=tk.Frame(self).cget('background'),
                                    backColor='#F5F5F5', leftIndent=10)

        # 1. Title
        Story.append(Paragraph("LitLoom Poem Analysis Report", title_style))

        # 2. Original Poem
        Story.append(Paragraph("Original Poem", heading_style))
        poem_for_pdf = self.poem_text.strip().replace('\n', '<br/>')
        Story.append(Paragraph(poem_for_pdf, code_style))
        Story.append(Spacer(1, 0.1 * inch))

        # 3. Poem Overview
        Story.append(Paragraph("Poem Overview", heading_style))
        lines = self.poem_text.strip().split('\n')
        num_lines, num_words = len(lines), len(word_tokenize(self.poem_text))
        scheme, rhymes = self.analyze_rhyme_scheme(lines)
        Story.append(Paragraph(f"<b>Line Count:</b> {num_lines}", normal_style))
        Story.append(Paragraph(f"<b>Word Count:</b> {num_words}", normal_style))
        Story.append(Paragraph(f"<b>Rhyme Scheme:</b> {scheme if scheme else 'Not detected'}", normal_style))
        rhyme_text = "<br/>".join(f"• {' / '.join(g)}" for g in rhymes) if rhymes else "• None detected"
        Story.append(Paragraph(f"<b>Rhyming Word Groups:</b><br/>{rhyme_text}", normal_style))
        Story.append(Spacer(1, 0.2 * inch))

        # 4. Sentimental Tone
        Story.append(Paragraph("Sentimental Tone", heading_style))
        scores = self.sentiment_analyzer.polarity_scores(self.poem_text)
        if scores['compound'] >= 0.05:
            tone, mood = "Positive", "This may suggest a mood of joy, love, or hope."
        elif scores['compound'] <= -0.05:
            tone, mood = "Negative", "This may suggest a mood of sadness, anger, or despair."
        else:
            tone, mood = "Neutral", "The language is balanced, suggesting an objective or descriptive mood."
        tone_content = f"""
            <b>Overall Tone:</b> {tone}<br/>
            {mood}<br/><br/>
            <b><u>Scores:</u></b><br/>
            • Positive: {scores['pos']:.1%}<br/>
            • Neutral: {scores['neu']:.1%}<br/>
            • Negative: {scores['neg']:.1%}
        """
        Story.append(Paragraph(tone_content, normal_style))
        Story.append(Spacer(1, 0.2 * inch))

        # 5. Figures of Speech
        Story.append(Paragraph("Figures of Speech", heading_style))
        fos_sentences = sent_tokenize(self.poem_text)
        similes, metaphors, alliterations = [], [], []
        for s in fos_sentences:
            s_lower = f" {s.lower()} "
            if " like " in s_lower or " as " in s_lower:
                if " as " in s_lower and not re.search(r'\bas\s+\w+\s+as\b', s.lower()):
                    continue
                similes.append(s.strip())

            words, tagged = word_tokenize(s.lower()), nltk.pos_tag(word_tokenize(s.lower()))
            for i in range(len(tagged) - 2):
                if tagged[i][1].startswith('NN') and tagged[i + 1][0] in ['is', 'are'] and tagged[i + 2][
                    1].startswith('NN') and tagged[i][0] != tagged[i + 2][0]:
                    metaphors.append(s.strip())
                    break
            clean_words = [w.lower() for w in word_tokenize(s) if re.match(r'^[a-z]{2,}', w)]
            if len(clean_words) >= 3:
                consonants = {w[0]: [] for w in clean_words if w and w[0] not in 'aeiou'}
                for w in clean_words:
                    if w and w[0] in consonants: consonants[w[0]].append(w)
                for char, word_list in consonants.items():
                    if len(set(word_list)) >= 3:
                        alliterations.append(f"'{s.strip()}' (Words: {', '.join(sorted(list(set(word_list))))})")
                        break
        similes_text = '<br/>'.join(f'• "{s}"' for s in similes) if similes else "• No clear similes detected."
        metaphors_text = '<br/>'.join(
            f'• "{s}"' for s in sorted(list(set(metaphors)))) if metaphors else "• No simple metaphors detected."
        alliterations_text = '<br/>'.join(
            f'• {a}' for a in
            sorted(list(set(alliterations)))) if alliterations else "• No clear alliterations detected."
        fos_content = f"""
            <b>Similes (using 'like' or 'as'):</b><br/>{similes_text}<br/><br/>
            <b>Metaphors (e.g., 'X is Y'):</b><br/>{metaphors_text}<br/><br/>
            <b>Alliteration (repeated initial consonants):</b><br/>{alliterations_text}
        """
        Story.append(Paragraph(fos_content, normal_style))
        Story.append(Spacer(1, 0.2 * inch))

        # 6. Parts of Speech
        Story.append(Paragraph("Parts of Speech", heading_style))
        pos_map = {'NN': 'Noun', 'NNS': 'Noun, plural', 'NNP': 'Proper Noun', 'NNPS': 'Proper Noun, plural',
                   'VB': 'Verb', 'VBD': 'Verb, past tense', 'VBG': 'Verb, gerund', 'VBN': 'Verb, past participle',
                   'VBP': 'Verb, present', 'VBZ': 'Verb, 3rd person singular',
                   'JJ': 'Adjective', 'JJR': 'Adjective, comparative', 'JJS': 'Adjective, superlative',
                   'RB': 'Adverb', 'RBR': 'Adverb, comparative', 'RBS': 'Adverb, superlative',
                   'IN': 'Preposition', 'PRP': 'Pronoun', 'PRP$': 'Possessive Pronoun', 'CC': 'Conjunction'}
        pos_groups = {}
        for word, tag in nltk.pos_tag(word_tokenize(self.poem_text)):
            if re.match(r'[a-zA-Z0-9]', word):
                first_two = tag[:2]
                mapped_tag = pos_map.get(tag, pos_map.get(first_two, 'Other'))
                if mapped_tag not in pos_groups: pos_groups[mapped_tag] = set()
                pos_groups[mapped_tag].add(word.lower())
        pos_content = '<br/>'.join(
            f"<b>{name}s:</b> {', '.join(sorted(list(words)))}" for name, words in sorted(pos_groups.items()))
        Story.append(Paragraph(pos_content, normal_style))
        Story.append(Spacer(1, 0.2 * inch))

        # 7. Translation (if it exists)
        if self.translated_text and self.translated_lang:
            Story.append(Paragraph(f"Translation ({self.translated_lang})", heading_style))
            translated_for_pdf = self.translated_text.strip().replace('\n', '<br/>')
            Story.append(Paragraph(translated_for_pdf, code_style))

        # Build the document
        try:
            doc.build(Story)
            self.show_temp_message(f"PDF saved as {os.path.basename(pdf_filename)}", 3000)
        except Exception as e:
            error_message = f"Failed to create PDF. Ensure the file is not open elsewhere and check permissions. Details: {e}"
            self.show_temp_message(error_message, 5000)


if __name__ == "__main__":
    app = LitLoomApp()
    app.mainloop()
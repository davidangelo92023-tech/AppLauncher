import os
import sys
import json
import math
import re
import ast
import shutil
import random
import colorsys
import struct
import subprocess
import winsound
import ctypes
import ctypes.wintypes as wintypes
import threading
import time
import datetime
import getpass
import webbrowser
import urllib.request
import urllib.parse
import socket
import difflib
import platform
import tkinter as tk
from tkinter import font as tkfont
from tkinter import colorchooser, filedialog, messagebox

from PIL import Image, ImageDraw, ImageFilter, ImageTk

import AppGames
from AppGames import (GamesWindow, ChessWindow, TicTacToeWindow, Connect4Window,
                      SnakeWindow, Tile2048Window, WordleWindow, MemoryWindow)

APPS_DIR = r"C:\Users\taxvi\OneDrive\Desktop\apps"

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AppLauncher")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
STATS_FILE = os.path.join(CONFIG_DIR, "stats.json")
SOUNDS_DIR = os.path.join(CONFIG_DIR, "sounds")

# ------- themes -------
THEMES = {
    "Nebula":   {"bg_top": (24, 29, 50),  "bg_bottom": (11, 13, 20), "glow": (86, 108, 255), "accent": "#6c8cff"},
    "Crimson":  {"bg_top": (44, 16, 26),  "bg_bottom": (12, 6, 10),  "glow": (255, 84, 94),  "accent": "#ff5a66"},
    "Emerald":  {"bg_top": (13, 40, 34),  "bg_bottom": (7, 15, 13),  "glow": (64, 224, 158), "accent": "#3ee69e"},
    "Sunset":   {"bg_top": (52, 26, 38),  "bg_bottom": (15, 10, 16), "glow": (255, 150, 82), "accent": "#ff9e58"},
    "Cyber":    {"bg_top": (22, 24, 54),  "bg_bottom": (10, 8, 24),  "glow": (0, 244, 208),  "accent": "#00f4d0"},
    "Mono":     {"bg_top": (33, 35, 41),  "bg_bottom": (13, 14, 17), "glow": (150, 158, 176),"accent": "#a5aebb"},
}

ACCENT_SWATCHES = ["#6c8cff", "#a06cff", "#ff6cb2", "#4ade80",
                   "#ffb454", "#38d2e6", "#ff6b6b", "#00f4d0"]

ICON_SIZES = {"Small": 44, "Medium": 56, "Large": 72}

DEFAULT_CONFIG = {
    "theme": "Nebula",
    "custom_accent": None,
    "icon_size": 56,
    "click": "single",
    "on_top": False,
    "auto_refresh": True,
    "sort": "name",
    "particles": True,
    "card_anim": True,
    "confetti": True,
    "party": False,
    "sound": False,
    "aurora": False,
    "stats": True,
    "tray": False,
    "launch_sound": "Coin",
    "radius": 18,
    "label_size": 9,
    "alpha": 1.0,
    "max_cols": 8,
    "scroll_speed": 1,
    "particle_density": 3,
    "hover_glow": True,
    "hover_color": None,
    "show_count": True,
    "bg_top": None,
    "bg_bottom": None,
    "glow": None,
    "card_color": None,
    "card_border": None,
    "shadow_color": None,
    "text_color": None,
    "muted_color": None,
    "particle_color": None,
    "browser_bg_top": None,
    "browser_bg_bottom": None,
    "browser_accent": None,
    "browser_button": None,
    "browser_search": None,
    "browser_text": None,
    "ai_api_key": "",
    "ai_api_url": "https://api.openai.com/v1/chat/completions",
    "ai_model": "gpt-4o-mini",
}

# ------- fixed palette (works with any accent) -------
CARD_FILL_HEX = "#262c40"
CARD_HOVER_HEX = "#313a55"
CARD_BORDER_HEX = "#3b4470"
SHADOW_HEX = "#0a0c12"
SEARCH_FILL_HEX = "#1a1f30"
BUTTON_FILL_HEX = "#2c3450"
BUTTON_HOVER_HEX = "#38415f"
TEXT_HEX = "#e9ecf5"
MUTED_HEX = "#8b93a7"
ACCENTS = ["#6c8cff", "#a06cff", "#ff6cb2", "#4ade80",
           "#ffb454", "#38d2e6", "#ff6b6b", "#c084fc"]

# ------- geometry -------
CARD_W = 170
H_GAP = 14
V_GAP = 20
MARGIN = 30
HEADER_Y = 118
FOOTER_H = 46


def _hex(c):
    return "#%02x%02x%02x" % c


def accent_for(name):
    h = 0
    for ch in name:
        h = (h * 31 + ord(ch)) & 0x7FFFFFFF
    return ACCENTS[h % len(ACCENTS)]


def unique_path(path):
    if not os.path.exists(path):
        return path
    folder, base = os.path.split(path)
    stem, ext = os.path.splitext(base)
    n = 1
    while os.path.exists(os.path.join(folder, f"{stem} ({n}){ext}")):
        n += 1
    return os.path.join(folder, f"{stem} ({n}){ext}")


def open_location(path):
    if os.path.isdir(path):
        os.startfile(path)
    else:
        subprocess.Popen(["explorer", f"/select,{path}"])


def create_shortcut(target, lnk_path):
    def q(s):
        return "'" + s.replace("'", "''") + "'"
    ps = ("$ws = New-Object -ComObject WScript.Shell\n"
          f"$s = $ws.CreateShortcut({q(lnk_path)})\n"
          f"$s.TargetPath = {q(target)}\n"
          "$s.Save()")
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-STA",
                    "-Command", ps], capture_output=True)


def recycle(path):
    class SHFILEOPSTRUCT(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", ctypes.c_uint),
                    ("pFrom", ctypes.c_wchar_p), ("pTo", ctypes.c_wchar_p),
                    ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", ctypes.c_wchar_p)]
    FO_DELETE, FOF_ALLOWUNDO, FOF_NOCONFIRMATION = 3, 0x40, 0x10
    op = SHFILEOPSTRUCT()
    op.wFunc = FO_DELETE
    op.pFrom = path + "\0"
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION
    ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))


# ------- soundboard -------
SR = 22050
SOUND_ICONS = {
    "Laser": "\U0001F47E", "Coin": "\U0001FA99", "Pop": "\U0001F4A5",
    "Ding": "\U0001F514", "Alarm": "\U0001F6A8", "Fanfare": "\U0001F3BA",
    "Bloop": "\U0001FAE7", "Sweep": "\U0001F30A", "Wobble": "\U0001F300",
    "Bass": "\U0001F50A", "Weird": "\U0001F4AB", "Machine": "\U0001F52B",
}


def _tone(dur, freq_fn, kind="sine", gain=0.5, decay=0.35):
    n = int(dur * SR)
    out = []
    phase = 0.0
    a = int(n * 0.01)
    r = max(1, int(n * decay))
    for i in range(n):
        f = freq_fn(i / n) if callable(freq_fn) else freq_fn
        phase += 2 * math.pi * f / SR
        ph = phase
        if kind == "sine":
            v = math.sin(ph)
        elif kind == "square":
            v = 1.0 if math.sin(ph) >= 0 else -1.0
        else:
            v = 2 * ((ph / (2 * math.pi)) - math.floor(0.5 + ph / (2 * math.pi)))
        if i < a:
            v *= i / a
        elif i > n - r:
            v *= max(0.0, (n - i) / r)
        out.append(int(max(-1.0, min(1.0, v)) * gain * 32767))
    return out


def _noise(dur, gain=0.4, decay=0.3):
    n = int(dur * SR)
    out = []
    a = int(n * 0.01)
    r = max(1, int(n * decay))
    prev = 0.0
    for i in range(n):
        v = prev + 0.6 * (random.uniform(-1, 1) - prev)
        prev = v
        if i < a:
            v *= i / a
        elif i > n - r:
            v *= max(0.0, (n - i) / r)
        out.append(int(max(-1.0, min(1.0, v)) * gain * 32767))
    return out


def _s_laser():
    return _tone(0.28, lambda t: 900 - 750 * t, "saw", gain=0.4, decay=0.6)


def _s_coin():
    return _tone(0.09, 988, "sine", gain=0.5, decay=0.2) + \
           _tone(0.3, 1319, "sine", gain=0.5, decay=0.5)


def _s_pop():
    return _tone(0.08, 380, "sine", gain=0.7, decay=0.5)


def _s_ding():
    return _tone(1.0, 1568, "sine", gain=0.5, decay=0.75)


def _s_alarm():
    one = _tone(0.22, 760, "square", gain=0.3, decay=0.05)
    two = _tone(0.22, 540, "square", gain=0.3, decay=0.05)
    return (one + two + one + two) * 2


def _s_fanfare():
    out = []
    for f in (523, 659, 784, 1047):
        out += _tone(0.14, f, "square", gain=0.28, decay=0.15)
    return out


def _s_bloop():
    return _tone(0.3, lambda t: 200 + 500 * t, "sine", gain=0.5, decay=0.5)


def _s_error():
    return (_noise(0.18, gain=0.35, decay=0.05)
            + _tone(0.12, 140, "square", gain=0.3, decay=0.1)
            + _noise(0.18, gain=0.35, decay=0.05)
            + _tone(0.2, 120, "square", gain=0.28, decay=0.4))


def _s_sweep():
    return _tone(0.6, lambda t: 150 + 1200 * t, "sine", gain=0.45, decay=0.5)


def _s_wobble():
    return _tone(0.5, lambda t: 120 + 30 * math.sin(t * 40 * math.pi), "saw", gain=0.4, decay=0.5)


def _s_bass():
    return _tone(0.5, 70, "sine", gain=0.7, decay=0.6)


def _s_weird():
    return (_tone(0.5, lambda t: 800 - 1400 * t, "sine", gain=0.4, decay=0.4)
            + _tone(0.5, lambda t: 150 + 800 * t, "sine", gain=0.4, decay=0.4))


def _s_machine():
    out = []
    for _ in range(8):
        out += _tone(0.05, 500, "square", gain=0.35, decay=0.05)
        out += _noise(0.03, gain=0.25, decay=0.2)
    return out


SOUND_DEFS = {
    "Laser": _s_laser, "Coin": _s_coin, "Pop": _s_pop, "Ding": _s_ding,
    "Alarm": _s_alarm, "Fanfare": _s_fanfare, "Bloop": _s_bloop,
    "Sweep": _s_sweep, "Wobble": _s_wobble, "Bass": _s_bass,
    "Weird": _s_weird, "Machine": _s_machine,
}


def ensure_sounds():
    try:
        os.makedirs(SOUNDS_DIR, exist_ok=True)
        for name, gen in SOUND_DEFS.items():
            path = os.path.join(SOUNDS_DIR, name + ".wav")
            if not os.path.exists(path):
                samples = gen()
                with open(path, "wb") as wf:
                    import wave
                    with wave.open(wf, "wb") as f:
                        f.setnchannels(1)
                        f.setsampwidth(2)
                        f.setframerate(SR)
                        f.writeframes(struct.pack("<%dh" % len(samples), *samples))
    except Exception:
        pass


def play_sound(name):
    if name not in SOUND_DEFS:
        return
    ensure_sounds()
    try:
        winsound.PlaySound(os.path.join(SOUNDS_DIR, name + ".wav"),
                           winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass


class SHFILEINFO(ctypes.Structure):
    _fields_ = [
        ("hIcon", wintypes.HANDLE),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", wintypes.DWORD),
        ("szDisplayName", ctypes.c_wchar * 260),
        ("szTypeName", ctypes.c_wchar * 80),
    ]


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", wintypes.HBITMAP),
        ("hbmColor", wintypes.HBITMAP),
    ]


class BITMAP(ctypes.Structure):
    _fields_ = [
        ("bmType", ctypes.c_long),
        ("bmWidth", ctypes.c_long),
        ("bmHeight", ctypes.c_long),
        ("bmWidthBytes", ctypes.c_long),
        ("bmPlanes", ctypes.c_short),
        ("bmBitsPixel", ctypes.c_short),
        ("bmBits", ctypes.c_void_p),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", ctypes.c_ubyte * 4)]


def hicon_to_pil(hIcon):
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    user32.GetIconInfo.argtypes = [wintypes.HICON, ctypes.POINTER(ICONINFO)]
    user32.GetIconInfo.restype = wintypes.BOOL
    gdi32.GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p]
    gdi32.GetObjectW.restype = ctypes.c_int
    gdi32.GetDIBits.argtypes = [
        wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
        ctypes.c_void_p, ctypes.POINTER(BITMAPINFO), wintypes.UINT,
    ]
    gdi32.GetDIBits.restype = ctypes.c_int
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.ReleaseDC.restype = ctypes.c_int
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteObject.restype = wintypes.BOOL

    info = ICONINFO()
    if not user32.GetIconInfo(hIcon, ctypes.byref(info)):
        return None

    hbm = info.hbmColor or info.hbmMask
    bmp = BITMAP()
    if not gdi32.GetObjectW(hbm, ctypes.sizeof(bmp), ctypes.byref(bmp)):
        return None

    w, h = bmp.bmWidth, bmp.bmHeight
    if w <= 0 or h <= 0:
        return None

    buf = ctypes.create_string_buffer(w * h * 4)
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0

    hdc = user32.GetDC(0)
    try:
        lines = gdi32.GetDIBits(hdc, hbm, 0, h, buf, ctypes.byref(bmi), 0)
    finally:
        user32.ReleaseDC(0, hdc)

    if info.hbmMask:
        gdi32.DeleteObject(info.hbmMask)
    if info.hbmColor:
        gdi32.DeleteObject(info.hbmColor)

    if lines == 0:
        return None

    img = Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1)
    img = img.convert("RGBA")

    alpha = img.getchannel("A")
    if not alpha.getextrema()[1]:
        img = img.convert("RGB")
        img.putalpha(255)

    return img


def get_file_icon(path, size=56):
    shinfo = SHFILEINFO()
    shell32 = ctypes.windll.shell32
    SHGFI_ICON = 0x100
    SHGFI_LARGEICON = 0x0
    shell32.SHGetFileInfoW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(SHFILEINFO),
        ctypes.c_int, wintypes.UINT,
    ]
    shell32.SHGetFileInfoW.restype = ctypes.c_size_t
    user32 = ctypes.windll.user32
    user32.DestroyIcon.argtypes = [wintypes.HICON]
    user32.DestroyIcon.restype = wintypes.BOOL

    res = shell32.SHGetFileInfoW(
        path, 0, ctypes.byref(shinfo), ctypes.sizeof(shinfo),
        SHGFI_ICON | SHGFI_LARGEICON,
    )
    if not res or not shinfo.hIcon:
        return None
    try:
        img = hicon_to_pil(shinfo.hIcon)
    finally:
        user32.DestroyIcon(shinfo.hIcon)
    if img is None:
        return None
    img = img.resize((size, size), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


def fallback_icon(size=56):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, size - 3, size - 3], radius=14, fill="#3a4050", outline="#4b5468", width=2)
    d.rounded_rectangle([size // 2 - 8, size // 4, size // 2 + 8, size // 4 + 16], radius=2, fill="#6c8cff")
    d.polygon([(size // 2, size // 2), (size // 2 - 10, size // 2 + 16), (size // 2 + 10, size // 2 + 16)], fill="#6c8cff")
    d.rounded_rectangle([size // 2 - 8, size // 2 + 22, size // 2 + 8, size // 2 + 34], radius=2, fill="#6c8cff")
    return ImageTk.PhotoImage(img)


def make_tray_image():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, 58, 58], radius=14, fill="#262c40")
    d.rounded_rectangle([26, 14, 38, 26], radius=3, fill="#6c8cff")
    d.polygon([(32, 28), (22, 46), (42, 46)], fill="#6c8cff")
    d.rounded_rectangle([26, 50, 38, 53], radius=2, fill="#6c8cff")
    return img


def make_gradient(w, h, bg_top, bg_bottom):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(bg_top[0] + (bg_bottom[0] - bg_top[0]) * t)
        g = int(bg_top[1] + (bg_bottom[1] - bg_top[1]) * t)
        b = int(bg_top[2] + (bg_bottom[2] - bg_top[2]) * t)
        d.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def make_background(w, h, bg_top, bg_bottom, glow_rgb):
    img = make_gradient(w, h, bg_top, bg_bottom)

    glow = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(glow)
    rx, ry = w * 0.62, h * 0.62
    gd.ellipse([(w * 0.5 - rx, -ry), (w * 0.5 + rx, ry * 0.9)], fill=150)
    glow = glow.filter(ImageFilter.GaussianBlur(max(w, h) * 0.12))
    accent = Image.new("RGB", (w, h), glow_rgb)
    img = Image.composite(accent, img, glow)

    glow2 = Image.new("L", (w, h), 0)
    gd2 = ImageDraw.Draw(glow2)
    gd2.ellipse([(-rx * 0.6, h - ry * 0.9), (rx, h + ry)], fill=110)
    glow2 = glow2.filter(ImageFilter.GaussianBlur(max(w, h) * 0.1))
    img = Image.composite(Image.new("RGB", (w, h), (40, 24, 80)), img, glow2)

    return ImageTk.PhotoImage(img)


class AppLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("App Launcher")
        self.geometry("940x680")
        self.minsize(670, 420)

        self.font_title = tkfont.Font(family="Segoe UI", size=20, weight="bold")
        self.font_sub = tkfont.Font(family="Segoe UI", size=9)
        self.font_card = tkfont.Font(family="Segoe UI", size=9)
        self.font_footer = tkfont.Font(family="Segoe UI", size=9)
        self._badge_font = tkfont.Font(family="Segoe UI", size=8, weight="bold")

        self.config = self._load_config()
        self.icon_size = self.config["icon_size"]
        self.card_h = self.icon_size + 104

        self.items = []
        self.visible = []
        self._photos = []
        self._bg_photo = None
        self._icon_cache = {}
        self._offset = 0
        self._content_h = 0
        self._hover_idx = None
        self._pressed_idx = None
        self._drag_mode = None
        self._drag_start_y = 0
        self._drag_start_off = 0
        self._resize_job = None
        self._auto_job = None
        self._last_snap = ()
        self._card_rects = {}
        self._base_pos = {}
        self._btn_bgs = {}
        self._part_job = None
        self._party_job = None
        self._party_i = 0
        self._party_accents = []
        self._anim_jobs = []
        self._confetti_jobs = []
        self._confetti = []
        self._particles = []
        self._allow_anim = True
        self._aurora_job = None
        self._aurora_phase = 0.0
        self._gradient_cache = {}
        self._sprite_cache = {}
        self._stats_job = None
        self._weather_cache = None
        self._weather_fetching = False
        self._tray = None
        self._tray_running = False
        self._tray_action = None
        self._hotkey_job = None
        self._quitting = False
        self._launches, self._order = self._load_stats()
        self._dragged = False

        self.configure(bg=_hex(self._bg_bottom()))
        self.attributes("-topmost", bool(self.config["on_top"]))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_widgets()
        self._apply_color_widgets()
        self.refresh()
        self._start_auto()
        self._start_effects()
        self._start_stats()
        self._apply_tray()
        self.after(30, self._fade_in)

    # ---------- config ----------
    def _load_config(self):
        cfg = dict(DEFAULT_CONFIG)
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k in DEFAULT_CONFIG:
                    if k in data:
                        cfg[k] = data[k]
        except Exception:
            pass
        if cfg.get("theme") not in THEMES:
            cfg["theme"] = DEFAULT_CONFIG["theme"]
        return cfg

    def _save_config(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def _load_stats(self):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data.get("launches", {}), data.get("order", [])
        except Exception:
            pass
        return {}, []

    def _save_stats(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump({"launches": self._launches, "order": self._order}, f, indent=2)
        except Exception:
            pass

    def _record_launch(self, path):
        self._launches[path] = self._launches.get(path, 0) + 1
        self._save_stats()

    def set_config(self, key, value):
        self.config[key] = value
        self._save_config()
        self._apply_config()

    def reset_config(self):
        self.config = dict(DEFAULT_CONFIG)
        self._save_config()
        self._apply_config()

    def _apply_config(self):
        self.icon_size = self.config["icon_size"]
        self.card_h = self.icon_size + 104
        self.font_card.configure(size=self.config["label_size"])
        self.attributes("-topmost", bool(self.config["on_top"]))
        self.attributes("-alpha", float(self.config.get("alpha", 1.0)))
        self._apply_color_widgets()
        self.configure(bg=_hex(self._bg_bottom()))
        self.cv.configure(bg=_hex(self._bg_bottom()))
        self._draw_bg()
        self.refresh()
        self._start_auto()
        self._start_effects()
        self._start_stats()
        self._apply_tray()

    def _apply_color_widgets(self):
        tc, mc = self._text_color(), self._muted_color()
        for b in (self.refresh_btn, self.gear_btn, self.add_btn, self.sound_btn):
            b.config(fg=tc)
        self.search_entry.config(insertbackground=tc)
        if self._placeholder:
            self.search_entry.config(fg=mc)
        else:
            self.search_entry.config(fg=tc)

    def _theme(self):
        return THEMES[self.config["theme"]]

    def _accent(self):
        return self.config["custom_accent"] or self._theme()["accent"]

    def _rgb(self, color):
        if isinstance(color, str) and color.startswith("#"):
            color = color.lstrip("#")
            return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
        return color

    def _bg_top(self):
        return self._rgb(self.config.get("bg_top") or self._theme()["bg_top"])

    def _bg_bottom(self):
        return self._rgb(self.config.get("bg_bottom") or self._theme()["bg_bottom"])

    def _glow(self):
        return self._rgb(self.config.get("glow") or self._theme()["glow"])

    def _text_color(self):
        return self.config.get("text_color") or TEXT_HEX

    def _muted_color(self):
        return self.config.get("muted_color") or MUTED_HEX

    def _card_fill(self):
        return self.config.get("card_color") or CARD_FILL_HEX

    def _card_border(self):
        return self.config.get("card_border") or CARD_BORDER_HEX

    def _card_hover(self):
        return self.config.get("hover_color") or CARD_HOVER_HEX

    def _shadow(self):
        return self.config.get("shadow_color") or SHADOW_HEX

    def _particle_color(self):
        return self.config.get("particle_color")

    # ---------- widgets ----------
    def _build_widgets(self):
        self.cv = tk.Canvas(self, highlightthickness=0, bd=0, bg=_hex(self._bg_bottom()))
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Configure>", self._on_cv_resize)
        self.cv.bind("<MouseWheel>", self._on_wheel)
        self.cv.bind("<Motion>", self._on_motion)
        self.cv.bind("<Button-1>", self._on_press)
        self.cv.bind("<B1-Motion>", self._on_drag)
        self.cv.bind("<ButtonRelease-1>", self._on_release)
        self.cv.bind("<Double-1>", self._on_double)
        self.cv.bind("<Button-3>", self._on_context)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search())
        self._placeholder = True
        self.search_var.set("Search apps\u2026")
        self.search_entry = tk.Entry(
            self.cv, textvariable=self.search_var, font=self.font_sub,
            bg=SEARCH_FILL_HEX, fg=MUTED_HEX, insertbackground=TEXT_HEX,
            relief="flat", bd=0, highlightthickness=0, width=19,
            selectbackground=_hex(self._glow()), selectforeground="#ffffff",
        )
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)
        self.search_entry.bind("<Escape>", lambda e: self._clear_search())

        btn_font = tkfont.Font(family="Segoe UI", size=11)
        self.refresh_btn = tk.Button(
            self.cv, text="\u21bb  Refresh", command=self.refresh, font=self.font_sub,
            bg=BUTTON_FILL_HEX, fg=TEXT_HEX, activebackground=BUTTON_HOVER_HEX,
            activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
        )
        self.refresh_btn.bind("<Enter>", lambda e: self._set_btn_hover("refresh", True))
        self.refresh_btn.bind("<Leave>", lambda e: self._set_btn_hover("refresh", False))

        self.gear_btn = tk.Button(
            self.cv, text="\u2699", command=self.open_settings, font=btn_font,
            bg=BUTTON_FILL_HEX, fg=TEXT_HEX, activebackground=BUTTON_HOVER_HEX,
            activeforeground="#ffffff", relief="flat", bd=0, width=3, pady=4, cursor="hand2",
        )
        self.gear_btn.bind("<Enter>", lambda e: self._set_btn_hover("gear", True))
        self.gear_btn.bind("<Leave>", lambda e: self._set_btn_hover("gear", False))

        self.add_btn = tk.Button(
            self.cv, text="+", command=self.add_app, font=btn_font,
            bg=BUTTON_FILL_HEX, fg=TEXT_HEX, activebackground=BUTTON_HOVER_HEX,
            activeforeground="#ffffff", relief="flat", bd=0, width=3, pady=4, cursor="hand2",
        )
        self.add_btn.bind("<Enter>", lambda e: self._set_btn_hover("add", True))
        self.add_btn.bind("<Leave>", lambda e: self._set_btn_hover("add", False))

        self.sound_btn = tk.Button(
            self.cv, text="\u266a", command=self.open_soundboard, font=btn_font,
            bg=BUTTON_FILL_HEX, fg=TEXT_HEX, activebackground=BUTTON_HOVER_HEX,
            activeforeground="#ffffff", relief="flat", bd=0, width=3, pady=4, cursor="hand2",
        )
        self.sound_btn.bind("<Enter>", lambda e: self._set_btn_hover("music", True))
        self.sound_btn.bind("<Leave>", lambda e: self._set_btn_hover("music", False))

        self.assistant_btn = tk.Button(
            self.cv, text="AI", command=self.open_assistant, font=tkfont.Font(family="Segoe UI", size=10, weight="bold"),
            bg=BUTTON_FILL_HEX, fg=self._accent(), activebackground=BUTTON_HOVER_HEX,
            activeforeground="#ffffff", relief="flat", bd=0, width=3, pady=4, cursor="hand2",
        )
        self.assistant_btn.bind("<Enter>", lambda e: self._set_btn_hover("assistant", True))
        self.assistant_btn.bind("<Leave>", lambda e: self._set_btn_hover("assistant", False))

        self.games_btn = tk.Button(
            self.cv, text="Games", command=self.open_games, font=tkfont.Font(family="Segoe UI", size=10, weight="bold"),
            bg=BUTTON_FILL_HEX, fg=self._accent(), activebackground=BUTTON_HOVER_HEX,
            activeforeground="#ffffff", relief="flat", bd=0, width=6, pady=4, cursor="hand2",
        )
        self.games_btn.bind("<Enter>", lambda e: self._set_btn_hover("games", True))
        self.games_btn.bind("<Leave>", lambda e: self._set_btn_hover("games", False))

        self.browser_btn = tk.Button(
            self.cv, text="\U0001f310", command=self.open_browser, font=tkfont.Font(family="Segoe UI", size=12),
            bg=BUTTON_FILL_HEX, fg=self._accent(), activebackground=BUTTON_HOVER_HEX,
            activeforeground="#ffffff", relief="flat", bd=0, width=3, pady=2, cursor="hand2",
        )
        self.browser_btn.bind("<Enter>", lambda e: self._set_btn_hover("browser", True))
        self.browser_btn.bind("<Leave>", lambda e: self._set_btn_hover("browser", False))

        self._search_win = self.cv.create_window(0, 0, window=self.search_entry, anchor="e")
        self._btn_win = self.cv.create_window(0, 0, window=self.refresh_btn, anchor="e")
        self._gear_win = self.cv.create_window(0, 0, window=self.gear_btn, anchor="center")
        self._add_win = self.cv.create_window(0, 0, window=self.add_btn, anchor="center")
        self._music_win = self.cv.create_window(0, 0, window=self.sound_btn, anchor="center")
        self._assistant_win = self.cv.create_window(0, 0, window=self.assistant_btn, anchor="center")
        self._games_win = self.cv.create_window(0, 0, window=self.games_btn, anchor="center")
        self._browser_win = self.cv.create_window(0, 0, window=self.browser_btn, anchor="center")
        self._search_bg = None

        self.bind("<Control-f>", self._focus_search)
        self.bind("<Control-r>", lambda e: self.refresh())
        self.bind("<Control-g>", lambda e: self.open_games())
        self.bind("<Control-b>", lambda e: self.open_browser())
        self.bind("<Escape>", lambda e: self._clear_search() if not self._placeholder else None)

    def _focus_search(self, event=None):
        if self._placeholder:
            self._on_search_focus_in()
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")
        return "break"

    # ---------- background / header ----------
    def _on_cv_resize(self, event=None):
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(100, self._draw_bg)

    def _draw_bg(self, event=None):
        w, h = self.cv.winfo_width(), self.cv.winfo_height()
        if w < 10 or h < 10:
            return
        if self.config.get("aurora"):
            self._draw_aurora(w, h)
        else:
            self._bg_photo = make_background(w, h, self._bg_top(), self._bg_bottom(), self._glow())
            self.cv.delete("bg")
            self.cv.create_image(0, 0, image=self._bg_photo, anchor="nw", tags="bg")
            self.cv.tag_lower("bg")
        self.search_entry.config(selectbackground=_hex(self._glow()))
        self._layout_header()
        self._rebuild_cards()
        self._draw_stats()
        if self.config["particles"]:
            self._spawn_particles()
    # ---------- effects ----------
    def _start_effects(self):
        self._stop_effects()
        if self.config["particles"]:
            self._spawn_particles()
            self._part_job = self.after(40, self._tick_particles)
        if self.config["party"]:
            self._party_accents = [
                "#%02x%02x%02x" % tuple(int(255 * x) for x in colorsys.hsv_to_rgb(i / 24, 0.78, 0.96))
                for i in range(24)
            ]
            self._party_i = 0
            self._tick_party()
        if self.config.get("aurora"):
            self._aurora_phase = 0.0
            self._tick_aurora()

    def _stop_effects(self):
        for job in (self._part_job, self._party_job, self._aurora_job):
            if job:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
        self._part_job = None
        self._party_job = None
        self._aurora_job = None
        if hasattr(self, "cv"):
            self.cv.delete("part")

    def _spawn_particles(self):
        self.cv.delete("part")
        self._particles = []
        w = self.cv.winfo_width()
        h = self.cv.winfo_height()
        if w < 20 or h < 20:
            return
        n = int(w / 28) * int(self.config.get("particle_density", 3))
        for _ in range(n):
            x = random.uniform(0, w)
            y = random.uniform(0, h)
            vx = random.uniform(-0.25, 0.25)
            vy = random.uniform(0.12, 0.6)
            size = random.uniform(1.6, 3.6)
            color = self._particle_color() or random.choice(ACCENTS)
            self._particles.append([x, y, vx, vy, size, color])
            self.cv.create_oval(x - size, y - size, x + size, y + size,
                                fill=color, outline="", tags="part")
        self.cv.tag_lower("part")

    def _tick_particles(self):
        if not self.config["particles"]:
            return
        w = self.cv.winfo_width()
        h = self.cv.winfo_height()
        items = self.cv.find_withtag("part")
        for i, p in enumerate(self._particles):
            x, y, vx, vy, size, color = p
            x += vx
            y += vy
            if y > h + 6:
                y = -6
                x = random.uniform(0, w)
            if x > w + 6:
                x = -6
            if x < -6:
                x = w + 6
            self._particles[i][0] = x
            self._particles[i][1] = y
            if i < len(items):
                self.cv.coords(items[i], x - size, y - size, x + size, y + size)
        self._part_job = self.after(40, self._tick_particles)

    def _tick_party(self):
        self._party_i = (self._party_i + 1) % len(self._party_accents)
        if self.cv.find_withtag("accentbar"):
            self.cv.itemconfig("accentbar", fill=self._party_accents[self._party_i])
        if self.config["party"]:
            self._party_job = self.after(350, self._tick_party)

    # ---------- aurora background ----------
    def _aurora_sprite(self, bw, bh, col):
        key = (bw, bh, col)
        s = self._sprite_cache.get(key)
        if s is None:
            if len(self._sprite_cache) > 16:
                self._sprite_cache.clear()
            mask = Image.new("L", (bw, bh), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, bw - 1, bh - 1], fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(max(2, int(bw / 5))))
            sprite = Image.new("RGB", (bw, bh), col)
            s = (sprite, mask)
            self._sprite_cache[key] = s
        return s

    def _aurora_frame(self, w, h):
        key = (w, h, self._bg_top(), self._bg_bottom())
        base = self._gradient_cache.get(key)
        if base is None:
            if len(self._gradient_cache) > 4:
                self._gradient_cache.clear()
            base = make_gradient(w, h, self._bg_top(), self._bg_bottom())
            self._gradient_cache[key] = base
        img = base.copy()
        accent = self._rgb(self._accent())
        phase = self._aurora_phase
        blobs = [
            (0.5 + 0.42 * math.sin(phase * 0.8), 0.45 + 0.30 * math.cos(phase), 0.55, accent),
            (0.22 + 0.20 * math.cos(phase * 1.2), 0.75 + 0.22 * math.sin(phase * 0.9), 0.40, accent),
            (0.82 + 0.16 * math.sin(phase * 1.1), 0.22 + 0.18 * math.cos(phase * 1.4), 0.35, accent),
        ]
        for fx, fy, fs, col in blobs:
            bw = max(8, int(w * fs))
            bh = max(8, int(h * fs))
            bx = int(w * fx - bw // 2)
            by = int(h * fy - bh // 2)
            sprite, mask = self._aurora_sprite(bw, bh, col)
            img.paste(sprite, (bx, by), mask)
        return img

    def _draw_aurora(self, w, h):
        self._bg_photo = ImageTk.PhotoImage(self._aurora_frame(w, h))
        self.cv.delete("bg")
        self.cv.create_image(0, 0, image=self._bg_photo, anchor="nw", tags="bg")
        self.cv.tag_lower("bg")

    def _tick_aurora(self):
        if not self.config.get("aurora"):
            return
        self._aurora_phase += 0.05
        w, h = self.cv.winfo_width(), self.cv.winfo_height()
        if w > 10 and h > 10:
            self._draw_aurora(w, h)
        self._aurora_job = self.after(50, self._tick_aurora)

    # ---------- live stats bar ----------
    def _draw_stats(self):
        self.cv.delete("stats")
        w = self.cv.winfo_width()
        if w < 10 or not self.config.get("stats"):
            return
        y = HEADER_Y - 12
        f = self.font_footer
        mc = self._muted_color()
        clock = datetime.datetime.now().strftime("%A %I:%M %p")
        self.cv.create_text(MARGIN, y, anchor="w", text=clock, font=f, fill=mc, tags="stats")
        wea = self._weather_text()
        if wea:
            self.cv.create_text(MARGIN + 200, y, anchor="w", text=wea, font=f, fill=mc, tags="stats")
        s = self._sys_stats()
        if s:
            self.cv.create_text(w - MARGIN, y, anchor="e", text=s, font=f, fill=mc, tags="stats")

    def _start_stats(self):
        self._stop_stats()
        if self.config.get("stats"):
            self._draw_stats()
            self._stats_job = self.after(1000, self._tick_stats)

    def _stop_stats(self):
        if self._stats_job:
            try:
                self.after_cancel(self._stats_job)
            except Exception:
                pass
        self._stats_job = None
        if hasattr(self, "cv"):
            self.cv.delete("stats")

    def _tick_stats(self):
        if not self.config.get("stats"):
            return
        self._draw_stats()
        self._stats_job = self.after(1000, self._tick_stats)

    def _weather_text(self):
        now = time.time()
        if self._weather_cache and now - self._weather_cache[0] < 600:
            return self._weather_cache[1]
        if self._weather_fetching:
            return self._weather_cache[1] if self._weather_cache else ""
        self._weather_fetching = True
        threading.Thread(target=self._fetch_weather, daemon=True).start()
        return self._weather_cache[1] if self._weather_cache else ""

    def _fetch_weather(self):
        try:
            req = urllib.request.Request("https://wttr.in/?format=%c+%t,+%w",
                                         headers={"User-Agent": "curl/8.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read().decode("utf-8", "ignore").strip()
            self._weather_cache = (time.time(), data)
        except Exception:
            self._weather_cache = (time.time(), "")
        finally:
            self._weather_fetching = False

    def _sys_stats(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            return f"CPU {cpu:.0f}%  RAM {ram:.0f}%"
        except Exception:
            return ""

    def _cancel_anim(self):
        for j in self._anim_jobs:
            try:
                self.after_cancel(j)
            except Exception:
                pass
        self._anim_jobs = []

    def _animate_cards(self):
        if not self.config["card_anim"] or not self._allow_anim:
            return
        n = len(self.visible)
        if n == 0:
            return
        xs = {round(self._base_pos[i][0]) for i in range(n)}
        cols = max(1, len(xs))
        drop, frames, frame_ms = 26, 6, 16
        for i in range(n):
            tag = f"c{i}"
            self.cv.move(tag, 0, drop)
            start = (i % cols) * 18
            state = [0, 0.0]

            def step(tag=tag, state=state):
                if not self.cv.find_withtag(tag):
                    return
                state[0] += 1
                f = state[0] / frames
                eased = f * (2 - f)
                dy = drop * (eased - state[1])
                state[1] = eased
                self.cv.move(tag, 0, -dy)
                if state[0] < frames:
                    self._anim_jobs.append(self.after(frame_ms, step))

            self._anim_jobs.append(self.after(start, step))

    def _burst_confetti(self):
        self.cv.delete("confetti")
        for j in self._confetti_jobs:
            try:
                self.after_cancel(j)
            except Exception:
                pass
        self._confetti_jobs = []
        self._confetti = []
        w = self.cv.winfo_width()
        for _ in range(70):
            x = random.uniform(0, w)
            y = random.uniform(-10, -140)
            vx = random.uniform(-1.2, 1.2)
            vy = random.uniform(2.2, 5.0)
            c = random.choice(ACCENTS)
            size = random.choice([(5, 8), (4, 7), (6, 9), (3, 6), (5, 5)])
            self._confetti.append([x, y, vx, vy, c, size])
            self.cv.create_rectangle(x, y, x + size[0], y + size[1],
                                     fill=c, outline="", tags="confetti")
        self._confetti_jobs.append(self.after(30, self._tick_confetti))

    def _tick_confetti(self):
        items = self.cv.find_withtag("confetti")
        if not items:
            return
        h = self.cv.winfo_height()
        alive = False
        for i, p in enumerate(self._confetti):
            if i >= len(items):
                break
            x, y, vx, vy, c, size = p
            vy += 0.16
            vx += random.uniform(-0.05, 0.05)
            x += vx
            y += vy
            self._confetti[i][0] = x
            self._confetti[i][1] = y
            self._confetti[i][2] = vx
            self._confetti[i][3] = vy
            if y < h + 30:
                alive = True
            self.cv.coords(items[i], x, y, x + size[0], y + size[1])
        if alive:
            self._confetti_jobs.append(self.after(30, self._tick_confetti))
        else:
            self.cv.delete("confetti")
            self._confetti = []

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.cv.create_polygon(pts, smooth=True, splinesteps=24, **kw)

    def _layout_header(self):
        w = self.cv.winfo_width()
        x = MARGIN
        self.cv.delete("hdr")
        self.cv.create_text(x, 34, anchor="w", text="App Launcher",
                            font=self.font_title, fill=self._text_color(), tags="hdr")
        self.cv.create_text(x, 64, anchor="w", text=APPS_DIR,
                            font=self.font_sub, fill=self._muted_color(), tags="hdr")
        self.cv.create_rectangle(x, 78, x + 118, 82, fill=self._accent(),
                                 outline="", tags=("hdr", "accentbar"))

        right = w - MARGIN
        rw, gw, aw, mw, bw, cw, dw, gap, ew = 118, 44, 44, 44, 44, 44, 44, 8, 190
        r1 = right - rw
        g2 = r1 - gap
        g1 = g2 - gw
        a2 = g1 - gap
        a1 = a2 - aw
        m2 = a1 - gap
        m1 = m2 - mw
        b2 = m1 - gap
        b1 = b2 - bw
        c2 = b1 - gap
        c1 = c2 - cw
        d2 = c1 - gap
        d1 = d2 - dw
        s2 = d1 - gap
        s1 = s2 - ew

        self._search_bg = self._round_rect(s1, 28, s2, 60, 16,
                                           fill=SEARCH_FILL_HEX, outline=self._card_border(), tags="hdr", width=1)
        self._btn_bgs["browser"] = self._round_rect(d1, 28, d2, 60, 12, fill=BUTTON_FILL_HEX, outline="", tags="hdr", width=0)
        self._btn_bgs["games"] = self._round_rect(c1, 28, c2, 60, 12, fill=BUTTON_FILL_HEX, outline="", tags="hdr", width=0)
        self._btn_bgs["assistant"] = self._round_rect(b1, 28, b2, 60, 12, fill=BUTTON_FILL_HEX, outline="", tags="hdr", width=0)
        self._btn_bgs["music"] = self._round_rect(m1, 28, m2, 60, 12, fill=BUTTON_FILL_HEX, outline="", tags="hdr", width=0)
        self._btn_bgs["add"] = self._round_rect(a1, 28, a2, 60, 12, fill=BUTTON_FILL_HEX, outline="", tags="hdr", width=0)
        self._btn_bgs["gear"] = self._round_rect(g1, 28, g2, 60, 12, fill=BUTTON_FILL_HEX, outline="", tags="hdr", width=0)
        self._btn_bgs["refresh"] = self._round_rect(r1, 28, r2 := right, 60, 16, fill=BUTTON_FILL_HEX, outline="", tags="hdr", width=0)

        self.cv.coords(self._search_win, s2 - 10, 44)
        self.cv.coords(self._browser_win, (d1 + d2) / 2, 44)
        self.cv.coords(self._games_win, (c1 + c2) / 2, 44)
        self.cv.coords(self._assistant_win, (b1 + b2) / 2, 44)
        self.cv.coords(self._music_win, (m1 + m2) / 2, 44)
        self.cv.coords(self._add_win, (a1 + a2) / 2, 44)
        self.cv.coords(self._gear_win, (g1 + g2) / 2, 44)
        self.cv.coords(self._btn_win, r2 - 8, 44)
        self.cv.tag_raise(self._search_win)
        self.cv.tag_raise(self._browser_win)
        self.cv.tag_raise(self._games_win)
        self.cv.tag_raise(self._assistant_win)
        self.cv.tag_raise(self._music_win)
        self.cv.tag_raise(self._add_win)
        self.cv.tag_raise(self._gear_win)
        self.cv.tag_raise(self._btn_win)

    def _set_search_focus(self, focused):
        if self._search_bg:
            self.cv.itemconfig(self._search_bg, outline=self._accent() if focused else self._card_border(),
                               width=1.5 if focused else 1)

    def _set_btn_hover(self, which, hovered):
        if which in self._btn_bgs:
            self.cv.itemconfig(self._btn_bgs[which],
                               fill=BUTTON_HOVER_HEX if hovered else BUTTON_FILL_HEX)

    # ---------- footer ----------
    def _draw_footer(self):
        w = self.cv.winfo_width()
        h = self.cv.winfo_height()
        click_hint = "Click a card to launch" if self.config["click"] == "single" else "Double-click a card to launch"
        self.cv.delete("ftr")
        left = click_hint
        if self.config.get("show_count", True):
            left = f"{len(self.items)} apps  \u00b7  {left}"
        self.cv.create_text(MARGIN, h - 24, anchor="w",
                            text=left,
                            font=self.font_footer, fill=self._muted_color(), tags="ftr")
        self.cv.create_text(w - MARGIN, h - 24, anchor="e",
                            text="Refresh \u21bb to pick up new apps",
                            font=self.font_footer, fill=self._muted_color(), tags="ftr")

    # ---------- scanning / filtering ----------
    def _scan(self):
        found = []
        if not os.path.isdir(APPS_DIR):
            return found
        for name in os.listdir(APPS_DIR):
            path = os.path.join(APPS_DIR, name)
            if os.path.isdir(path):
                found.append([name, path, True])
            elif name.lower().endswith((".lnk", ".url", ".exe", ".bat", ".cmd", ".appref-ms")):
                found.append([name, path, False])

        sort = self.config["sort"]
        if sort == "name":
            found.sort(key=lambda e: e[0].lower())
        elif sort == "type":
            def key(e):
                return (0 if e[2] else 1,
                        os.path.splitext(e[0])[1].lower(),
                        e[0].lower())
            found.sort(key=key)
        elif sort == "newest":
            def mtime(e):
                try:
                    return os.path.getmtime(e[1])
                except Exception:
                    return 0
            found.sort(key=mtime, reverse=True)
        elif sort == "most_used":
            found.sort(key=lambda e: (-self._launches.get(e[1], 0), e[0].lower()))
        elif sort == "custom":
            order = {p: i for i, p in enumerate(self._order)}
            found.sort(key=lambda e: (order.get(e[1], 10 ** 9), e[0].lower()))
        elif sort == "random":
            random.shuffle(found)
        return found

    def refresh(self):
        self.items = self._scan()
        try:
            self._last_snap = tuple(sorted(os.listdir(APPS_DIR))) if os.path.isdir(APPS_DIR) else ()
        except Exception:
            self._last_snap = ()
        self._apply_filter()

    def _on_search(self, *args):
        self._apply_filter()

    def _on_search_focus_in(self, event=None):
        if self._placeholder:
            self.search_var.set("")
            self._placeholder = False
            self.search_entry.config(fg=self._text_color())
        self._set_search_focus(True)

    def _on_search_focus_out(self, event=None):
        self._set_search_focus(False)
        if not self.search_var.get():
            self._placeholder = True
            self.search_var.set("Search apps\u2026")
            self.search_entry.config(fg=self._muted_color())

    def _clear_search(self):
        self.search_var.set("")
        self._on_search_focus_out()
        self.focus_set()

    def _apply_filter(self):
        query = self.search_var.get().strip().lower()
        if self._placeholder:
            query = ""
        if query:
            self.visible = [it for it in self.items if query in it[0].lower()]
        else:
            self.visible = list(self.items)
        self._allow_anim = True
        self._offset = 0
        self._rebuild_cards()
        self._draw_footer()

    # ---------- cards ----------
    def _viewport(self):
        return HEADER_Y, self.cv.winfo_height() - FOOTER_H

    def _rebuild_cards(self):
        self._cancel_anim()
        self.cv.delete("card")
        self.cv.delete("thumb")
        self._photos = []
        self._hover_idx = None
        self._pressed_idx = None
        self._card_rects = {}
        self._base_pos = {}

        top, bottom = self._viewport()
        view_h = bottom - top
        if view_h <= 0:
            return

        w = self.cv.winfo_width()
        max_cols = max(2, int(self.config.get("max_cols", 8)))
        cols = min(max_cols, max(2, (w - 2 * MARGIN + H_GAP) // (CARD_W + H_GAP)))
        rows = (len(self.visible) + cols - 1) // cols if self.visible else 0
        self._content_h = max(view_h, rows * (self.card_h + V_GAP) - V_GAP)
        self._offset = min(self._offset, max(0, self._content_h - view_h))

        for i, (name, path, is_dir) in enumerate(self.visible):
            cx = MARGIN + CARD_W // 2 + (i % cols) * (CARD_W + H_GAP)
            cy = top + self.card_h // 2 + (i // cols) * (self.card_h + V_GAP) - self._offset
            self._base_pos[i] = (cx, cy)
            self._draw_card(i, name, path, is_dir, cx, cy)

        self._draw_thumb()
        self._draw_footer()
        self._animate_cards()

    def _draw_card(self, idx, name, path, is_dir, cx, cy):
        tag = f"c{idx}"
        x0, y0 = cx - CARD_W // 2, cy - self.card_h // 2
        x1, y1 = cx + CARD_W // 2, cy + self.card_h // 2
        r = max(0, int(self.config["radius"]))
        self._card_rects[idx] = (x0, y0, x1, y1)

        self._round_rect(x0, y0 + 6, x1, y1 + 6, r, fill=self._shadow(),
                         outline="", tags=(tag, "card"))

        photo = self._icon_for(path)
        hover_on = idx == self._hover_idx
        glow = bool(self.config.get("hover_glow", True))
        body = self._card_hover() if hover_on else self._card_fill()
        border = accent_for(name) if (hover_on and glow) else self._card_border()
        bwidth = 2 if (hover_on and glow) else 1

        self._round_rect(x0, y0, x1, y1, r, fill=body, outline=border,
                         width=bwidth, tags=(tag, "card"))

        s = self.icon_size
        icon_y = y0 + 38 + s // 2
        self.cv.create_image(cx, icon_y, image=photo, tags=(tag, "card"))

        if hover_on and glow:
            self.cv.create_oval(cx - s / 2 - 5, icon_y - s / 2 - 5, cx + s / 2 + 5, icon_y + s / 2 + 5,
                                outline=border, width=2, tags=(tag, "card"))

        text_color = "#ffffff" if idx == self._hover_idx else self._text_color()
        self.cv.create_text(cx, y0 + self.card_h - 24, anchor="center", width=CARD_W - 18,
                            text=name, font=self.font_card, fill=text_color,
                            justify="center", tags=(tag, "card"))

        if is_dir:
            chip = accent_for(name)
            chip_r = min(8, r + 2) if r else 6
            self._round_rect(x1 - 34, y0 + 10, x1 - 10, y0 + 26, chip_r,
                             fill=chip, outline="", tags=(tag, "card"))
            self.cv.create_text(x1 - 22, y0 + 18, anchor="center",
                                text="\u229e", font=self.font_sub, fill="#14182a",
                                tags=(tag, "card"))

        count = self._launches.get(path, 0)
        if count > 0:
            br = 11
            self._round_rect(x0 + 6, y0 + 6, x0 + 6 + 2 * br, y0 + 6 + 2 * br, br,
                             fill=self._accent(), outline="", tags=(tag, "card"))
            self.cv.create_text(x0 + 6 + br, y0 + 6 + br, anchor="center", text=str(count),
                                font=self._badge_font, fill="#14182a", tags=(tag, "card"))

    def _icon_for(self, path):
        key = (path, self.icon_size)
        if key not in self._icon_cache:
            photo = get_file_icon(path, self.icon_size)
            if photo is None:
                photo = fallback_icon(self.icon_size)
            self._icon_cache[key] = photo
        self._photos.append(self._icon_cache[key])
        return self._icon_cache[key]

    def _draw_thumb(self):
        self.cv.delete("thumb")
        top, bottom = self._viewport()
        view_h = bottom - top
        w = self.cv.winfo_width()
        if self._content_h <= view_h:
            return
        ratio = view_h / self._content_h
        thumb_h = max(36, ratio * view_h)
        frac = self._offset / max(1, self._content_h - view_h)
        ty = top + frac * (view_h - thumb_h)
        self._round_rect(w - 12, ty, w - 6, ty + thumb_h, 3, fill=self._card_border(),
                         outline="", tags="thumb")

    # ---------- interaction ----------
    def _hit_card(self, x, y):
        for idx, (x0, y0, x1, y1) in self._card_rects.items():
            if x0 <= x <= x1 and y0 <= y <= y1:
                return idx
        return None

    def _thumb_geo(self):
        top, bottom = self._viewport()
        view_h = bottom - top
        w = self.cv.winfo_width()
        if self._content_h <= view_h:
            return None
        ratio = view_h / self._content_h
        thumb_h = max(36, ratio * view_h)
        frac = self._offset / max(1, self._content_h - view_h)
        ty = top + frac * (view_h - thumb_h)
        return (w - 12, ty, w - 6, ty + thumb_h)

    def _on_wheel(self, event):
        top, bottom = self._viewport()
        view_h = bottom - top
        if self._content_h <= view_h:
            return
        step = 52 * int(self.config.get("scroll_speed", 1))
        self._offset += step if event.delta < 0 else -step
        self._offset = max(0, min(self._offset, self._content_h - view_h))
        self._allow_anim = False
        self._rebuild_cards()

    def _on_motion(self, event):
        if self._drag_mode == "thumb":
            return
        idx = self._hit_card(event.x, event.y)
        if idx != self._hover_idx:
            if self._hover_idx is not None:
                self._set_hover(self._hover_idx, False)
            self._hover_idx = idx
            if idx is not None:
                self._set_hover(idx, True)

    def _set_hover(self, idx, on):
        self._allow_anim = False
        self._redraw_cards()

    def _redraw_cards(self):
        self.cv.delete("card")
        self._card_rects = {}
        for j in range(len(self.visible)):
            jcx, jcy = self._base_pos[j]
            self._draw_card(j, *self.visible[j], jcx, jcy)

    def _on_press(self, event):
        geo = self._thumb_geo()
        if geo and geo[0] <= event.x <= geo[2] and geo[1] <= event.y <= geo[3]:
            self._drag_mode = "thumb"
            self._drag_start_y = event.y
            self._drag_start_off = self._offset
            return
        idx = self._hit_card(event.x, event.y)
        if idx is not None:
            self._pressed_idx = idx
            self._dragged = False
            self.cv.move(f"c{idx}", 0, 2)

    def _on_drag(self, event):
        if self._drag_mode == "thumb":
            top, bottom = self._viewport()
            view_h = bottom - top
            if self._content_h <= view_h:
                return
            dy = event.y - self._drag_start_y
            span = view_h - max(36, view_h / self._content_h * view_h)
            ratio = max(0, self._content_h - view_h) / max(1, span)
            self._offset = self._drag_start_off + dy * ratio
            self._offset = max(0, min(self._offset, self._content_h - view_h))
            self._allow_anim = False
            self._rebuild_cards()
            return
        if self._pressed_idx is not None and self.config["sort"] == "custom":
            target = self._hit_card(event.x, event.y)
            if target is not None and target != self._pressed_idx:
                self.visible[target], self.visible[self._pressed_idx] = (
                    self.visible[self._pressed_idx], self.visible[target])
                self._pressed_idx = target
                self._dragged = True
                self._allow_anim = False
                self._redraw_cards()

    def _on_release(self, event):
        if self._drag_mode == "thumb":
            self._drag_mode = None
            return
        if self._pressed_idx is not None:
            self.cv.move(f"c{self._pressed_idx}", 0, -2)
            if self._dragged:
                self._order = [it[1] for it in self.visible]
                self._save_stats()
                self._dragged = False
            elif self.config["click"] == "single":
                idx = self._hit_card(event.x, event.y)
                if idx == self._pressed_idx:
                    self._launch(idx)
            self._pressed_idx = None

    def _on_double(self, event):
        if self.config["click"] != "double":
            return
        idx = self._hit_card(event.x, event.y)
        if idx is not None:
            self._launch(idx)

    def _on_context(self, event):
        idx = self._hit_card(event.x, event.y)
        menu = tk.Menu(self.cv, tearoff=0, bg="#1d2130", fg=self._text_color(), bd=0,
                       activebackground=BUTTON_HOVER_HEX, activeforeground="#ffffff")
        if idx is not None:
            name, path, is_dir = self.visible[idx]
            menu.add_command(label=f"Launch {name}", command=lambda: self._launch(idx))
            menu.add_command(label="Open location", command=lambda: open_location(path))
            if not is_dir:
                menu.add_separator()
                menu.add_command(label="Remove from launcher",
                                 command=lambda: self._remove_app(idx))
        else:
            menu.add_command(label="Open apps folder", command=self.open_folder)
            menu.add_command(label="Add app\u2026", command=self.add_app)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ---------- actions ----------
    def _launch_target(self, path, is_dir):
        if is_dir:
            try:
                for fn in sorted(os.listdir(path)):
                    if fn.lower().endswith((".bat", ".cmd", ".lnk")):
                        return os.path.join(path, fn)
            except Exception:
                pass
        return path

    def _launch(self, idx):
        name, path, is_dir = self.visible[idx]
        if not os.path.exists(path):
            self._flash_status(f"Cannot find: {name}")
            return
        try:
            os.startfile(self._launch_target(path, is_dir))
            self._flash_status(f"Launching {name}\u2026")
            self._record_launch(path)
            if self.config["sound"]:
                try:
                    ls = self.config.get("launch_sound")
                    if ls and ls != "None":
                        play_sound(ls)
                    else:
                        winsound.Beep(660, 55)
                        winsound.Beep(880, 70)
                except Exception:
                    pass
            if self.config["confetti"]:
                self._burst_confetti()
        except Exception as e:
            self._flash_status(f"Failed to open {name}: {e}")

    def _remove_app(self, idx):
        name, path, is_dir = self.visible[idx]
        if not messagebox.askyesno("Remove app",
                                   f"Move \u201c{name}\u201d to the Recycle Bin?"):
            return
        try:
            recycle(path)
            self._flash_status(f"Removed {name}")
        except Exception as e:
            self._flash_status(f"Could not remove {name}: {e}")
        self.refresh()

    def open_folder(self):
        try:
            os.startfile(APPS_DIR)
        except Exception as e:
            self._flash_status(str(e))

    def add_app(self):
        path = filedialog.askopenfilename(
            title="Choose an app to add",
            initialdir=os.path.expanduser("~"),
            filetypes=[("Applications", "*.exe *.lnk *.url *.appref-ms *.bat *.cmd"),
                       ("All files", "*.*")],
        )
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        base = os.path.basename(path)
        try:
            if ext == ".exe":
                target = os.path.join(APPS_DIR, os.path.splitext(base)[0] + ".lnk")
                create_shortcut(path, unique_path(target))
            else:
                shutil.copy2(path, unique_path(os.path.join(APPS_DIR, base)))
            self.refresh()
            self._flash_status(f"Added {base}")
        except Exception as e:
            self._flash_status(f"Could not add app: {e}")

    def open_settings(self):
        SettingsWindow(self)

    def open_soundboard(self):
        SoundboardWindow(self)

    def open_assistant(self):
        AssistantWindow(self)

    def open_games(self):
        AppGames.GamesWindow(self)

    def open_browser(self, url=None):
        browser_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AppBrowser.py")
        if not os.path.exists(browser_py):
            webbrowser.open(url or "https://www.google.com")
            return
        cmd = [sys.executable, browser_py]
        if url:
            cmd.append(url)
        subprocess.Popen(cmd, shell=False, close_fds=True)

    def open_music(self):
        music_bat = os.path.join(APPS_DIR, "Music", "Music.bat")
        if os.path.exists(music_bat):
            try:
                os.startfile(music_bat)
                self._flash_status("Launching Music\u2026")
                self._record_launch(os.path.dirname(music_bat))
            except Exception as e:
                self._flash_status(f"Failed to open Music: {e}")
        else:
            self._flash_status("Music app not found")

    # ---------- auto refresh ----------
    def _start_auto(self):
        self._stop_auto()
        if self.config["auto_refresh"]:
            self._auto_job = self.after(2500, self._auto_check)

    def _stop_auto(self):
        if self._auto_job:
            try:
                self.after_cancel(self._auto_job)
            except Exception:
                pass
            self._auto_job = None

    def _auto_check(self):
        try:
            snap = tuple(sorted(os.listdir(APPS_DIR))) if os.path.isdir(APPS_DIR) else ()
        except Exception:
            snap = ()
        if snap != self._last_snap:
            self.refresh()
        if self.config["auto_refresh"]:
            self._auto_job = self.after(2500, self._auto_check)

    # ---------- misc ----------
    def _flash_status(self, msg):
        self._draw_footer()
        w = self.cv.winfo_width()
        h = self.cv.winfo_height()
        self.cv.create_text(MARGIN, h - 24, anchor="w", text=msg,
                            font=self.font_footer, fill=self._accent(), tags="ftr")

    def _fade_in(self):
        target = float(self.config.get("alpha", 1.0))
        try:
            for step in range(1, 11):
                self.attributes("-alpha", target * step / 10)
                self.update_idletasks()
                self.after(14)
        except Exception:
            pass
        self.attributes("-alpha", target)

    # ---------- system tray + hotkey ----------
    def _apply_tray(self):
        if self.config.get("tray") and not self._tray_running:
            self._start_tray()
        elif not self.config.get("tray") and self._tray_running:
            self._stop_tray()

    def _start_tray(self):
        try:
            import pystray
        except Exception:
            self._tray = None
            self._check_hotkey()
            return
        menu = pystray.Menu(
            pystray.MenuItem("Open Launcher", lambda icon, item: self._tray_set("show"),
                             default=True),
            pystray.MenuItem("Quit", lambda icon, item: self._tray_set("quit")),
        )
        try:
            icon = pystray.Icon("applauncher", make_tray_image(), "App Launcher", menu)
            self._tray = icon
            threading.Thread(target=icon.run, daemon=True).start()
            self._tray_running = True
        except Exception:
            self._tray = None
        self._check_hotkey()

    def _stop_tray(self):
        if self._hotkey_job:
            try:
                self.after_cancel(self._hotkey_job)
            except Exception:
                pass
        self._hotkey_job = None
        if self._tray is not None:
            try:
                self._tray.stop()
            except Exception:
                pass
        self._tray = None
        self._tray_running = False

    def _tray_set(self, action):
        self._tray_action = action

    def _check_hotkey(self):
        try:
            ctrl = ctypes.windll.user32.GetAsyncKeyState(0x11) & 0x8000
            shift = ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000
            key = ctypes.windll.user32.GetAsyncKeyState(0x4C) & 0x8000
            if ctrl and shift and key:
                if self.state() == "withdrawn":
                    self._restore_window()
                else:
                    self._hide_window()
                time.sleep(0.35)
        except Exception:
            pass
        if self._tray_action:
            action, self._tray_action = self._tray_action, None
            if action == "quit":
                self._quitting = True
                self.destroy()
                return
            if action == "show":
                self._restore_window()
        if self.config.get("tray"):
            self._hotkey_job = self.after(150, self._check_hotkey)

    def _hide_window(self):
        self.withdraw()

    def _restore_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_close(self):
        if self.config.get("tray") and not self._quitting:
            self._hide_window()
        else:
            self._quitting = True
            self._stop_tray()
            self.destroy()


class SettingsWindow(tk.Toplevel):
    SET_BG = "#161a26"
    SET_CARD = "#1f2434"
    SET_TEXT = "#e9ecf5"
    SET_MUTED = "#8b93a7"
    LBL_FONT = ("Segoe UI", 9)

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Settings")
        self.configure(bg=self.SET_BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.geometry("420x700")

        outer = tk.Frame(self, bg=self.SET_BG)
        outer.pack(fill="both", expand=True)
        self._canvas = tk.Canvas(outer, bg=self.SET_BG, highlightthickness=0, bd=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=self._canvas.yview,
                          bg=self.SET_CARD, troughcolor=self.SET_BG, bd=0)
        self._canvas.configure(yscrollcommand=sb.set)
        self._inner = tk.Frame(self._canvas, bg=self.SET_BG)
        self._win = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>",
                         lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(self._win, width=e.width))
        self._canvas.bind_all("<MouseWheel>", self._on_scroll)
        sb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._swatches = {}
        self._themes = {}
        self._color_swatches = {}
        self._build()

    def _on_scroll(self, event):
        w = self.winfo_containing(event.x_root, event.y_root)
        if w is not None and w.winfo_toplevel() is self:
            self._canvas.yview_scroll(int(-event.delta / 120), "units")

    def _title(self, text):
        tk.Label(self._inner, text=text,
                 font=tkfont.Font(family="Segoe UI", size=10, weight="bold"),
                 bg=self.SET_BG, fg=self.SET_TEXT).pack(anchor="w", padx=18, pady=(14, 6))

    def _check(self, parent, text, var, command):
        return tk.Checkbutton(parent, text=text, variable=var, command=command,
                              bg=self.SET_BG, fg=self.SET_TEXT, selectcolor=self.SET_CARD,
                              activebackground=self.SET_BG, activeforeground="#ffffff",
                              font=self.LBL_FONT, cursor="hand2", anchor="w")

    def _build(self):
        self._title("Theme")
        theme_frame = tk.Frame(self._inner, bg=self.SET_BG)
        theme_frame.pack(fill="x", padx=18)
        self._themes = {}
        names = list(THEMES.keys())
        for i, name in enumerate(names):
            acc = THEMES[name]["accent"]
            b = tk.Button(theme_frame, text=name, command=lambda n=name: self._set_theme(n),
                          bg=acc, fg="#111111", activebackground=acc, relief="flat", bd=0,
                          font=tkfont.Font(family="Segoe UI", size=8, weight="bold"),
                          width=9, height=2, cursor="hand2")
            b.grid(row=i // 3, column=i % 3, padx=3, pady=3)
            self._themes[name] = b

        self._title("Accent color")
        acc_frame = tk.Frame(self._inner, bg=self.SET_BG)
        acc_frame.pack(fill="x", padx=18)
        self._swatches = {}
        for i, color in enumerate(ACCENT_SWATCHES):
            b = tk.Button(acc_frame, command=lambda c=color: self._set_accent(c),
                          bg=color, activebackground=color, relief="flat", bd=0,
                          width=3, height=2, cursor="hand2")
            b.grid(row=0, column=i, padx=2, pady=3)
            self._swatches[color] = b
        tk.Button(acc_frame, text="\u25a0 Custom\u2026", command=self._pick_custom,
                  bg=self.SET_CARD, fg=self.SET_TEXT, activebackground="#2a3150",
                  activeforeground="#ffffff", relief="flat", bd=0, padx=8, pady=6,
                  font=self.LBL_FONT, cursor="hand2").grid(row=0, column=len(ACCENT_SWATCHES), padx=6, pady=3)

        self._title("Icon size")
        icon_frame = tk.Frame(self._inner, bg=self.SET_BG)
        icon_frame.pack(fill="x", padx=18)
        self._icon_var = tk.StringVar(value=self._size_label())
        for label in ("Small", "Medium", "Large"):
            tk.Radiobutton(icon_frame, text=label, value=label, variable=self._icon_var,
                           command=self._set_icon, bg=self.SET_BG, fg=self.SET_TEXT,
                           selectcolor=self.SET_CARD, activebackground=self.SET_BG,
                           activeforeground="#ffffff", font=self.LBL_FONT, cursor="hand2"
                           ).pack(side="left", padx=(0, 18))

        self._title("Card label size")
        lbl_frame = tk.Frame(self._inner, bg=self.SET_BG)
        lbl_frame.pack(fill="x", padx=18)
        self._label_var = tk.StringVar(value=str(self.app.config["label_size"]))
        for label, size in (("Small", 9), ("Normal", 10), ("Large", 12)):
            tk.Radiobutton(lbl_frame, text=label, value=str(size), variable=self._label_var,
                           command=self._set_label, bg=self.SET_BG, fg=self.SET_TEXT,
                           selectcolor=self.SET_CARD, activebackground=self.SET_BG,
                           activeforeground="#ffffff", font=self.LBL_FONT, cursor="hand2"
                           ).pack(side="left", padx=(0, 18))

        self._title("Corner roundness")
        self._radius_var = tk.IntVar(value=int(self.app.config["radius"]))
        tk.Scale(self._inner, from_=0, to=28, orient="horizontal", variable=self._radius_var,
                 command=self._set_radius, bg=self.SET_BG, fg=self.SET_TEXT, troughcolor=self.SET_CARD,
                 highlightthickness=0, bd=0, activebackground=self.SET_BG,
                 font=self.LBL_FONT, sliderrelief="flat", showvalue=False,
                 length=360).pack(fill="x", padx=18)

        self._title("Window opacity")
        self._alpha_var = tk.DoubleVar(value=float(self.app.config.get("alpha", 1.0)))
        tk.Scale(self._inner, from_=0.55, to=1.0, resolution=0.05, orient="horizontal",
                 variable=self._alpha_var, command=self._set_alpha,
                 bg=self.SET_BG, fg=self.SET_TEXT, troughcolor=self.SET_CARD,
                 highlightthickness=0, bd=0, activebackground=self.SET_BG,
                 font=self.LBL_FONT, sliderrelief="flat", showvalue=False,
                 length=360).pack(fill="x", padx=18)

        self._title("Launch on")
        click_frame = tk.Frame(self._inner, bg=self.SET_BG)
        click_frame.pack(fill="x", padx=18)
        self._click_var = tk.StringVar(value=self.app.config["click"])
        for label, value in (("Single click", "single"), ("Double click", "double")):
            tk.Radiobutton(click_frame, text=label, value=value, variable=self._click_var,
                           command=self._set_click, bg=self.SET_BG, fg=self.SET_TEXT,
                           selectcolor=self.SET_CARD, activebackground=self.SET_BG,
                           activeforeground="#ffffff", font=self.LBL_FONT, cursor="hand2"
                           ).pack(side="left", padx=(0, 18))

        self._title("Sort apps by")
        sort_frame = tk.Frame(self._inner, bg=self.SET_BG)
        sort_frame.pack(fill="x", padx=18)
        self._sort_var = tk.StringVar(value=self.app.config["sort"])
        sort_row1 = tk.Frame(sort_frame, bg=self.SET_BG)
        sort_row1.pack(anchor="w")
        for label, value in (("Name", "name"), ("Type", "type"), ("Newest", "newest")):
            tk.Radiobutton(sort_row1, text=label, value=value, variable=self._sort_var,
                           command=self._set_sort, bg=self.SET_BG, fg=self.SET_TEXT,
                           selectcolor=self.SET_CARD, activebackground=self.SET_BG,
                           activeforeground="#ffffff", font=self.LBL_FONT, cursor="hand2"
                           ).pack(side="left", padx=(0, 14))
        sort_row2 = tk.Frame(sort_frame, bg=self.SET_BG)
        sort_row2.pack(anchor="w", pady=(4, 0))
        for label, value in (("Random", "random"), ("Most used", "most_used"), ("Custom", "custom")):
            tk.Radiobutton(sort_row2, text=label, value=value, variable=self._sort_var,
                           command=self._set_sort, bg=self.SET_BG, fg=self.SET_TEXT,
                           selectcolor=self.SET_CARD, activebackground=self.SET_BG,
                           activeforeground="#ffffff", font=self.LBL_FONT, cursor="hand2"
                           ).pack(side="left", padx=(0, 14))

        self._title("Grid & motion")
        grid_frame = tk.Frame(self._inner, bg=self.SET_BG)
        grid_frame.pack(fill="x", padx=18)
        tk.Label(grid_frame, text="Max columns", bg=self.SET_BG, fg=self.SET_MUTED,
                 font=self.LBL_FONT).pack(anchor="w")
        self._cols_var = tk.IntVar(value=int(self.app.config.get("max_cols", 8)))
        tk.Scale(grid_frame, from_=3, to=8, orient="horizontal", variable=self._cols_var,
                 command=self._set_cols, bg=self.SET_BG, fg=self.SET_TEXT, troughcolor=self.SET_CARD,
                 highlightthickness=0, bd=0, activebackground=self.SET_BG,
                 font=self.LBL_FONT, sliderrelief="flat", showvalue=False,
                 length=360).pack(fill="x", pady=(0, 6))
        tk.Label(grid_frame, text="Scroll speed", bg=self.SET_BG, fg=self.SET_MUTED,
                 font=self.LBL_FONT).pack(anchor="w")
        self._scroll_var = tk.IntVar(value=int(self.app.config.get("scroll_speed", 1)))
        tk.Scale(grid_frame, from_=1, to=5, orient="horizontal", variable=self._scroll_var,
                 command=self._set_scroll, bg=self.SET_BG, fg=self.SET_TEXT, troughcolor=self.SET_CARD,
                 highlightthickness=0, bd=0, activebackground=self.SET_BG,
                 font=self.LBL_FONT, sliderrelief="flat", showvalue=False,
                 length=360).pack(fill="x", pady=(0, 6))
        tk.Label(grid_frame, text="Particle density", bg=self.SET_BG, fg=self.SET_MUTED,
                 font=self.LBL_FONT).pack(anchor="w")
        self._density_var = tk.IntVar(value=int(self.app.config.get("particle_density", 3)))
        tk.Scale(grid_frame, from_=1, to=6, orient="horizontal", variable=self._density_var,
                 command=self._set_density, bg=self.SET_BG, fg=self.SET_TEXT, troughcolor=self.SET_CARD,
                 highlightthickness=0, bd=0, activebackground=self.SET_BG,
                 font=self.LBL_FONT, sliderrelief="flat", showvalue=False,
                 length=360).pack(fill="x")

        self._title("Options")
        opt_frame = tk.Frame(self._inner, bg=self.SET_BG)
        opt_frame.pack(fill="x", padx=18)
        self._top_var = tk.BooleanVar(value=bool(self.app.config["on_top"]))
        self._check(opt_frame, "Keep window on top", self._top_var, self._set_on_top).pack(anchor="w")
        self._auto_var = tk.BooleanVar(value=bool(self.app.config["auto_refresh"]))
        self._check(opt_frame, "Auto-refresh the app list", self._auto_var, self._set_auto).pack(anchor="w")
        self._count_var = tk.BooleanVar(value=bool(self.app.config.get("show_count", True)))
        self._check(opt_frame, "Show app count in the footer", self._count_var, self._set_count).pack(anchor="w")
        self._stats_var = tk.BooleanVar(value=bool(self.app.config.get("stats", True)))
        self._check(opt_frame, "Live stats bar (clock, weather, CPU/RAM)", self._stats_var, self._set_stats).pack(anchor="w")
        self._tray_var = tk.BooleanVar(value=bool(self.app.config.get("tray", False)))
        self._check(opt_frame, "Minimize to tray (Ctrl+Shift+L)", self._tray_var, self._set_tray).pack(anchor="w")

        self._title("Hover highlight")
        hov_frame = tk.Frame(self._inner, bg=self.SET_BG)
        hov_frame.pack(fill="x", padx=18)
        self._glow_var = tk.BooleanVar(value=bool(self.app.config.get("hover_glow", True)))
        self._check(hov_frame, "Accent glow ring on hover", self._glow_var, self._set_glow).pack(anchor="w")
        hov_btns = tk.Frame(hov_frame, bg=self.SET_BG)
        hov_btns.pack(anchor="w", pady=(4, 0))
        tk.Button(hov_btns, text="Card hover color\u2026", command=self._pick_hover,
                  bg=self.SET_CARD, fg=self.SET_TEXT, activebackground="#2a3150",
                  activeforeground="#ffffff", relief="flat", bd=0, padx=12, pady=6,
                  font=self.LBL_FONT, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(hov_btns, text="Reset", command=self._reset_hover,
                  bg=self.SET_CARD, fg=self.SET_MUTED, activebackground="#2a3150",
                  activeforeground="#ffffff", relief="flat", bd=0, padx=12, pady=6,
                  font=self.LBL_FONT, cursor="hand2").pack(side="left")

        self._title("More colors")
        tk.Label(self._inner, text="Overrides the current theme (live preview).",
                 bg=self.SET_BG, fg=self.SET_MUTED, font=self.LBL_FONT).pack(anchor="w", padx=18, pady=(0, 4))
        col_frame = tk.Frame(self._inner, bg=self.SET_BG)
        col_frame.pack(fill="x", padx=18)
        rows = (
            ("Background top", "bg_top", self.app._bg_top()),
            ("Background bottom", "bg_bottom", self.app._bg_bottom()),
            ("Glow color", "glow", self.app._glow()),
            ("Card fill", "card_color", CARD_FILL_HEX),
            ("Card border", "card_border", CARD_BORDER_HEX),
            ("Card shadow", "shadow_color", SHADOW_HEX),
            ("Text color", "text_color", TEXT_HEX),
            ("Muted text", "muted_color", MUTED_HEX),
            ("Particle color", "particle_color", ACCENTS[0]),
        )
        for label, key, default in rows:
            self._color_row(col_frame, label, key, default)

        self._title("Browser colors")
        tk.Label(self._inner, text="Applies to the built-in browser toolbar.",
                 bg=self.SET_BG, fg=self.SET_MUTED, font=self.LBL_FONT).pack(anchor="w", padx=18, pady=(0, 4))
        brow_frame = tk.Frame(self._inner, bg=self.SET_BG)
        brow_frame.pack(fill="x", padx=18)
        brow_rows = (
            ("Toolbar top", "browser_bg_top", _hex(self.app._bg_top())),
            ("Toolbar bottom", "browser_bg_bottom", _hex(self.app._bg_bottom())),
            ("Accent", "browser_accent", self.app._accent()),
            ("Button fill", "browser_button", BUTTON_FILL_HEX),
            ("Search bar", "browser_search", SEARCH_FILL_HEX),
            ("Text", "browser_text", TEXT_HEX),
        )
        for label, key, default in brow_rows:
            self._color_row(brow_frame, label, key, default)

        self._title("Fun stuff")
        fun_frame = tk.Frame(self._inner, bg=self.SET_BG)
        fun_frame.pack(fill="x", padx=18)
        self._part_var = tk.BooleanVar(value=bool(self.app.config["particles"]))
        self._check(fun_frame, "Floating background particles", self._part_var, self._set_part).pack(anchor="w")
        self._aurora_var = tk.BooleanVar(value=bool(self.app.config.get("aurora", False)))
        self._check(fun_frame, "Animated aurora background", self._aurora_var, self._set_aurora).pack(anchor="w")
        self._anim_var = tk.BooleanVar(value=bool(self.app.config["card_anim"]))
        self._check(fun_frame, "Card entrance animation", self._anim_var, self._set_anim).pack(anchor="w")
        self._conf_var = tk.BooleanVar(value=bool(self.app.config["confetti"]))
        self._check(fun_frame, "Confetti when launching an app", self._conf_var, self._set_conf).pack(anchor="w")
        self._party_var = tk.BooleanVar(value=bool(self.app.config["party"]))
        self._check(fun_frame, "Party mode (cycling colors)", self._party_var, self._set_party).pack(anchor="w")
        self._sound_var = tk.BooleanVar(value=bool(self.app.config["sound"]))
        self._check(fun_frame, "Play a sound on launch", self._sound_var, self._set_sound).pack(anchor="w")

        self._title("Apps folder")
        act_frame = tk.Frame(self._inner, bg=self.SET_BG)
        act_frame.pack(fill="x", padx=18)
        tk.Button(act_frame, text="Open apps folder", command=self.app.open_folder,
                  bg=self.SET_CARD, fg=self.SET_TEXT, activebackground="#2a3150",
                  activeforeground="#ffffff", relief="flat", bd=0, padx=12, pady=6,
                  font=self.LBL_FONT, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(act_frame, text="Add app\u2026", command=self.app.add_app,
                  bg=self.SET_CARD, fg=self.SET_TEXT, activebackground="#2a3150",
                  activeforeground="#ffffff", relief="flat", bd=0, padx=12, pady=6,
                  font=self.LBL_FONT, cursor="hand2").pack(side="left")

        self._title("AI Assistant")
        ai_frame = tk.Frame(self._inner, bg=self.SET_BG)
        ai_frame.pack(fill="x", padx=18)
        tk.Label(ai_frame, text="Optional API key (e.g. OpenAI). Without one the assistant\n"
                                "works offline: opens apps, searches the web, math, weather, PC info.",
                 bg=self.SET_BG, fg=self.SET_MUTED, font=self.LBL_FONT, justify="left").pack(anchor="w", pady=(0, 6))
        self._ai_key_var = tk.StringVar(value=self.app.config.get("ai_api_key", ""))
        self._ai_key_entry = tk.Entry(ai_frame, textvariable=self._ai_key_var, show="*",
                                      bg=self.SET_CARD, fg=self.SET_TEXT,
                                      insertbackground=self.SET_TEXT, relief="flat", bd=0,
                                      highlightthickness=1, highlightbackground="#333a55")
        self._ai_key_entry.pack(fill="x", ipady=5, pady=(0, 4))
        self._ai_key_show_var = tk.BooleanVar()
        tk.Checkbutton(ai_frame, text="Show API key", variable=self._ai_key_show_var,
                       command=self._toggle_key, bg=self.SET_BG, fg=self.SET_MUTED,
                       selectcolor=self.SET_CARD, activebackground=self.SET_BG,
                       activeforeground="#ffffff", font=self.LBL_FONT,
                       cursor="hand2").pack(anchor="w", pady=(0, 6))
        tk.Label(ai_frame, text="API URL", bg=self.SET_BG, fg=self.SET_MUTED,
                 font=self.LBL_FONT).pack(anchor="w")
        self._ai_url_var = tk.StringVar(value=self.app.config.get("ai_api_url", "https://api.openai.com/v1/chat/completions"))
        tk.Entry(ai_frame, textvariable=self._ai_url_var, bg=self.SET_CARD, fg=self.SET_TEXT,
                 insertbackground=self.SET_TEXT, relief="flat", bd=0,
                 highlightthickness=1, highlightbackground="#333a55",
                 font=self.LBL_FONT).pack(fill="x", ipady=5, pady=(2, 6))
        tk.Label(ai_frame, text="Model", bg=self.SET_BG, fg=self.SET_MUTED,
                 font=self.LBL_FONT).pack(anchor="w")
        self._ai_model_var = tk.StringVar(value=self.app.config.get("ai_model", "gpt-4o-mini"))
        tk.Entry(ai_frame, textvariable=self._ai_model_var, bg=self.SET_CARD, fg=self.SET_TEXT,
                 insertbackground=self.SET_TEXT, relief="flat", bd=0,
                 highlightthickness=1, highlightbackground="#333a55",
                 font=self.LBL_FONT).pack(fill="x", ipady=5, pady=(2, 6))
        tk.Button(ai_frame, text="Save AI settings", command=self._save_ai,
                  bg=self.SET_CARD, fg=self.SET_TEXT, activebackground="#2a3150",
                  activeforeground="#ffffff", relief="flat", bd=0, padx=12, pady=6,
                  font=self.LBL_FONT, cursor="hand2").pack(anchor="w")

        tk.Button(self._inner, text="Reset all settings", command=self._reset,
                  bg="#3a2230", fg="#ffb3c1", activebackground="#4a2a3a",
                  activeforeground="#ffffff", relief="flat", bd=0, padx=12, pady=6,
                  font=self.LBL_FONT, cursor="hand2").pack(anchor="w", padx=18, pady=(18, 10))

        self._refresh_markers()

    def _size_label(self):
        for label, size in ICON_SIZES.items():
            if size == self.app.config["icon_size"]:
                return label
        return "Medium"

    def _refresh_markers(self):
        active = self.app.config["custom_accent"]
        for color, b in self._swatches.items():
            on = (active == color)
            b.config(relief="solid" if on else "flat", bd=2 if on else 0,
                     highlightbackground="#ffffff" if on else self.SET_BG)
        for name, b in self._themes.items():
            on = (self.app.config["theme"] == name and not active)
            b.config(relief="solid" if on else "flat", bd=2 if on else 0,
                     highlightbackground="#ffffff" if on else self.SET_BG)

    def _set_theme(self, name):
        self.app.set_config("theme", name)
        self._refresh_markers()

    def _set_accent(self, color):
        self.app.set_config("custom_accent", color)
        self._refresh_markers()

    def _pick_custom(self):
        color = colorchooser.askcolor(color=self.app._accent(), parent=self,
                                      title="Pick an accent color")
        if color and color[1]:
            self.app.set_config("custom_accent", color[1])
            self._refresh_markers()

    def _set_icon(self):
        self.app.set_config("icon_size", ICON_SIZES[self._icon_var.get()])

    def _set_label(self):
        self.app.set_config("label_size", int(self._label_var.get()))

    def _set_radius(self, value):
        self.app.set_config("radius", int(float(value)))

    def _set_alpha(self, value):
        self.app.set_config("alpha", float(value))

    def _set_cols(self, value):
        self.app.set_config("max_cols", int(float(value)))

    def _set_scroll(self, value):
        self.app.set_config("scroll_speed", int(float(value)))

    def _set_density(self, value):
        self.app.set_config("particle_density", int(float(value)))

    def _set_glow(self):
        self.app.set_config("hover_glow", bool(self._glow_var.get()))

    def _set_count(self):
        self.app.set_config("show_count", bool(self._count_var.get()))

    def _pick_hover(self):
        color = colorchooser.askcolor(color=self.app.config.get("hover_color") or CARD_HOVER_HEX,
                                      parent=self, title="Pick a card hover color")
        if color and color[1]:
            self.app.set_config("hover_color", color[1])

    def _reset_hover(self):
        self.app.set_config("hover_color", None)

    def _color_display(self, key, default):
        val = self.app.config.get(key) or default
        if isinstance(val, tuple):
            return _hex(val)
        return val

    def _color_row(self, parent, label, key, default):
        row = tk.Frame(parent, bg=self.SET_BG)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, bg=self.SET_BG, fg=self.SET_TEXT, font=self.LBL_FONT,
                 width=19, anchor="w").pack(side="left")
        cur = tk.Frame(row, bg=self._color_display(key, default), width=18, height=18,
                       highlightthickness=1, highlightbackground="#333a55")
        cur.pack(side="left", padx=(0, 6))
        tk.Button(row, text="Pick\u2026", command=lambda k=key, d=default: self._pick_color(k, d),
                  bg=self.SET_CARD, fg=self.SET_TEXT, activebackground="#2a3150",
                  activeforeground="#ffffff", relief="flat", bd=0, padx=8, pady=2,
                  font=self.LBL_FONT, cursor="hand2").pack(side="left", padx=(0, 4))
        tk.Button(row, text="Reset", command=lambda k=key, d=default: self._reset_color(k, d),
                  bg=self.SET_CARD, fg=self.SET_MUTED, activebackground="#2a3150",
                  activeforeground="#ffffff", relief="flat", bd=0, padx=8, pady=2,
                  font=self.LBL_FONT, cursor="hand2").pack(side="left")
        self._color_swatches[key] = cur

    def _pick_color(self, key, default):
        color = colorchooser.askcolor(color=self._color_display(key, default), parent=self,
                                      title="Pick a color")
        if color and color[1]:
            self.app.set_config(key, color[1])
            if key in self._color_swatches:
                self._color_swatches[key].config(bg=color[1])

    def _reset_color(self, key, default):
        self.app.set_config(key, None)
        if key in self._color_swatches:
            self._color_swatches[key].config(bg=self._color_display(key, default))

    def _set_click(self):
        self.app.set_config("click", self._click_var.get())

    def _set_sort(self):
        self.app.set_config("sort", self._sort_var.get())

    def _set_on_top(self):
        self.app.set_config("on_top", bool(self._top_var.get()))

    def _set_auto(self):
        self.app.set_config("auto_refresh", bool(self._auto_var.get()))

    def _set_part(self):
        self.app.set_config("particles", bool(self._part_var.get()))

    def _set_aurora(self):
        self.app.set_config("aurora", bool(self._aurora_var.get()))

    def _set_stats(self):
        self.app.set_config("stats", bool(self._stats_var.get()))

    def _set_tray(self):
        self.app.set_config("tray", bool(self._tray_var.get()))

    def _set_anim(self):
        self.app.set_config("card_anim", bool(self._anim_var.get()))

    def _set_conf(self):
        self.app.set_config("confetti", bool(self._conf_var.get()))

    def _set_party(self):
        self.app.set_config("party", bool(self._party_var.get()))

    def _set_sound(self):
        self.app.set_config("sound", bool(self._sound_var.get()))

    def _toggle_key(self):
        self._ai_key_entry.config(show="" if self._ai_key_show_var.get() else "*")

    def _save_ai(self):
        self.app.set_config("ai_api_key", self._ai_key_var.get().strip())
        self.app.set_config("ai_api_url", self._ai_url_var.get().strip() or "https://api.openai.com/v1/chat/completions")
        self.app.set_config("ai_model", self._ai_model_var.get().strip() or "gpt-4o-mini")

    def _reset(self):
        if messagebox.askyesno("Reset settings", "Restore all default settings?",
                               parent=self):
            self.app.reset_config()
            self.destroy()
            SettingsWindow(self.app)


class SoundboardWindow(tk.Toplevel):
    SB_BG = "#161a26"
    SB_CARD = "#1f2434"
    SB_TEXT = "#e9ecf5"

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Soundboard")
        self.configure(bg=self.SB_BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.geometry("480x560")
        ensure_sounds()
        self._build()

    def _build(self):
        top = tk.Frame(self, bg=self.SB_BG)
        top.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(top, text="Launch sound:", font=("Segoe UI", 9),
                 bg=self.SB_BG, fg=self.SB_TEXT).pack(side="left")
        self._ls_var = tk.StringVar(value=self.app.config.get("launch_sound") or "Coin")
        opts = ["None"] + list(SOUND_DEFS.keys())
        om = tk.OptionMenu(top, self._ls_var, *opts, command=self._set_ls)
        om.config(bg=self.SB_CARD, fg=self.SB_TEXT, activebackground="#2a3150",
                  activeforeground="#ffffff", relief="flat", bd=0, highlightthickness=0,
                  font=("Segoe UI", 9), cursor="hand2")
        om["menu"].config(bg=self.SB_CARD, fg=self.SB_TEXT, activebackground="#2a3150", bd=0)
        om.pack(side="left", padx=(10, 0))

        self._en_var = tk.BooleanVar(value=bool(self.app.config["sound"]))
        tk.Checkbutton(top, text="Play when launching", variable=self._en_var,
                       command=self._toggle_enabled, bg=self.SB_BG, fg=self.SB_TEXT,
                       selectcolor=self.SB_CARD, activebackground=self.SB_BG,
                       activeforeground="#ffffff", font=("Segoe UI", 9),
                       cursor="hand2").pack(side="left", padx=(16, 0))

        tk.Label(top, text="Pick a sound to play it.\nThe selected sound plays whenever you launch an app.",
                 font=("Segoe UI", 8), bg=self.SB_BG, fg=self.SB_TEXT,
                 justify="left").pack(anchor="w", pady=(8, 0))

        tk.Label(self, text="\u2015\u2015 Music \u2015\u2015", font=("Segoe UI", 8, "bold"),
                 bg=self.SB_BG, fg=self.SB_TEXT).pack(anchor="w", padx=16, pady=(10, 4))
        music_row = tk.Frame(self, bg=self.SB_BG)
        music_row.pack(fill="x", padx=16)
        tk.Button(music_row, text="\U0001f3b5  Open Music player",
                  command=self.app.open_music,
                  bg=self.SB_CARD, fg="#6c8cff", activebackground="#2a3150",
                  activeforeground="#ffffff", relief="flat", bd=0, padx=12, pady=9,
                  font=("Segoe UI", 10, "bold"), cursor="hand2").pack(fill="x")

        grid = tk.Frame(self, bg=self.SB_BG)
        grid.pack(fill="both", expand=True, padx=16, pady=6)
        names = list(SOUND_DEFS.keys())
        for i, name in enumerate(names):
            color = ACCENTS[i % len(ACCENTS)]
            b = tk.Button(grid, text=f"{SOUND_ICONS[name]}\n{name}",
                          command=lambda n=name, c=color: self._play(n, c),
                          bg=self.SB_CARD, fg=self.SB_TEXT, activebackground=color,
                          activeforeground="#111111", relief="flat", bd=0,
                          font=("Segoe UI", 9, "bold"), width=11, height=3,
                          cursor="hand2", highlightthickness=2, highlightbackground=color)
            b.grid(row=i // 3, column=i % 3, padx=5, pady=5)

        self._status = tk.Label(self, text="", font=("Segoe UI", 9), bg=self.SB_BG,
                                fg=self.SB_TEXT)
        self._status.pack(side="bottom", pady=(0, 12))

    def _play(self, name, color):
        play_sound(name)
        self._set_ls(name)
        self._status.config(text=f"Playing: {name}", fg=color)
        self._status.after(1500, lambda: self._status.config(text="", fg=self.SB_TEXT))

    def _set_ls(self, value):
        self.app.set_config("launch_sound", value)
        if value != "None":
            self.app.set_config("sound", True)
            self._en_var.set(True)

    def _toggle_enabled(self):
        self.app.set_config("sound", bool(self._en_var.get()))


JOKES = [
    "Why don't programmers like nature? Too many bugs.",
    "Why did the developer go broke? They used up all their cache.",
    "There are only 10 kinds of people: those who understand binary and those who don't.",
    "Why was the computer cold? Because it left its Windows open.",
    "I told my computer I needed a break. Now it keeps sending me Kit-Kat ads.",
    "Why do Java developers wear glasses? Because they can't C#.",
]

BUILTIN_APPS = {
    "notepad": "notepad", "note pad": "notepad",
    "calculator": "calc", "calc": "calc",
    "paint": "mspaint",
    "command prompt": "cmd", "cmd": "cmd", "terminal": "wt",
    "file explorer": "explorer", "explorer": "explorer", "files": "explorer",
    "control panel": "control",
    "settings": "start ms-settings:",
    "task manager": "taskmgr",
    "snipping tool": "snippingtool",
    "wordpad": "write",
    "camera": "start microsoft.windows.camera:",
    "microsoft store": "start ms-windows-store:",
    "edge": "msedge", "microsoft edge": "msedge",
    "chrome": "chrome", "google chrome": "chrome",
    "firefox": "firefox",
    "vs code": "code", "visual studio code": "code",
    "spotify": "spotify",
    "youtube": "start https://www.youtube.com",
    "maps": "start ms-windows-map:",
}

SITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com", "yt": "https://www.youtube.com",
    "wikipedia": "https://www.wikipedia.org", "wiki": "https://www.wikipedia.org",
    "github": "https://github.com", "gh": "https://github.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://x.com", "x": "https://x.com",
    "facebook": "https://www.facebook.com", "fb": "https://www.facebook.com",
    "instagram": "https://www.instagram.com", "insta": "https://www.instagram.com",
    "tiktok": "https://www.tiktok.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "amazon": "https://www.amazon.com",
    "ebay": "https://www.ebay.com",
    "steam": "https://store.steampowered.com",
    "twitch": "https://www.twitch.tv",
    "discord": "https://discord.com",
    "gmail": "https://mail.google.com",
    "maps": "https://www.google.com/maps",
    "chatgpt": "https://chat.openai.com",
    "bing": "https://www.bing.com",
    "duckduckgo": "https://duckduckgo.com",
    "roblox": "https://www.roblox.com",
    "yahoo": "https://www.yahoo.com",
    "pinterest": "https://www.pinterest.com",
    "linkedin": "https://www.linkedin.com",
    "bbc": "https://www.bbc.com",
    "cnn": "https://www.cnn.com",
    "whatsapp": "https://web.whatsapp.com",
    "stackoverflow": "https://stackoverflow.com",
    "hacker news": "https://news.ycombinator.com",
    "weather": "https://weather.com",
    "speedtest": "https://www.speedtest.net",
    "canva": "https://www.canva.com",
    "drive": "https://drive.google.com",
    "classroom": "https://classroom.google.com",
    "meet": "https://meet.google.com",
    "spotify web": "https://open.spotify.com",
}

SITE_SEARCH = {
    "youtube": "https://www.youtube.com/results?search_query={}",
    "youtube music": "https://music.youtube.com/search?q={}",
    "google": "https://www.google.com/search?q={}",
    "bing": "https://www.bing.com/search?q={}",
    "duckduckgo": "https://duckduckgo.com/?q={}",
    "wikipedia": "https://en.wikipedia.org/w/index.php?search={}",
    "github": "https://github.com/search?q={}",
    "reddit": "https://www.reddit.com/search/?q={}",
    "amazon": "https://www.amazon.com/s?k={}",
    "ebay": "https://www.ebay.com/sch/i.html?_nkw={}",
    "twitter": "https://x.com/search?q={}",
    "maps": "https://www.google.com/maps/search/{}",
    "stackoverflow": "https://stackoverflow.com/search?q={}",
    "walmart": "https://www.walmart.com/search?q={}",
    "spotify": "https://open.spotify.com/search/{}",
    "netflix": "https://www.netflix.com/search?q={}",
    "chatgpt": "https://chatgpt.com/?q={}",
    "roblox": "https://www.roblox.com/search/results?Keyword={}",
}


def safe_eval(expr):
    e = (expr.replace("^", "**").replace("\u00d7", "*").replace("\u00f7", "/")
         .replace("x", "*").replace("X", "*"))
    tree = ast.parse(e, mode="eval")
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Add, ast.Sub,
               ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv, ast.USub, ast.UAdd)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError("disallowed expression")
    return eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, {})


class AssistantWindow(tk.Toplevel):
    AS_BG = "#14182a"
    AS_CARD = "#1f2434"
    AS_TEXT = "#e9ecf5"
    AS_MUTED = "#8b93a7"

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("AI Assistant")
        self.configure(bg=self.AS_BG)
        self.geometry("560x660")
        self.minsize(420, 480)
        self._busy = False
        self._history = []
        self._links = {}
        self._build()
        self._greet()

    def _build(self):
        title = tk.Label(self, text="AI Assistant",
                         font=tkfont.Font(family="Segoe UI", size=14, weight="bold"),
                         bg=self.AS_BG, fg=self.app._accent())
        title.pack(anchor="w", padx=14, pady=(12, 0))
        mode = ("AI mode \u00b7 uses your API key"
                if self.app.config.get("ai_api_key")
                else "Local mode \u00b7 works offline")
        tk.Label(self, text=mode, font=("Segoe UI", 8), bg=self.AS_BG,
                 fg=self.AS_MUTED).pack(anchor="w", padx=14)

        chat_wrap = tk.Frame(self, bg=self.AS_BG)
        chat_wrap.pack(fill="both", expand=True, padx=14, pady=(8, 6))
        self.chat = tk.Text(chat_wrap, bg=self.AS_CARD, fg=self.AS_TEXT, relief="flat", bd=0,
                            font=("Segoe UI", 10), wrap="word", state="disabled",
                            padx=10, pady=10, highlightthickness=1, highlightbackground="#2c3350",
                            selectbackground=self.app._accent())
        self.chat.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(chat_wrap, command=self.chat.yview, bg=self.AS_CARD,
                          troughcolor=self.AS_BG, bd=0)
        sb.pack(side="right", fill="y")
        self.chat.configure(yscrollcommand=sb.set)
        self.chat.tag_configure("you", foreground=self.app._accent(),
                                font=("Segoe UI", 10, "bold"))
        self.chat.tag_configure("ai", foreground="#9ad7ff")
        self.chat.tag_configure("err", foreground="#ff9aa2")

        chips = tk.Frame(self, bg=self.AS_BG)
        chips.pack(fill="x", padx=14)
        for label in ("What apps do I have?", "Open apps folder", "What time is it?",
                      "System info", "Search the web for games", "Tell me a joke"):
            tk.Button(chips, text=label, command=lambda l=label: self._fill(l),
                      bg=self.AS_CARD, fg=self.AS_TEXT, activebackground="#2a3150",
                      activeforeground="#ffffff", relief="flat", bd=0, padx=8, pady=4,
                      font=("Segoe UI", 8), cursor="hand2").pack(side="left", padx=(0, 6))

        input_wrap = tk.Frame(self, bg=self.AS_BG)
        input_wrap.pack(fill="x", padx=14, pady=(8, 0))
        self.entry = tk.Entry(input_wrap, bg=self.AS_CARD, fg=self.AS_TEXT,
                              insertbackground=self.AS_TEXT, relief="flat", bd=0,
                              highlightthickness=1, highlightbackground="#2c3350",
                              highlightcolor=self.app._accent(), font=("Segoe UI", 10))
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.entry.bind("<Return>", self._send)
        self.send_btn = tk.Button(input_wrap, text="Send", command=self._send,
                                  bg=self.app._accent(), fg="#0d1220",
                                  activebackground="#86a0ff", activeforeground="#0d1220",
                                  relief="flat", bd=0, padx=16,
                                  font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.send_btn.pack(side="left", padx=(8, 0))
        self.status = tk.Label(self, text="", font=("Segoe UI", 8), bg=self.AS_BG,
                               fg=self.AS_MUTED)
        self.status.pack(anchor="w", padx=14, pady=(4, 10))
        self.entry.focus_set()

    # ---------- chat plumbing ----------
    def _append(self, text, tag=None):
        self.chat.configure(state="normal")
        self.chat.insert("end", text, tag)
        self.chat.insert("end", "\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _add(self, who, text, link_url=None):
        tag = "you" if who == "You" else "ai"
        self._append(f"{who}: ", tag)
        if link_url:
            name = "lnk%d" % len(self._links)
            self._links[name] = link_url
            self.chat.configure(state="normal")
            self.chat.insert("end", text, name)
            self.chat.insert("end", "\n")
            self.chat.configure(state="disabled")
            self.chat.tag_configure(name, foreground="#7cc7ff", underline=True)
            self.chat.tag_bind(name, "<Enter>",
                               lambda e: self.chat.configure(cursor="hand2"))
            self.chat.tag_bind(name, "<Leave>",
                               lambda e: self.chat.configure(cursor=""))
            self.chat.tag_bind(name, "<Button-1>",
                               lambda e, n=name: self._open_link(n))
            self.chat.see("end")
        else:
            self._append(text)

    def _open_link(self, name):
        url = self._links.get(name)
        if url:
            webbrowser.open(url)

    def _greet(self):
        self._add("AI", f"Hey {getpass.getuser()}! I'm your launcher assistant. "
                        "I can open apps and websites, search the web, do quick math, check the weather "
                        "and tell you about your PC. Type 'help' to see everything.")

    def _fill(self, label):
        if self._busy:
            return
        self.entry.delete(0, "end")
        self.entry.insert(0, label)
        self.entry.focus_set()

    def _set_busy(self, busy):
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.send_btn.config(state=state)
        self.entry.config(state=state)
        self.status.config(text="Thinking\u2026" if busy else "")

    def _send(self, event=None):
        text = self.entry.get().strip()
        if not text or self._busy:
            return
        self.entry.delete(0, "end")
        self._add("You", text)
        self._set_busy(True)
        threading.Thread(target=self._work, args=(text,), daemon=True).start()

    def _work(self, text):
        try:
            reply, link = self._handle(text)
        except Exception as e:
            reply, link = f"Oops, I hit a problem: {e}", None
        self.after(0, lambda: self._finish(reply, link))

    def _finish(self, reply, link):
        self._set_busy(False)
        self._add("AI", reply, link)
        self.entry.focus_set()

    # ---------- intents ----------
    def _handle(self, text):
        t = text.strip()
        low = t.lower()
        self._history.append({"role": "user", "content": t})
        self._history = self._history[-12:]

        if re.fullmatch(r"(hi|hello|hey|yo|hiya|sup|howdy)[\s!.]*", low):
            return "Hello! Try 'help' to see what I can do.", None
        if any(w in low for w in ("who are you", "what are you")):
            return ("I'm your launcher assistant. I live inside your App Launcher: I can "
                    "open your apps, list what's installed, search the web, do math, check "
                    "the weather and read your PC's info."), None
        if low in ("help", "commands", "help me") or "what can you do" in low:
            return self._help(), None
        if re.search(r"\b(thanks|thank you|thx)\b", low):
            return "You're welcome!", None
        if "joke" in low or "make me laugh" in low:
            return random.choice(JOKES), None
        if "flip" in low and "coin" in low:
            return f"I flipped a coin: {random.choice(['Heads', 'Tails'])}.", None
        if "roll" in low and ("dice" in low or "die" in low):
            return f"You rolled a {random.randint(1, 6)}.", None
        if "time" in low and any(w in low for w in ("what", "current", "now", "is it")):
            return f"The time is {datetime.datetime.now():%I:%M %p}.", None
        if "date" in low or ("day" in low and "what" in low):
            return f"Today is {datetime.datetime.now():%A, %B %d, %Y}.", None

        low2 = low.rstrip("?!.")
        m = re.search(r"(?:calculate|compute|what is|what's|whats|eval)\s+([0-9+\-*/().%^xX\u00d7\u00f7\s]+)$", low2)
        expr = m.group(1) if m else (low2 if re.fullmatch(r"[0-9+\-*/().%^xX\u00d7\u00f7\s]+", low2) else None)
        if expr:
            try:
                return f"{expr.strip()} = {safe_eval(expr)}", None
            except Exception:
                pass

        if "apps folder" in low and ("open" in low or "show" in low):
            try:
                os.startfile(APPS_DIR)
                return "Opened your apps folder.", None
            except Exception as e:
                return f"Could not open the apps folder: {e}", None

        if re.fullmatch(r"(?:open|start|launch|show)(?: the| my)? browser(?: now)?", low):
            self.after(0, self.app.open_browser)
            return "Opening the browser.", None

        m = re.match(r"(?:browse|go(?: to)?|visit|open website|open the website|open site|navigate to)\s+(?:the\s+)?(.+?)\s*$", low)
        if m and m.group(1).strip():
            return self._open_site(m.group(1).strip().rstrip(".!?"))

        game = self._game_from(low)
        if game:
            cls, name = game
            if isinstance(cls, str):
                url = cls
                webbrowser.open(url)
                return f"Opening {name} in your browser - have fun!", url
            self.after(0, lambda c=cls: c(self.app))
            return f"Opening {name} - have fun!", None
        if low in ("games", "play games", "play a game", "open games", "show games") or re.search(r"(play|open|show)\s+games", low):
            self.after(0, lambda: AppGames.GamesWindow(self.app))
            return "Opening the games menu - enjoy!", None

        m = re.match(r"(?:open|launch|start|run)\s+(?:the\s+|an?\s+|app\s+|application\s+)?(.+?)\s*$", low)
        if m:
            return self._open_target(m.group(1).strip().rstrip(".!?"))

        if any(k in low for k in ("what apps", "list apps", "show apps", "my apps", "which apps")):
            names = sorted(os.path.splitext(n)[0] for n, _, _ in self.app.items)
            if not names:
                return "Your apps folder is empty - use the + button to add apps!", None
            return f"You have {len(names)} app(s): {', '.join(names)}", None

        m = re.match(r"(?:search|find|look up)\s+(?:for\s+)?(.+?)\s+(?:on|in)\s+([a-zA-Z0-9 .-]+)$", low)
        if m and m.group(1).strip() and m.group(2).strip():
            return self._site_search(m.group(2).strip(), m.group(1).strip().rstrip("?!."))
        m = re.match(r"(?:search|find)\s+([a-zA-Z0-9 .-]+?)\s+(?:for|about)\s+(.+)$", low)
        if m and m.group(1).strip() and m.group(2).strip():
            return self._site_search(m.group(1).strip(), m.group(2).strip().rstrip("?!."))

        m = re.match(r"(?:search(?: the web| google| for| online| up)?|google|look up|find|who is|how to|how do)\s+(?:for\s+)?(.+)", low)
        if m and m.group(1).strip():
            q = m.group(1).strip().rstrip("?!.")
            url = "https://www.google.com/search?q=" + urllib.parse.quote(q)
            webbrowser.open(url)
            return f"Opened a Google search for \"{q}\" in your browser.", url

        m = re.match(r"(?:weather|temperature)(?: in| for)?\s+([\w\s,'-]+)", low)
        if m and m.group(1).strip():
            return self._weather(m.group(1).strip())

        if any(k in low for k in ("system info", "system information", "pc info", "computer info", "specs", "about this pc")):
            return self._sysinfo()
        if "battery" in low:
            return self._battery()
        if "my ip" in low or ("ip" in low and "what" in low):
            return self._my_ip()

        if re.fullmatch(r"lock( the)? (pc|computer|screen)", low) or low in ("lock", "lock pc"):
            self.after(0, self._lock)
            return "Locking your PC.", None
        if re.match(r"(shut\s*down|shutdown|turn off the (pc|computer))", low):
            self.after(0, self._shutdown)
            return "OK, I'll ask you to confirm shutting down.", None
        if re.match(r"(restart|reboot)( the (pc|computer))?", low):
            self.after(0, self._restart)
            return "OK, I'll ask you to confirm restarting.", None

        key = (self.app.config.get("ai_api_key") or "").strip()
        if key:
            reply = self._llm(text)
            return reply, None

        url = "https://www.google.com/search?q=" + urllib.parse.quote(t)
        return "I don't have a built-in answer for that, but I can look it up for you:", url

    def _help(self):
        return ("Here's what I can do:\n"
                "  \u2022 Open an app: \"open calculator\" or \"launch youtube\"\n"
                "  \u2022 Open a website: \"go to youtube\", \"open github.com\"\n"
                "  \u2022 Search a site: \"search youtube for kittens\" or \"look up python on wikipedia\"\n"
                "  \u2022 List your apps: \"what apps do I have?\"\n"
                "  \u2022 Search the web: \"search the web for kittens\"\n"
                "  \u2022 Quick math: \"what is 25*4?\"\n"
                "  \u2022 Weather: \"weather in Tokyo\"\n"
                "  \u2022 Your PC: \"system info\", \"battery\", \"my ip\"\n"
                "  \u2022 Time and date: \"what time is it?\"\n"
                "  \u2022 Fun: \"tell me a joke\", \"flip a coin\"\n"
                "  \u2022 Power: \"lock the pc\", \"shut down\", \"restart\"\n"
                "  \u2022 Games: \"play chess\", \"play snake\", \"play 2048\", \"play wordle\"\n"
                "Add an API key in Settings to chat about anything.")

    GAME_OPENERS = [
        (("chess", "chess game"), ChessWindow, "Chess"),
        (("tic tac toe", "tictactoe"), TicTacToeWindow, "Tic-Tac-Toe"),
        (("connect four", "connect 4", "connect4"), Connect4Window, "Connect 4"),
        (("snake", "snake game"), SnakeWindow, "Snake"),
        (("2048", "twenty forty eight"), Tile2048Window, "2048"),
        (("wordle", "word game"), WordleWindow, "Wordle"),
        (("memory", "memory game", "memory match"), MemoryWindow, "Memory"),
        (("slope", "slope game"), "https://slopeio.org/", "Slope"),
    ]

    def _game_from(self, low):
        m = re.match(r"(?:play|start|open|launch)\s+(?:a\s+)?(?:game\s+of\s+)?(.+?)\s*$", low)
        q = re.sub(r"[^a-z0-9 ]", "", m.group(1).strip()) if m else low.strip()
        q = re.sub(r"\s+", " ", q).strip()
        if not q or q in ("games", "a game", "the game"):
            return None
        for names, cls, label in self.GAME_OPENERS:
            for n in names:
                if q == n or q.startswith(n) or n in q:
                    return cls, label
        return None

    def _open_target(self, target):
        hit = self._find_app(target)
        if hit:
            n, p = hit
            try:
                os.startfile(p)
                self._history.append({"role": "assistant", "content": f"Opened {n}."})
                return f"Opened {n} for you.", None
            except Exception as e:
                return f"I couldn't open {n}: {e}", None
        if re.fullmatch(r"[\w.-]+\.[a-z]{2,}(?:[/?#].*)?", target, re.IGNORECASE):
            url = target if target.startswith("http") else "https://" + target
            webbrowser.open(url)
            return f"Opened {url}.", url
        s = SITES.get(target)
        if not s:
            close = difflib.get_close_matches(target, list(SITES), n=1, cutoff=0.6)
            if close:
                s = SITES[close[0]]
        if s:
            webbrowser.open(s)
            return f"Opened {target.title()} for you.", s
        builtin = BUILTIN_APPS.get(target)
        if not builtin:
            close = difflib.get_close_matches(target, BUILTIN_APPS, n=1, cutoff=0.6)
            if close:
                builtin = BUILTIN_APPS[close[0]]
        if builtin:
            try:
                if builtin.startswith("start "):
                    os.system(builtin)
                else:
                    subprocess.Popen(builtin, shell=True)
                return f"Opened {builtin.split(' ')[-1]} for you.", None
            except Exception as e:
                return f"I couldn't open that: {e}", None
        if os.path.exists(target):
            try:
                os.startfile(target)
                return f"Opened {target}.", None
            except Exception as e:
                return f"I couldn't open {target}: {e}", None
        names = ", ".join(sorted(os.path.splitext(n)[0] for n, _, _ in self.app.items))
        return f"I couldn't find \"{target}\" in your apps. You have: {names or 'nothing yet - add apps with the + button'}.", None

    def _find_app(self, target):
        want = re.sub(r"\W+", "", target.lower())
        items = self.app.items
        for n, p, _ in items:
            base = re.sub(r"\W+", "", os.path.splitext(n)[0].lower())
            if base == want:
                return n, p
        for n, p, _ in items:
            if want and want in os.path.splitext(n)[0].lower():
                return n, p
        bases = {os.path.splitext(n)[0].lower(): (n, p) for n, p, _ in items}
        matches = difflib.get_close_matches(want, list(bases), n=1, cutoff=0.55)
        if matches:
            return bases[matches[0]]
        return None

    def _open_site(self, name):
        n = name.lower().strip()
        if re.fullmatch(r"[\w.-]+\.[a-z]{2,}(?:[/?#].*)?", n, re.IGNORECASE):
            url = n if n.startswith("http") else "https://" + n
            self.app.open_browser(url)
            return f"Opened {url}.", url
        s = SITES.get(n)
        if not s:
            close = difflib.get_close_matches(n, list(SITES), n=1, cutoff=0.6)
            if close:
                s = SITES[close[0]]
        if s:
            self.app.open_browser(s)
            return f"Opened {n.title()} for you.", s
        return self._open_target(name)

    def _site_search(self, site, q):
        s = site.lower().strip()
        template = SITE_SEARCH.get(s)
        if not template:
            close = difflib.get_close_matches(s, list(SITE_SEARCH), n=1, cutoff=0.6)
            if close:
                template = SITE_SEARCH[close[0]]
        if not template and s in SITES:
            template = SITES[s] + "/search?q={}"
        if not template:
            url = "https://www.google.com/search?q=" + urllib.parse.quote(q)
            webbrowser.open(url)
            return f"I don't know a search for \"{site}\", so I Googled \"{q}\" instead.", url
        url = template.format(urllib.parse.quote(q))
        webbrowser.open(url)
        return f"Opened a {site} search for \"{q}\".", url

    def _weather(self, city):
        try:
            url = ("https://wttr.in/" + urllib.parse.quote(city)
                   + "?format=%l:+%c+%t,+%w,+%h")
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
            with urllib.request.urlopen(req, timeout=12) as r:
                data = r.read().decode("utf-8", "ignore").strip()
            if data and "Unknown location" not in data:
                return f"Here's the weather: {data}", None
            return f"I couldn't find weather for \"{city}\".", None
        except Exception:
            return f"I couldn't fetch the weather for \"{city}\" right now.", None

    def _sysinfo(self):
        info = [f"OS: {platform.system()} {platform.release()} ({platform.version()[:45]})"]
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
                cpu = winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
            info.append(f"CPU: {cpu}")
        except Exception:
            pass
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        ms = MEMORYSTATUSEX()
        ms.dwLength = ctypes.sizeof(ms)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
            info.append(f"RAM: {ms.ullTotalPhys / 1024**3:.1f} GB total, "
                        f"{ms.ullAvailPhys / 1024**3:.1f} GB free")
        return "\n".join(info), None

    def _battery(self):
        class SYSTEM_POWER_STATUS(ctypes.Structure):
            _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte),
                        ("BatteryLifePercent", ctypes.c_ubyte), ("SystemStatusFlag", ctypes.c_ubyte),
                        ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]
        try:
            lib = ctypes.windll.kernel32
            func = lib.GetSystemPowerStatus
            func.restype = ctypes.c_ubyte
            func.argtypes = [ctypes.POINTER(SYSTEM_POWER_STATUS)]
            p = SYSTEM_POWER_STATUS()
            if func(ctypes.byref(p)):
                if p.BatteryFlag in (128, 255):
                    return "No battery detected (desktop PC).", None
                status = "charging" if p.ACLineStatus == 1 else "on battery"
                return f"Battery: {p.BatteryLifePercent}% ({status}).", None
            return "I couldn't read the battery status.", None
        except Exception:
            return "I couldn't read the battery status.", None

    def _my_ip(self):
        out = []
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            out.append("Local IP: " + s.getsockname()[0])
            s.close()
        except Exception:
            pass
        try:
            with urllib.request.urlopen("https://api.ipify.org", timeout=8) as r:
                out.append("Public IP: " + r.read().decode("utf-8", "ignore").strip())
        except Exception:
            pass
        return "\n".join(out) if out else "I couldn't find your IP address.", None

    def _lock(self):
        try:
            ctypes.windll.user32.LockWorkStation()
        except Exception:
            pass

    def _shutdown(self):
        if messagebox.askyesno("AI Assistant",
                               "Shut down this PC in 10 seconds? (you can cancel later with 'shutdown /a')",
                               parent=self):
            os.system("shutdown /s /t 10")

    def _restart(self):
        if messagebox.askyesno("AI Assistant",
                               "Restart this PC in 10 seconds? (you can cancel later with 'shutdown /a')",
                               parent=self):
            os.system("shutdown /r /t 10")

    def _llm(self, text):
        key = (self.app.config.get("ai_api_key") or "").strip()
        url = self.app.config.get("ai_api_url") or "https://api.openai.com/v1/chat/completions"
        model = self.app.config.get("ai_model") or "gpt-4o-mini"
        body = json.dumps({
            "model": model,
            "messages": [{"role": "system",
                          "content": "You are a friendly, concise desktop assistant inside a launcher app."}]
                         + self._history,
            "max_tokens": 350,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
        })
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.loads(r.read().decode("utf-8"))
            reply = data["choices"][0]["message"]["content"].strip()
            self._history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            return f"I couldn't reach the AI service: {e}"


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    try:
        app = AppLauncher()
        app.mainloop()
    except Exception as e:
        try:
            import tkinter.messagebox as mb
            mb.showerror("App Launcher error", str(e))
        except Exception:
            pass


if __name__ == "__main__":
    main()

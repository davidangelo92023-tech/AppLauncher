import os
import sys
import json
import math
import re
import ast
import shutil
import stat
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
import AppContacts
import AppNet

if getattr(sys, "frozen", False):
    # Running as a PyInstaller .exe - __file__ points inside the temporary
    # extraction folder, not the real install folder, so anchor on the exe
    # itself instead. Otherwise every relative path (apps/, icon.ico, Music/)
    # silently resolves to an empty temp dir and the app grid looks empty.
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APPS_DIR = os.path.join(BASE_DIR, "apps")
try:
    os.makedirs(APPS_DIR, exist_ok=True)
except Exception:
    pass

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
    "autostart": False,
    "clear_mode": False,
    "launch_sound": "Coin",
    "radius": 20,
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
    "username": "",
    "avatar": "",
    "owner_secret": "",
    "owner_machine": "",
    "cloud_sync": False,
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
CARD_W = 178
H_GAP = 20
V_GAP = 28
MARGIN = 34
HEADER_Y = 150

FAVORITES_LABEL = "★ Favorites"

# ------- update check -------
# Bump VERSION and push a matching VERSION file to the repo's default branch
# to make this fire for everyone running an older copy. Silently does
# nothing if the file isn't there or can't be reached - never blocks startup.
# AppNet.CLIENT_VERSION is the single source of truth (it's also what gets
# sent to the server on login/register) - mirror it here so a stale copy of
# this constant can never drift out of sync and quietly disable the update
# notice.
VERSION = AppNet.CLIENT_VERSION
UPDATE_REPO_URL = "https://github.com/davidangelo92023-tech/AppLauncher"
UPDATE_RAW_BASE = "https://raw.githubusercontent.com/davidangelo92023-tech/AppLauncher/main/"
UPDATE_CHECK_URL = UPDATE_RAW_BASE + "VERSION"
# The actual app files that get pulled down and overwritten in place when
# someone clicks "Update available". Keep this in sync with what the zip
# ships - apps/, config, and personal data are never touched.
UPDATE_FILES = [
    "AppLauncher.py", "AppContacts.py", "AppNet.py", "AppBrowser.py",
    "AppFriends.py", "AppGames.py", "run.py", "VERSION",
]
FOOTER_H = 46


_NO_WINDOW_FLAGS = 0x08000000  # CREATE_NO_WINDOW


def _hidden_startupinfo():
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE
    return si


def run_hidden(cmd, shell=False, **kwargs):
    """subprocess.Popen wrapper that never flashes a console window.

    Safe to use from pythonw.exe (no console) or python.exe alike -
    replaces os.system()/shell=True calls that would otherwise pop a
    visible cmd.exe window.
    """
    kwargs.setdefault("close_fds", True)
    return subprocess.Popen(
        cmd, shell=shell,
        creationflags=_NO_WINDOW_FLAGS,
        startupinfo=_hidden_startupinfo(),
        **kwargs,
    )


def run_hidden_wait(cmd, shell=False, **kwargs):
    """subprocess.run wrapper that never flashes a console window."""
    return subprocess.run(
        cmd, shell=shell,
        creationflags=_NO_WINDOW_FLAGS,
        startupinfo=_hidden_startupinfo(),
        **kwargs,
    )


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
    run_hidden_wait(["powershell", "-NoProfile", "-NonInteractive", "-STA",
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
        try:
            icon_path = os.path.join(BASE_DIR, "icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass
        self.geometry("1020x680")
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sx = self.winfo_screenwidth()
        sy = self.winfo_screenheight()
        x = (sx - w) // 2
        y = (sy - h) // 2
        self.geometry(f"+{x}+{y}")
        self.minsize(670, 420)
        self.lift()
        self.focus_force()

        self.font_title = tkfont.Font(family="Segoe UI", size=20, weight="bold")
        self.font_sub = tkfont.Font(family="Segoe UI", size=9)
        self.font_card = tkfont.Font(family="Segoe UI", size=9)
        self.font_footer = tkfont.Font(family="Segoe UI", size=9)
        self._badge_font = tkfont.Font(family="Segoe UI", size=8, weight="bold")

        self.config = self._load_config()
        self.icon_size = self.config["icon_size"]
        self.card_h = self.icon_size + 118

        self.items = []
        self.visible = []
        self._photos = []
        self._bg_photo = None
        self._icon_cache = {}
        self._card_bg_cache = {}
        self._pill_bg_cache = {}
        self._logo_cache = {}
        self._accent_bar_cache = {}
        self._btn_specs = {}
        self._search_focused = False
        self._search_focus_ring = None
        self._offset = 0
        self._content_h = 0
        self._hover_idx = None
        self._kbd_idx = None
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
        self._spin_job = None
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
        self._contacts_unread = False
        self._contacts_watch_since = 0.0
        self._contacts_poll_job = None
        self._update_version = None
        self._updating = False
        (self._launches, self._order, self._favorites, self._categories,
         self._dock, self._schedules, self._app_colors, self._app_icons) = self._load_stats()
        self._active_category = "All"
        self._schedule_fired = {}
        self._schedule_job = None
        self._sync_job = None
        self._syncing = False
        self._dragged = False

        self.configure(bg=_hex(self._bg_bottom()))
        self.attributes("-topmost", bool(self.config["on_top"]))
        self._apply_clear_mode()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_widgets()
        self._apply_color_widgets()
        self.refresh_profile_btn()
        self.refresh()
        self._start_auto()
        self._start_effects()
        self._start_stats()
        self._apply_tray()
        self._apply_autostart()
        self._start_contacts_watch()
        self._start_update_check()
        self._start_schedule_watch()
        self._start_cloud_sync()
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
                return (data.get("launches", {}), data.get("order", []),
                        set(data.get("favorites", [])), data.get("categories", {}),
                        data.get("dock", []), data.get("schedules", {}),
                        data.get("app_colors", {}), data.get("app_icons", {}))
        except Exception:
            pass
        return {}, [], set(), {}, [], {}, {}, {}

    def _save_stats(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump({"launches": self._launches, "order": self._order,
                          "favorites": sorted(self._favorites), "categories": self._categories,
                          "dock": self._dock, "schedules": self._schedules,
                          "app_colors": self._app_colors, "app_icons": self._app_icons},
                         f, indent=2)
        except Exception:
            pass

    # Config keys that identify *this PC* rather than being a look/feel
    # preference - never sync or export/import these, or a pull on another
    # machine would silently steal the Owner claim or move it to nowhere.
    _NON_SYNCED_CONFIG_KEYS = ("owner_secret", "owner_machine")

    def _stats_blob(self):
        """Everything sync-worthy, bundled as one dict - used by both the
        export-to-file and the cloud-sync features so they stay in sync with
        each other and with what _save_stats persists locally."""
        cfg = {k: v for k, v in self.config.items() if k not in self._NON_SYNCED_CONFIG_KEYS}
        return {
            "favorites": sorted(self._favorites), "categories": self._categories,
            "dock": self._dock, "schedules": self._schedules,
            "app_colors": self._app_colors, "config": cfg,
        }

    def _apply_stats_blob(self, blob):
        if not isinstance(blob, dict):
            return
        self._favorites = set(blob.get("favorites", []))
        self._categories = dict(blob.get("categories", {}))
        self._dock = list(blob.get("dock", []))
        self._schedules = dict(blob.get("schedules", {}))
        self._app_colors = dict(blob.get("app_colors", {}))
        incoming_cfg = blob.get("config")
        if isinstance(incoming_cfg, dict):
            for k, v in incoming_cfg.items():
                if k not in self._NON_SYNCED_CONFIG_KEYS:
                    self.config[k] = v
            self._save_config()
        self._save_stats()

    def export_settings(self):
        path = filedialog.asksaveasfilename(
            title="Export settings", defaultextension=".json",
            initialfile="AppLauncher-settings.json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._stats_blob(), f, indent=2)
            self._flash_status("Settings exported")
        except Exception as e:
            messagebox.showerror("Export settings", str(e))

    def import_settings(self):
        path = filedialog.askopenfilename(
            title="Import settings", filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                blob = json.load(f)
        except Exception as e:
            messagebox.showerror("Import settings", str(e))
            return
        if not messagebox.askyesno("Import settings",
                                   "This will replace your current favorites, categories, dock,\n"
                                   "schedules and look/feel settings with what's in this file. Continue?"):
            return
        self._apply_stats_blob(blob)
        self.refresh()
        if hasattr(self, "cv") and self.cv.winfo_width() > 10:
            self._draw_bg()
        self._flash_status("Settings imported")

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

    TRANSPARENT_COLOR = "#010001"

    def _apply_config(self):
        self.icon_size = self.config["icon_size"]
        self.card_h = self.icon_size + 118
        self.font_card.configure(size=self.config["label_size"])
        self.attributes("-topmost", bool(self.config["on_top"]))
        self.attributes("-alpha", float(self.config.get("alpha", 1.0)))
        self._apply_clear_mode()
        self._apply_color_widgets()
        if not self.config.get("clear_mode", False):
            self.configure(bg=_hex(self._bg_bottom()))
            self.cv.configure(bg=_hex(self._bg_bottom()))
        self._draw_bg()
        self.refresh()
        self._start_auto()
        self._start_effects()
        self._start_stats()
        self._apply_tray()
        self._apply_autostart()

    def _apply_clear_mode(self):
        try:
            cm = self.config.get("clear_mode", False)
            if cm:
                tc = self.TRANSPARENT_COLOR
                self.attributes("-transparentcolor", tc)
                self.configure(bg=tc)
                self.cv.configure(bg=tc)
                self.search_entry.config(bg=SEARCH_FILL_HEX)
                # toolbar buttons are canvas-drawn pills now, not widgets -
                # nothing to reconfigure here, they redraw via _layout_header.
            else:
                self.attributes("-transparentcolor", "")
                self.configure(bg=_hex(self._bg_bottom()))
                self.cv.configure(bg=_hex(self._bg_bottom()))
        except Exception:
            pass

    def _apply_color_widgets(self):
        tc, mc = self._text_color(), self._muted_color()
        # toolbar button labels are canvas text now, recolored on every
        # _layout_header() call - nothing to configure here for them.
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

    def _mix(self, c1, c2, t):
        a, b = self._rgb(c1), self._rgb(c2)
        return tuple(max(0, min(255, int(a[i] + (b[i] - a[i]) * t))) for i in range(3))

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

        # Toolbar buttons are drawn entirely on the canvas (pill image + label,
        # click/hover wired via tag bindings) instead of native tk.Button
        # widgets - a real button sitting on top of a rounded pill is always
        # a hard rectangle, so it would hide the pill's rounded corners
        # behind its own square edges no matter how round the pill is.
        self._toolbar_defs = {
            "refresh":   dict(glyph="\u21bb  Refresh", font=("Segoe UI", 10), command=self.refresh, color="text"),
            "gear":      dict(glyph="\u2699", font=("Segoe UI", 13), command=self.open_settings, color="text"),
            "add":       dict(glyph="+", font=("Segoe UI", 15), command=self.add_app, color="text"),
            "music":     dict(glyph="\u266a", font=("Segoe UI", 13), command=self.open_soundboard, color="text"),
            "assistant": dict(glyph="AI", font=("Segoe UI", 10, "bold"), command=self.open_assistant, color="accent"),
            "games":     dict(glyph="Games", font=("Segoe UI", 10, "bold"), command=self.open_games, color="accent"),
            "browser":   dict(glyph="\U0001f310", font=("Segoe UI", 14), command=self.open_browser, color="accent"),
            "surprise":  dict(glyph="\U0001f3b0", font=("Segoe UI", 15), command=self.open_surprise, color="accent"),
            "contacts":  dict(glyph="\U0001f465", font=("Segoe UI", 13), command=self.open_contacts, color="accent"),
            "profile":   dict(glyph="\U0001f464", font=("Segoe UI", 13), command=self.open_profile, color="accent"),
        }
        self._profile_photo = None

        self._search_win = self.cv.create_window(0, 0, window=self.search_entry, anchor="e")
        self._search_bg = None

        self.bind("<Control-f>", self._focus_search)
        self.bind("<Control-r>", lambda e: self.refresh())
        self.bind("<Control-g>", lambda e: self.open_games())
        self.bind("<Control-b>", lambda e: self.open_browser())
        self.bind("<Control-s>", lambda e: self.open_surprise())
        self.bind("<Escape>", self._on_escape)

        # keyboard grid navigation - arrows move a selection highlight,
        # Enter/Space launches it. Guarded so typing in the search box
        # (or any other text entry) still behaves normally.
        self.bind("<Up>", lambda e: self._kbd_move(0, -1))
        self.bind("<Down>", lambda e: self._kbd_move(0, 1))
        self.bind("<Left>", lambda e: self._kbd_move(-1, 0))
        self.bind("<Right>", lambda e: self._kbd_move(1, 0))
        self.bind("<Return>", self._kbd_activate)
        self.bind("<KP_Enter>", self._kbd_activate)
        self.bind("<space>", self._kbd_activate)

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
        self.cv.delete("bg")
        if self.config.get("clear_mode", False):
            self.cv.create_rectangle(0, 0, w, HEADER_Y - 8, fill=_hex(self._bg_bottom()),
                                     outline="", tags="bg")
            self.cv.create_rectangle(0, h - FOOTER_H, w, h, fill=_hex(self._bg_bottom()),
                                     outline="", tags="bg")
            self.cv.tag_lower("bg")
        elif self.config.get("aurora"):
            self._draw_aurora(w, h)
        else:
            self._bg_photo = make_background(w, h, self._bg_top(), self._bg_bottom(), self._glow())
            self.cv.create_image(0, 0, image=self._bg_photo, anchor="nw", tags="bg")
            self.cv.tag_lower("bg")
        self.search_entry.config(selectbackground=_hex(self._glow()))
        self._layout_header()
        self._layout_chips()
        self._rebuild_cards()
        self._draw_stats()
        if self.config["particles"] and not self.config.get("clear_mode", False):
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
        items = self.cv.find_withtag("accentbar")
        if items:
            color = self._party_accents[self._party_i]
            self.cv.itemconfig(items[0], image=self._accent_bar_photo(118, color=color))
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

    def _glass_photo(self, w, h, r, base, border, hover, gloss_frac=0.5, scale=2):
        """Shared glassy gradient renderer (fill + gloss + border), supersampled
        then downsampled for crisp edges. Used for cards, header pills and the
        logo mark so the whole app shares one visual language."""
        w = max(1, int(w))
        h = max(1, int(h))
        r = max(0, min(int(r), w // 2, h // 2))
        sw, sh, sr = w * scale, h * scale, r * scale

        top_c = self._mix(base, (255, 255, 255), 0.16 if hover else 0.10)
        bot_c = self._mix(base, (0, 0, 0), 0.16 if hover else 0.10)

        col = Image.new("RGB", (1, sh))
        cpx = col.load()
        for y in range(sh):
            cpx[0, y] = self._mix(top_c, bot_c, y / max(1, sh - 1))
        grad = col.resize((sw, sh))

        mask = Image.new("L", (sw, sh), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=sr, fill=255)

        img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        img.paste(grad, (0, 0), mask)

        gloss = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        ImageDraw.Draw(gloss).rounded_rectangle([0, 0, sw - 1, sh * gloss_frac], radius=sr,
                                                 fill=(255, 255, 255, 26 if hover else 18))
        gloss_a = Image.new("L", (sw, sh), 0)
        gloss_a.paste(gloss.split()[3], (0, 0), mask)
        gloss.putalpha(gloss_a)
        img = Image.alpha_composite(img, gloss)

        outline = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        ImageDraw.Draw(outline).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=sr,
                                                   outline=self._rgb(border) + (255,),
                                                   width=max(1, scale))
        img = Image.alpha_composite(img, outline)

        return img.resize((w, h), Image.LANCZOS)

    def _card_bg(self, hover):
        """Glassy gradient card background, cached per (size, radius, colors)
        so it's only re-rendered when the look actually changes - not on
        every hover/scroll."""
        w, h = CARD_W, self.card_h
        r = max(0, int(self.config["radius"]))
        base = self._card_hover() if hover else self._card_fill()
        border = self._card_border()
        key = (w, h, r, base, border, hover)
        cached = self._card_bg_cache.get(key)
        if cached is not None:
            return cached
        photo = ImageTk.PhotoImage(self._glass_photo(w, h, r, base, border, hover))
        self._card_bg_cache[key] = photo
        return photo

    def _pill_bg(self, w, h, r, base, hover):
        """Glassy gradient pill background for the header toolbar/search bar,
        cached per (size, radius, color, hover)."""
        border = self._card_border()
        key = (w, h, r, base, border, hover)
        cached = self._pill_bg_cache.get(key)
        if cached is not None:
            return cached
        photo = ImageTk.PhotoImage(
            self._glass_photo(w, h, r, base, border, hover, gloss_frac=0.55, scale=3)
        )
        self._pill_bg_cache[key] = photo
        return photo

    def _logo_photo(self, size=34):
        """Small glassy app-grid mark shown next to the "App Launcher" title,
        echoing the desktop icon's tile motif. Cached per (size, accent)."""
        accent = self._accent()
        key = (size, accent)
        cached = self._logo_cache.get(key)
        if cached is not None:
            return cached

        scale = 4
        s = size * scale
        a = self._rgb(accent)
        lighter = self._mix(a, (255, 255, 255), 0.35)

        grad = Image.new("RGB", (1, s))
        gpx = grad.load()
        for y in range(s):
            gpx[0, y] = self._mix(lighter, a, y / max(1, s - 1))
        grad = grad.resize((s, s))

        mask = Image.new("L", (s, s), 0)
        r = int(size * 0.32 * scale)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=r, fill=255)
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        img.paste(grad, (0, 0), mask)

        gloss = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(gloss).rounded_rectangle([0, 0, s - 1, int(s * 0.55)], radius=r,
                                                 fill=(255, 255, 255, 55))
        gloss_a = Image.new("L", (s, s), 0)
        gloss_a.paste(gloss.split()[3], (0, 0), mask)
        gloss.putalpha(gloss_a)
        img = Image.alpha_composite(img, gloss)

        # 2x2 grid of tiny tiles, echoing the desktop icon
        pad = int(s * 0.24)
        gap = int(s * 0.10)
        tile = (s - 2 * pad - gap) // 2
        tr = max(1, int(tile * 0.28))
        tiles = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        td = ImageDraw.Draw(tiles)
        for row in range(2):
            for col_i in range(2):
                tx0 = pad + col_i * (tile + gap)
                ty0 = pad + row * (tile + gap)
                alpha = 235 if (row + col_i) % 2 == 0 else 190
                td.rounded_rectangle([tx0, ty0, tx0 + tile, ty0 + tile], radius=tr,
                                      fill=(255, 255, 255, alpha))
        img = Image.alpha_composite(img, tiles)

        outline = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(outline).rounded_rectangle([0, 0, s - 1, s - 1], radius=r,
                                                   outline=(255, 255, 255, 40), width=scale)
        img = Image.alpha_composite(img, outline)

        img = img.resize((size, size), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self._logo_cache[key] = photo
        return photo

    def _accent_bar_photo(self, w, h=4, color=None):
        """Fading gradient underline (solid accent -> transparent) used below
        the title instead of a flat bar."""
        accent = color or self._accent()
        key = (w, h, accent)
        cached = self._accent_bar_cache.get(key)
        if cached is not None:
            return cached
        a = self._rgb(accent)
        img = Image.new("RGBA", (max(1, w), h), (0, 0, 0, 0))
        px = img.load()
        for x in range(w):
            t = x / max(1, w - 1)
            alpha = int(255 * (1 - 0.72 * t))
            for y in range(h):
                px[x, y] = a + (alpha,)
        photo = ImageTk.PhotoImage(img)
        self._accent_bar_cache[key] = photo
        return photo

    def _layout_header(self):
        w = self.cv.winfo_width()
        x = MARGIN
        self.cv.delete("hdr")

        logo_size = 34
        self.cv.create_image(x, 17, image=self._logo_photo(logo_size), anchor="n", tags="hdr")
        title_x = x + logo_size + 10
        self.cv.create_text(title_x, 34, anchor="w", text="App Launcher",
                            font=self.font_title, fill=self._text_color(), tags="hdr")
        self.cv.create_text(title_x, 64, anchor="w", text=APPS_DIR,
                            font=self.font_sub, fill=self._muted_color(), tags="hdr")
        self.cv.create_image(title_x, 78, image=self._accent_bar_photo(118), anchor="nw",
                             tags=("hdr", "accentbar"))

        right = w - MARGIN
        # icon-only pills are shrunk toward square (36) so the max corner
        # radius (16) reads as a near-circle; text pills (AI/Games) stay wider.
        rw, gw, aw, mw, bw, cw, dw, uw, vw, pw, gap, ew = 118, 36, 36, 36, 44, 44, 36, 36, 36, 36, 8, 190
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
        u2 = d1 - gap
        u1 = u2 - uw
        v2 = u1 - gap
        v1 = v2 - vw
        p2 = v1 - gap
        p1 = p2 - pw
        s2 = p1 - gap
        s1 = s2 - ew

        def toolbar_item(which, x1, x2, r, base):
            """Draw a toolbar pill fully on the canvas (background + label)
            and bind clicks/hover to it directly, instead of sitting a real
            tk.Button on top - a native button is always a hard rectangle,
            so it would just hide the pill's rounded corners behind its own
            square edges."""
            w_, h_ = x2 - x1, 32
            cx, cy = (x1 + x2) / 2, 44
            tag = f"tb_{which}"
            img_id = self.cv.create_image(cx, cy, image=self._pill_bg(w_, h_, r, base, False),
                                          tags=("hdr", tag))
            spec = self._toolbar_defs[which]
            if which == "profile" and self._profile_photo is not None:
                self.cv.create_image(cx, cy, image=self._profile_photo, tags=("hdr", tag))
            else:
                fg = self._accent() if spec.get("color") == "accent" else self._text_color()
                self.cv.create_text(cx, cy, anchor="center", text=spec["glyph"],
                                    font=spec["font"], fill=fg, tags=("hdr", tag))
            if which == "contacts" and self._contacts_unread:
                dot_r, dcx, dcy = 5, cx + w_ / 2 - 4, cy - h_ / 2 + 2
                self.cv.create_oval(dcx - dot_r, dcy - dot_r, dcx + dot_r, dcy + dot_r,
                                    fill="#ff4d4f", outline=_hex(self._bg_bottom()), width=2,
                                    tags=("hdr", tag))
            self.cv.tag_bind(tag, "<Button-1>", lambda e, w=which: self._toolbar_defs[w]["command"]())
            self.cv.tag_bind(tag, "<Enter>", lambda e, w=which: self._on_toolbar_hover(w, True))
            self.cv.tag_bind(tag, "<Leave>", lambda e, w=which: self._on_toolbar_hover(w, False))
            self._btn_bgs[which] = img_id
            self._btn_specs[which] = (w_, h_, r, base)

        self._search_bg = self.cv.create_image((s1 + s2) / 2, 44,
                                                image=self._pill_bg(s2 - s1, 32, 16, SEARCH_FILL_HEX, False),
                                                tags="hdr")
        self._search_focus_ring = self._round_rect(s1, 28, s2, 60, 16, fill="",
                                                    outline=self._accent(), width=1.5, tags="hdr")
        self.cv.itemconfig(self._search_focus_ring, state="normal" if self._search_focused else "hidden")

        toolbar_item("profile", p1, p2, 16, BUTTON_FILL_HEX)
        toolbar_item("contacts", v1, v2, 16, BUTTON_FILL_HEX)
        toolbar_item("surprise", u1, u2, 16, BUTTON_FILL_HEX)
        toolbar_item("browser", d1, d2, 16, BUTTON_FILL_HEX)
        toolbar_item("games", c1, c2, 16, BUTTON_FILL_HEX)
        toolbar_item("assistant", b1, b2, 16, BUTTON_FILL_HEX)
        toolbar_item("music", m1, m2, 16, BUTTON_FILL_HEX)
        toolbar_item("add", a1, a2, 16, BUTTON_FILL_HEX)
        toolbar_item("gear", g1, g2, 16, BUTTON_FILL_HEX)
        r2 = right
        toolbar_item("refresh", r1, r2, 16, BUTTON_FILL_HEX)

        self.cv.coords(self._search_win, s2 - 10, 44)
        self.cv.tag_raise(self._search_win)

    def _set_search_focus(self, focused):
        self._search_focused = focused
        if self._search_focus_ring:
            self.cv.itemconfig(self._search_focus_ring, state="normal" if focused else "hidden")

    def _set_btn_hover(self, which, hovered):
        if which in self._btn_bgs and which in self._btn_specs:
            w, h, r, base = self._btn_specs[which]
            self.cv.itemconfig(self._btn_bgs[which], image=self._pill_bg(w, h, r, base, hovered))

    def _on_toolbar_hover(self, which, hovered):
        self._set_btn_hover(which, hovered)
        self.cv.config(cursor="hand2" if hovered else "")

    # ---------- category filter chips ----------
    def _layout_chips(self):
        self.cv.delete("chips")
        labels = ["All", FAVORITES_LABEL] + self._all_categories()
        x = MARGIN
        cy = 100
        h = 24
        gap = 8
        for i, label in enumerate(labels):
            active = label == self._active_category
            tw = self.font_sub.measure(label)
            cw = max(h, tw + 24)
            tag = f"chip{i}"
            base = self._accent() if active else BUTTON_FILL_HEX
            fg = "#14182a" if active else self._text_color()
            self.cv.create_image(x + cw / 2, cy, image=self._pill_bg(cw, h, h // 2, base, False),
                                 tags=("chips", tag))
            self.cv.create_text(x + cw / 2, cy, anchor="center", text=label,
                                font=self.font_sub, fill=fg, tags=("chips", tag))
            self.cv.tag_bind(tag, "<Button-1>", lambda e, l=label: self._set_active_category(l))
            self.cv.tag_bind(tag, "<Enter>", lambda e: self.cv.config(cursor="hand2"))
            self.cv.tag_bind(tag, "<Leave>", lambda e: self.cv.config(cursor=""))
            x += cw + gap

        self._layout_dock(x, cy, h)

    def _set_active_category(self, label):
        if self._active_category == label:
            return
        self._active_category = label
        self._layout_chips()
        self._apply_filter()

    def _toggle_favorite(self, path):
        if path in self._favorites:
            self._favorites.discard(path)
        else:
            self._favorites.add(path)
        self._save_stats()
        self._layout_chips()
        if self._active_category == FAVORITES_LABEL:
            self._apply_filter()

    def _prompt_category(self, path):
        from tkinter import simpledialog
        current = self._categories.get(path, "")
        existing = self._all_categories()
        hint = ", ".join(existing) if existing else "none yet"
        name = simpledialog.askstring(
            "Set category",
            f"Category for this app (existing: {hint}).\nLeave blank to clear.",
            initialvalue=current, parent=self,
        )
        if name is None:
            return
        name = name.strip()
        if name:
            self._categories[path] = name
        else:
            self._categories.pop(path, None)
        self._save_stats()
        if self._active_category not in ("All", FAVORITES_LABEL, *self._all_categories()):
            self._active_category = "All"
        self._layout_chips()
        self._apply_filter()

    def _prompt_app_color(self, path):
        current = self._app_colors.get(path) or accent_for(self._dock_name(path))
        color = colorchooser.askcolor(color=current, parent=self, title="Custom card color")
        if color and color[1]:
            self._app_colors[path] = color[1]
            self._save_stats()
            self._rebuild_cards()

    def _prompt_app_icon(self, path):
        img_path = filedialog.askopenfilename(
            title="Choose a custom icon", parent=self,
            filetypes=[("Images", "*.png *.jpg *.jpeg *.ico *.bmp *.gif"), ("All files", "*.*")],
        )
        if not img_path:
            return
        self._app_icons[path] = img_path
        self._icon_cache = {k: v for k, v in self._icon_cache.items() if k[0] != path}
        self._save_stats()
        self._rebuild_cards()

    def _reset_app_appearance(self, path):
        self._app_colors.pop(path, None)
        self._app_icons.pop(path, None)
        self._icon_cache = {k: v for k, v in self._icon_cache.items() if k[0] != path}
        self._save_stats()
        self._rebuild_cards()

    # ---------- footer ----------
    def _draw_footer(self):
        w = self.cv.winfo_width()
        h = self.cv.winfo_height()
        click_hint = "Click a card to launch" if self.config["click"] == "single" else "Double-click a card to launch"
        self.cv.delete("ftr")
        left = click_hint
        if self.config.get("show_count", True):
            left = f"{len(self.items)} apps  \u00b7  {left}"
        if AppContacts.is_verified_owner():
            left = f"\u2b50 Owner  \u00b7  {left}"
        self.cv.create_text(MARGIN, h - 24, anchor="w",
                            text=left,
                            font=self.font_footer, fill=self._muted_color(), tags="ftr")
        update_to = getattr(self, "_update_version", None)
        if getattr(self, "_updating", False):
            item = self.cv.create_text(w - MARGIN, h - 24, anchor="e",
                                       text="\u2b07 Updating\u2026",
                                       font=self.font_footer, fill=self._accent(), tags="ftr")
        elif update_to:
            item = self.cv.create_text(w - MARGIN, h - 24, anchor="e",
                                       text=f"\U0001f514 Update available (v{update_to}) \u2014 click to update",
                                       font=self.font_footer, fill=self._accent(), tags=("ftr", "update"))
            self.cv.tag_bind(item, "<Button-1>", lambda e: self._on_update_click())
            self.cv.tag_bind(item, "<Enter>", lambda e: self.cv.config(cursor="hand2"))
            self.cv.tag_bind(item, "<Leave>", lambda e: self.cv.config(cursor=""))
        else:
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

    def _on_escape(self, event=None):
        if not self._placeholder:
            self._clear_search()
        elif self._kbd_idx is not None:
            self._kbd_clear()

    # ---------- keyboard grid navigation ----------
    def _kbd_nav_active(self):
        """False while a text entry (search box, etc.) has focus, so arrow
        keys/Enter/Space keep doing their normal text-editing thing there
        instead of also moving the card selection."""
        try:
            f = self.focus_get()
        except Exception:
            return True
        return not isinstance(f, (tk.Entry, tk.Text))

    def _kbd_move(self, dx, dy):
        if not self._kbd_nav_active():
            return
        if not self.visible:
            return "break"
        cols = self._cols()
        n = len(self.visible)
        if self._kbd_idx is None or self._kbd_idx >= n:
            new_idx = 0
        else:
            row, col = divmod(self._kbd_idx, cols)
            row = max(0, row + dy)
            col = max(0, min(cols - 1, col + dx))
            new_idx = min(n - 1, row * cols + col)
        self._set_kbd_idx(new_idx)
        return "break"

    def _set_kbd_idx(self, idx):
        self._kbd_idx = idx
        self._redraw_cards()
        self._scroll_to_kbd_idx()

    def _kbd_clear(self):
        if self._kbd_idx is not None:
            self._kbd_idx = None
            self._redraw_cards()

    def _scroll_to_kbd_idx(self):
        if self._kbd_idx is None or self._kbd_idx not in self._base_pos:
            return
        top, bottom = self._viewport()
        view_h = bottom - top
        if self._content_h <= view_h:
            return
        cols = self._cols()
        row = self._kbd_idx // cols
        card_top = row * (self.card_h + V_GAP)
        card_bottom = card_top + self.card_h
        changed = False
        if card_top < self._offset:
            self._offset = card_top
            changed = True
        elif card_bottom > self._offset + view_h:
            self._offset = card_bottom - view_h
            changed = True
        if changed:
            self._offset = max(0, min(self._offset, self._content_h - view_h))
            self._allow_anim = False
            self._rebuild_cards()

    def _kbd_activate(self, event=None):
        if not self._kbd_nav_active():
            return
        if self._kbd_idx is not None and 0 <= self._kbd_idx < len(self.visible):
            self._launch(self._kbd_idx)
        return "break"

    def _matches_category(self, item):
        if self._active_category == "All":
            return True
        if self._active_category == FAVORITES_LABEL:
            return item[1] in self._favorites
        return self._categories.get(item[1]) == self._active_category

    def _all_categories(self):
        return sorted({c for c in self._categories.values() if c})

    def _apply_filter(self):
        query = self.search_var.get().strip().lower()
        if self._placeholder:
            query = ""
        items = self.items
        if query:
            items = [it for it in items if query in it[0].lower()]
        if self._active_category != "All":
            items = [it for it in items if self._matches_category(it)]
        self.visible = items
        self._allow_anim = True
        self._offset = 0
        self._kbd_idx = None
        self._rebuild_cards()
        self._draw_footer()

    # ---------- cards ----------
    def _viewport(self):
        return HEADER_Y, self.cv.winfo_height() - FOOTER_H

    def _cols(self):
        w = self.cv.winfo_width()
        max_cols = max(2, int(self.config.get("max_cols", 8)))
        return min(max_cols, max(2, (w - 2 * MARGIN + H_GAP) // (CARD_W + H_GAP)))

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

        cols = self._cols()
        rows = (len(self.visible) + cols - 1) // cols if self.visible else 0
        self._content_h = max(view_h, rows * (self.card_h + V_GAP) - V_GAP)
        self._offset = min(self._offset, max(0, self._content_h - view_h))

        for i, (name, path, is_dir) in enumerate(self.visible):
            cx = MARGIN + CARD_W // 2 + (i % cols) * (CARD_W + H_GAP)
            cy = top + self.card_h // 2 + (i // cols) * (self.card_h + V_GAP) - self._offset
            self._base_pos[i] = (cx, cy)
            self._draw_card(i, name, path, is_dir, cx, cy)

        if not self.visible:
            self._draw_empty_state(top, bottom)

        self._draw_thumb()
        self._draw_footer()
        self._animate_cards()

    def _draw_empty_state(self, top, bottom):
        """Shown instead of a blank grid so it's obvious *why* nothing is
        there - either nothing's been added yet, or the active filter/search
        is hiding everything that has been."""
        w = self.cv.winfo_width()
        cx, cy = w / 2, top + (bottom - top) / 2
        if not self.items:
            title = "No apps here yet"
            sub = "Click the + button above to add one, or drop a shortcut into the apps folder."
        elif self._active_category != "All":
            title = f"Nothing in “{self._active_category}”"
            sub = "Click “All” above to see everything again."
        else:
            title = "No matches"
            sub = "Try a different search, or clear it to see everything again."
        self.cv.create_text(cx, cy - 12, anchor="center", text=title,
                            font=self.font_title, fill=self._text_color(), tags="card")
        self.cv.create_text(cx, cy + 16, anchor="center", text=sub, width=min(420, w - 80),
                            justify="center", font=self.font_sub, fill=self._muted_color(),
                            tags="card")

    def _draw_card(self, idx, name, path, is_dir, cx, cy):
        tag = f"c{idx}"
        x0, y0 = cx - CARD_W // 2, cy - self.card_h // 2
        x1, y1 = cx + CARD_W // 2, cy + self.card_h // 2
        r = max(0, int(self.config["radius"]))
        self._card_rects[idx] = (x0, y0, x1, y1)

        self._round_rect(x0, y0 + 8, x1, y1 + 8, r, fill=self._shadow(),
                         outline="", tags=(tag, "card"))

        photo = self._icon_for(path)
        hover_on = idx == self._hover_idx or idx == self._kbd_idx
        glow = bool(self.config.get("hover_glow", True))

        self.cv.create_image(cx, cy, image=self._card_bg(hover_on), tags=(tag, "card"))

        if hover_on and glow:
            border = self._app_colors.get(path) or accent_for(name)
            self._round_rect(x0, y0, x1, y1, r, fill="", outline=border,
                             width=2, tags=(tag, "card"))

        s = self.icon_size
        icon_y = y0 + 44 + s // 2
        self.cv.create_image(cx, icon_y, image=photo, tags=(tag, "card"))

        if hover_on and glow:
            self.cv.create_oval(cx - s / 2 - 6, icon_y - s / 2 - 6, cx + s / 2 + 6, icon_y + s / 2 + 6,
                                outline=border, width=2, tags=(tag, "card"))

        text_color = "#ffffff" if hover_on else self._text_color()
        self.cv.create_text(cx, y0 + self.card_h - 28, anchor="center", width=CARD_W - 26,
                            text=name, font=self.font_card, fill=text_color,
                            justify="center", tags=(tag, "card"))

        if is_dir:
            chip = self._app_colors.get(path) or accent_for(name)
            chip_r = min(9, r + 2) if r else 7
            self._round_rect(x1 - 38, y0 + 12, x1 - 12, y0 + 30, chip_r,
                             fill=chip, outline="", tags=(tag, "card"))
            self.cv.create_text(x1 - 25, y0 + 21, anchor="center",
                                text="\u229e", font=self.font_sub, fill="#14182a",
                                tags=(tag, "card"))

        count = self._launches.get(path, 0)
        if count > 0:
            br = 12
            self._round_rect(x0 + 8, y0 + 8, x0 + 8 + 2 * br, y0 + 8 + 2 * br, br,
                             fill=self._accent(), outline="", tags=(tag, "card"))
            self.cv.create_text(x0 + 8 + br, y0 + 8 + br, anchor="center", text=str(count),
                                font=self._badge_font, fill="#14182a", tags=(tag, "card"))

    def _icon_for(self, path):
        custom = self._app_icons.get(path)
        key = (path, self.icon_size, custom)
        if key not in self._icon_cache:
            photo = None
            if custom and os.path.exists(custom):
                try:
                    img = Image.open(custom).convert("RGBA")
                    img = img.resize((self.icon_size, self.icon_size), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                except Exception:
                    photo = None
            if photo is None:
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
            self._kbd_idx = idx
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
            menu.add_separator()
            fav_label = ("★ Remove from Favorites" if path in self._favorites
                        else "☆ Pin to Favorites")
            menu.add_command(label=fav_label, command=lambda: self._toggle_favorite(path))
            menu.add_command(label="Set category…", command=lambda: self._prompt_category(path))
            dock_label = "Unpin from quick-launch dock" if path in self._dock else "Pin to quick-launch dock"
            menu.add_command(label=dock_label, command=lambda: self._toggle_dock(path))
            menu.add_command(label="Schedule daily launch…", command=lambda: self._prompt_schedule(path))
            menu.add_separator()
            menu.add_command(label="Custom color…", command=lambda: self._prompt_app_color(path))
            menu.add_command(label="Custom icon…", command=lambda: self._prompt_app_icon(path))
            if path in self._app_colors or path in self._app_icons:
                menu.add_command(label="Reset appearance", command=lambda: self._reset_app_appearance(path))
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
        self._do_launch(name, path, is_dir)

    def _do_launch(self, name, path, is_dir):
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
        self._favorites.discard(path)
        self._categories.pop(path, None)
        if path in self._dock:
            self._dock.remove(path)
        self._schedules.pop(path, None)
        self._app_colors.pop(path, None)
        self._app_icons.pop(path, None)
        self._save_stats()
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

    def open_contacts(self):
        if self._contacts_unread:
            self._contacts_unread = False
            if hasattr(self, "cv") and self.cv.winfo_width() > 10:
                self._layout_header()
        AppContacts.ContactsWindow(self)

    def open_profile(self):
        AppContacts.ProfileWindow(self)

    def refresh_profile_btn(self):
        try:
            key = AppContacts.avatar_key()
            if not key:
                self._profile_photo = None
            else:
                letter = (self.config.get("username") or "?")[:1].upper()
                self._profile_photo = AppContacts.avatar_photo(key, 28, letter, shape="rounded")
        except Exception:
            self._profile_photo = None
        # the profile pill redraws itself (photo or fallback glyph) the next
        # time the header lays out; if the canvas is already up, do it now.
        if hasattr(self, "cv") and self.cv.winfo_width() > 10:
            self._layout_header()

    def open_browser(self, url=None):
        if getattr(sys, "frozen", False):
            # running as a bundled .exe - launch the sibling AppBrowser.exe
            base_dir = os.path.dirname(os.path.abspath(sys.executable))
            browser_exe = os.path.join(base_dir, "AppBrowser.exe")
            if not os.path.exists(browser_exe):
                webbrowser.open(url or "https://www.google.com")
                return
            cmd = [browser_exe]
            if url:
                cmd.append(url)
            run_hidden(cmd, shell=False)
            return

        browser_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AppBrowser.py")
        if not os.path.exists(browser_py):
            webbrowser.open(url or "https://www.google.com")
            return
        cmd = [sys.executable, browser_py]
        if url:
            cmd.append(url)
        run_hidden(cmd, shell=False)

    # ---------- surprise me ----------
    def open_surprise(self):
        if self._spin_job:
            return
        pool = [it for it in self.items if os.path.exists(it[1])]
        if not pool:
            self._flash_status("No apps to surprise you with!")
            return
        pick = random.choice(pool)
        n = random.randint(8, 12)
        self._spin_count = 0
        self._spin_steps = n
        self._spin_names = [random.choice(pool)[0] for _ in range(n)]
        self._spin_pick = pick
        try:
            play_sound("Sweep")
        except Exception:
            pass
        self._tick_spin()

    def _tick_spin(self):
        if self._spin_job:
            self.after_cancel(self._spin_job)
            self._spin_job = None
        i = self._spin_count
        if i < self._spin_steps:
            self._flash_status(f"\U0001f3b0  {self._spin_names[i]} \u2026?")
            self._spin_count += 1
            self._spin_job = self.after(90 + i * 16, self._tick_spin)
        else:
            name, path, is_dir = self._spin_pick
            self._flash_status(f"\U0001f3b0  Surprise! Launching {name}")
            try:
                play_sound("Coin")
            except Exception:
                pass
            self._do_launch(name, path, is_dir)

    def open_music(self):
        music_bat = os.path.join(BASE_DIR, "Music", "Music.bat")
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

    # ---------- start with Windows ----------
    def _startup_command(self):
        """Command line that should open App Launcher, mirroring the same
        exe-if-present-else-python logic App Launcher.vbs uses."""
        if getattr(sys, "frozen", False):
            return f'"{os.path.abspath(sys.executable)}"'
        exe_path = os.path.join(BASE_DIR, "AppLauncher.exe")
        if os.path.exists(exe_path):
            return f'"{exe_path}"'
        py_dir = os.path.dirname(os.path.abspath(sys.executable))
        pythonw = os.path.join(py_dir, "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = "pythonw.exe"
        run_py = os.path.join(BASE_DIR, "run.py")
        return f'"{pythonw}" "{run_py}"'

    def _apply_autostart(self):
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as k:
                if self.config.get("autostart", False):
                    winreg.SetValueEx(k, "AppLauncher", 0, winreg.REG_SZ, self._startup_command())
                else:
                    try:
                        winreg.DeleteValue(k, "AppLauncher")
                    except FileNotFoundError:
                        pass
        except Exception:
            pass

    # ---------- Contacts unread badge ----------
    def _start_contacts_watch(self):
        self._contacts_watch_since = time.time()
        self._poll_contacts_unread()

    def _stop_contacts_watch(self):
        if self._contacts_poll_job:
            try:
                self.after_cancel(self._contacts_poll_job)
            except Exception:
                pass
        self._contacts_poll_job = None

    def _poll_contacts_unread(self):
        try:
            session = AppNet.load_session()
        except Exception:
            session = None
        if session:
            threading.Thread(target=self._check_contacts_unread, args=(session,), daemon=True).start()
        self._contacts_poll_job = self.after(60000, self._poll_contacts_unread)

    def _check_contacts_unread(self, session):
        # Best-effort: only flags messages that arrive while the app is
        # running (no server-side unread tracking to catch up on history).
        try:
            net = AppNet.Net(session["url"], session["token"])
            me_id = str(session.get("id") or "")
            since = self._contacts_watch_since
            friends = net.friends() or []
            found = False
            for f in friends:
                fid = f.get("id")
                if not fid:
                    continue
                try:
                    msgs = net.messages(fid, after=since) or []
                except Exception:
                    continue
                if any(str(m.get("from")) != me_id for m in msgs):
                    found = True
                    break
            if found:
                self._contacts_watch_since = time.time()
                self.after(0, self._set_contacts_unread, True)
        except Exception:
            pass

    def _set_contacts_unread(self, value):
        if self._contacts_unread == value:
            return
        self._contacts_unread = value
        if hasattr(self, "cv") and self.cv.winfo_width() > 10:
            self._layout_header()

    # ---------- update check ----------
    def _start_update_check(self):
        threading.Thread(target=self._fetch_update_version, daemon=True).start()

    def _fetch_update_version(self):
        try:
            req = urllib.request.Request(UPDATE_CHECK_URL, headers={"User-Agent": "AppLauncher"})
            with urllib.request.urlopen(req, timeout=8) as r:
                remote = r.read().decode("utf-8", "ignore").strip()
            if remote and remote != VERSION:
                self.after(0, self._set_update_available, remote)
        except Exception:
            pass

    def _set_update_available(self, remote_version):
        self._update_version = remote_version
        if hasattr(self, "cv") and self.cv.winfo_width() > 10:
            self._draw_footer()

    def _on_update_click(self):
        if self._updating:
            return
        version = self._update_version
        if not messagebox.askyesno(
            "Update available",
            f"Download and install v{version} now?\n\n"
            "App Launcher will restart automatically once it's done. "
            "Your apps, contacts, and settings are not touched.",
        ):
            return
        self._updating = True
        self._draw_footer()
        threading.Thread(target=self._download_update, args=(version,), daemon=True).start()

    def _download_update(self, version):
        # Fetch every file into memory first - only write to disk once the
        # whole set has downloaded cleanly, so a dropped connection midway
        # never leaves a half-updated, broken app on disk.
        try:
            fetched = {}
            for name in UPDATE_FILES:
                req = urllib.request.Request(UPDATE_RAW_BASE + name, headers={"User-Agent": "AppLauncher"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    fetched[name] = r.read()
                if not fetched[name]:
                    raise ValueError(f"{name} came back empty.")
            # Distributed copies get their source files marked read-only (see
            # run.py's _lock_down_distributed_copy) so friends can't casually
            # edit them - clear that before overwriting, then reapply it, so
            # the updater itself still works.
            locked = not os.path.isdir(os.path.join(BASE_DIR, ".git"))
            for name, data in fetched.items():
                dest = os.path.join(BASE_DIR, name)
                tmp = dest + ".update_tmp"
                with open(tmp, "wb") as f:
                    f.write(data)
                if os.path.exists(dest):
                    try:
                        os.chmod(dest, stat.S_IWRITE)
                    except Exception:
                        pass
                os.replace(tmp, dest)
                if locked:
                    try:
                        os.chmod(dest, stat.S_IREAD)
                    except Exception:
                        pass
        except Exception as e:
            self.after(0, self._update_failed, str(e))
            return
        self.after(0, self._update_applied, version)

    def _update_failed(self, message):
        self._updating = False
        self._draw_footer()
        messagebox.showerror(
            "Update failed",
            f"Couldn't finish updating: {message}\n\n"
            f"You can still update manually from {UPDATE_REPO_URL}",
        )

    def _update_applied(self, version):
        self._updating = False
        self._update_version = None
        if not messagebox.askyesno(
            "Update installed",
            f"v{version} is installed. Restart App Launcher now to start using it?",
        ):
            self._draw_footer()
            return
        self._restart_app()

    def _restart_app(self):
        # Relaunch through the same wrapper the user's shortcut points to
        # rather than re-exec'ing directly - the wrapper already knows how
        # to pick freshly-updated .py files over a now-stale built .exe.
        try:
            vbs = os.path.join(BASE_DIR, "App Launcher.vbs")
            bat = os.path.join(BASE_DIR, "App Launcher.bat")
            if os.path.exists(vbs):
                os.startfile(vbs)
            elif os.path.exists(bat):
                os.startfile(bat)
            else:
                subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "run.py")],
                                 cwd=BASE_DIR, creationflags=_NO_WINDOW_FLAGS)
        except Exception:
            pass
        self.after(300, lambda: os._exit(0))

    # ---------- cloud settings sync ----------
    def _cloud_net(self):
        try:
            session = AppNet.load_session()
        except Exception:
            session = None
        if not session:
            return None
        return AppNet.Net(session["url"], session["token"])

    def push_to_cloud(self, silent=False):
        net = self._cloud_net()
        if not net:
            if not silent:
                messagebox.showinfo("Cloud sync",
                                    "Sign in via Contacts first, then your settings can sync to your account.")
            return
        if self._syncing:
            return
        self._syncing = True
        blob = self._stats_blob()
        threading.Thread(target=self._do_push, args=(net, blob, silent), daemon=True).start()

    def _do_push(self, net, blob, silent):
        try:
            net.set_settings(blob)
            self.after(0, self._sync_done, True, silent, None, "push")
        except Exception as e:
            self.after(0, self._sync_done, False, silent, str(e), "push")

    def pull_from_cloud(self, silent=False):
        net = self._cloud_net()
        if not net:
            if not silent:
                messagebox.showinfo("Cloud sync",
                                    "Sign in via Contacts first, then your settings can sync to your account.")
            return
        if self._syncing:
            return
        self._syncing = True
        threading.Thread(target=self._do_pull, args=(net, silent), daemon=True).start()

    def _do_pull(self, net, silent):
        try:
            remote = net.get_settings()
            data = remote.get("data") if isinstance(remote, dict) else None
            if not data:
                self.after(0, self._sync_done, False, silent,
                          "No settings have been saved to your account yet - try Push first.", "pull")
                return
            self.after(0, self._apply_pulled, data, silent)
        except Exception as e:
            self.after(0, self._sync_done, False, silent, str(e), "pull")

    def _apply_pulled(self, data, silent):
        self._apply_stats_blob(data)
        self.refresh()
        if hasattr(self, "cv") and self.cv.winfo_width() > 10:
            self._draw_bg()
        self._sync_done(True, silent, None, "pull")

    def _sync_done(self, ok, silent, err, direction):
        self._syncing = False
        if silent:
            return
        if ok:
            msg = ("Pushed your settings to your account." if direction == "push"
                  else "Pulled settings from your account.")
            self._flash_status(msg)
        elif direction == "pull" and err and "saved to your account" in err:
            messagebox.showinfo("Cloud sync", err)
        else:
            messagebox.showerror("Cloud sync", f"Sync failed: {err}")

    def _start_cloud_sync(self):
        if self.config.get("cloud_sync"):
            self.pull_from_cloud(silent=True)

    # ---------- scheduled launch ----------
    def _start_schedule_watch(self):
        self._check_schedules()

    def _stop_schedule_watch(self):
        if self._schedule_job:
            try:
                self.after_cancel(self._schedule_job)
            except Exception:
                pass
        self._schedule_job = None

    def _check_schedules(self):
        if self._schedules:
            now = datetime.datetime.now()
            stamp = now.strftime("%Y-%m-%d %H:%M")
            hhmm = now.strftime("%H:%M")
            for path, sched_time in list(self._schedules.items()):
                if sched_time == hhmm and self._schedule_fired.get(path) != stamp:
                    self._schedule_fired[path] = stamp
                    if os.path.exists(path):
                        name = os.path.basename(path)
                        self._do_launch(name, path, os.path.isdir(path))
        self._schedule_job = self.after(20000, self._check_schedules)

    def _prompt_schedule(self, path):
        from tkinter import simpledialog
        current = self._schedules.get(path, "")
        val = simpledialog.askstring(
            "Schedule daily launch",
            "Launch this every day at (24-hour HH:MM, e.g. 17:30).\nLeave blank to remove the schedule.",
            initialvalue=current, parent=self,
        )
        if val is None:
            return
        val = val.strip()
        if not val:
            self._schedules.pop(path, None)
            self._save_stats()
            return
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", val):
            messagebox.showerror("Schedule daily launch", "Please use 24-hour HH:MM, e.g. 09:00 or 17:30.")
            return
        self._schedules[path] = val
        self._save_stats()
        self._flash_status(f"Scheduled for {val} daily")

    # ---------- quick-launch dock ----------
    def _toggle_dock(self, path):
        if path in self._dock:
            self._dock.remove(path)
        else:
            if len(self._dock) >= 8:
                messagebox.showinfo("Quick-launch dock", "The dock holds up to 8 apps - unpin one first.")
                return
            self._dock.append(path)
        self._save_stats()
        self._layout_chips()

    def _dock_name(self, path):
        for name, p, _ in self.items:
            if p == path:
                return name
        return os.path.basename(path)

    def _layout_dock(self, x, cy, h):
        """Draws pinned quick-launch icons after the filter chips, on the
        same row. Returns nothing - just advances the shared canvas state."""
        valid = [p for p in self._dock if os.path.exists(p)]
        if len(valid) != len(self._dock):
            self._dock = valid
            self._save_stats()
        if not valid:
            return
        self.cv.create_line(x, cy - h / 2, x, cy + h / 2, fill=self._card_border(), tags="chips")
        x += 12
        for path in valid:
            name = self._dock_name(path)
            tag = f"dock_{abs(hash(path))}"
            self.cv.create_image(x + h / 2, cy, image=self._pill_bg(h, h, h // 2, BUTTON_FILL_HEX, False),
                                 tags=("chips", tag))
            icon = self._icon_for_size(path, int(h * 0.6))
            if icon is not None:
                self.cv.create_image(x + h / 2, cy, image=icon, tags=("chips", tag))
            self.cv.tag_bind(tag, "<Button-1>", lambda e, p=path, n=name: self._do_launch(n, p, os.path.isdir(p)))
            self.cv.tag_bind(tag, "<Enter>", lambda e: self.cv.config(cursor="hand2"))
            self.cv.tag_bind(tag, "<Leave>", lambda e: self.cv.config(cursor=""))
            x += h + 6

    def _icon_for_size(self, path, size):
        custom = self._app_icons.get(path)
        key = (path, size, "dock", custom)
        if key not in self._icon_cache:
            photo = None
            if custom and os.path.exists(custom):
                try:
                    img = Image.open(custom).convert("RGBA")
                    img = img.resize((size, size), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                except Exception:
                    photo = None
            if photo is None:
                photo = get_file_icon(path, size)
            if photo is None:
                photo = fallback_icon(size)
            self._icon_cache[key] = photo
        self._photos.append(self._icon_cache[key])
        return self._icon_cache[key]

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
            self._stop_contacts_watch()
            self._stop_schedule_watch()
            if self.config.get("cloud_sync"):
                # Best-effort, synchronous so it actually gets a chance to
                # finish before the window (and its background threads) go
                # away - a slow/offline server just means this is skipped.
                try:
                    net = self._cloud_net()
                    if net:
                        net.set_settings(self._stats_blob())
                except Exception:
                    pass
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
        self._autostart_var = tk.BooleanVar(value=bool(self.app.config.get("autostart", False)))
        self._check(opt_frame, "Start with Windows", self._autostart_var, self._set_autostart).pack(anchor="w")

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
        self._clear_var = tk.BooleanVar(value=bool(self.app.config.get("clear_mode", False)))
        self._check(fun_frame, "Clear / glass mode (transparent background)", self._clear_var, self._set_clear).pack(anchor="w")
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

        self._title("Usage insights")
        ins_frame = tk.Frame(self._inner, bg=self.SET_BG)
        ins_frame.pack(fill="x", padx=18)
        tk.Label(ins_frame, text="See which apps you launch most.",
                 bg=self.SET_BG, fg=self.SET_MUTED, font=self.LBL_FONT).pack(anchor="w", pady=(0, 6))
        tk.Button(ins_frame, text="View usage insights", command=lambda: InsightsWindow(self.app),
                  bg=self.SET_CARD, fg=self.SET_TEXT, activebackground="#2a3150",
                  activeforeground="#ffffff", relief="flat", bd=0, padx=12, pady=6,
                  font=self.LBL_FONT, cursor="hand2").pack(anchor="w")

        self._title("Cloud sync")
        sync_frame = tk.Frame(self._inner, bg=self.SET_BG)
        sync_frame.pack(fill="x", padx=18)
        signed_in = bool(AppNet.load_session())
        if signed_in:
            tk.Label(sync_frame,
                    text="Syncs favorites, categories, the quick-launch dock, schedules\n"
                         "and your look/feel settings to your account (not app icons/shortcuts\n"
                         "themselves, since those are specific to each PC).",
                    bg=self.SET_BG, fg=self.SET_MUTED, font=self.LBL_FONT, justify="left").pack(anchor="w", pady=(0, 6))
            self._cloud_var = tk.BooleanVar(value=bool(self.app.config.get("cloud_sync")))
            self._check(sync_frame, "Auto-pull on launch / push on close", self._cloud_var,
                       self._set_cloud_sync).pack(anchor="w", pady=(0, 6))
            sync_btns = tk.Frame(sync_frame, bg=self.SET_BG)
            sync_btns.pack(anchor="w")
            tk.Button(sync_btns, text="Push to cloud", command=lambda: self.app.push_to_cloud(),
                      bg=self.SET_CARD, fg=self.SET_TEXT, activebackground="#2a3150",
                      activeforeground="#ffffff", relief="flat", bd=0, padx=12, pady=6,
                      font=self.LBL_FONT, cursor="hand2").pack(side="left", padx=(0, 8))
            tk.Button(sync_btns, text="Pull from cloud", command=lambda: self.app.pull_from_cloud(),
                      bg=self.SET_CARD, fg=self.SET_TEXT, activebackground="#2a3150",
                      activeforeground="#ffffff", relief="flat", bd=0, padx=12, pady=6,
                      font=self.LBL_FONT, cursor="hand2").pack(side="left")
        else:
            tk.Label(sync_frame, text="Sign in via Contacts to sync settings across your PCs.",
                    bg=self.SET_BG, fg=self.SET_MUTED, font=self.LBL_FONT, justify="left").pack(anchor="w", pady=(0, 6))
            tk.Button(sync_frame, text="Open Contacts", command=self.app.open_contacts,
                      bg=self.SET_CARD, fg=self.SET_TEXT, activebackground="#2a3150",
                      activeforeground="#ffffff", relief="flat", bd=0, padx=12, pady=6,
                      font=self.LBL_FONT, cursor="hand2").pack(anchor="w")

        self._title("Backup & restore")
        bak_frame = tk.Frame(self._inner, bg=self.SET_BG)
        bak_frame.pack(fill="x", padx=18)
        tk.Label(bak_frame, text="Save your settings to a file, or load them from one\n"
                                 "(same scope as cloud sync - not app shortcuts themselves).",
                bg=self.SET_BG, fg=self.SET_MUTED, font=self.LBL_FONT, justify="left").pack(anchor="w", pady=(0, 6))
        bak_btns = tk.Frame(bak_frame, bg=self.SET_BG)
        bak_btns.pack(anchor="w")
        tk.Button(bak_btns, text="Export settings\u2026", command=self.app.export_settings,
                  bg=self.SET_CARD, fg=self.SET_TEXT, activebackground="#2a3150",
                  activeforeground="#ffffff", relief="flat", bd=0, padx=12, pady=6,
                  font=self.LBL_FONT, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(bak_btns, text="Import settings\u2026", command=self.app.import_settings,
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

    def _set_clear(self):
        self.app.set_config("clear_mode", bool(self._clear_var.get()))

    def _set_part(self):
        self.app.set_config("particles", bool(self._part_var.get()))

    def _set_aurora(self):
        self.app.set_config("aurora", bool(self._aurora_var.get()))

    def _set_stats(self):
        self.app.set_config("stats", bool(self._stats_var.get()))

    def _set_tray(self):
        self.app.set_config("tray", bool(self._tray_var.get()))

    def _set_autostart(self):
        self.app.set_config("autostart", bool(self._autostart_var.get()))

    def _set_cloud_sync(self):
        self.app.set_config("cloud_sync", bool(self._cloud_var.get()))

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


class InsightsWindow(tk.Toplevel):
    BG = "#161a26"
    TEXT = "#e9ecf5"
    MUTED = "#8b93a7"

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Usage insights")
        self.configure(bg=self.BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        launches = {p: c for p, c in app._launches.items() if c > 0}
        total = sum(launches.values())
        names_by_path = {p: n for n, p, _ in app.items}
        top = sorted(launches.items(), key=lambda kv: -kv[1])[:10]

        tk.Label(self, text="Usage insights", bg=self.BG, fg=self.TEXT,
                 font=tkfont.Font(family="Segoe UI", size=13, weight="bold")
                 ).pack(anchor="w", padx=18, pady=(16, 4))
        summary = (f"{total} total launch{'es' if total != 1 else ''} across "
                  f"{len(launches)} app{'s' if len(launches) != 1 else ''}"
                  if launches else "No launches recorded yet - use the launcher a bit first!")
        tk.Label(self, text=summary, bg=self.BG, fg=self.MUTED, font=("Segoe UI", 9)
                 ).pack(anchor="w", padx=18, pady=(0, 12))

        row_h = 34
        height = max(60, len(top) * row_h + 20)
        canvas = tk.Canvas(self, bg=self.BG, highlightthickness=0, width=390, height=height)
        canvas.pack(padx=18, pady=(0, 18))

        if top:
            max_count = top[0][1]
            for i, (path, count) in enumerate(top):
                name = names_by_path.get(path, os.path.basename(path))
                if len(name) > 20:
                    name = name[:19] + "…"
                y = i * row_h + 8
                canvas.create_text(0, y, anchor="nw", text=name, fill=self.TEXT, font=("Segoe UI", 9))
                bar_w = max(4, int((count / max_count) * 170))
                accent = app._app_colors.get(path) or accent_for(names_by_path.get(path, name))
                canvas.create_rectangle(160, y + 1, 160 + bar_w, y + 15, fill=accent, outline="")
                canvas.create_text(160 + bar_w + 8, y + 8, anchor="w", text=str(count),
                                   fill=self.MUTED, font=("Segoe UI", 8))

        self.geometry(f"426x{height + 130}")


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
                run_hidden(builtin, shell=True)
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
            run_hidden(["shutdown", "/s", "/t", "10"])

    def _restart(self):
        if messagebox.askyesno("AI Assistant",
                               "Restart this PC in 10 seconds? (you can cancel later with 'shutdown /a')",
                               parent=self):
            run_hidden(["shutdown", "/r", "/t", "10"])

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


def _require_signin(root):
    done = {}

    def on_ready():
        done["ok"] = True

    login = AppContacts.LoginWindow(root, on_ready=on_ready)
    login.title("Sign in to use App Launcher")

    def on_close():
        done["ok"] = False
        try:
            login.destroy()
        except Exception:
            pass

    login.protocol("WM_DELETE_WINDOW", on_close)
    while "ok" not in done:
        root.update()
        time.sleep(0.03)
    return done["ok"] is True


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    try:
        if not AppNet.load_session():
            gate = tk.Tk()
            gate.withdraw()
            gate.title("App Launcher")
            ok = _require_signin(gate)
            gate.destroy()
            if not ok:
                return
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

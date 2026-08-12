import json
import os
import sys
import threading
import time

import webview

HOME = "https://www.google.com/"

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AppLauncher")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# ------- launcher palette (matches AppLauncher.py) -------
BUTTON_FILL = "#2c3450"
BUTTON_HOVER = "#38415f"
CARD_BORDER = "#3b4470"
SEARCH_FILL = "#1a1f30"
TEXT_HEX = "#e9ecf5"
MUTED_HEX = "#8b93a7"
ON_ACCENT = "#14182a"

THEMES = {
    "Nebula":  {"bg_top": "#181d32", "bg_bottom": "#0b0d14", "accent": "#6c8cff"},
    "Crimson": {"bg_top": "#2c101a", "bg_bottom": "#0c060a", "accent": "#ff5a66"},
    "Emerald": {"bg_top": "#0d2822", "bg_bottom": "#070f0d", "accent": "#3ee69e"},
    "Sunset":  {"bg_top": "#341a26", "bg_bottom": "#0f0a10", "accent": "#ff9e58"},
    "Cyber":   {"bg_top": "#161836", "bg_bottom": "#0a0818", "accent": "#00f4d0"},
    "Mono":    {"bg_top": "#212329", "bg_bottom": "#0d0e11", "accent": "#a5aebb"},
}


def load_theme():
    t = dict(THEMES["Nebula"])
    t["button"] = BUTTON_FILL
    t["search"] = SEARCH_FILL
    t["border"] = CARD_BORDER
    t["text"] = TEXT_HEX
    t["muted"] = MUTED_HEX
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if isinstance(cfg, dict):
            name = cfg.get("theme", "Nebula")
            if name in THEMES:
                t.update(THEMES[name])
            # launcher-wide custom colors feed the browser too
            if cfg.get("custom_accent"):
                t["accent"] = cfg["custom_accent"]
            for key in ("bg_top", "bg_bottom"):
                if cfg.get(key):
                    t[key] = cfg[key]
            if cfg.get("card_color"):
                t["button"] = cfg["card_color"]
            if cfg.get("card_border"):
                t["border"] = cfg["card_border"]
            if cfg.get("text_color"):
                t["text"] = cfg["text_color"]
            if cfg.get("muted_color"):
                t["muted"] = cfg["muted_color"]
            # browser-specific overrides win
            for key, target in (("browser_bg_top", "bg_top"),
                                ("browser_bg_bottom", "bg_bottom"),
                                ("browser_accent", "accent"),
                                ("browser_button", "button"),
                                ("browser_search", "search"),
                                ("browser_text", "text")):
                if cfg.get(key):
                    t[target] = cfg[key]
    except Exception:
        pass
    return t


def _rgba(hex_color, alpha):
    h = (hex_color or "#000000").lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return "rgba(%d,%d,%d,%s)" % (r, g, b, alpha)


def color_map(theme):
    bg_top = theme["bg_top"]
    bg_bottom = theme["bg_bottom"]
    accent = theme["accent"]
    button = theme.get("button", BUTTON_FILL)
    border = theme.get("border", CARD_BORDER)
    search = theme.get("search", SEARCH_FILL)
    return {
        "bgTop": bg_top,
        "bgBottom": bg_bottom,
        "bgTopA": _rgba(bg_top, 0.96),
        "bgBottomA": _rgba(bg_bottom, 0.96),
        "accent": accent,
        "accentGlow": _rgba(accent, 0.35),
        "button": button,
        "buttonA": _rgba(button, 0.96),
        "buttonHover": _rgba(button, 1.0),
        "border": border,
        "borderA": _rgba(border, 0.8),
        "search": search,
        "searchA": _rgba(search, 0.85),
        "text": theme.get("text", TEXT_HEX),
        "muted": theme.get("muted", MUTED_HEX),
        "onAccent": ON_ACCENT,
    }


def normalize_url(u):
    u = (u or "").strip()
    if not u:
        return HOME
    if u.startswith(("http://", "https://", "file://", "about:")):
        return u
    if " " in u and "." not in u:
        return "https://www.google.com/search?q=" + u.replace(" ", "+")
    return "https://" + u


ADBLOCK_SELECTORS = [
    "ins.adsbygoogle",
    "[data-ad-slot]", "[data-ad-client]", "[data-ad-format]", "[data-text-ad]",
    "[class*=\"advert\"]", "[id*=\"advert\"]",
    "[class*=\"ad-slot\"]", "[id*=\"ad-slot\"]",
    "[class*=\"ad_unit\"]", "[id*=\"ad_unit\"]",
    "[class*=\"ad-unit\"]", "[id*=\"ad-unit\"]",
    "[class*=\"ad_banner\"]", "[id*=\"ad_banner\"]",
    "[class*=\"ad-container\"]", "[id*=\"ad-container\"]",
    "[class*=\"adsense\"]", "[id*=\"adsense\"]",
    "[class*=\"doubleclick\"]", "[id*=\"doubleclick\"]",
    "[class*=\"sponsor\"]", "[id*=\"sponsor\"]",
    "[class*=\"promot\"]", "[id*=\"promot\"]",
    "[class*=\"adbox\"]", "[id*=\"adbox\"]",
    "[class*=\"adsbox\"]", "[id*=\"adsbox\"]",
    "[aria-label=\"Advertisement\"]", "[aria-label=\"Ads\"]",
    "iframe[src*=\"doubleclick\"]", "iframe[src*=\"googlesyndication\"]",
    "iframe[src*=\"adservice\"]", "iframe[src*=\"adsystem\"]",
    "iframe[src*=\"adnxs\"]", "iframe[src*=\"adserver\"]",
    "img[src*=\"adserver\"]", "img[src*=\"doubleclick\"]",
    ".gpt-ad", ".google-ads", ".banner-ad", ".ad-container", ".ad-slot",
    ".ytp-ad-module", ".ytp-ad-overlay-container", ".video-ads", ".ad-showing",
    ".ad", ".ads", ".adsbox", ".advert", ".advertisement", ".ad-banner", ".sponsored",
    "#ad", "#ads", "#adv", "#advert", "#sponsored",
]

ADBLOCK_CSS = (",".join(ADBLOCK_SELECTORS) +
    "{display:none!important;visibility:hidden!important;max-height:0!important;"
    "overflow:hidden!important}")


def adblock_enabled():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return bool(cfg.get("adblock", True))
    except Exception:
        return True


def make_adblock_js(enabled):
    return """
(function () {
  var id = 'pwv_adblock_css';
  var el = document.getElementById(id);
  if (!el) {
    el = document.createElement('style');
    el.id = id;
    el.textContent = %s;
    (document.head || document.documentElement).appendChild(el);
  }
  el.disabled = %s;
  window.__adblockOn = !el.disabled;
})();
""" % (json.dumps(ADBLOCK_CSS), "false" if enabled else "true")


def make_toolbar_js(theme, adblock_on=True):
    C = json.dumps(color_map(theme))
    return """
(function () {
  var id = 'pwv_tb';
  if (document.getElementById(id)) return;
  var C = %s;

  var root = document.documentElement;
  window.__pwvTheme = function (c) {
    root.style.setProperty('--pwv-bg-top', c.bgTop);
    root.style.setProperty('--pwv-bg-bottom', c.bgBottom);
    root.style.setProperty('--pwv-bg-top-a', c.bgTopA);
    root.style.setProperty('--pwv-bg-bottom-a', c.bgBottomA);
    root.style.setProperty('--pwv-accent', c.accent);
    root.style.setProperty('--pwv-accent-glow', c.accentGlow);
    root.style.setProperty('--pwv-button', c.button);
    root.style.setProperty('--pwv-button-a', c.buttonA);
    root.style.setProperty('--pwv-button-hover', c.buttonHover);
    root.style.setProperty('--pwv-search', c.search);
    root.style.setProperty('--pwv-search-a', c.searchA);
    root.style.setProperty('--pwv-border', c.border);
    root.style.setProperty('--pwv-border-a', c.borderA);
    root.style.setProperty('--pwv-text', c.text);
    root.style.setProperty('--pwv-muted', c.muted);
    root.style.setProperty('--pwv-on-accent', c.onAccent);
  };
  window.__pwvTheme(C);

  var css = document.createElement('style');
  css.textContent = [
    '#pwv_tb{position:fixed;top:0;left:0;right:0;height:52px;z-index:2147483647;display:flex;align-items:center;gap:6px;padding:0 10px;box-sizing:border-box;font-family:\\'Segoe UI\\',Arial,sans-serif;overflow:hidden;background:linear-gradient(180deg,var(--pwv-bg-top-a),var(--pwv-bg-bottom-a));border-bottom:1px solid var(--pwv-border-a)}',
    '#pwv_tb::before{content:"";position:absolute;top:0;left:0;right:0;height:3px;background:var(--pwv-accent);box-shadow:0 1px 6px var(--pwv-accent-glow)}',
    '.pwv-btn{width:36px;height:32px;border:1px solid var(--pwv-border-a);border-radius:8px;background:var(--pwv-button-a);color:var(--pwv-text);font-size:15px;cursor:pointer;flex:none;transition:background .12s ease,border-color .12s ease,color .12s ease,transform .08s ease}',
    '.pwv-btn:hover{background:var(--pwv-button-hover);border-color:var(--pwv-accent);color:#ffffff}',
    '.pwv-btn:active{transform:translateY(1px)}',
    '.pwv-go{padding:0 14px;width:auto;background:var(--pwv-accent);border-color:var(--pwv-accent);color:var(--pwv-on-accent);font-weight:600}',
    '.pwv-go:hover{background:var(--pwv-accent);border-color:var(--pwv-accent);filter:brightness(1.15);color:var(--pwv-on-accent)}',
    '#pwv_addr{flex:1;height:32px;border:1px solid var(--pwv-border-a);border-radius:8px;background:var(--pwv-search-a);color:var(--pwv-text);padding:0 12px;font-size:13px;outline:none;min-width:80px;transition:border-color .12s ease,box-shadow .12s ease}',
    '#pwv_addr:focus{border-color:var(--pwv-accent);box-shadow:0 0 0 3px var(--pwv-accent-glow)}',
    '#pwv_addr::placeholder{color:var(--pwv-muted)}',
    'html,body{background:transparent !important}',
    'html{opacity:0.96}',
    'body.pwv-tb{margin-top:52px !important}'
  ].join('\\n');
  (document.head || document.documentElement).appendChild(css);
  root.style.setProperty('--pwv-button-hover', C.buttonHover);
  root.style.setProperty('--pwv-on-accent', C.onAccent);

  function api(method) {
    try { window.pywebview.api[method](); } catch (e) {}
  }

  function btn(sym, fn, title, cls) {
    var b = document.createElement('button');
    b.textContent = sym; b.title = title;
    b.className = 'pwv-btn ' + (cls || '');
    b.onclick = fn;
    return b;
  }

  var tb = document.createElement('div');
  tb.id = id;

  tb.appendChild(btn('\\u2190', function () { api('back'); }, 'Back (Alt+Left)'));
  tb.appendChild(btn('\\u2192', function () { api('forward'); }, 'Forward (Alt+Right)'));
  tb.appendChild(btn('\\u27f3', function () { api('reload'); }, 'Reload (Ctrl+R)'));
  tb.appendChild(btn('\\u2302', function () { api('home'); }, 'Home'));

  var adOn = %s;
  var adBtn = btn(adOn ? '\\ud83d\\udee1' : '\\ud83d\\udeab', function () {
    var on = window.__toggleAdblock();
    try { window.pywebview.api.set_adblock(on); } catch (e) {}
  }, 'Ad blocker: ' + (adOn ? 'on' : 'off'));
  if (!adOn) { adBtn.style.opacity = 0.5; }
  window.__toggleAdblock = function () {
    var el = document.getElementById('pwv_adblock_css');
    if (!el) return;
    el.disabled = !el.disabled;
    var on = !el.disabled;
    adBtn.textContent = on ? '\\ud83d\\udee1' : '\\ud83d\\udeab';
    adBtn.title = 'Ad blocker: ' + (on ? 'on' : 'off');
    adBtn.style.opacity = on ? '1' : '0.5';
    return on;
  };
  tb.appendChild(adBtn);

  var inp = document.createElement('input');
  inp.id = 'pwv_addr';
  inp.type = 'text';
  inp.placeholder = 'Search or enter address';
  inp.value = location.href;
  inp.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      try { window.pywebview.api.navigate(inp.value); } catch (err) {}
    }
  });
  tb.appendChild(inp);
  tb.appendChild(btn('Go', function () {
    try { window.pywebview.api.navigate(inp.value); } catch (e) {}
  }, 'Go', 'pwv-go'));

  document.body.appendChild(tb);
  document.body.className += ' pwv-tb';
  setInterval(function () {
    if (document.activeElement !== inp && inp.value !== location.href) inp.value = location.href;
  }, 500);
})();
""" % (C, "true" if adblock_on else "false")


class Api:
    def __init__(self):
        self._win = None

    def set_window(self, window):
        self._win = window

    def navigate(self, url):
        self._win.load_url(normalize_url(url))

    def back(self):
        self._win.evaluate_js("history.back()")

    def forward(self):
        self._win.evaluate_js("history.forward()")

    def reload(self):
        self._win.evaluate_js("location.reload()")

    def home(self):
        self._win.load_url(HOME)

    def set_adblock(self, on):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not isinstance(cfg, dict):
                cfg = {}
            cfg["adblock"] = bool(on)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass


def main():
    theme = load_theme()
    url = HOME
    if len(sys.argv) > 1:
        url = normalize_url(sys.argv[1])

    api = Api()
    win = webview.create_window(
        "App Browser",
        url,
        width=1200,
        height=800,
        min_size=(640, 480),
        zoomable=True,
        transparent=True,
        background_color=theme["bg_bottom"],
        js_api=api,
    )
    api.set_window(win)

    def inject_all():
        try:
            win.evaluate_js(make_adblock_js(adblock_enabled()))
        except Exception:
            pass
        try:
            win.evaluate_js(make_toolbar_js(load_theme(), adblock_enabled()))
        except Exception:
            pass

    win.events.loaded += inject_all

    def watch_theme():
        last = None
        while True:
            time.sleep(2)
            try:
                colors = color_map(load_theme())
                sig = json.dumps(colors, sort_keys=True)
                if sig != last:
                    last = sig
                    win.evaluate_js("window.__pwvTheme && __pwvTheme(%s)" % json.dumps(colors))
            except Exception:
                pass

    threading.Thread(target=watch_theme, daemon=True).start()
    webview.start()


if __name__ == "__main__":
    main()

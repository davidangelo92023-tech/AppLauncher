import datetime
import getpass
import hashlib
import json
import os
import platform
import threading
import time
import uuid
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox
from tkinter import filedialog

from PIL import Image, ImageDraw, ImageFont, ImageTk

import AppNet

try:
    import winsound
except Exception:
    winsound = None

BG = "#07050f"
CARD = "#150f28"
CARD2 = "#221a3d"
TEXT = "#eaf2ff"
MUTED = "#8f87c2"
ACC = "#00f0ff"
GREEN = "#39ff8c"
RED = "#ff2255"

DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AppLauncher")
CONTACTS_FILE = os.path.join(DATA_DIR, "contacts.json")
CHATS_FILE = os.path.join(DATA_DIR, "chats.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
BANNED_FILE = os.path.join(DATA_DIR, "banned.json")


def my_username():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return (cfg.get("username") or "").strip()
    except Exception:
        return ""


def machine_fingerprint():
    guid = ""
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
        try:
            guid, _ = winreg.QueryValueEx(k, "MachineGuid")
        finally:
            winreg.CloseKey(k)
    except Exception:
        pass
    raw = "|".join([guid.strip().lower(), getpass.getuser().lower(), platform.node().lower()])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# The one account allowed to hold Owner powers (Kick/Ban/etc), regardless
# of what any server-reported or locally-cached "is_owner" flag says. This
# is a hard-coded safety net on top of the normal server-side check, so a
# stale cache or a mix-up while switching accounts can never hand admin
# powers to the wrong account.
OWNER_USERNAME = "ash"


def _is_owner_username(name):
    return (name or "").strip().casefold() == OWNER_USERNAME


def is_owner():
    cfg = _load_config()
    return bool(cfg.get("owner_secret")) and cfg.get("owner_machine") == machine_fingerprint()


def net_is_owner(net):
    """True only if net is actually signed in, the server says this account
    is the Owner, AND the signed-in username is the one true Owner account."""
    return bool(net and net.signed_in and net.me
                and net.me.get("is_owner") and _is_owner_username(net.me.get("username")))


def net_is_admin(net):
    """True for the Owner or for any account holding a moderation role
    (Trial Mod, Mod, Co-Owner) - server-verified. See net_rank for what
    each tier can actually do."""
    if net_is_owner(net):
        return True
    return bool(net and net.signed_in and net.me and net.me.get("is_admin"))


# Role ladder mirrored from server/main.py - keep in sync. "owner" is never
# stored anywhere; it's purely derived from the username check above.
_ROLE_RANK = {"member": 0, "trial_mod": 1, "mod": 2, "co_owner": 3, "owner": 4}


def net_role(net):
    """The signed-in account's role, server-verified where possible. Falls
    back to "member" for anyone signed out or without a recognized role."""
    if net_is_owner(net):
        return "owner"
    if net and net.signed_in and net.me:
        r = net.me.get("role")
        if r in _ROLE_RANK:
            return r
    return "member"


def net_rank(net):
    return _ROLE_RANK.get(net_role(net), 0)


def net_can_kick(net):
    """Trial Mod and up."""
    return net_rank(net) >= 1


# Muting is gated at the same tier as kicking - see server/main.py.
net_can_mute = net_can_kick


def net_can_ban(net):
    """Mod and up."""
    return net_rank(net) >= 2


def net_can_manage_bans(net):
    """Co-Owner and up - full ban-list visibility/management."""
    return net_rank(net) >= 3


def is_verified_owner():
    """Single source of truth for whether Owner-only UI (the footer's Owner
    tag, admin buttons, etc) should show, usable even without a live Net
    object - reads whatever session is saved locally. Prefers the network
    account's server-verified status; falls back to the local per-PC claim
    only when signed out."""
    try:
        session = AppNet.load_session()
    except Exception:
        session = None
    if session:
        return bool(session.get("is_owner")) and _is_owner_username(session.get("username"))
    return is_owner() and _is_owner_username(my_username())


def claim_owner():
    cfg = _load_config()
    if cfg.get("owner_secret"):
        if cfg.get("owner_machine") == machine_fingerprint():
            return False, "You are already the Owner on this PC."
        return False, "The Owner tag is already claimed on a different PC \u2014 you cannot claim it here."
    cfg["owner_secret"] = uuid.uuid4().hex
    cfg["owner_machine"] = machine_fingerprint()
    save_json(CONFIG_FILE, cfg)
    return True, "You are now the Owner! \u2b50"


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, type(default)) else default
    except Exception:
        return default


def save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def load_contacts():
    return load_json(CONTACTS_FILE, [])


def save_contacts(data):
    save_json(CONTACTS_FILE, data)


def load_chats():
    return load_json(CHATS_FILE, {})


def save_chats(data):
    save_json(CHATS_FILE, data)


def load_banned():
    return [n for n in load_json(BANNED_FILE, []) if isinstance(n, str) and n.strip()]


def save_banned(data):
    save_json(BANNED_FILE, [n.strip() for n in data if n.strip()])


def is_banned(name):
    n = (name or "").strip().lower()
    return any(b.lower() == n for b in load_banned())


def ban_name(name):
    n = (name or "").strip()
    if n and not is_banned(n):
        b = load_banned()
        b.append(n)
        save_banned(b)


def unban_name(name):
    n = (name or "").strip().lower()
    save_banned([b for b in load_banned() if b.lower() != n])


def _ring():
    if winsound:
        try:
            winsound.Beep(720, 200)
            winsound.Beep(940, 200)
        except Exception:
            pass


class ContactsWindow(tk.Toplevel):
    def __init__(self, app=None):
        super().__init__(app)
        self.title("Contacts")
        self.configure(bg=BG)
        self.geometry("620x480")
        self.minsize(520, 400)
        self.net = None
        self._placeholder = True
        self.search_var = tk.StringVar()
        self.search_var.set("Search contacts\u2026")
        self.search_var.trace_add("write", lambda *_: self.refresh_list())
        self._notices_job = None
        self._presence_job = None

        self._build()
        self._load_session()
        self.refresh_list()

    def _net_async(self, fn, on_done):
        """Run a blocking AppNet call on a background thread so it never
        freezes the UI, then deliver (result, error) back via on_done on
        the Tk main thread."""
        def worker():
            result, err = None, None
            try:
                result = fn()
            except AppNet.NetError as e:
                err = e
            except Exception as e:
                err = AppNet.NetError(str(e))

            def deliver():
                if not self.winfo_exists():
                    return
                on_done(result, err)
            try:
                self.after(0, deliver)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _load_session(self):
        self.contacts = load_contacts()  # show cached contacts immediately, no network wait
        try:
            session = AppNet.load_session()
            if session:
                self.net = AppNet.Net(session["url"], session["token"])
                self.net.me = {
                    "id": session["id"],
                    "username": session["username"],
                    "is_owner": session["is_owner"],
                    "is_admin": session.get("is_admin"),
                    "role": session.get("role"),
                }
            else:
                self.net = None
        except Exception:
            self.net = None
        self._update_net_ui()
        self._start_notices()
        if self.net_active:
            self._apply_net_friends()

    @property
    def net_active(self):
        return bool(self.net and self.net.signed_in)

    def _handle_stale_session(self, err):
        """Common handling for a token the server no longer accepts - either
        it genuinely expired (401) or the server force-revoked it because
        this copy of the app is too old to keep signing in (426, from the
        minimum-version check). Clears the local session and tells the user
        why. Returns True if it handled the error (caller should stop),
        False if err is something else (offline, etc.) that the caller
        should keep handling itself."""
        if err is None or err.status not in (401, 426):
            return False
        self.net = None
        AppNet.clear_session()
        self._update_net_ui()
        if err.status == 426:
            messagebox.showwarning("Update required", err.message, parent=self)
        else:
            messagebox.showwarning("Signed out", "Your session expired. Please sign in again.",
                                   parent=self)
        return True

    def _apply_net_friends(self):
        net = self.net
        if not net:
            return

        def done(friends, err):
            if self.net is not net:
                return  # signed out / switched accounts while this was in flight
            if self._handle_stale_session(err):
                self.contacts = load_contacts()
                self.refresh_list()
                return
            if err is not None:
                # server unreachable / timed out / hiccup - stay signed in, just show
                # cached contacts until the connection recovers
                messagebox.showwarning("Offline", err.message, parent=self)
                self.contacts = load_contacts()
            else:
                self.contacts = [{"name": f["username"], "id": f["id"], "banned": f.get("banned"),
                                  "is_admin": f.get("is_admin", False), "role": f.get("role", "member"),
                                  "online": f.get("online", False)}
                                 for f in friends]
                save_contacts(self.contacts)
            self.refresh_list()

        self._net_async(net.friends, done)

    def _update_net_ui(self):
        try:
            if self.net_active:
                self.sign_btn.config(text=f"Signed in as {self.net.me['username']}",
                                     bg="#0f3d2e", fg="#39ff8c")
            else:
                self.sign_btn.config(text="Sign in", bg=ACC, fg="#ffffff")
            self.add_btn.config(text="+ Add" if not self.net_active else "+ Add (by username)")
            for w, cmd in self._kick_buttons:
                w.pack_forget()
                if self._kick_ok():
                    w.pack(**cmd)
            for w, cmd in self._owner_buttons:
                w.pack_forget()
                if self._ban_ok():
                    w.pack(**cmd)
            if self.net_active and net_can_manage_bans(self.net):
                self.bans_btn.pack(side="right", padx=(0, 8))
            else:
                self.bans_btn.pack_forget()
            if self.net_active and net_can_manage_bans(self.net):
                self.special_btn.pack(side="right", padx=(0, 8))
            else:
                self.special_btn.pack_forget()
        except Exception:
            pass

    def _start_notices(self):
        if self._notices_job:
            self.after_cancel(self._notices_job)
            self._notices_job = None
        if self._presence_job:
            self.after_cancel(self._presence_job)
            self._presence_job = None
        if not self.net_active:
            return
        self._poll_notices()
        self._poll_presence()

    def _poll_presence(self):
        # Silent background refresh of each friend's online dot - unlike
        # _apply_net_friends (used for user-initiated loads), a transient
        # network hiccup here just skips this tick rather than popping up a
        # warning dialog every 10 seconds.
        if not self.net_active:
            return
        net = self.net

        def done(friends, err):
            if not self.net_active or self.net is not net:
                return
            if err is None and friends is not None:
                online_by_id = {f["id"]: f.get("online", False) for f in friends}
                changed = False
                for c in self.contacts:
                    o = online_by_id.get(c.get("id"), False)
                    if c.get("online") != o:
                        c["online"] = o
                        changed = True
                if changed:
                    self.refresh_list()
            if self.net_active:
                self._presence_job = self.after(10000, self._poll_presence)

        self._net_async(net.friends, done)

    def _poll_notices(self):
        if not self.net_active:
            return
        net = self.net

        def done(notices, err):
            if not self.net_active or self.net is not net:
                return
            if self._handle_stale_session(err):
                self.refresh_list()
                return  # signed out - stop polling until they sign in again
            if err is None and notices:
                for n in notices:
                    self.after(0, self._handle_notice, n.get("text", ""))
            self._notices_job = self.after(4000, self._poll_notices)

        self._net_async(net.notices, done)

    def _handle_notice(self, text):
        low = text.lower()
        if "banned" in low:
            self._sign_out(forced=True, notice=text)
        elif "kicked" in low:
            messagebox.showinfo("Kicked", text, parent=self)
            self._load_session()
            self.refresh_list()
        else:
            messagebox.showinfo("Notice", text, parent=self)
            self._load_session()
            self.refresh_list()

    def toggle_sign_in(self):
        if self.net_active:
            self._sign_out()
        else:
            LoginWindow(self, on_ready=self._after_login)

    def refresh_net(self):
        if self.net_active:
            self._apply_net_friends()
        else:
            self.refresh_list()

    def _after_login(self):
        self._load_session()
        self.refresh_list()

    def _sign_out(self, forced=False, notice=None):
        if not forced:
            if not messagebox.askyesno("Sign out", "Sign out of the network?",
                                       parent=self):
                return
        if self.net:
            self.net.logout()
        self.net = None
        AppNet.clear_session()
        self.contacts = load_contacts()
        self._update_net_ui()
        self.refresh_list()
        if notice:
            messagebox.showwarning("Banned", notice, parent=self)

    def _build(self):
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=14, pady=(12, 2))
        tk.Label(bar, text="Contacts", font=tkfont.Font(family="Segoe UI", size=16, weight="bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        self.bans_btn = tk.Button(bar, text="Bans\u2026", command=self.manage_bans, bg=CARD2, fg="#ffd166",
                                  activebackground=CARD2, activeforeground="#ffd166", relief="flat", bd=0,
                                  padx=10, pady=5, font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.special_btn = tk.Button(bar, text="\u2b50 Special Menu\u2026", command=self.open_special_menu,
                                     bg=CARD2, fg=ACC, activebackground=CARD2, activeforeground=ACC,
                                     relief="flat", bd=0, padx=10, pady=5,
                                     font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.sign_btn = tk.Button(bar, text="Sign in", command=self.toggle_sign_in, bg=ACC, fg="#ffffff",
                                  activebackground=ACC, activeforeground="#ffffff", relief="flat", bd=0,
                                  padx=10, pady=5, font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.sign_btn.pack(side="right", padx=(0, 6))
        self.refresh_btn = tk.Button(bar, text="\u21bb Refresh", command=self.refresh_net, bg=CARD2, fg=TEXT,
                                     activebackground="#2c1f52", activeforeground="#ffffff", relief="flat", bd=0,
                                     padx=10, pady=5, font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.refresh_btn.pack(side="right", padx=(0, 6))
        self.add_btn = tk.Button(bar, text="+ Add", command=self.add_contact, bg=ACC, fg="#ffffff",
                                 activebackground=ACC, activeforeground="#ffffff", relief="flat", bd=0,
                                 padx=12, pady=5, font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.add_btn.pack(side="right")

        tk.Label(self, text="Add people you know \u2014 text them, or call for a live chat",
                 font=("Segoe UI", 8), bg=BG, fg=MUTED, anchor="w").pack(fill="x", padx=14, pady=(4, 4))

        self.search = tk.Entry(self, textvariable=self.search_var, bg=CARD2, fg=MUTED, insertbackground=TEXT,
                               relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 10))
        self.search.pack(fill="x", padx=14, pady=(4, 8))
        self.search.bind("<FocusIn>", self._search_focus_in)
        self.search.bind("<FocusOut>", self._search_focus_out)
        self.search.bind("<Return>", lambda e: self.message())

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.lb = tk.Listbox(frame, bg=CARD, fg=TEXT, selectbackground=ACC, selectforeground="#ffffff",
                             relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 11),
                             activestyle="none", cursor="hand2")
        sb = tk.Scrollbar(frame, orient="vertical", command=self.lb.yview, bg=BG, troughcolor=BG,
                          activebackground=MUTED)
        self.lb.config(yscrollcommand=sb.set)
        self.lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.lb.bind("<Double-Button-1>", lambda e: self.message())
        self.lb.bind("<Return>", lambda e: self.message())
        self.lb.bind("<Delete>", lambda e: self.delete_contact())

        btns = tk.Frame(self, bg=BG)
        btns.pack(fill="x", padx=14, pady=(0, 10))

        def b(text, cmd, color=CARD2, fg=TEXT, bold=False):
            return tk.Button(btns, text=text, command=cmd, bg=color, fg=fg,
                             activebackground=color, activeforeground=fg, relief="flat", bd=0,
                             padx=12, pady=6, font=("Segoe UI", 9, "bold" if bold else "normal"),
                             cursor="hand2")

        b("Message", self.message, ACC, "#ffffff", True).pack(side="left", padx=(0, 6))
        b("Call", self.call).pack(side="left", padx=(0, 6))
        b("Edit", self.edit_contact).pack(side="left", padx=(0, 6))
        kick_btn = b("Kick", self.kick_contact, RED, "#ffffff")
        ban_btn = b("Ban", self.ban_contact, "#a3003f", "#ffffff")
        # Kick is Trial Mod and up; Ban is Mod and up (mirrors the server's
        # kick_guard vs ban_guard split). Role management (Trial Mod / Mod /
        # Co-Owner) lives in the Owner-only Special Menu instead of a quick
        # button here, since it's no longer a simple on/off toggle.
        self._kick_buttons = [
            (kick_btn, {"side": "right", "padx": (6, 0)}),
        ]
        self._owner_buttons = [
            (ban_btn, {"side": "right", "padx": (6, 0)}),
        ]
        self._update_net_ui()

    def _search_focus_in(self, event=None):
        if self._placeholder:
            self.search_var.set("")
            self._placeholder = False
            self.search.config(fg=TEXT)

    def _search_focus_out(self, event=None):
        if not self.search_var.get():
            self._placeholder = True
            self.search_var.set("Search contacts\u2026")
            self.search.config(fg=MUTED)

    def _filtered(self):
        q = "" if self._placeholder else self.search_var.get().strip().lower()
        if not q:
            return self.contacts
        return [c for c in self.contacts if q in c.get("name", "").lower()
                or q in c.get("note", "").lower()]

    def refresh_list(self):
        self.lb.delete(0, "end")
        for c in self._filtered():
            note = c.get("note", "")
            # The colored-circle emoji carries its own color regardless of
            # the Listbox's per-item text color, so it works as a plain
            # online/offline dot without needing per-character coloring
            # (which tk.Listbox doesn't support anyway).
            dot = ""
            if self.net_active and "online" in c:
                dot = "\U0001f7e2 " if c.get("online") else "\u26aa "
            self.lb.insert("end", dot + c["name"] + (f"  \u2014  {note}" if note else ""))

    def _selected(self):
        sel = self.lb.curselection()
        if not sel:
            return None
        filtered = self._filtered()
        if sel[0] >= len(filtered):
            return None
        return filtered[sel[0]]

    def message(self):
        c = self._selected()
        if c:
            ChatWindow(self, c, net=self.net)

    def call(self):
        c = self._selected()
        if c:
            ChatWindow(self, c, start_call=True, net=self.net)

    def add_contact(self):
        if self.net_active:
            self._net_add_dialog()
        else:
            self._dialog("Add contact")

    def _net_add_dialog(self):
        win = tk.Toplevel(self)
        win.title("Add by username")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        form = tk.Frame(win, bg=BG)
        form.pack(padx=16, pady=(14, 6))
        tk.Label(form, text="Their username (as they signed in with)", font=("Segoe UI", 9),
                 bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        e_user = tk.Entry(form, bg=CARD2, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                          highlightthickness=0, font=("Segoe UI", 10), width=34)
        e_user.pack(fill="x", pady=(2, 4))

        hint = tk.Label(form, text="", font=("Segoe UI", 9), bg=BG, fg=MUTED, anchor="w")
        hint.pack(fill="x", pady=(0, 8))

        def on_key(_=None):
            q = e_user.get().strip()
            if len(q) < 1:
                hint.config(text="")
                return
            try:
                results = self.net.search_users(q)
                hint.config(text="\u2713 " + ", ".join(r["username"] for r in results[:8]) if results
                            else "No users found")
            except AppNet.NetError as e:
                hint.config(text=e.message)

        e_user.bind("<KeyRelease>", on_key)

        def save():
            username = e_user.get().strip()
            if not username:
                return
            try:
                self.net.add_friend(username)
            except AppNet.NetError as e:
                messagebox.showwarning("Couldn't add", e.message, parent=win)
                return
            win.destroy()
            self._load_session()
            self.refresh_list()

        row = tk.Frame(win, bg=BG)
        row.pack(pady=(2, 14))
        tk.Button(row, text="Cancel", command=win.destroy, bg=CARD2, fg=TEXT,
                  activebackground="#2c1f52", activeforeground="#ffffff", relief="flat", bd=0,
                  padx=14, pady=6, font=("Segoe UI", 9), cursor="hand2").pack(side="left", padx=4)
        tk.Button(row, text="Add", command=save, bg=ACC, fg="#ffffff", activebackground=ACC,
                  activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left", padx=4)
        e_user.focus_set()

    def edit_contact(self):
        if self.net_active:
            messagebox.showinfo("Contacts", "Online contacts can't be edited \u2014 they sign in "
                                "with their own username.", parent=self)
            return
        c = self._selected()
        if c:
            self._dialog("Edit contact", c)
        else:
            messagebox.showinfo("Contacts", "Pick a contact to edit first.", parent=self)

    def _dialog(self, title, contact=None):
        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        form = tk.Frame(win, bg=BG)
        form.pack(padx=16, pady=(14, 6))

        def field(label):
            tk.Label(form, text=label, font=("Segoe UI", 9), bg=BG, fg=MUTED, anchor="w").pack(fill="x")
            e = tk.Entry(form, bg=CARD2, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                         highlightthickness=0, font=("Segoe UI", 10), width=34)
            e.pack(fill="x", pady=(2, 8))
            return e

        e_name = field("Name")
        e_note = field("Note (optional)")
        if contact:
            e_name.insert(0, contact.get("name", ""))
            e_note.insert(0, contact.get("note", ""))

        def save():
            name = e_name.get().strip()
            if not name:
                messagebox.showwarning("Missing name", "A name is required.", parent=win)
                return
            if is_banned(name):
                messagebox.showwarning("Banned", f"{name} is banned and cannot be added.",
                                       parent=win)
                return
            if contact is None:
                self.contacts.append({"name": name, "note": e_note.get().strip()})
            else:
                old = contact["name"]
                contact["name"] = name
                contact["note"] = e_note.get().strip()
                chats = load_chats()
                if old in chats and old != name:
                    chats[name] = chats.pop(old)
                    save_chats(chats)
            save_contacts(self.contacts)
            win.destroy()
            self.refresh_list()

        row = tk.Frame(win, bg=BG)
        row.pack(pady=(2, 14))
        tk.Button(row, text="Cancel", command=win.destroy, bg=CARD2, fg=TEXT,
                  activebackground="#2c1f52", activeforeground="#ffffff", relief="flat", bd=0,
                  padx=14, pady=6, font=("Segoe UI", 9), cursor="hand2").pack(side="left", padx=4)
        tk.Button(row, text="Save", command=save, bg=ACC, fg="#ffffff", activebackground=ACC,
                  activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left", padx=4)
        e_name.focus_set()

    def _owner_ok(self):
        """Strictly Owner-only actions, like deleting a contact outright."""
        if self.net_active:
            return net_is_owner(self.net)
        return is_owner() and _is_owner_username(my_username())

    def _kick_ok(self):
        """Kick is available to Trial Mod and up."""
        if self.net_active:
            return net_can_kick(self.net)
        return is_owner() and _is_owner_username(my_username())

    def _ban_ok(self):
        """Ban is available to Mod and up."""
        if self.net_active:
            return net_can_ban(self.net)
        return is_owner() and _is_owner_username(my_username())

    def _banlist_ok(self):
        """Full ban-list visibility is Co-Owner and up."""
        if self.net_active:
            return net_can_manage_bans(self.net)
        return is_owner() and _is_owner_username(my_username())

    def delete_contact(self):
        c = self._selected()
        if not c:
            return
        if not self._owner_ok():
            return
        if not messagebox.askyesno("Delete contact", f"Remove {c['name']}?", parent=self):
            return
        self._remove_contact(c)

    def kick_contact(self):
        c = self._selected()
        if not c:
            return
        if not self._kick_ok():
            return
        if not messagebox.askyesno("Kick", f"Kick {c['name']} from your network?\n"
                                           f"They will be removed.", parent=self):
            return
        if self.net_active:
            try:
                self.net.kick(c["id"])
            except AppNet.NetError as e:
                messagebox.showwarning("Couldn't kick", e.message, parent=self)
                return
        else:
            self._remove_contact(c)
        self._load_session()
        self.refresh_list()

    def ban_contact(self):
        c = self._selected()
        if not c:
            return
        if not self._ban_ok():
            return
        if not messagebox.askyesno("Ban", f"Ban {c['name']}?\n\n"
                                          f"They will be removed and blocked from being added again.",
                                   parent=self):
            return
        name = c["name"]
        if self.net_active:
            try:
                self.net.ban(c["id"])
            except AppNet.NetError as e:
                messagebox.showwarning("Couldn't ban", e.message, parent=self)
                return
        else:
            self._remove_contact(c)
            ban_name(name)
        self._load_session()
        self.refresh_list()
        messagebox.showinfo("Banned", f"{name} has been banned.", parent=self)

    def _remove_contact(self, c):
        name = c.get("name")
        self.contacts = [x for x in self.contacts if x is not c]
        save_contacts(self.contacts)
        if name:
            chats = load_chats()
            chats.pop(name, None)
            save_chats(chats)
        self.refresh_list()

    def manage_bans(self):
        if not self._banlist_ok():
            return
        win = tk.Toplevel(self)
        win.title("Banned people")
        win.configure(bg=BG)
        win.geometry("360x360")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="Banned people", font=tkfont.Font(family="Segoe UI", size=14, weight="bold"),
                 bg=BG, fg=TEXT).pack(pady=(14, 2))
        tk.Label(win, text="They can\u2019t be added to your network while banned.",
                 font=("Segoe UI", 8), bg=BG, fg=MUTED).pack(pady=(0, 8))

        box = tk.Frame(win, bg=BG)
        box.pack(fill="both", expand=True, padx=14)
        lb = tk.Listbox(box, bg=CARD, fg=TEXT, selectbackground=ACC, selectforeground="#ffffff",
                        relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 11),
                        activestyle="none", cursor="hand2")
        sb = tk.Scrollbar(box, orient="vertical", command=lb.yview, bg=BG, troughcolor=BG,
                          activebackground=MUTED)
        lb.config(yscrollcommand=sb.set)
        lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def refresh():
            lb.delete(0, "end")
            if self.net_active:
                try:
                    for b in self.net.bans():
                        lb.insert("end", b["username"])
                except AppNet.NetError as e:
                    messagebox.showwarning("Offline", e.message, parent=win)
                    lb.insert("end", "(can't load bans)")
            else:
                for n in load_banned():
                    lb.insert("end", n)

        def unban():
            sel = lb.curselection()
            if not sel:
                return
            name = lb.get(sel[0])
            try:
                if self.net_active:
                    target = next((b for b in self.net.bans() if b["username"] == name), None)
                    if target:
                        self.net.unban(target["id"])
                else:
                    unban_name(name)
            except AppNet.NetError as e:
                messagebox.showwarning("Couldn't unban", e.message, parent=win)
                return
            refresh()

        btns = tk.Frame(win, bg=BG)
        btns.pack(fill="x", padx=14, pady=(0, 14))
        tk.Button(btns, text="Close", command=win.destroy, bg=CARD2, fg=TEXT,
                  activebackground="#2c1f52", activeforeground="#ffffff", relief="flat", bd=0,
                  padx=14, pady=6, font=("Segoe UI", 9), cursor="hand2").pack(side="right")
        tk.Button(btns, text="Unban", command=unban, bg=GREEN, fg="#0d1220",
                  activebackground=GREEN, activeforeground="#0d1220", relief="flat", bd=0,
                  padx=14, pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right", padx=(0, 8))
        refresh()

    def open_special_menu(self):
        # Double-guarded on top of the button only showing for the Owner or
        # a Co-Owner in the first place - opening this window always
        # re-checks, since the server is what actually enforces every action
        # taken inside it.
        if not (self.net_active and net_can_manage_bans(self.net)):
            messagebox.showwarning("Owner or Co-Owner only",
                                   "You need to be signed in as the Owner or a Co-Owner to use this.",
                                   parent=self)
            return
        SpecialMenuWindow(self, self.net, on_change=self._apply_net_friends)


class SpecialMenuWindow(tk.Toplevel):
    """Owner- and Co-Owner-accessible management panel: a stats-at-a-glance
    line up top (total/banned/muted counts) - search for any account
    (including ones you're not already friends with, and banned ones) - or
    click "All Accounts" to list literally everyone at once. The list
    supports ctrl/shift-click multi-select, so Kick, Ban/Unban (permanent
    or timed), Mute/Unmute, Warn, Force sign-out, and Set role can all be
    applied to several accounts in one go (each reports its own success or
    failure rather than stopping at the first problem). Selecting a single
    account additionally shows its join date and friend count, and a
    private moderation note (visible only in this window, never to the
    account itself) that can be read and saved right here. Also available:
    Warn (notice + log entry, no restriction), Force sign-out (ends every
    active session), Broadcast (a notice to every account) - a Co-Owner has
    every capability here that the Owner does. The one exception is View
    Log (the moderation history, which now also records every new account
    signing up), which stays Owner-only and simply doesn't appear for
    anyone else. The Owner rank itself is never touched by any of this -
    it isn't a grantable role, it's derived purely from OWNER_USERNAME, and
    the Owner account can't be targeted by these actions at all (nor can it
    be selected alongside others in a bulk action). Everything here is a
    thin UI over server endpoints that independently re-check the caller's
    actual rank - this window is convenience, not the security boundary."""

    ROLE_LABELS = {
        "member": "Member",
        "trial_mod": "Trial Mod",
        "mod": "Mod",
        "co_owner": "Co-Owner",
    }
    ROLE_PERKS = {
        "member": "No special powers.",
        "trial_mod": "Can Kick.",
        "mod": "Can Kick and Ban.",
        "co_owner": "Can Kick, Ban, and manage the ban list.",
    }

    def __init__(self, app, net, on_change=None):
        super().__init__(app)
        self.net = net
        self.on_change = on_change
        self.title("Special Menu")
        self.configure(bg=BG)
        self.geometry("480x880")
        self.minsize(440, 680)
        self.transient(app)
        self.results = []
        self._selected_rows = []
        self._build()
        self._load_stats()

    def _build(self):
        header_row = tk.Frame(self, bg=BG)
        header_row.pack(fill="x", padx=14, pady=(14, 0))
        tk.Label(header_row, text="\u2b50 Special Menu", font=tkfont.Font(family="Segoe UI", size=15, weight="bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        # View Log stays Owner-only, unlike the rest of this menu - so it's
        # the one control here that doesn't even show for a Co-Owner.
        if net_is_owner(self.net):
            tk.Button(header_row, text="View Log", command=self.open_mod_log, bg=CARD2, fg=TEXT,
                      activebackground="#2c1f52", activeforeground="#ffffff", relief="flat", bd=0,
                      padx=10, pady=4, font=("Segoe UI", 8, "bold"), cursor="hand2").pack(side="right")
        tk.Button(header_row, text="\U0001f4e2 Broadcast…", command=self.open_broadcast, bg=CARD2, fg=ACC,
                  activebackground="#2c1f52", activeforeground=ACC, relief="flat", bd=0,
                  padx=10, pady=4, font=("Segoe UI", 8, "bold"), cursor="hand2").pack(side="right", padx=(0, 6))
        tk.Label(self, text="Find any account (or click All Accounts), then Kick, Ban, Mute, Warn, "
                            "Force sign-out, or set their role. Ctrl/Shift-click to act on several at once.",
                 font=("Segoe UI", 8), bg=BG, fg=MUTED, anchor="w", wraplength=440,
                 justify="left").pack(fill="x", padx=14, pady=(2, 2))
        self.stats_lbl = tk.Label(self, text="Loading stats…", font=("Segoe UI", 8, "bold"),
                                  bg=BG, fg=ACC, anchor="w")
        self.stats_lbl.pack(fill="x", padx=14, pady=(0, 8))

        search_row = tk.Frame(self, bg=BG)
        search_row.pack(fill="x", padx=14)
        self.q_var = tk.StringVar()
        entry = tk.Entry(search_row, textvariable=self.q_var, bg=CARD2, fg=TEXT, insertbackground=TEXT,
                         relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 10))
        entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
        entry.bind("<Return>", lambda e: self.search())
        entry.focus_set()
        tk.Button(search_row, text="Find", command=self.search, bg=ACC, fg="#ffffff",
                  activebackground=ACC, activeforeground="#ffffff", relief="flat", bd=0,
                  padx=12, pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right")
        tk.Button(search_row, text="\U0001f4cb All Accounts", command=self.list_all, bg=CARD2, fg=TEXT,
                  activebackground="#2c1f52", activeforeground="#ffffff", relief="flat", bd=0,
                  padx=10, pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right", padx=(0, 6))

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="both", expand=True, padx=14, pady=(10, 6))
        self.lb = tk.Listbox(frame, bg=CARD, fg=TEXT, selectbackground=ACC, selectforeground="#ffffff",
                             relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 11),
                             activestyle="none", cursor="hand2", selectmode="extended")
        sb = tk.Scrollbar(frame, orient="vertical", command=self.lb.yview, bg=BG, troughcolor=BG,
                          activebackground=MUTED)
        self.lb.config(yscrollcommand=sb.set)
        self.lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.lb.bind("<<ListboxSelect>>", self._on_select)

        self.detail_lbl = tk.Label(self, text="Search for someone to see actions.",
                                   font=("Segoe UI", 9), bg=BG, fg=MUTED, anchor="w", justify="left",
                                   wraplength=440)
        self.detail_lbl.pack(fill="x", padx=14, pady=(0, 4))

        note_row = tk.Frame(self, bg=BG)
        note_row.pack(fill="x", padx=14, pady=(0, 6))
        tk.Label(note_row, text="Private note (only Owner/Co-Owner see this):",
                 font=("Segoe UI", 8), bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        self.note_txt = tk.Text(note_row, bg=CARD2, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                                highlightthickness=0, font=("Segoe UI", 9), height=2, wrap="word",
                                state="disabled")
        self.note_txt.pack(fill="x", pady=(2, 4))
        self.note_save_btn = tk.Button(note_row, text="Save note", command=self.do_save_note, bg=CARD2, fg=TEXT,
                                       activebackground="#2c1f52", activeforeground="#ffffff", relief="flat",
                                       bd=0, padx=10, pady=4, font=("Segoe UI", 8, "bold"), cursor="hand2",
                                       state="disabled")
        self.note_save_btn.pack(anchor="e")

        actions = tk.Frame(self, bg=BG)
        actions.pack(fill="x", padx=14, pady=(0, 6))

        def b(parent, text, cmd, color=CARD2, fg=TEXT):
            return tk.Button(parent, text=text, command=cmd, bg=color, fg=fg,
                             activebackground=color, activeforeground=fg, relief="flat", bd=0,
                             padx=10, pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2")

        self.kick_btn = b(actions, "Kick", self.do_kick, RED, "#ffffff")
        self.kick_btn.pack(side="left", padx=(0, 6))
        self.ban_btn = b(actions, "Ban", self.do_ban, "#a3003f", "#ffffff")
        self.ban_btn.pack(side="left", padx=(0, 6))
        self.unban_btn = b(actions, "Unban", self.do_unban, GREEN, "#0d1220")
        self.unban_btn.pack(side="left")

        ban_row = tk.Frame(self, bg=BG)
        ban_row.pack(fill="x", padx=14, pady=(4, 0))
        tk.Label(ban_row, text="Ban length:", font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(side="left", padx=(0, 8))
        self.ban_min_var = tk.StringVar(value="")
        ban_entry = tk.Entry(ban_row, textvariable=self.ban_min_var, width=6, bg=CARD2, fg=TEXT,
                             insertbackground=TEXT, relief="flat", bd=0, highlightthickness=0,
                             font=("Segoe UI", 9), justify="center")
        ban_entry.pack(side="left", ipady=4)
        tk.Label(ban_row, text="min (blank = permanent)", font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(
            side="left", padx=(4, 0))

        mute_row = tk.Frame(self, bg=BG)
        mute_row.pack(fill="x", padx=14, pady=(6, 0))
        self.mute_btn = b(mute_row, "Mute", self.do_mute, "#8a5a00", "#ffffff")
        self.mute_btn.pack(side="left", padx=(0, 6))
        self.unmute_btn = b(mute_row, "Unmute", self.do_unmute, GREEN, "#0d1220")
        self.unmute_btn.pack(side="left", padx=(0, 10))
        tk.Label(mute_row, text="for", font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(side="left", padx=(0, 4))
        self.mute_min_var = tk.StringVar(value="30")
        mute_entry = tk.Entry(mute_row, textvariable=self.mute_min_var, width=5, bg=CARD2, fg=TEXT,
                              insertbackground=TEXT, relief="flat", bd=0, highlightthickness=0,
                              font=("Segoe UI", 9), justify="center")
        mute_entry.pack(side="left", ipady=4)
        tk.Label(mute_row, text="min", font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(side="left", padx=(4, 0))

        extra_row = tk.Frame(self, bg=BG)
        extra_row.pack(fill="x", padx=14, pady=(6, 0))
        self.warn_btn = b(extra_row, "Warn", self.do_warn, "#ffd166", "#0d1220")
        self.warn_btn.pack(side="left", padx=(0, 6))
        self.force_btn = b(extra_row, "Force sign-out", self.do_force_signout, "#5a3d99", "#ffffff")
        self.force_btn.pack(side="left")

        reason_row = tk.Frame(self, bg=BG)
        reason_row.pack(fill="x", padx=14, pady=(6, 0))
        tk.Label(reason_row, text="Reason (optional):", font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(
            side="left", padx=(0, 8))
        self.reason_var = tk.StringVar()
        reason_entry = tk.Entry(reason_row, textvariable=self.reason_var, bg=CARD2, fg=TEXT,
                                insertbackground=TEXT, relief="flat", bd=0, highlightthickness=0,
                                font=("Segoe UI", 9))
        reason_entry.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Label(self, text="Included in the notice they get, and saved to the log below.",
                 font=("Segoe UI", 7), bg=BG, fg=MUTED, anchor="w").pack(fill="x", padx=14, pady=(2, 0))

        # Role assignment is Owner- and Co-Owner-level, same as everything
        # else in this menu (see set_role in server/main.py) - the Owner
        # rank itself is never affected either way, since it's derived
        # purely from OWNER_USERNAME and isn't a role that can be granted.
        role_row = tk.Frame(self, bg=BG)
        role_row.pack(fill="x", padx=14, pady=(6, 14))
        tk.Label(role_row, text="Set role:", font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(side="left", padx=(0, 8))
        self.role_var = tk.StringVar(value="member")
        opt = tk.OptionMenu(role_row, self.role_var, "member", "trial_mod", "mod", "co_owner")
        opt.config(bg=CARD2, fg=TEXT, activebackground=CARD2, activeforeground=TEXT, relief="flat", bd=0,
                  font=("Segoe UI", 9), highlightthickness=0, cursor="hand2")
        opt["menu"].config(bg=CARD2, fg=TEXT)
        opt.pack(side="left", padx=(0, 8))
        b(role_row, "Apply", self.do_set_role, ACC, "#ffffff").pack(side="left")

        self._set_actions_enabled(False)

    def _set_actions_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for w in (self.kick_btn, self.ban_btn, self.unban_btn, self.mute_btn, self.unmute_btn,
                  self.warn_btn, self.force_btn):
            w.config(state=state)

    def _set_note_enabled(self, enabled):
        if enabled:
            self.note_txt.config(state="normal")
            self.note_save_btn.config(state="normal")
        else:
            self.note_txt.config(state="normal")
            self.note_txt.delete("1.0", "end")
            self.note_txt.config(state="disabled")
            self.note_save_btn.config(state="disabled")

    def _set_note_text(self, text):
        self.note_txt.config(state="normal")
        self.note_txt.delete("1.0", "end")
        self.note_txt.insert("1.0", text or "")

    def _load_stats(self):
        try:
            stats = self.net.owner_stats()
        except AppNet.NetError:
            self.stats_lbl.config(text="")
            return
        self.stats_lbl.config(
            text=f"{stats.get('total', 0)} account(s) total  ·  {stats.get('banned', 0)} banned  ·  "
                 f"{stats.get('muted', 0)} muted right now")

    def list_all(self):
        # Same as searching, just with the box cleared - the server treats
        # a blank query as "show every account" (see owner_search).
        self.q_var.set("")
        self.search()

    def search(self):
        q = (self.q_var.get() or "").strip()
        try:
            self.results = self.net.search_any(q)
        except AppNet.NetError as e:
            messagebox.showwarning("Search failed", e.message, parent=self)
            return
        self.lb.delete(0, "end")
        self._selected_rows = []
        self._set_actions_enabled(False)
        self._set_note_enabled(False)
        self.detail_lbl.config(text=f"{len(self.results)} account(s)." if not q
                               else f"{len(self.results)} result(s).")
        for r in self.results:
            tag = " [OWNER]" if r.get("is_owner") else (
                f" [{self.ROLE_LABELS.get(r.get('role', 'member'), r.get('role'))}]"
                if r.get("role", "member") != "member" else "")
            banned = " (banned)" if r.get("banned") else ""
            muted = " (muted)" if r.get("muted") else ""
            self.lb.insert("end", f"{r['username']}{tag}{banned}{muted}")

    def _format_joined(self, ts):
        try:
            return datetime.datetime.fromtimestamp(ts).strftime("%b %d, %Y")
        except Exception:
            return "unknown"

    def _on_select(self, event=None):
        sel = self.lb.curselection()
        rows = [self.results[i] for i in sel if i < len(self.results)]
        if any(r.get("is_owner") for r in rows):
            # The Owner is never a valid target for anything here - block
            # the whole selection rather than silently skipping just them.
            self._selected_rows = []
            self.detail_lbl.config(text="The Owner can't be acted on \u2014 deselect them to continue.")
            self._set_actions_enabled(False)
            self._set_note_enabled(False)
            return
        self._selected_rows = rows
        if not rows:
            self.detail_lbl.config(text="Search for someone to see actions.")
            self._set_actions_enabled(False)
            self._set_note_enabled(False)
            return
        if len(rows) == 1:
            r = rows[0]
            role = r.get("role", "member")
            perk = self.ROLE_PERKS.get(role, "")
            status = "banned" if r.get("banned") else "not banned"
            if r.get("muted"):
                status += ", muted"
            joined = self._format_joined(r.get("created"))
            friends = r.get("friend_count", 0)
            self.detail_lbl.config(
                text=f"{r['username']} \u2014 role: {self.ROLE_LABELS.get(role, role)} ({perk}) \u2014 {status}\n"
                     f"Joined {joined}  \u00b7  {friends} friend(s)")
            self.role_var.set(role)
            self._set_note_enabled(True)
            self._set_note_text(r.get("note", ""))
        else:
            self.detail_lbl.config(text=f"{len(rows)} accounts selected.")
            self._set_note_enabled(False)
        self._set_actions_enabled(True)

    def _selected_rows_or_warn(self):
        if not self._selected_rows:
            messagebox.showinfo("Pick someone", "Select one or more results from the list first.", parent=self)
            return None
        return self._selected_rows

    def _confirm_bulk(self, title, verb, rows):
        """Builds a consistent yes/no confirmation whether one account or
        several are selected - verb is a plain action phrase like "Kick" or
        "Mute for 30 minute(s)"."""
        if len(rows) == 1:
            text = f"{verb} {rows[0]['username']}?"
        else:
            names = ", ".join(r["username"] for r in rows)
            text = f"{verb} {len(rows)} accounts?\n\n{names}"
        return messagebox.askyesno(title, text, parent=self)

    def _apply_bulk(self, rows, fn, verb):
        """Runs fn(r) for every selected row, collecting per-account errors
        into one combined warning instead of stopping at the first
        failure - so one bad row (e.g. someone who got unbanned by someone
        else a second ago) doesn't block the rest of the batch."""
        errors = []
        for r in rows:
            try:
                fn(r)
            except AppNet.NetError as e:
                errors.append(f"{r['username']}: {e.message}")
        if errors:
            messagebox.showwarning(f"Some {verb} failed", "\n".join(errors), parent=self)

    def _after_change(self, refreshed_username=None):
        # Re-run the search so the list reflects the new state, and let the
        # Contacts window refresh its own friend list (role/ban tags, etc.)
        # in case anyone acted on happens to be a friend. Only try to
        # reselect a highlighted row for a single-target action - a bulk
        # action just clears the selection, since there's no one row to
        # land back on.
        if self._selected_rows:
            self.search()
            if refreshed_username:
                for i, r in enumerate(self.results):
                    if r["username"] == refreshed_username:
                        self.lb.selection_set(i)
                        self._on_select()
                        break
        self._load_stats()
        if self.on_change:
            try:
                self.on_change()
            except Exception:
                pass

    def _reason(self):
        return (self.reason_var.get() or "").strip() or None

    def do_save_note(self):
        if len(self._selected_rows) != 1:
            return
        r = self._selected_rows[0]
        note = self.note_txt.get("1.0", "end").strip()
        try:
            self.net.set_note(r["id"], note)
        except AppNet.NetError as e:
            messagebox.showwarning("Couldn't save note", e.message, parent=self)
            return
        r["note"] = note

    def do_kick(self):
        rows = self._selected_rows_or_warn()
        if not rows:
            return
        if not self._confirm_bulk("Kick", "Kick", rows):
            return
        reason = self._reason()
        self._apply_bulk(rows, lambda r: self.net.kick(r["id"], reason), "kicks")
        self.reason_var.set("")
        self._after_change(rows[0]["username"] if len(rows) == 1 else None)

    def _ban_minutes(self):
        raw = (self.ban_min_var.get() or "").strip()
        if not raw:
            return 0  # blank = permanent
        try:
            minutes = int(raw)
        except ValueError:
            messagebox.showinfo("Ban length", "Enter a whole number of minutes, or leave it blank for permanent.",
                                parent=self)
            return None
        if minutes < 1:
            messagebox.showinfo("Ban length", "Duration must be at least 1 minute, or leave it blank for permanent.",
                                parent=self)
            return None
        return minutes

    def do_ban(self):
        rows = self._selected_rows_or_warn()
        if not rows:
            return
        minutes = self._ban_minutes()
        if minutes is None:
            return
        verb = f"Ban for {minutes} minute(s)" if minutes else "Ban permanently"
        if not self._confirm_bulk("Ban", verb, rows):
            return
        reason = self._reason()
        self._apply_bulk(rows, lambda r: self.net.ban(r["id"], minutes, reason), "bans")
        self.reason_var.set("")
        self._after_change(rows[0]["username"] if len(rows) == 1 else None)

    def do_unban(self):
        rows = self._selected_rows_or_warn()
        if not rows:
            return
        if len(rows) > 1 and not self._confirm_bulk("Unban", "Unban", rows):
            return
        reason = self._reason()
        self._apply_bulk(rows, lambda r: self.net.unban(r["id"], reason), "unbans")
        self.reason_var.set("")
        self._after_change(rows[0]["username"] if len(rows) == 1 else None)

    def do_set_role(self):
        rows = self._selected_rows_or_warn()
        if not rows:
            return
        role = self.role_var.get()
        label = self.ROLE_LABELS.get(role, role)
        if not self._confirm_bulk("Set role", f"Set role to {label} for", rows):
            return
        reason = self._reason()
        self._apply_bulk(rows, lambda r: self.net.set_role(r["id"], role, reason), "role changes")
        self.reason_var.set("")
        self._after_change(rows[0]["username"] if len(rows) == 1 else None)

    def _mute_minutes(self):
        raw = (self.mute_min_var.get() or "").strip()
        try:
            minutes = int(raw)
        except ValueError:
            messagebox.showinfo("Mute duration", "Enter a whole number of minutes.", parent=self)
            return None
        if minutes < 1:
            messagebox.showinfo("Mute duration", "Duration must be at least 1 minute.", parent=self)
            return None
        return minutes

    def do_mute(self):
        rows = self._selected_rows_or_warn()
        if not rows:
            return
        minutes = self._mute_minutes()
        if minutes is None:
            return
        if not self._confirm_bulk("Mute", f"Mute for {minutes} minute(s)", rows):
            return
        reason = self._reason()
        self._apply_bulk(rows, lambda r: self.net.mute(r["id"], minutes, reason), "mutes")
        self.reason_var.set("")
        self._after_change(rows[0]["username"] if len(rows) == 1 else None)

    def do_unmute(self):
        rows = self._selected_rows_or_warn()
        if not rows:
            return
        if len(rows) > 1 and not self._confirm_bulk("Unmute", "Unmute", rows):
            return
        reason = self._reason()
        self._apply_bulk(rows, lambda r: self.net.unmute(r["id"], reason), "unmutes")
        self.reason_var.set("")
        self._after_change(rows[0]["username"] if len(rows) == 1 else None)

    def do_warn(self):
        rows = self._selected_rows_or_warn()
        if not rows:
            return
        reason = self._reason()
        if not reason:
            messagebox.showinfo("Reason needed",
                                "Enter a reason before warning - it's included in the notice they get.",
                                parent=self)
            return
        if not self._confirm_bulk("Warn", "Warn", rows):
            return
        self._apply_bulk(rows, lambda r: self.net.warn(r["id"], reason), "warnings")
        self.reason_var.set("")
        self._after_change(rows[0]["username"] if len(rows) == 1 else None)

    def do_force_signout(self):
        rows = self._selected_rows_or_warn()
        if not rows:
            return
        if not self._confirm_bulk("Force sign-out", "Sign out of every device", rows):
            return
        reason = self._reason()
        self._apply_bulk(rows, lambda r: self.net.force_signout(r["id"], reason), "sign-outs")
        self.reason_var.set("")
        self._after_change(rows[0]["username"] if len(rows) == 1 else None)

    def open_mod_log(self):
        try:
            entries = self.net.mod_log()
        except AppNet.NetError as e:
            messagebox.showwarning("Couldn't load log", e.message, parent=self)
            return
        ModLogWindow(self, entries)

    def open_broadcast(self):
        win = tk.Toplevel(self)
        win.title("Broadcast announcement")
        win.configure(bg=BG)
        win.geometry("380x240")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="\U0001f4e2 Send to everyone",
                 font=tkfont.Font(family="Segoe UI", size=13, weight="bold"),
                 bg=BG, fg=TEXT).pack(pady=(14, 2))
        tk.Label(win, text="Every account gets this as a notice next time they open the app.",
                 font=("Segoe UI", 8), bg=BG, fg=MUTED, wraplength=340).pack(pady=(0, 8))

        txt = tk.Text(win, bg=CARD2, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                     highlightthickness=0, font=("Segoe UI", 10), height=4, wrap="word")
        txt.pack(fill="both", expand=True, padx=14)
        txt.focus_set()

        hint = tk.Label(win, text="", font=("Segoe UI", 8), bg=BG, fg=RED, wraplength=340)
        hint.pack(pady=(4, 0))

        def send():
            message = txt.get("1.0", "end").strip()
            if not message:
                hint.config(text="Enter a message first.")
                return
            if not messagebox.askyesno("Broadcast", "Send this to every account on the server?", parent=win):
                return
            try:
                result = self.net.broadcast(message)
            except AppNet.NetError as e:
                hint.config(text=e.message)
                return
            messagebox.showinfo("Sent", f"Sent to {result.get('recipients', '?')} account(s).", parent=win)
            win.destroy()

        row = tk.Frame(win, bg=BG)
        row.pack(pady=(8, 14))
        tk.Button(row, text="Cancel", command=win.destroy, bg=CARD2, fg=TEXT,
                  activebackground="#2c1f52", activeforeground="#ffffff", relief="flat", bd=0,
                  padx=14, pady=6, font=("Segoe UI", 9), cursor="hand2").pack(side="left", padx=4)
        tk.Button(row, text="Send", command=send, bg=ACC, fg="#ffffff",
                  activebackground=ACC, activeforeground="#ffffff", relief="flat", bd=0,
                  padx=14, pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left", padx=4)


class ModLogWindow(tk.Toplevel):
    """Read-only view of the moderation history (kicks/bans/unbans/role
    changes) returned by /api/owner/modlog - most recent first."""

    ACTION_LABELS = {
        "kick": "Kicked",
        "ban": "Banned permanently",
        "unban": "Unbanned",
        "unmute": "Unmuted",
        "force_signout": "Force signed out",
        "warn": "Warned",
        "broadcast": "Sent an announcement to",
    }

    def __init__(self, app, entries):
        super().__init__(app)
        self.title("Moderation log")
        self.configure(bg=BG)
        self.geometry("480x420")
        self.minsize(400, 300)
        self.transient(app)

        tk.Label(self, text="Moderation log", font=tkfont.Font(family="Segoe UI", size=14, weight="bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=14, pady=(14, 2))
        tk.Label(self, text="Most recent 200 actions, newest first.",
                 font=("Segoe UI", 8), bg=BG, fg=MUTED, anchor="w").pack(fill="x", padx=14, pady=(0, 8))

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        txt = tk.Text(frame, bg=CARD, fg=TEXT, relief="flat", bd=0, highlightthickness=0,
                      font=("Segoe UI", 9), wrap="word", state="normal", cursor="arrow")
        sb = tk.Scrollbar(frame, orient="vertical", command=txt.yview, bg=BG, troughcolor=BG,
                          activebackground=MUTED)
        txt.config(yscrollcommand=sb.set)
        txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        txt.tag_config("who", foreground=ACC, font=("Segoe UI", 9, "bold"))
        txt.tag_config("time", foreground=MUTED, font=("Segoe UI", 8))
        txt.tag_config("reason", foreground="#ffd166")

        if not entries:
            txt.insert("end", "No moderation actions logged yet.")
        for e in entries:
            action = e.get("action", "")
            ts = e.get("ts") or 0
            try:
                when = datetime.datetime.fromtimestamp(ts).strftime("%b %d, %I:%M %p")
            except Exception:
                when = ""
            if action == "register":
                # Actor and target are the same account (nobody moderated
                # anything - they just signed up), so this reads once
                # instead of repeating the username as its own target.
                txt.insert("end", e.get("actor", "?"), "who")
                txt.insert("end", " created an account")
                if when:
                    txt.insert("end", f"  \u00b7  {when}", "time")
                txt.insert("end", "\n\n")
                continue
            if action.startswith("role:"):
                role = action.split(":", 1)[1]
                label = f"Set role to {role.replace('_', '-').title()}"
            elif action.startswith("mute:"):
                mins = action.split(":", 1)[1]
                label = f"Muted for {mins} min"
            elif action.startswith("ban:"):
                mins = action.split(":", 1)[1]
                label = f"Banned for {mins} min"
            else:
                label = self.ACTION_LABELS.get(action, action)
            txt.insert("end", e.get("actor", "?"), "who")
            txt.insert("end", f" {label.lower()} ")
            txt.insert("end", e.get("target", "?"), "who")
            if when:
                txt.insert("end", f"  \u00b7  {when}", "time")
            if e.get("reason"):
                # A broadcast's "reason" is really the announcement text
                # itself - labeled differently so it doesn't read like an
                # excuse for a moderation action.
                tag_label = "Message" if action == "broadcast" else "Reason"
                txt.insert("end", f"\n    {tag_label}: {e['reason']}", "reason")
            txt.insert("end", "\n\n")
        txt.config(state="disabled")

        tk.Button(self, text="Close", command=self.destroy, bg=CARD2, fg=TEXT,
                  activebackground="#2c1f52", activeforeground="#ffffff", relief="flat", bd=0,
                  padx=14, pady=6, font=("Segoe UI", 9), cursor="hand2").pack(pady=(0, 14))


# The reaction picker offered in ChatWindow's right-click menu - must match
# server/main.py's ALLOWED_REACTIONS exactly, since the server rejects
# anything outside this set.
REACTION_EMOJIS = ("\U0001F44D", "❤️", "\U0001F602", "\U0001F62E", "\U0001F622", "\U0001F525")


class ChatWindow(tk.Toplevel):
    def __init__(self, app, contact, start_call=False, net=None):
        super().__init__(app)
        self.contact = contact
        self.net = net if (net is not None and net.signed_in) else None
        self.remote_id = contact.get("id") if self.net else None
        self.configure(bg=BG)
        self.title(contact["name"])
        self.geometry("460x560")
        self.minsize(380, 400)
        self.calling = False
        self.in_call = False
        self._initiated_call = False
        self._incoming = False
        self.call_job = None
        self._poll_stop = threading.Event()
        self._poll_thread = None
        self._last_typing_sent = 0.0
        # Net-mode messages are keyed by their server id and reconciled in
        # place every poll (see _reconcile_msgs) rather than appended
        # blindly, so an edit/delete/reaction on a message already on
        # screen updates that same line instead of adding a duplicate.
        self._msg_cache = {}
        self._msg_by_id = {}
        self.me = my_username() or "You"
        self.me_display = self.me + (" \u2b50" if net_is_owner(self.net) or
                                     (is_owner() and _is_owner_username(my_username())) else "")
        net_msgs = []
        if self.net:
            try:
                net_msgs = self.net.messages(self.remote_id, 0)
            except AppNet.NetError:
                net_msgs = []
        else:
            self.chats = load_chats()
            self.messages = self.chats.setdefault(contact["name"], [])

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()
        if self.net:
            self._reconcile_msgs(net_msgs)
            self._start_poll()
        else:
            self._render()
        if start_call:
            self.start_call()

    def _on_close(self):
        self._poll_stop.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=1.0)
        self.destroy()

    def _ban_ok(self):
        if self.net:
            return net_can_ban(self.net)
        return is_owner() and _is_owner_username(my_username())

    def _kick_ok(self):
        if self.net:
            return net_can_kick(self.net)
        return is_owner() and _is_owner_username(my_username())

    def _build(self):
        head = tk.Frame(self, bg=CARD)
        head.pack(fill="x", pady=(0, 8))
        pad = tk.Frame(head, bg=CARD, padx=12, pady=10)
        pad.pack(fill="x")
        self.avatar = tk.Canvas(pad, width=44, height=44, bg=CARD, highlightthickness=0)
        self.avatar.pack(side="left", padx=(0, 10))
        self._draw_avatar()
        names = tk.Frame(pad, bg=CARD)
        names.pack(side="left")
        tk.Label(names, text=self.contact["name"], font=tkfont.Font(family="Segoe UI", size=13, weight="bold"),
                 bg=CARD, fg=TEXT).pack(anchor="w")
        # Online/offline dot for this specific conversation - kept up to
        # date by the same 2-second poll that fetches messages (see
        # _apply_presence), separate from status_lbl below which tracks
        # call state instead.
        self.presence_lbl = tk.Label(names, text="", font=("Segoe UI", 8), bg=CARD, fg=MUTED)
        if self.net:
            self.presence_lbl.pack(anchor="w")
        self.status_lbl = tk.Label(names, text=f"Idle \u00b7 as {self.me_display}", font=("Segoe UI", 9), bg=CARD, fg=MUTED)
        self.status_lbl.pack(anchor="w")
        self.call_btn = tk.Button(pad, text="\u260e Call", command=self.toggle_call, bg=GREEN, fg="#0d1220",
                                  activebackground=GREEN, activeforeground="#0d1220", relief="flat", bd=0,
                                  padx=12, pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.call_btn.pack(side="right")
        if self._kick_ok():
            tk.Button(pad, text="Kick", command=lambda: self._admin(True), bg=RED, fg="#ffffff",
                      activebackground=RED, activeforeground="#ffffff", relief="flat", bd=0,
                      padx=10, pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right", padx=(0, 6))
        if self._kick_ok() and self.net:
            # Mute is net-only (there's nothing to mute in local/offline
            # chats) and same tier as Kick - a quick 30-minute mute right
            # from the conversation, without leaving it. Longer/custom
            # durations still go through the Special Menu.
            tk.Button(pad, text="Mute", command=self._mute_from_chat, bg="#8a5a00", fg="#ffffff",
                      activebackground="#8a5a00", activeforeground="#ffffff", relief="flat", bd=0,
                      padx=10, pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right", padx=(0, 6))
        if self._ban_ok():
            tk.Button(pad, text="Ban", command=lambda: self._admin(False), bg="#a3003f", fg="#ffffff",
                      activebackground="#a3003f", activeforeground="#ffffff", relief="flat", bd=0,
                      padx=10, pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right", padx=(0, 6))

        self.txt = tk.Text(self, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                           highlightthickness=0, font=("Segoe UI", 10), wrap="word", state="disabled")
        self.txt.pack(fill="both", expand=True, padx=14, pady=(0, 6))
        self.txt.tag_config("chat", foreground=TEXT)
        self.txt.tag_config("call", foreground=GREEN)
        self.txt.tag_config("time", foreground=MUTED, font=("Segoe UI", 8))
        self.txt.tag_config("me", foreground=ACC, font=("Segoe UI", 9, "bold"))
        self.txt.tag_config("deleted", foreground=MUTED, font=("Segoe UI", 10, "italic"))
        self.txt.tag_config("reactions", foreground=MUTED, font=("Segoe UI", 9))
        if self.net:
            # Right-click a message to react to it, or edit/delete your own.
            self.txt.bind("<Button-3>", self._on_right_click)

        self.typing_lbl = tk.Label(self, text="", font=("Segoe UI", 8, "italic"), bg=BG, fg=MUTED, anchor="w")
        self.typing_lbl.pack(fill="x", padx=14)

        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=14, pady=(0, 12))
        self.entry = tk.Entry(row, bg=CARD2, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                              highlightthickness=0, font=("Segoe UI", 10))
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=6)
        self.entry.bind("<Return>", lambda e: self.send())
        if self.net:
            self.entry.bind("<KeyRelease>", self._on_typing_key)
        tk.Button(row, text="Send", command=self.send, bg=ACC, fg="#ffffff", activebackground=ACC,
                  activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right")
        self.entry.focus_set()

    def _draw_avatar(self):
        c = self.avatar
        c.delete("all")
        c.create_oval(1, 1, 43, 43, fill=ACC, outline="")
        letter = (self.contact.get("name", "?")[:1] or "?").upper()
        c.create_text(22, 22, text=letter, fill="#0d1220",
                      font=tkfont.Font(family="Segoe UI", size=18, weight="bold"))

    def _ts(self):
        return datetime.datetime.now().strftime("%H:%M")

    def _admin(self, kick=True):
        if not (self._kick_ok() if kick else self._ban_ok()):
            return
        name = self.contact["name"]
        action = "Kick" if kick else "Ban"
        if not messagebox.askyesno(action, f"{action} {name}?\n\n"
                                           f"They will be removed from your network."
                                           + ("" if kick else " and blocked from being added again, "
                                                              "permanently. For a timed ban, use the "
                                                              "Special Menu instead."),
                                   parent=self):
            return
        if self.net:
            try:
                if kick:
                    self.net.kick(self.remote_id)
                else:
                    self.net.ban(self.remote_id)
            except AppNet.NetError as e:
                messagebox.showwarning(f"Couldn't {action.lower()}", e.message, parent=self)
                return
        else:
            chats = load_chats()
            chats.pop(name, None)
            save_chats(chats)
            contacts = load_contacts()
            save_contacts([c for c in contacts if c.get("name") != name])
            if not kick:
                ban_name(name)
        self._poll_stop.set()
        parent = self.master
        self.destroy()
        if hasattr(parent, "_load_session"):
            parent._load_session()
        elif hasattr(parent, "refresh_list"):
            parent.refresh_list()
        messagebox.showinfo(action, f"{name} has been {'kicked' if kick else 'banned'}.", parent=parent)

    def _mute_from_chat(self):
        if not (self._kick_ok() and self.net):
            return
        name = self.contact["name"]
        if not messagebox.askyesno("Mute", f"Mute {name} for 30 minutes?\n\n"
                                           f"They won't be able to send messages until it expires. "
                                           f"For a custom duration, use the Special Menu instead.",
                                   parent=self):
            return
        try:
            self.net.mute(self.remote_id, 30)
        except AppNet.NetError as e:
            messagebox.showwarning("Couldn't mute", e.message, parent=self)
            return
        messagebox.showinfo("Mute", f"{name} has been muted for 30 minutes.", parent=self)

    def toggle_call(self):
        if self.net:
            if self.in_call:
                self.end_call()
            elif self._incoming:
                self.accept_call()
            elif self.calling or self._initiated_call:
                self.end_call()
            else:
                self.start_call()
        else:
            if self.in_call:
                self.end_call()
            else:
                self.start_call()

    def start_call(self):
        if self.in_call:
            return
        if self.net:
            try:
                self.net.call(self.remote_id, "start")
            except AppNet.NetError as e:
                messagebox.showwarning("Call failed", e.message, parent=self)
                return
            self._initiated_call = True
            self._incoming = False
        self.calling = True
        self.status_lbl.config(text="Calling\u2026", fg=ACC)
        self.call_btn.config(text="\u260e Hang up", bg=RED, fg="#ffffff", activeforeground="#ffffff")
        _ring()
        if not self.net:
            self.call_job = self.after(1600, self._connect)

    def accept_call(self):
        if self.net:
            try:
                self.net.call(self.remote_id, "accept")
            except AppNet.NetError as e:
                messagebox.showwarning("Couldn't answer", e.message, parent=self)
                return
        self._incoming = False
        self._connect()

    def _connect(self):
        self.call_job = None
        self.calling = False
        self._initiated_call = False
        self._incoming = False
        self.in_call = True
        self.status_lbl.config(text="In call \u2014 live", fg=GREEN)
        self.call_btn.config(text="\u260e Hang up", bg=RED, fg="#ffffff", activeforeground="#ffffff")
        self._append_local("\u260e Call connected", "call")
        if winsound:
            try:
                winsound.Beep(880, 90)
                winsound.Beep(1320, 120)
            except Exception:
                pass

    def end_call(self):
        if self.net:
            was = self.in_call or self.calling or self._initiated_call or self._incoming
            if was:
                try:
                    self.net.call(self.remote_id, "end")
                except AppNet.NetError:
                    pass
            self._reset_call()
            if was:
                self._append_local("\u260e Call ended", "call")
        else:
            if self.call_job:
                self.after_cancel(self.call_job)
                self.call_job = None
            was_in = self.in_call or self.calling
            self._reset_call()
            if was_in:
                self._append_local("\u260e Call ended", "call")
                save_chats(self.chats)

    def _reset_call(self):
        self.calling = False
        self.in_call = False
        self._initiated_call = False
        self._incoming = False
        self.status_lbl.config(text="Idle", fg=MUTED)
        self.call_btn.config(text="\u260e Call", bg=GREEN, fg="#0d1220", activeforeground="#0d1220")

    def _start_poll(self):
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self):
        while not self._poll_stop.is_set():
            try:
                # Always after=0 - a message already on screen can still
                # change (edited, deleted, reacted to) without its ts
                # changing, so the full recent window is re-fetched every
                # tick and reconciled by id rather than filtered by time.
                msgs = self.net.messages(self.remote_id, 0)
                state = self.net.call_state(self.remote_id).get("state", "none")
                pres = self.net.presence(self.remote_id)
            except AppNet.NetError:
                msgs, state, pres = [], None, None
            if msgs:
                try:
                    self.after(0, self._reconcile_msgs, msgs)
                except Exception:
                    pass
            if state is not None:
                try:
                    self.after(0, self._apply_call_state, state)
                except Exception:
                    pass
            if pres is not None:
                try:
                    self.after(0, self._apply_presence, pres)
                except Exception:
                    pass
            self._poll_stop.wait(2.0)

    def _apply_presence(self, pres):
        online = bool(pres.get("online"))
        self.presence_lbl.config(
            text=("\U0001f7e2 Online" if online else "⚪ Offline"),
            fg=(GREEN if online else MUTED))
        if pres.get("typing"):
            self.typing_lbl.config(text=f"{self.contact['name']} is typing…")
        else:
            self.typing_lbl.config(text="")

    def _on_typing_key(self, event=None):
        if not self.net:
            return
        t = time.time()
        if t - self._last_typing_sent < 2.0:
            return
        self._last_typing_sent = t
        remote_id = self.remote_id
        net = self.net

        def worker():
            try:
                net.set_typing(remote_id)
            except AppNet.NetError:
                pass
        threading.Thread(target=worker, daemon=True).start()

    # --- message reconciliation (net mode) ------------------------------
    #
    # Every poll fetches the whole recent window and diffs it against what's
    # already rendered, by message id, so an edit/delete/reaction on a
    # message already on screen updates that one block in place instead of
    # appending a duplicate. Local/offline chats (no self.net) don't use any
    # of this - they still go through the older _render()/_append_local path
    # below, since there's no server round trip to reconcile against.

    def _reaction_sig(self, reactions):
        return tuple(sorted((r.get("user_id"), r.get("emoji")) for r in (reactions or [])))

    def _message_sig(self, m):
        return (m.get("text"), bool(m.get("edited")), bool(m.get("deleted")), self._reaction_sig(m.get("reactions")))

    def _reconcile_msgs(self, msgs):
        for m in msgs:
            mid = m["id"]
            sig = self._message_sig(m)
            self._msg_by_id[mid] = m
            if mid not in self._msg_cache:
                self._insert_message_block(m)
                self._msg_cache[mid] = sig
            elif self._msg_cache[mid] != sig:
                self._update_message_block(m)
                self._msg_cache[mid] = sig

    def _format_reactions(self, reactions):
        if not reactions:
            return ""
        counts, order = {}, []
        for r in reactions:
            e = r.get("emoji")
            if e not in counts:
                counts[e] = 0
                order.append(e)
            counts[e] += 1
        return "   " + "  ".join(f"{e} {counts[e]}" for e in order)

    def _message_parts(self, m):
        """Returns a flat (text, tag, text, tag, ...) run for one message
        block, suitable for a single Text.insert() call - inserting several
        tagged runs in one call keeps them in order regardless of mark
        gravity, which matters once _update_message_block starts replacing
        a block in place."""
        tstr = datetime.datetime.fromtimestamp(m["ts"]).strftime("%H:%M")
        name = self.net.me["username"] if m["sender"] == self.net.me["id"] else self.contact["name"]
        parts = [f"[{tstr}]  ", "time", name + ": ", "me"]
        if m.get("deleted"):
            parts += ["⚠ This message was deleted.", "deleted"]
        else:
            body = m["text"] + (" (edited)" if m.get("edited") else "")
            parts += [body, "chat"]
        parts += ["\n", ""]
        rx = self._format_reactions(m.get("reactions"))
        if rx:
            parts += [rx + "\n", "reactions"]
        return parts

    def _insert_run(self, idx, *parts):
        self.txt.insert(idx, *parts)

    def _insert_message_block(self, m):
        mid = m["id"]
        self.txt.config(state="normal")
        start_idx = self.txt.index("end-1c")
        self._insert_run("end-1c", *self._message_parts(m))
        end_idx = self.txt.index("end-1c")
        s, e = f"mstart_{mid}", f"mend_{mid}"
        self.txt.mark_set(s, start_idx)
        self.txt.mark_gravity(s, "left")
        self.txt.mark_set(e, end_idx)
        self.txt.mark_gravity(e, "right")
        self.txt.config(state="disabled")
        self.txt.see("end")

    def _update_message_block(self, m):
        mid = m["id"]
        s, e = f"mstart_{mid}", f"mend_{mid}"
        if s not in self.txt.mark_names() or e not in self.txt.mark_names():
            self._insert_message_block(m)
            return
        self.txt.config(state="normal")
        self.txt.delete(s, e)
        self._insert_run(s, *self._message_parts(m))
        self.txt.config(state="disabled")

    def _msg_at(self, click_idx):
        for mid in self._msg_by_id:
            s, e = f"mstart_{mid}", f"mend_{mid}"
            if s not in self.txt.mark_names() or e not in self.txt.mark_names():
                continue
            if self.txt.compare(click_idx, ">=", s) and self.txt.compare(click_idx, "<", e):
                return mid
        return None

    def _my_reaction(self, m):
        me_id = self.net.me["id"]
        for r in (m.get("reactions") or []):
            if r.get("user_id") == me_id:
                return r.get("emoji")
        return None

    def _on_right_click(self, event):
        click_idx = self.txt.index(f"@{event.x},{event.y}")
        mid = self._msg_at(click_idx)
        if mid is None:
            return
        m = self._msg_by_id.get(mid)
        if m is None or m.get("deleted"):
            return
        menu = tk.Menu(self, tearoff=0, bg=CARD2, fg=TEXT, activebackground=ACC, activeforeground="#ffffff")
        react_menu = tk.Menu(menu, tearoff=0, bg=CARD2, fg=TEXT, activebackground=ACC, activeforeground="#ffffff")
        for emoji in REACTION_EMOJIS:
            react_menu.add_command(label=emoji, command=lambda e=emoji: self._react(mid, e))
        if self._my_reaction(m):
            react_menu.add_separator()
            react_menu.add_command(label="Remove my reaction", command=lambda: self._react(mid, ""))
        menu.add_cascade(label="React", menu=react_menu)
        if m["sender"] == self.net.me["id"]:
            menu.add_separator()
            menu.add_command(label="Edit…", command=lambda: self._edit_message(mid, m["text"]))
            menu.add_command(label="Delete", command=lambda: self._delete_message(mid))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _react(self, mid, emoji):
        try:
            self.net.react(mid, emoji)
        except AppNet.NetError as e:
            messagebox.showwarning("Couldn't react", e.message, parent=self)
            return
        self._force_refresh()

    def _edit_message(self, mid, current_text):
        win = tk.Toplevel(self)
        win.title("Edit message")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        box = tk.Text(win, width=40, height=4, bg=CARD2, fg=TEXT, insertbackground=TEXT, relief="flat",
                      bd=0, highlightthickness=0, font=("Segoe UI", 10), wrap="word")
        box.pack(padx=14, pady=(14, 8))
        box.insert("1.0", current_text)
        box.focus_set()

        def save():
            text = box.get("1.0", "end").strip()
            if not text:
                messagebox.showwarning("Empty", "Message can't be empty - delete it instead.", parent=win)
                return
            try:
                self.net.edit_message(mid, text)
            except AppNet.NetError as err:
                messagebox.showwarning("Couldn't edit", err.message, parent=win)
                return
            win.destroy()
            self._force_refresh()

        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(pady=(0, 14))
        tk.Button(btn_row, text="Cancel", command=win.destroy, bg=CARD2, fg=TEXT, activebackground="#2c1f52",
                  activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6,
                  font=("Segoe UI", 9), cursor="hand2").pack(side="left", padx=4)
        tk.Button(btn_row, text="Save", command=save, bg=ACC, fg="#ffffff", activebackground=ACC,
                  activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left", padx=4)

    def _delete_message(self, mid):
        if not messagebox.askyesno("Delete message", "Delete this message for both of you?\n\n"
                                                       "This can't be undone.", parent=self):
            return
        try:
            self.net.delete_message(mid)
        except AppNet.NetError as e:
            messagebox.showwarning("Couldn't delete", e.message, parent=self)
            return
        self._force_refresh()

    def _force_refresh(self):
        try:
            msgs = self.net.messages(self.remote_id, 0)
        except AppNet.NetError:
            return
        self._reconcile_msgs(msgs)

    def _apply_call_state(self, state):
        if state == "live":
            if not self.in_call:
                self._incoming = False
                self.calling = False
                self._initiated_call = False
                self.in_call = True
                self.status_lbl.config(text="In call \u2014 live", fg=GREEN)
                self.call_btn.config(text="\u260e Hang up", bg=RED, fg="#ffffff", activeforeground="#ffffff")
                self._append_local("\u260e Call connected", "call")
                if winsound:
                    try:
                        winsound.Beep(880, 90)
                        winsound.Beep(1320, 120)
                    except Exception:
                        pass
        elif state == "calling":
            if self._initiated_call:
                self.calling = True
                self.status_lbl.config(text="Calling\u2026", fg=ACC)
                self.call_btn.config(text="\u260e Hang up", bg=RED, fg="#ffffff", activeforeground="#ffffff")
            elif not self.in_call and not self.calling and not self._incoming:
                self._incoming = True
                self.status_lbl.config(text="Incoming call\u2026", fg=ACC)
                self.call_btn.config(text="\u260e Answer", bg=GREEN, fg="#0d1220", activeforeground="#0d1220")
                _ring()
        elif state == "ended":
            was = self.in_call or self.calling or self._incoming or self._initiated_call
            self._reset_call()
            if was:
                self._append_local("\u260e Call ended", "call")

    def send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        if self.net:
            try:
                self.net.send(self.remote_id, text)
            except AppNet.NetError as e:
                messagebox.showwarning("Couldn't send", e.message, parent=self)
                self.entry.insert(0, text)
                return
            # Pull the just-sent message back down (with its real server id,
            # needed before it can be edited/reacted to) rather than
            # appending a local guess of what the server stored.
            self._force_refresh()
            self.typing_lbl.config(text="")
        else:
            kind = "call" if self.in_call else "chat"
            self._append_local(text, kind)
            save_chats(self.chats)

    def _append_local(self, text, kind):
        tstr = self._ts()
        self.messages.append({"time": tstr, "name": self.me_display, "text": text, "kind": kind})
        self._insert_line(tstr, self.me_display, text, kind)

    def _insert_line(self, tstr, name, text, kind):
        self.txt.config(state="normal")
        self.txt.insert("end", f"[{tstr}]  ", "time")
        if name:
            self.txt.insert("end", name + ": ", "me")
        self.txt.insert("end", text + "\n", kind)
        self.txt.config(state="disabled")
        self.txt.see("end")

    def _render(self):
        self.txt.config(state="normal")
        self.txt.delete("1.0", "end")
        for m in self.messages:
            tstr = m.get("time") or ""
            name = m.get("name")
            kind = m.get("kind", "chat")
            if name is None and kind in ("chat", "call"):
                name = self.me_display
            self.txt.insert("end", f"[{tstr}]  ", "time")
            if name:
                self.txt.insert("end", name + ": ", "me")
            self.txt.insert("end", m["text"] + "\n", kind)
        self.txt.config(state="disabled")
        self.txt.see("end")


DEFAULT_SERVER_URL = "https://applauncher-rt0v.onrender.com"


class LoginWindow(tk.Toplevel):
    def __init__(self, app=None, on_ready=None):
        super().__init__(app)
        self.configure(bg=BG)
        self.title("Sign in to the network")
        self.resizable(False, False)
        self.transient(app)
        self.grab_set()
        self._on_ready = on_ready
        self.pending_username = None

        tk.Label(self, text="App Launcher Network", font=tkfont.Font(family="Segoe UI", size=16, weight="bold"),
                 bg=BG, fg=TEXT).pack(pady=(16, 2))
        tk.Label(self, text="Same server, same people, on any PC.",
                 font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(pady=(0, 12))

        self.form_frame = tk.Frame(self, bg=BG)
        self.form_frame.pack(padx=22, pady=(0, 8))
        form = self.form_frame

        tk.Label(form, text="Server URL", font=("Segoe UI", 9), bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        self.url_var = tk.StringVar(value=(AppNet.load_session() or {}).get("url", DEFAULT_SERVER_URL))
        tk.Entry(form, textvariable=self.url_var, bg=CARD2, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 10), width=40).pack(fill="x", ipady=4, pady=(2, 10))

        tk.Label(form, text="Username", font=("Segoe UI", 9), bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        self.user_var = tk.StringVar()
        tk.Entry(form, textvariable=self.user_var, bg=CARD2, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 10), width=40).pack(fill="x", ipady=4, pady=(2, 10))

        tk.Label(form, text="Password", font=("Segoe UI", 9), bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        self.pass_var = tk.StringVar()
        tk.Entry(form, textvariable=self.pass_var, show="*", bg=CARD2, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 10), width=40).pack(fill="x", ipady=4, pady=(2, 10))

        tk.Label(form, text="Email (only needed to create an account)", font=("Segoe UI", 9), bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        self.email_var = tk.StringVar()
        tk.Entry(form, textvariable=self.email_var, bg=CARD2, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 10), width=40).pack(fill="x", ipady=4, pady=(2, 2))

        self.hint = tk.Label(self, text="", font=("Segoe UI", 9), bg=BG, fg=RED, wraplength=340)
        self.hint.pack(pady=(6, 2))

        self.button_row = tk.Frame(self, bg=BG)
        self.button_row.pack(pady=(4, 16))
        self.signin_btn = tk.Button(self.button_row, text="Sign in", command=self._login, bg=ACC, fg="#ffffff",
                  activebackground=ACC, activeforeground="#ffffff", relief="flat", bd=0,
                  padx=18, pady=7, font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.signin_btn.pack(side="left", padx=6)
        self.create_btn = tk.Button(self.button_row, text="Create account", command=self._create_account, bg=CARD2, fg=TEXT,
                  activebackground="#2c1f52", activeforeground="#ffffff", relief="flat", bd=0,
                  padx=14, pady=7, font=("Segoe UI", 10), cursor="hand2")
        self.create_btn.pack(side="left", padx=6)
        self.pass_var.trace_add("write", lambda *_: self.hint.config(text=""))

        # Verification step - a new account isn't usable until its emailed
        # code is confirmed here, so this stays built but hidden (pack_forget)
        # until registration or a blocked sign-in tells us to show it.
        self.verify_frame = tk.Frame(self, bg=BG)
        vform = tk.Frame(self.verify_frame, bg=BG)
        vform.pack(padx=22, pady=(0, 8))
        tk.Label(vform, text="Verification code", font=("Segoe UI", 9), bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        self.code_var = tk.StringVar()
        tk.Entry(vform, textvariable=self.code_var, bg=CARD2, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 12), justify="center",
                 width=40).pack(fill="x", ipady=4, pady=(2, 2))
        self.code_var.trace_add("write", lambda *_: self.hint.config(text=""))

        vrow = tk.Frame(self.verify_frame, bg=BG)
        vrow.pack(pady=(10, 4))
        self.verify_btn = tk.Button(vrow, text="Verify", command=self._verify, bg=ACC, fg="#ffffff",
                  activebackground=ACC, activeforeground="#ffffff", relief="flat", bd=0,
                  padx=18, pady=7, font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.verify_btn.pack(side="left", padx=6)
        self.resend_btn = tk.Button(vrow, text="Resend code", command=self._resend, bg=CARD2, fg=TEXT,
                  activebackground="#2c1f52", activeforeground="#ffffff", relief="flat", bd=0,
                  padx=14, pady=7, font=("Segoe UI", 10), cursor="hand2")
        self.resend_btn.pack(side="left", padx=6)
        tk.Button(self.verify_frame, text="← Back", command=self._back_to_form, bg=BG, fg=MUTED,
                  activebackground=BG, activeforeground=TEXT, relief="flat", bd=0,
                  font=("Segoe UI", 9, "underline"), cursor="hand2").pack(pady=(0, 16))

    def _set_busy(self, busy):
        state = "disabled" if busy else "normal"
        self.signin_btn.config(state=state)
        self.create_btn.config(state=state)
        self.verify_btn.config(state=state)
        self.resend_btn.config(state=state)

    def _do(self, fn, on_success=None):
        self.hint.config(fg=RED, text="")
        url = self.url_var.get().strip().rstrip("/")
        if not url or url in ("https://", "http://"):
            self.hint.config(text="Enter the server URL first.")
            return
        net = AppNet.Net(url)
        self.hint.config(fg=MUTED,
                         text="Working… free servers can take up to a minute "
                              "to wake up if nobody's used them in a while.")
        self._set_busy(True)

        def work():
            try:
                me = fn(net)
                err = None
            except AppNet.NetError as e:
                me, err = None, e
            except Exception as e:
                me, err = None, AppNet.NetError(str(e))
            self.after(0, done, me, err)

        def done(me, err):
            if not self.winfo_exists():
                return
            self._set_busy(False)
            if err is not None:
                if err.status == 428:
                    # The account exists and the password's right, but the
                    # email on file hasn't been confirmed yet - send the user
                    # straight to the code step instead of just an error.
                    self._show_verify_step(self.user_var.get().strip(), err.message)
                    return
                self.hint.config(fg=RED, text=err.message)
                return
            self.hint.config(fg=RED, text="")
            if on_success:
                on_success(net, me)
            else:
                AppNet.save_session(url, net.token, me)
                if self._on_ready:
                    self._on_ready()
                self.destroy()

        threading.Thread(target=work, daemon=True).start()

    def _login(self):
        self._do(lambda n: n.login(self.user_var.get().strip(), self.pass_var.get()))

    def _create_account(self):
        username = self.user_var.get().strip()
        email = self.email_var.get().strip()
        if not email or "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            self.hint.config(fg=RED, text="Enter a valid email address to create an account.")
            return

        def on_success(net, me):
            self._show_verify_step(
                username,
                f"We sent a 6-digit code to {email}. Enter it below to finish creating your account.")

        self._do(lambda n: n.register(username, self.pass_var.get(), email), on_success=on_success)

    def _show_verify_step(self, username, message):
        self.pending_username = username
        self.code_var.set("")
        self.form_frame.pack_forget()
        self.button_row.pack_forget()
        self.hint.config(fg=MUTED, text=message)
        self.verify_frame.pack()

    def _back_to_form(self):
        self.verify_frame.pack_forget()
        self.hint.config(fg=RED, text="")
        self.form_frame.pack(padx=22, pady=(0, 8))
        self.button_row.pack(pady=(4, 16))

    def _verify(self):
        code = self.code_var.get().strip()
        if not code:
            self.hint.config(fg=RED, text="Enter the code from your email.")
            return
        self._do(lambda n: n.verify_email(self.pending_username, code))

    def _resend(self):
        def on_success(net, me):
            self.hint.config(fg=MUTED, text="A new code is on its way - check your email.")

        self._do(lambda n: n.resend_code(self.pending_username), on_success=on_success)


# ---------------- profile pictures ----------------

AVATAR_PAIRS = [
    ((240, 101, 160), (150, 50, 100)),
    ((67, 201, 127), (35, 130, 80)),
    ((255, 184, 108), (200, 120, 50)),
    ((157, 123, 255), (90, 60, 190)),
    ((255, 107, 107), (190, 50, 60)),
    ((79, 214, 214), (30, 140, 150)),
    ((255, 224, 102), (200, 150, 40)),
]

AVATAR_CUSTOM = os.path.join(DATA_DIR, "avatar_custom.png")


def avatar_key():
    return (_load_config().get("avatar") or "").strip()


def set_avatar_key(key):
    cfg = _load_config()
    cfg["avatar"] = key
    save_json(CONFIG_FILE, cfg)


def _font(size):
    for name in ("segoeuib.ttf", "seguisb.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", name), size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_avatar(key, size, letter=None, circle=True, shape=None):
    from PIL import Image as _Image
    if shape is None:
        shape = "circle" if circle else "square"
    key = key or ""
    scale = 3
    big = max(8, size * scale)
    bg = _Image.new("RGBA", (big, big), (0, 0, 0, 0))

    def gradient(top, bottom):
        g = _Image.new("RGB", (big, big))
        d = ImageDraw.Draw(g)
        for y in range(big):
            t = y / (big - 1) if big > 1 else 0
            d.line([(0, y), (big, y)],
                   fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
        return g

    if key.startswith("default") and key[len("default"):].isdigit():
        idx = int(key[len("default"):]) % len(AVATAR_PAIRS)
        bg.paste(gradient(*AVATAR_PAIRS[idx]), (0, 0))
        bg = bg.convert("RGBA")
        letter = (letter or "").strip()[:1].upper()
        if letter:
            f = _font(int(big * 0.42))
            d = ImageDraw.Draw(bg)
            try:
                d.text((big / 2, big / 2 + 2), letter, font=f, fill="#ffffff", anchor="mm")
            except Exception:
                try:
                    bb = d.textbbox((0, 0), letter, font=f)
                    d.text((big / 2 - (bb[2] - bb[0]) / 2, big / 2 - (bb[3] - bb[1]) / 2),
                           letter, font=f, fill="#ffffff")
                except Exception:
                    pass
    elif key == "custom" and os.path.exists(AVATAR_CUSTOM):
        try:
            src = Image.open(AVATAR_CUSTOM).convert("RGBA")
            side = min(src.size)
            left = (src.width - side) // 2
            top = (src.height - side) // 2
            src = src.crop((left, top, left + side, top + side)).resize((big, big), Image.LANCZOS)
            bg = src
        except Exception:
            pass

    if bg.getbbox() is None:
        bg.paste(gradient(*AVATAR_PAIRS[0]), (0, 0))
        bg = bg.convert("RGBA")

    if shape == "circle":
        mask = _Image.new("L", (big, big), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, big - 1, big - 1), fill=255)
        out = _Image.new("RGBA", (big, big), (0, 0, 0, 0))
        out.paste(bg, (0, 0), mask)
        ring = _Image.new("RGBA", (big, big), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((0, 0, big - 1, big - 1),
                                     outline=(255, 255, 255, 70), width=max(3, big // 35))
        out.alpha_composite(ring)
    elif shape == "rounded":
        r = big // 4
        mask = _Image.new("L", (big, big), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius=r, fill=255)
        out = _Image.new("RGBA", (big, big), (0, 0, 0, 0))
        out.paste(bg, (0, 0), mask)
    else:
        out = bg

    out = out.resize((size, size), Image.LANCZOS)
    return out


def avatar_photo(key, size, letter=None, circle=True, shape=None):
    return ImageTk.PhotoImage(render_avatar(key, size, letter, circle, shape))


def save_custom_avatar(img):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        img.save(AVATAR_CUSTOM)
    except Exception:
        pass


class ProfileWindow(tk.Toplevel):
    def __init__(self, app=None):
        super().__init__(app)
        self.app = app
        self.title("Profile")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.geometry("520x560")
        self._photos = []
        self._build()
        self._refresh()

    def _build(self):
        tk.Label(self, text="Your Profile", font=tkfont.Font(family="Segoe UI", size=16, weight="bold"),
                 bg=BG, fg=TEXT).pack(pady=(14, 2))
        self.sub_lbl = tk.Label(self, font=("Segoe UI", 9), bg=BG, fg=MUTED)
        self.sub_lbl.pack()

        self.preview = tk.Label(self, bg=BG)
        self.preview.pack(pady=(10, 4))

        self.name_var = tk.StringVar()
        name_row = tk.Frame(self, bg=BG)
        name_row.pack(pady=(4, 2))
        tk.Label(name_row, text="Name:", font=("Segoe UI", 10), bg=BG, fg=TEXT).pack(side="left", padx=(0, 8))
        self.name_entry = tk.Entry(name_row, textvariable=self.name_var, bg=CARD2, fg=TEXT,
                                   insertbackground=TEXT, relief="flat", bd=0, highlightthickness=0,
                                   font=("Segoe UI", 10), width=24)
        self.name_entry.pack(side="left", ipady=4, padx=(0, 8))
        tk.Button(name_row, text="Save name", command=self._save_name, bg=ACC, fg="#ffffff",
                  activebackground=ACC, activeforeground="#ffffff", relief="flat", bd=0,
                  padx=12, pady=5, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left")

        tk.Label(self, text="Pick a default picture", font=("Segoe UI", 9, "bold"), bg=BG, fg=MUTED
                 ).pack(pady=(12, 4))
        grid = tk.Frame(self, bg=BG)
        grid.pack()
        for i in range(len(AVATAR_PAIRS)):
            key = f"default{i}"
            img = avatar_photo(key, 56)
            self._photos.append(img)
            b = tk.Button(grid, image=img, command=lambda k=key: self._pick(k),
                          bg=BG, activebackground=BG, relief="flat", bd=0,
                          highlightthickness=2, highlightbackground=BG, cursor="hand2")
            b.grid(row=i // 4, column=i % 4, padx=7, pady=7)

        tk.Button(self, text="Choose a picture from your PC\u2026", command=self._browse,
                  bg=CARD2, fg=TEXT, activebackground="#2c1f52", activeforeground="#ffffff",
                  relief="flat", bd=0, padx=14, pady=7, font=("Segoe UI", 9), cursor="hand2"
                  ).pack(pady=(12, 4))

        self.owner_lbl = tk.Label(self, font=("Segoe UI", 9), bg=BG, fg=MUTED)
        self.owner_lbl.pack(pady=(8, 12))

    def _refresh(self):
        key = avatar_key()
        letter = (self.name_var.get() or my_username() or "?")[:1].upper()
        self._preview_img = avatar_photo(key, 128, letter)
        self._photos.append(self._preview_img)
        self.preview.config(image=self._preview_img)
        self.name_var.set(my_username())
        self.sub_lbl.config(text=("You are the Owner \u2b50" if is_owner() else "Regular user"))
        self.owner_lbl.config(text="Your picture and name are stored on this PC only."
                              if is_owner() else "")

    def _pick(self, key):
        set_avatar_key(key)
        self._refresh()
        if self.app is not None:
            try:
                self.app.refresh_profile_btn()
            except Exception:
                pass

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Choose a profile picture",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"), ("All files", "*.*")])
        if not path:
            return
        try:
            img = Image.open(path).convert("RGBA")
            side = min(img.size)
            left = (img.width - side) // 2
            top = (img.height - side) // 2
            img = img.crop((left, top, left + side, top + side)).resize((256, 256), Image.LANCZOS)
            save_custom_avatar(img)
            set_avatar_key("custom")
        except Exception as e:
            messagebox.showerror("Couldn't load image", str(e), parent=self)
            return
        self._refresh()
        if self.app is not None:
            try:
                self.app.refresh_profile_btn()
            except Exception:
                pass

    def _save_name(self):
        cfg = _load_config()
        cfg["username"] = self.name_var.get().strip()
        save_json(CONFIG_FILE, cfg)
        self.sub_lbl.config(text="Saved!" if not is_owner() else "Saved! You are the Owner \u2b50")
        self._refresh()

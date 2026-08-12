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

BG = "#12161f"
CARD = "#1d2130"
CARD2 = "#262c40"
TEXT = "#e9ecf5"
MUTED = "#8b93a7"
ACC = "#6c8cff"
GREEN = "#43c97f"
RED = "#ff6b6b"

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


def is_owner():
    cfg = _load_config()
    return bool(cfg.get("owner_secret")) and cfg.get("owner_machine") == machine_fingerprint()


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

        self._build()
        self._load_session()
        self.refresh_list()

    def _load_session(self):
        try:
            session = AppNet.load_session()
            if session:
                self.net = AppNet.Net(session["url"], session["token"])
                self.net.me = {
                    "id": session["id"],
                    "username": session["username"],
                    "is_owner": session["is_owner"],
                }
                self._apply_net_friends()
        except Exception:
            self.net = None
        self._update_net_ui()
        self._start_notices()

    @property
    def net_active(self):
        return bool(self.net and self.net.signed_in)

    def _apply_net_friends(self):
        try:
            friends = self.net.friends()
            self.contacts = [{"name": f["username"], "id": f["id"], "banned": f.get("banned")}
                             for f in friends]
            save_contacts(self.contacts)
        except AppNet.NetError as e:
            messagebox.showwarning("Offline", e.message, parent=self)
            self.net = None
            self.contacts = load_contacts()

    def _update_net_ui(self):
        try:
            if self.net_active:
                self.sign_btn.config(text=f"Signed in as {self.net.me['username']}",
                                     bg="#2b5c40", fg="#8fffc0")
            else:
                self.sign_btn.config(text="Sign in", bg=ACC, fg="#ffffff")
            self.add_btn.config(text="+ Add" if not self.net_active else "+ Add (by username)")
            for w, cmd in self._admin_buttons:
                if self.net_active:
                    w.pack_forget()
                    if self.net.me.get("is_owner"):
                        w.pack(**cmd)
                else:
                    w.pack_forget()
                    if is_owner():
                        w.pack(**cmd)
            if self.net_active:
                self.bans_btn.pack(side="right", padx=(0, 8))
            else:
                self.bans_btn.pack_forget()
        except Exception:
            pass

    def _start_notices(self):
        if self._notices_job:
            self.after_cancel(self._notices_job)
            self._notices_job = None
        if not self.net_active:
            return
        self._poll_notices()

    def _poll_notices(self):
        if not self.net_active:
            return
        try:
            for n in self.net.notices():
                text = n.get("text", "")
                self.after(0, self._handle_notice, text)
        except AppNet.NetError:
            pass
        self._notices_job = self.after(4000, self._poll_notices)

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
        self.sign_btn = tk.Button(bar, text="Sign in", command=self.toggle_sign_in, bg=ACC, fg="#ffffff",
                                  activebackground=ACC, activeforeground="#ffffff", relief="flat", bd=0,
                                  padx=10, pady=5, font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.sign_btn.pack(side="right", padx=(0, 6))
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
        self._admin_buttons = []
        kick_btn = b("Kick", self.kick_contact, RED, "#ffffff")
        ban_btn = b("Ban", self.ban_contact, "#b3001b", "#ffffff")
        self._admin_buttons = [
            (kick_btn, {"side": "right", "padx": (6, 0)}),
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
            self.lb.insert("end", c["name"] + (f"  \u2014  {note}" if note else ""))

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
                  activebackground="#343c58", activeforeground="#ffffff", relief="flat", bd=0,
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
                  activebackground="#343c58", activeforeground="#ffffff", relief="flat", bd=0,
                  padx=14, pady=6, font=("Segoe UI", 9), cursor="hand2").pack(side="left", padx=4)
        tk.Button(row, text="Save", command=save, bg=ACC, fg="#ffffff", activebackground=ACC,
                  activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left", padx=4)
        e_name.focus_set()

    def _admin_ok(self):
        if self.net_active:
            return bool(self.net.me.get("is_owner"))
        return is_owner()

    def delete_contact(self):
        c = self._selected()
        if not c:
            return
        if not self._admin_ok():
            return
        if not messagebox.askyesno("Delete contact", f"Remove {c['name']}?", parent=self):
            return
        self._remove_contact(c)

    def kick_contact(self):
        c = self._selected()
        if not c:
            return
        if not self._admin_ok():
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
        if not self._admin_ok():
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
        if not self._admin_ok():
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
                  activebackground="#343c58", activeforeground="#ffffff", relief="flat", bd=0,
                  padx=14, pady=6, font=("Segoe UI", 9), cursor="hand2").pack(side="right")
        tk.Button(btns, text="Unban", command=unban, bg=GREEN, fg="#0d1220",
                  activebackground=GREEN, activeforeground="#0d1220", relief="flat", bd=0,
                  padx=14, pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right", padx=(0, 8))
        refresh()


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
        self._last_ts = 0.0
        self.me = my_username() or "You"
        self.me_display = self.me + (" \u2b50" if (self.net and self.net.me.get("is_owner")) or is_owner() else "")
        if self.net:
            self.messages = []
            try:
                self.messages = self.net.messages(self.remote_id, 0)
                if self.messages:
                    self._last_ts = max(m["ts"] for m in self.messages)
            except AppNet.NetError:
                self.messages = []
        else:
            self.chats = load_chats()
            self.messages = self.chats.setdefault(contact["name"], [])

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()
        self._render()
        if self.net:
            self._start_poll()
        if start_call:
            self.start_call()

    def _on_close(self):
        self._poll_stop.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=1.0)
        self.destroy()

    def _admin_ok(self):
        if self.net:
            return bool(self.net.me.get("is_owner"))
        return is_owner()

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
        self.status_lbl = tk.Label(names, text=f"Idle \u00b7 as {self.me_display}", font=("Segoe UI", 9), bg=CARD, fg=MUTED)
        self.status_lbl.pack(anchor="w")
        self.call_btn = tk.Button(pad, text="\u260e Call", command=self.toggle_call, bg=GREEN, fg="#0d1220",
                                  activebackground=GREEN, activeforeground="#0d1220", relief="flat", bd=0,
                                  padx=12, pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.call_btn.pack(side="right")
        if self._admin_ok():
            tk.Button(pad, text="Kick", command=lambda: self._admin(True), bg=RED, fg="#ffffff",
                      activebackground=RED, activeforeground="#ffffff", relief="flat", bd=0,
                      padx=10, pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right", padx=(0, 6))
            tk.Button(pad, text="Ban", command=lambda: self._admin(False), bg="#b3001b", fg="#ffffff",
                      activebackground="#b3001b", activeforeground="#ffffff", relief="flat", bd=0,
                      padx=10, pady=6, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right", padx=(0, 6))

        self.txt = tk.Text(self, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                           highlightthickness=0, font=("Segoe UI", 10), wrap="word", state="disabled")
        self.txt.pack(fill="both", expand=True, padx=14, pady=(0, 6))
        self.txt.tag_config("chat", foreground=TEXT)
        self.txt.tag_config("call", foreground=GREEN)
        self.txt.tag_config("time", foreground=MUTED, font=("Segoe UI", 8))
        self.txt.tag_config("me", foreground=ACC, font=("Segoe UI", 9, "bold"))

        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=14, pady=(0, 12))
        self.entry = tk.Entry(row, bg=CARD2, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                              highlightthickness=0, font=("Segoe UI", 10))
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=6)
        self.entry.bind("<Return>", lambda e: self.send())
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
        if not self._admin_ok():
            return
        name = self.contact["name"]
        action = "Kick" if kick else "Ban"
        if not messagebox.askyesno(action, f"{action} {name}?\n\n"
                                           f"They will be removed from your network."
                                           + ("" if kick else " and blocked from being added again."),
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
                msgs = self.net.messages(self.remote_id, self._last_ts)
                state = self.net.call_state(self.remote_id).get("state", "none")
            except AppNet.NetError:
                msgs, state = [], None
            if msgs:
                try:
                    self.after(0, self._apply_msgs, msgs)
                except Exception:
                    pass
            if state is not None:
                try:
                    self.after(0, self._apply_call_state, state)
                except Exception:
                    pass
            self._poll_stop.wait(2.0)

    def _apply_msgs(self, msgs):
        for m in msgs:
            if m["ts"] > self._last_ts:
                self._append_net(m["sender"], m["text"], m["ts"])
                self._last_ts = m["ts"]

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
            self._append_net(self.net.me["id"], text, time.time())
        else:
            kind = "call" if self.in_call else "chat"
            self._append_local(text, kind)
            save_chats(self.chats)

    def _append_local(self, text, kind):
        tstr = self._ts()
        self.messages.append({"time": tstr, "name": self.me_display, "text": text, "kind": kind})
        self._insert_line(tstr, self.me_display, text, kind)

    def _append_net(self, sender, text, ts):
        name = self.net.me["username"] if sender == self.net.me["id"] else self.contact["name"]
        tstr = datetime.datetime.fromtimestamp(ts).strftime("%H:%M")
        self.messages.append({"time": tstr, "name": name, "text": text, "kind": "chat"})
        self._insert_line(tstr, name, text, "chat")

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


class LoginWindow(tk.Toplevel):
    def __init__(self, app=None, on_ready=None):
        super().__init__(app)
        self.configure(bg=BG)
        self.title("Sign in to the network")
        self.resizable(False, False)
        self.transient(app)
        self.grab_set()
        self._on_ready = on_ready

        tk.Label(self, text="App Launcher Network", font=tkfont.Font(family="Segoe UI", size=16, weight="bold"),
                 bg=BG, fg=TEXT).pack(pady=(16, 2))
        tk.Label(self, text="Same server, same people, on any PC.",
                 font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(pady=(0, 12))

        form = tk.Frame(self, bg=BG)
        form.pack(padx=22, pady=(0, 8))

        tk.Label(form, text="Server URL", font=("Segoe UI", 9), bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        self.url_var = tk.StringVar(value=(AppNet.load_session() or {}).get("url", "https://"))
        tk.Entry(form, textvariable=self.url_var, bg=CARD2, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 10), width=40).pack(fill="x", ipady=4, pady=(2, 10))

        tk.Label(form, text="Username", font=("Segoe UI", 9), bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        self.user_var = tk.StringVar()
        tk.Entry(form, textvariable=self.user_var, bg=CARD2, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 10), width=40).pack(fill="x", ipady=4, pady=(2, 10))

        tk.Label(form, text="Password", font=("Segoe UI", 9), bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        self.pass_var = tk.StringVar()
        tk.Entry(form, textvariable=self.pass_var, show="*", bg=CARD2, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 10), width=40).pack(fill="x", ipady=4, pady=(2, 2))

        self.hint = tk.Label(self, text="", font=("Segoe UI", 9), bg=BG, fg=RED, wraplength=340)
        self.hint.pack(pady=(6, 2))

        row = tk.Frame(self, bg=BG)
        row.pack(pady=(4, 16))
        tk.Button(row, text="Sign in", command=self._login, bg=ACC, fg="#ffffff",
                  activebackground=ACC, activeforeground="#ffffff", relief="flat", bd=0,
                  padx=18, pady=7, font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="left", padx=6)
        tk.Button(row, text="Create account", command=self._register, bg=CARD2, fg=TEXT,
                  activebackground="#343c58", activeforeground="#ffffff", relief="flat", bd=0,
                  padx=14, pady=7, font=("Segoe UI", 10), cursor="hand2").pack(side="left", padx=6)
        self.pass_var.trace_add("write", lambda *_: self.hint.config(text=""))

    def _do(self, fn):
        self.hint.config(text="")
        url = self.url_var.get().strip().rstrip("/")
        if not url or url in ("https://", "http://"):
            self.hint.config(text="Enter the server URL first.")
            return
        net = AppNet.Net(url)
        try:
            me = fn(net)
        except AppNet.NetError as e:
            self.hint.config(text=e.message)
            return
        AppNet.save_session(url, net.token, me)
        if self._on_ready:
            self._on_ready()
        self.destroy()

    def _login(self):
        self._do(lambda n: n.login(self.user_var.get().strip(), self.pass_var.get()))

    def _register(self):
        self._do(lambda n: n.register(self.user_var.get().strip(), self.pass_var.get()))


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
                  bg=CARD2, fg=TEXT, activebackground="#343c58", activeforeground="#ffffff",
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

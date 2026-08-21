import json
import os
import webbrowser
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox

FRIENDS_FILE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AppLauncher", "friends.json")

BG = "#12161f"
CARD = "#1d2130"
CARD2 = "#262c40"
TEXT = "#e9ecf5"
MUTED = "#8b93a7"
ACC = "#5865f2"
GREEN = "#43c97f"
RED = "#ff6b6b"


def load_friends():
    try:
        with open(FRIENDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_friends(friends):
    try:
        os.makedirs(os.path.dirname(FRIENDS_FILE), exist_ok=True)
        with open(FRIENDS_FILE, "w", encoding="utf-8") as f:
            json.dump(friends, f, indent=2)
    except Exception:
        pass


def open_discord(user_id):
    url = "discord://-/channels/@me/%s" % user_id
    try:
        os.startfile(url)
        return True
    except Exception:
        pass
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False


class FriendsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Discord Friends")
        self.configure(bg=BG)
        self.geometry("640x540")
        self.minsize(520, 420)
        self.friends = load_friends()
        self._placeholder = True
        self.search_var = tk.StringVar()
        self.search_var.set("Search friends\u2026")
        self.search_var.trace_add("write", lambda *_: self.refresh_list())

        self._build()
        self.refresh_list()

    def _build(self):
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=14, pady=(12, 2))
        tk.Label(bar, text="Discord Friends", font=tkfont.Font(family="Segoe UI", size=16, weight="bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Button(bar, text="+ Add friend", command=self.add_friend, bg=ACC, fg="#ffffff",
                  activebackground=ACC, activeforeground="#ffffff", relief="flat", bd=0,
                  padx=12, pady=5, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right")
        tk.Button(bar, text="Paste list", command=self.paste_list, bg=CARD2, fg=TEXT,
                  activebackground="#343c58", activeforeground="#ffffff", relief="flat", bd=0,
                  padx=10, pady=5, font=("Segoe UI", 9), cursor="hand2").pack(side="right", padx=(0, 6))

        tk.Label(self, text="Text or call by opening their DM \u2014 enable Developer Mode in Discord, "
                            "right-click a friend \u2192 Copy User ID",
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
        self.lb.bind("<Delete>", lambda e: self.delete_friend())

        btns = tk.Frame(self, bg=BG)
        btns.pack(fill="x", padx=14, pady=(0, 8))

        def b(text, cmd, color=CARD2, fg=TEXT, bold=False):
            return tk.Button(btns, text=text, command=cmd, bg=color, fg=fg,
                             activebackground=color, activeforeground=fg, relief="flat", bd=0,
                             padx=12, pady=6, font=("Segoe UI", 9, "bold" if bold else "normal"),
                             cursor="hand2")

        b("Message", self.message, ACC, "#ffffff", True).pack(side="left", padx=(0, 6))
        b("Call", self.call).pack(side="left", padx=(0, 6))
        b("Edit", self.edit_friend).pack(side="left", padx=(0, 6))
        b("Delete", self.delete_friend, RED, "#ffffff").pack(side="right")

        self.status = tk.Label(self, text="", font=("Segoe UI", 9), bg=BG, fg=MUTED, anchor="w")
        self.status.pack(fill="x", padx=14, pady=(0, 10))

    # ---------- search ----------
    def _search_focus_in(self, event=None):
        if self._placeholder:
            self.search_var.set("")
            self._placeholder = False
            self.search.config(fg=TEXT)

    def _search_focus_out(self, event=None):
        if not self.search_var.get():
            self._placeholder = True
            self.search_var.set("Search friends\u2026")
            self.search.config(fg=MUTED)

    # ---------- list ----------
    def _filtered(self):
        q = "" if self._placeholder else self.search_var.get().strip().lower()
        if not q:
            return self.friends
        return [f for f in self.friends if q in f.get("name", "").lower()
                or q in f.get("id", "").lower() or q in f.get("note", "").lower()]

    def refresh_list(self):
        self.lb.delete(0, "end")
        for f in self._filtered():
            note = f.get("note", "")
            self.lb.insert("end", f["name"] + (f"  \u2014  {note}" if note else ""))
        self._update_status_hint()

    def _update_status_hint(self):
        n = len(self._filtered())
        if not self.friends:
            self.status.config(text="No friends yet \u2014 click + Add friend to get started.", fg=MUTED)
        else:
            self.status.config(text=f"{n} friend{'s' if n != 1 else ''}  \u00b7  double-click to message", fg=MUTED)

    def _selected(self):
        sel = self.lb.curselection()
        if not sel:
            return None
        filtered = self._filtered()
        if sel[0] >= len(filtered):
            return None
        return filtered[sel[0]]

    # ---------- actions ----------
    def message(self):
        f = self._selected()
        if not f:
            self.status.config(text="Pick a friend first.", fg=RED)
            return
        if open_discord(f["id"]):
            self.status.config(text=f"Opened DM with {f['name']} \u2014 type away!", fg=GREEN)
        else:
            self.status.config(text="Couldn't open Discord \u2014 is it installed?", fg=RED)

    def call(self):
        f = self._selected()
        if not f:
            self.status.config(text="Pick a friend first.", fg=RED)
            return
        if open_discord(f["id"]):
            self.status.config(text=f"DM with {f['name']} opened \u2014 click the \U0001f4de icon at the top to call!",
                               fg=GREEN)
        else:
            self.status.config(text="Couldn't open Discord \u2014 is it installed?", fg=RED)

    # ---------- add / edit ----------
    def paste_list(self):
        win = tk.Toplevel(self)
        win.title("Paste friend list")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="One friend per line:   Name, Discord ID   (add , note for a note)",
                 font=("Segoe UI", 9), bg=BG, fg=MUTED, anchor="w").pack(fill="x", padx=14, pady=(12, 4))
        txt = tk.Text(win, bg=CARD2, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                      highlightthickness=0, font=("Segoe UI", 10), width=46, height=10)
        txt.pack(padx=14, pady=(0, 8))

        def do_import():
            added = 0
            skipped = 0
            seen = {f["id"] for f in self.friends}
            for line in txt.get("1.0", "end").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 2 or not parts[0] or not parts[1]:
                    continue
                name, uid = parts[0], parts[1]
                note = parts[2] if len(parts) > 2 else ""
                if uid in seen:
                    skipped += 1
                    continue
                seen.add(uid)
                self.friends.append({"name": name, "id": uid, "note": note})
                added += 1
            if added:
                save_friends(self.friends)
                self.refresh_list()
            win.destroy()
            self.status.config(text=f"Imported {added} friend(s)" + (f", {skipped} already there" if skipped else ""),
                               fg=GREEN)

        row = tk.Frame(win, bg=BG)
        row.pack(pady=(0, 14))
        tk.Button(row, text="Cancel", command=win.destroy, bg=CARD2, fg=TEXT,
                  activebackground="#343c58", activeforeground="#ffffff", relief="flat", bd=0,
                  padx=14, pady=6, font=("Segoe UI", 9), cursor="hand2").pack(side="left", padx=4)
        tk.Button(row, text="Import", command=do_import, bg=ACC, fg="#ffffff", activebackground=ACC,
                  activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left", padx=4)

    def add_friend(self):
        self._dialog("Add friend")

    def edit_friend(self):
        f = self._selected()
        if not f:
            self.status.config(text="Pick a friend to edit.", fg=RED)
            return
        self._dialog("Edit friend", f)

    def _dialog(self, title, friend=None):
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
        e_id = field("Discord user ID")
        e_note = field("Note (optional)")
        if friend:
            e_name.insert(0, friend.get("name", ""))
            e_id.insert(0, friend.get("id", ""))
            e_note.insert(0, friend.get("note", ""))

        def save():
            name = e_name.get().strip()
            uid = e_id.get().strip()
            if not name or not uid:
                messagebox.showwarning("Missing info", "Name and Discord user ID are required.", parent=win)
                return
            if friend is None:
                self.friends.append({"name": name, "id": uid, "note": e_note.get().strip()})
            else:
                friend["name"] = name
                friend["id"] = uid
                friend["note"] = e_note.get().strip()
            save_friends(self.friends)
            win.destroy()
            self.refresh_list()
            self.status.config(text=f"Saved {name}.", fg=GREEN)

        row = tk.Frame(win, bg=BG)
        row.pack(pady=(2, 14))
        tk.Button(row, text="Cancel", command=win.destroy, bg=CARD2, fg=TEXT,
                  activebackground="#343c58", activeforeground="#ffffff", relief="flat", bd=0,
                  padx=14, pady=6, font=("Segoe UI", 9), cursor="hand2").pack(side="left", padx=4)
        tk.Button(row, text="Save", command=save, bg=ACC, fg="#ffffff", activebackground=ACC,
                  activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=6,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left", padx=4)
        e_name.focus_set()

    def delete_friend(self):
        f = self._selected()
        if not f:
            self.status.config(text="Pick a friend to delete.", fg=RED)
            return
        if not messagebox.askyesno("Delete friend", f"Remove {f['name']} from your list?", parent=self):
            return
        self.friends = [x for x in self.friends if x is not f]
        save_friends(self.friends)
        self.refresh_list()
        self.status.config(text=f"Removed {f['name']}.", fg=GREEN)


def main():
    app = FriendsApp()
    app.mainloop()


if __name__ == "__main__":
    main()

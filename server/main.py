import hashlib
import os
import secrets
import sqlite3
import time
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "applauncher.db"))

app = FastAPI(title="AppLauncher Network")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            is_owner INTEGER NOT NULL DEFAULT 0,
            banned INTEGER NOT NULL DEFAULT 0,
            created REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS friends (
            user_a TEXT NOT NULL,
            user_b TEXT NOT NULL,
            created REAL NOT NULL,
            PRIMARY KEY (user_a, user_b)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            text TEXT NOT NULL,
            ts REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS calls (
            pair TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            since REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            text TEXT NOT NULL,
            ts REAL NOT NULL,
            seen INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    conn.commit()
    conn.close()


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def new_id() -> str:
    return secrets.token_hex(8)


def now() -> float:
    return time.time()


def get_user_by_username(username: str):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)).fetchone()
    conn.close()
    return row


def get_user(user_id: str):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def pair_key(a: str, b: str) -> str:
    return "|".join(sorted([a, b]))


def auth(authorization: str = Header(None)) -> sqlite3.Row:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not signed in.")
    tok = authorization[7:].strip()
    conn = db()
    row = conn.execute(
        "SELECT u.* FROM tokens t JOIN users u ON u.id = t.user_id WHERE t.token = ?",
        (tok,),
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(401, "Session expired. Sign in again.")
    if row["banned"]:
        raise HTTPException(403, "You have been banned.")
    return row


def owner_guard(user: sqlite3.Row):
    if not user["is_owner"]:
        raise HTTPException(403, "Only the Owner can do that.")


def add_notice(user_id: str, text: str):
    conn = db()
    conn.execute("INSERT INTO notices (user_id, text, ts) VALUES (?, ?, ?)", (user_id, text, now()))
    conn.commit()
    conn.close()


class RegisterIn(BaseModel):
    username: str
    password: str


class LoginIn(BaseModel):
    username: str
    password: str


class UsernameIn(BaseModel):
    username: str


class TargetIn(BaseModel):
    id: str


class MessageIn(BaseModel):
    to: str
    text: str


class CallIn(BaseModel):
    to: str
    action: str


class UserOut:
    @staticmethod
    def json(user):
        return {
            "id": user["id"],
            "username": user["username"],
            "is_owner": bool(user["is_owner"]),
        }


def make_session(user_id: str) -> str:
    tok = secrets.token_hex(24)
    conn = db()
    conn.execute("INSERT INTO tokens (token, user_id, created) VALUES (?, ?, ?)", (tok, user_id, now()))
    conn.commit()
    conn.close()
    return tok


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"app": "AppLauncher Network", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/register")
def register(body: RegisterIn):
    username = (body.username or "").strip()
    password = body.password or ""
    if not (3 <= len(username) <= 24) or not username.replace("_", "").isalnum():
        raise HTTPException(400, "Username must be 3-24 letters/numbers/underscores.")
    if len(password) < 4:
        raise HTTPException(400, "Password must be at least 4 characters.")
    if get_user_by_username(username) is not None:
        raise HTTPException(400, "That username is already taken.")
    user_id = new_id()
    salt = secrets.token_hex(8)
    conn = db()
    total = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    is_owner = 1 if total == 0 else 0
    conn.execute(
        "INSERT INTO users (id, username, password_hash, salt, is_owner, banned, created) "
        "VALUES (?, ?, ?, ?, ?, 0, ?)",
        (user_id, username, hash_password(password, salt), salt, is_owner, now()),
    )
    conn.commit()
    conn.close()
    user = get_user(user_id)
    token = make_session(user_id)
    return {**UserOut.json(user), "token": token}


@app.post("/api/login")
def login(body: LoginIn):
    username = (body.username or "").strip()
    password = body.password or ""
    user = get_user_by_username(username)
    if user is None:
        raise HTTPException(400, "No account with that username.")
    if user["banned"]:
        raise HTTPException(403, "You have been banned.")
    if user["password_hash"] != hash_password(password, user["salt"]):
        raise HTTPException(400, "Wrong password.")
    token = make_session(user["id"])
    return {**UserOut.json(user), "token": token}


@app.post("/api/logout")
def logout(user: sqlite3.Row = Depends(auth)):
    conn = db()
    conn.execute("DELETE FROM tokens WHERE user_id = ?", (user["id"],))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/me")
def me(user: sqlite3.Row = Depends(auth)):
    return UserOut.json(user)


@app.post("/api/users/search")
def search_users(body: UsernameIn, user: sqlite3.Row = Depends(auth)):
    q = (body.username or "").strip()
    if not q:
        return []
    conn = db()
    rows = conn.execute(
        "SELECT id, username FROM users WHERE username LIKE ? COLLATE NOCASE "
        "AND id != ? AND banned = 0 LIMIT 20",
        (f"%{q}%", user["id"]),
    ).fetchall()
    conn.close()
    return [{"id": r["id"], "username": r["username"]} for r in rows]


@app.get("/api/friends")
def list_friends(user: sqlite3.Row = Depends(auth)):
    conn = db()
    rows = conn.execute(
        "SELECT u.id, u.username, u.banned FROM friends f "
        "JOIN users u ON u.id IN (f.user_a, f.user_b) "
        "WHERE (f.user_a = ? OR f.user_b = ?) AND u.id != ?",
        (user["id"], user["id"], user["id"]),
    ).fetchall()
    conn.close()
    return [{"id": r["id"], "username": r["username"], "banned": bool(r["banned"])} for r in rows]


@app.post("/api/friends/add")
def add_friend(body: UsernameIn, user: sqlite3.Row = Depends(auth)):
    target = get_user_by_username(body.username or "")
    if target is None:
        raise HTTPException(404, "No user with that username.")
    if target["id"] == user["id"]:
        raise HTTPException(400, "That's you.")
    if target["banned"]:
        raise HTTPException(403, "That user is banned.")
    a, b = user["id"], target["id"]
    conn = db()
    conn.execute(
        "INSERT OR IGNORE INTO friends (user_a, user_b, created) VALUES (?, ?, ?)",
        (a, b, now()),
    )
    conn.commit()
    conn.close()
    return {"id": target["id"], "username": target["username"]}


@app.post("/api/friends/kick")
def kick(body: TargetIn, user: sqlite3.Row = Depends(auth)):
    owner_guard(user)
    target = get_user(body.id or "")
    if target is None:
        raise HTTPException(404, "User not found.")
    _clear_relationship(user["id"], target["id"])
    _end_call_between(user["id"], target["id"])
    add_notice(target["id"], f"You were kicked by the Owner ({user['username']}).")
    return {"ok": True}


@app.post("/api/ban")
def ban(body: TargetIn, user: sqlite3.Row = Depends(auth)):
    owner_guard(user)
    target = get_user(body.id or "")
    if target is None:
        raise HTTPException(404, "User not found.")
    if target["id"] == user["id"]:
        raise HTTPException(400, "You can't ban yourself.")
    conn = db()
    conn.execute("UPDATE users SET banned = 1 WHERE id = ?", (target["id"],))
    conn.commit()
    conn.close()
    _clear_relationship(user["id"], target["id"])
    _end_call_between(user["id"], target["id"])
    add_notice(target["id"], "You have been banned by the Owner.")
    return {"ok": True}


@app.post("/api/unban")
def unban(body: TargetIn, user: sqlite3.Row = Depends(auth)):
    owner_guard(user)
    target = get_user(body.id or "")
    if target is None:
        raise HTTPException(404, "User not found.")
    conn = db()
    conn.execute("UPDATE users SET banned = 0 WHERE id = ?", (target["id"],))
    conn.commit()
    conn.close()
    add_notice(target["id"], "Your ban has been lifted.")
    return {"ok": True}


@app.get("/api/bans")
def list_bans(user: sqlite3.Row = Depends(auth)):
    owner_guard(user)
    conn = db()
    rows = conn.execute("SELECT id, username FROM users WHERE banned = 1").fetchall()
    conn.close()
    return [{"id": r["id"], "username": r["username"]} for r in rows]


@app.get("/api/messages")
def get_messages(with_user: str, after: float = 0, user: sqlite3.Row = Depends(auth)):
    conn = db()
    rows = conn.execute(
        "SELECT id, sender, recipient, text, ts FROM messages "
        "WHERE ((sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?)) AND ts > ? "
        "ORDER BY ts ASC",
        (user["id"], with_user, with_user, user["id"], after),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "sender": r["sender"],
            "recipient": r["recipient"],
            "text": r["text"],
            "ts": r["ts"],
        }
        for r in rows
    ]


@app.post("/api/messages/send")
def send_message(body: MessageIn, user: sqlite3.Row = Depends(auth)):
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(400, "Empty message.")
    if len(text) > 2000:
        raise HTTPException(400, "Message too long.")
    recipient = get_user(body.to or "")
    if recipient is None:
        raise HTTPException(404, "User not found.")
    if recipient["banned"]:
        raise HTTPException(403, "That user is banned.")
    conn = db()
    linked = conn.execute(
        "SELECT 1 FROM friends WHERE (user_a = ? AND user_b = ?) OR (user_a = ? AND user_b = ?)",
        (user["id"], recipient["id"], recipient["id"], user["id"]),
    ).fetchone()
    if linked is None:
        conn.close()
        raise HTTPException(403, "You aren't connected to that user.")
    conn.execute(
        "INSERT INTO messages (sender, recipient, text, ts) VALUES (?, ?, ?, ?)",
        (user["id"], recipient["id"], text, now()),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/api/call")
def call(body: CallIn, user: sqlite3.Row = Depends(auth)):
    action = body.action
    if action not in ("start", "accept", "end"):
        raise HTTPException(400, "Bad action.")
    recipient = get_user(body.to or "")
    if recipient is None:
        raise HTTPException(404, "User not found.")
    if recipient["banned"]:
        raise HTTPException(403, "That user is banned.")
    pk = pair_key(user["id"], recipient["id"])
    conn = db()
    if action == "start":
        conn.execute(
            "INSERT INTO calls (pair, state, since) VALUES (?, 'calling', ?) "
            "ON CONFLICT(pair) DO UPDATE SET state='calling', since=?",
            (pk, now(), now()),
        )
    elif action == "accept":
        conn.execute(
            "INSERT INTO calls (pair, state, since) VALUES (?, 'live', ?) "
            "ON CONFLICT(pair) DO UPDATE SET state='live', since=?",
            (pk, now(), now()),
        )
    else:
        conn.execute(
            "INSERT INTO calls (pair, state, since) VALUES (?, 'ended', ?) "
            "ON CONFLICT(pair) DO UPDATE SET state='ended', since=?",
            (pk, now(), now()),
        )
    conn.commit()
    conn.close()
    return {"state": action_to_state(action)}


def action_to_state(action: str) -> str:
    return {"start": "calling", "accept": "live", "end": "ended"}[action]


@app.get("/api/call")
def get_call(with_user: str, user: sqlite3.Row = Depends(auth)):
    pk = pair_key(user["id"], with_user)
    conn = db()
    row = conn.execute("SELECT state, since FROM calls WHERE pair = ?", (pk,)).fetchone()
    conn.close()
    if row is None:
        return {"state": "none", "since": 0}
    return {"state": row["state"], "since": row["since"]}


@app.get("/api/notices")
def get_notices(user: sqlite3.Row = Depends(auth)):
    conn = db()
    rows = conn.execute(
        "SELECT id, text, ts FROM notices WHERE user_id = ? ORDER BY id ASC", (user["id"],)
    ).fetchall()
    conn.execute("DELETE FROM notices WHERE user_id = ?", (user["id"],))
    conn.commit()
    conn.close()
    return [{"id": r["id"], "text": r["text"], "ts": r["ts"]} for r in rows]


def _clear_relationship(a: str, b: str):
    conn = db()
    conn.execute(
        "DELETE FROM friends WHERE (user_a = ? AND user_b = ?) OR (user_a = ? AND user_b = ?)",
        (a, b, b, a),
    )
    conn.execute(
        "DELETE FROM messages WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?)",
        (a, b, b, a),
    )
    conn.commit()
    conn.close()


def _end_call_between(a: str, b: str):
    pk = pair_key(a, b)
    conn = db()
    conn.execute(
        "INSERT INTO calls (pair, state, since) VALUES (?, 'ended', ?) "
        "ON CONFLICT(pair) DO UPDATE SET state='ended', since=?",
        (pk, now(), now()),
    )
    conn.commit()
    conn.close()

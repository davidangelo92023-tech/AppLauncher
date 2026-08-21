import hashlib
import json
import os
import secrets
import time
from typing import Any, Optional

import psycopg2
import psycopg2.extras
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

DATABASE_URL = os.environ.get("DATABASE_URL")

app = FastAPI(title="AppLauncher Network")


def db():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Point it at your Postgres connection "
            "string (e.g. from Neon) as an environment variable."
        )
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def execute(conn, sql, params=()):
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            is_owner BOOLEAN NOT NULL DEFAULT FALSE,
            banned BOOLEAN NOT NULL DEFAULT FALSE,
            created DOUBLE PRECISION NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower_idx ON users (LOWER(username));
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created DOUBLE PRECISION NOT NULL
        );
        CREATE TABLE IF NOT EXISTS friends (
            user_a TEXT NOT NULL,
            user_b TEXT NOT NULL,
            created DOUBLE PRECISION NOT NULL,
            PRIMARY KEY (user_a, user_b)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            text TEXT NOT NULL,
            ts DOUBLE PRECISION NOT NULL
        );
        CREATE TABLE IF NOT EXISTS calls (
            pair TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            since DOUBLE PRECISION NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notices (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            text TEXT NOT NULL,
            ts DOUBLE PRECISION NOT NULL,
            seen BOOLEAN NOT NULL DEFAULT FALSE
        );
        CREATE TABLE IF NOT EXISTS settings (
            user_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            updated DOUBLE PRECISION NOT NULL
        );
        CREATE TABLE IF NOT EXISTS mod_log (
            id SERIAL PRIMARY KEY,
            actor_id TEXT NOT NULL,
            actor_username TEXT NOT NULL,
            action TEXT NOT NULL,
            target_id TEXT NOT NULL,
            target_username TEXT NOT NULL,
            reason TEXT,
            ts DOUBLE PRECISION NOT NULL
        );
        """
    )
    # Migration: users existed before is_admin/role did, so CREATE TABLE IF
    # NOT EXISTS above won't add these to an already-running database.
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;")
    # Replaces the old is_admin boolean with a proper role ladder (member <
    # trial_mod < mod < co_owner < owner). is_admin is left in place, unused,
    # rather than dropped - harmless, and avoids a destructive migration.
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'member';")
    conn.commit()
    conn.close()


def add_mod_log(actor: Any, action: str, target: Any, reason: Optional[str] = None):
    """Records a moderation action (kick/ban/unban/role change) so the Owner
    can review a history of who did what to whom, from the Special Menu."""
    conn = db()
    execute(
        conn,
        "INSERT INTO mod_log (actor_id, actor_username, action, target_id, target_username, reason, ts) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (actor["id"], actor["username"], action, target["id"], target["username"],
         (reason or "").strip()[:500] or None, now()),
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
    row = execute(conn, "SELECT * FROM users WHERE LOWER(username) = LOWER(%s)", (username,)).fetchone()
    conn.close()
    return row


def get_user(user_id: str):
    conn = db()
    row = execute(conn, "SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()
    conn.close()
    return row


def pair_key(a: str, b: str) -> str:
    return "|".join(sorted([a, b]))


def auth(authorization: str = Header(None), x_client_version: Optional[str] = Header(None)) -> Any:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not signed in.")
    tok = authorization[7:].strip()
    if _version_tuple(x_client_version) < _version_tuple(MIN_CLIENT_VERSION):
        # Don't just refuse this one call - revoke the session outright so an
        # already-signed-in old client gets logged out immediately (its next
        # request of any kind fails), not merely blocked from a fresh login.
        conn = db()
        execute(conn, "DELETE FROM tokens WHERE token = %s", (tok,))
        conn.commit()
        conn.close()
        check_client_version(x_client_version)  # raises the 426 with the update message
    conn = db()
    row = execute(
        conn,
        "SELECT u.* FROM tokens t JOIN users u ON u.id = t.user_id WHERE t.token = %s",
        (tok,),
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(401, "Session expired. Sign in again.")
    if row["banned"]:
        raise HTTPException(403, "You have been banned.")
    return row


# The one account allowed to hold Owner powers, pinned by username rather
# than trusting the "first account ever registered" flag alone - so a
# database reset, a race at registration time, or any other account never
# ends up with Kick/Ban access.
OWNER_USERNAME = "ash"


def is_owner_user(user: Any) -> bool:
    return (user.get("username") or "").strip().lower() == OWNER_USERNAME


# Role ladder, lowest to highest. "owner" is never stored in the database -
# it's purely derived from OWNER_USERNAME above - so it can never be granted,
# revoked, or lost to a database bug or reset.
ROLE_RANK = {"member": 0, "trial_mod": 1, "mod": 2, "co_owner": 3}
VALID_ROLES = ("member", "trial_mod", "mod", "co_owner")


def user_role(user: Any) -> str:
    if is_owner_user(user):
        return "owner"
    r = user.get("role") or "member"
    return r if r in VALID_ROLES else "member"


def user_rank(user: Any) -> int:
    if is_owner_user(user):
        return 4
    return ROLE_RANK.get(user.get("role") or "member", 0)


def is_admin_user(user: Any) -> bool:
    # "Admin" now means anyone with elevated standing at all (rank >= 1:
    # Trial Mod, Mod, Co-Owner, or the Owner) - kept for backward
    # compatibility with anything still checking this instead of a rank.
    return user_rank(user) >= 1


def owner_guard(user: Any):
    # Only the Owner - never anyone else, at any rank - can grant/revoke
    # roles or manage the ban list, so no role can be used to chain into
    # granting more roles.
    if not is_owner_user(user):
        raise HTTPException(403, "Only the Owner can do that.")


def kick_guard(user: Any):
    # Trial Mod and up can kick.
    if user_rank(user) < 1:
        raise HTTPException(403, "Only the Owner or a moderator can do that.")


def ban_guard(user: Any):
    # Mod and up can ban/unban.
    if user_rank(user) < 2:
        raise HTTPException(403, "Only the Owner, Co-Owner, or a Mod can do that.")


def banlist_guard(user: Any):
    # Co-Owner and up can see/manage the full ban list.
    if user_rank(user) < 3:
        raise HTTPException(403, "Only the Owner or a Co-Owner can do that.")


def protect_target(actor: Any, target: Any):
    # Guards who a moderation action can be pointed AT, separate from who's
    # allowed to act. The Owner can never be kicked/banned by anyone, and
    # nobody can act on someone at or above their own rank - only a strictly
    # higher rank can act on a lower one - so no one can turn on the Owner,
    # on an equal, or on someone above them.
    if is_owner_user(target):
        raise HTTPException(403, "The Owner can't be kicked or banned.")
    if user_rank(target) >= user_rank(actor):
        raise HTTPException(403, "You can't act on someone at or above your own rank.")


# Minimum app version allowed to sign in. Bump this together with the root
# VERSION file and AppNet.CLIENT_VERSION whenever you push a fix (like a
# security fix) that older, un-patched copies must not keep operating past -
# they'll be told to update instead of being allowed to authenticate. Leave
# it matching the current release in normal times; a client that's merely
# one point release behind but not otherwise unsafe doesn't need blocking.
MIN_CLIENT_VERSION = "1.1.0"


def _version_tuple(v: Any):
    try:
        return tuple(int(p) for p in str(v).strip().split("."))
    except Exception:
        return (0,)


def check_client_version(client_version: Any):
    # A missing/unparseable version means a copy of the app old enough to
    # predate this check existing at all - exactly the case that most needs
    # to be blocked, so it's treated as version (0,), always below minimum.
    if _version_tuple(client_version) < _version_tuple(MIN_CLIENT_VERSION):
        raise HTTPException(
            426,
            f"This copy of App Launcher is out of date and can't sign in until it's "
            f"updated (need v{MIN_CLIENT_VERSION} or newer). Open App Launcher and "
            f"click the \"Update available\" link in the bottom-right corner, or "
            f"download the latest version from "
            f"https://github.com/davidangelo92023-tech/AppLauncher.",
        )


def add_notice(user_id: str, text: str):
    conn = db()
    execute(conn, "INSERT INTO notices (user_id, text, ts) VALUES (%s, %s, %s)", (user_id, text, now()))
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
    reason: Optional[str] = None


class MessageIn(BaseModel):
    to: str
    text: str


class CallIn(BaseModel):
    to: str
    action: str


class SettingsIn(BaseModel):
    data: dict


class RoleIn(BaseModel):
    id: str
    role: str
    reason: Optional[str] = None


class UserOut:
    @staticmethod
    def json(user):
        return {
            "id": user["id"],
            "username": user["username"],
            "is_owner": is_owner_user(user),
            "is_admin": is_admin_user(user),
            "role": user_role(user),
        }


def make_session(user_id: str) -> str:
    tok = secrets.token_hex(24)
    conn = db()
    execute(conn, "INSERT INTO tokens (token, user_id, created) VALUES (%s, %s, %s)", (tok, user_id, now()))
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
def register(body: RegisterIn, x_client_version: Optional[str] = Header(None)):
    check_client_version(x_client_version)
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
    total = execute(conn, "SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    is_owner = total == 0
    execute(
        conn,
        "INSERT INTO users (id, username, password_hash, salt, is_owner, banned, created) "
        "VALUES (%s, %s, %s, %s, %s, FALSE, %s)",
        (user_id, username, hash_password(password, salt), salt, is_owner, now()),
    )
    conn.commit()
    conn.close()
    user = get_user(user_id)
    token = make_session(user_id)
    return {**UserOut.json(user), "token": token}


@app.post("/api/login")
def login(body: LoginIn, x_client_version: Optional[str] = Header(None)):
    check_client_version(x_client_version)
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
def logout(user: Any = Depends(auth)):
    conn = db()
    execute(conn, "DELETE FROM tokens WHERE user_id = %s", (user["id"],))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/me")
def me(user: Any = Depends(auth)):
    return UserOut.json(user)


@app.post("/api/users/search")
def search_users(body: UsernameIn, user: Any = Depends(auth)):
    q = (body.username or "").strip()
    if not q:
        return []
    conn = db()
    rows = execute(
        conn,
        "SELECT id, username FROM users WHERE username ILIKE %s "
        "AND id != %s AND banned = FALSE LIMIT 20",
        (f"%{q}%", user["id"]),
    ).fetchall()
    conn.close()
    return [{"id": r["id"], "username": r["username"]} for r in rows]


@app.get("/api/friends")
def list_friends(user: Any = Depends(auth)):
    conn = db()
    rows = execute(
        conn,
        "SELECT u.id, u.username, u.banned, u.is_admin, u.role FROM friends f "
        "JOIN users u ON u.id IN (f.user_a, f.user_b) "
        "WHERE (f.user_a = %s OR f.user_b = %s) AND u.id != %s",
        (user["id"], user["id"], user["id"]),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "username": r["username"],
            "banned": bool(r["banned"]),
            "is_admin": is_admin_user(r),
            "role": user_role(r),
        }
        for r in rows
    ]


@app.post("/api/friends/add")
def add_friend(body: UsernameIn, user: Any = Depends(auth)):
    target = get_user_by_username(body.username or "")
    if target is None:
        raise HTTPException(404, "No user with that username.")
    if target["id"] == user["id"]:
        raise HTTPException(400, "That's you.")
    if target["banned"]:
        raise HTTPException(403, "That user is banned.")
    a, b = user["id"], target["id"]
    conn = db()
    execute(
        conn,
        "INSERT INTO friends (user_a, user_b, created) VALUES (%s, %s, %s) "
        "ON CONFLICT (user_a, user_b) DO NOTHING",
        (a, b, now()),
    )
    conn.commit()
    conn.close()
    return {"id": target["id"], "username": target["username"]}


@app.post("/api/friends/kick")
def kick(body: TargetIn, user: Any = Depends(auth)):
    # Trial Mod and up can kick, but protect_target still stops anyone from
    # kicking the Owner or someone at/above their own rank.
    kick_guard(user)
    target = get_user(body.id or "")
    if target is None:
        raise HTTPException(404, "User not found.")
    protect_target(user, target)
    _clear_relationship(user["id"], target["id"])
    _end_call_between(user["id"], target["id"])
    kicker = "the Owner" if is_owner_user(user) else user_role(user).replace("_", "-").title()
    reason = (body.reason or "").strip()
    suffix = f" Reason: {reason}" if reason else ""
    add_notice(target["id"], f"You were kicked by {kicker} ({user['username']}).{suffix}")
    add_mod_log(user, "kick", target, reason)
    return {"ok": True}


@app.post("/api/ban")
def ban(body: TargetIn, user: Any = Depends(auth)):
    # Mod and up can ban, but protect_target still stops anyone from
    # banning the Owner or someone at/above their own rank.
    ban_guard(user)
    target = get_user(body.id or "")
    if target is None:
        raise HTTPException(404, "User not found.")
    if target["id"] == user["id"]:
        raise HTTPException(400, "You can't ban yourself.")
    protect_target(user, target)
    conn = db()
    execute(conn, "UPDATE users SET banned = TRUE WHERE id = %s", (target["id"],))
    conn.commit()
    conn.close()
    _clear_relationship(user["id"], target["id"])
    _end_call_between(user["id"], target["id"])
    banner = "the Owner" if is_owner_user(user) else user_role(user).replace("_", "-").title()
    reason = (body.reason or "").strip()
    suffix = f" Reason: {reason}" if reason else ""
    add_notice(target["id"], f"You have been banned by {banner} ({user['username']}).{suffix}")
    add_mod_log(user, "ban", target, reason)
    return {"ok": True}


@app.post("/api/unban")
def unban(body: TargetIn, user: Any = Depends(auth)):
    ban_guard(user)
    target = get_user(body.id or "")
    if target is None:
        raise HTTPException(404, "User not found.")
    conn = db()
    execute(conn, "UPDATE users SET banned = FALSE WHERE id = %s", (target["id"],))
    conn.commit()
    conn.close()
    add_notice(target["id"], "Your ban has been lifted.")
    add_mod_log(user, "unban", target, (body.reason or "").strip())
    return {"ok": True}


@app.get("/api/bans")
def list_bans(user: Any = Depends(auth)):
    # Full ban-list visibility is Co-Owner and up, per the permission tiers.
    banlist_guard(user)
    conn = db()
    rows = execute(conn, "SELECT id, username FROM users WHERE banned = TRUE").fetchall()
    conn.close()
    return [{"id": r["id"], "username": r["username"]} for r in rows]


@app.post("/api/roles/set")
def set_role(body: RoleIn, user: Any = Depends(auth)):
    # Owner-only: nobody else can grant or revoke any role, ever - so no
    # role can be used to chain into granting more roles. This replaces the
    # old /api/admin/grant and /api/admin/revoke endpoints with a single
    # endpoint that covers the whole Trial Mod / Mod / Co-Owner ladder.
    owner_guard(user)
    role = (body.role or "").strip().lower()
    if role not in VALID_ROLES:
        raise HTTPException(400, f"Role must be one of: {', '.join(VALID_ROLES)}.")
    target = get_user(body.id or "")
    if target is None:
        raise HTTPException(404, "User not found.")
    if is_owner_user(target):
        raise HTTPException(400, "That account is already the Owner.")
    conn = db()
    execute(conn, "UPDATE users SET role = %s WHERE id = %s", (role, target["id"]))
    conn.commit()
    conn.close()
    updated = get_user(target["id"])
    reason = (body.reason or "").strip()
    suffix = f" Reason: {reason}" if reason else ""
    if role == "member":
        add_notice(target["id"], f"Your role was reset by the Owner ({user['username']}).{suffix}")
    else:
        label = role.replace("_", "-").title()
        add_notice(target["id"], f"You were made {label} by the Owner ({user['username']}).{suffix}")
    add_mod_log(user, f"role:{role}", target, reason)
    return UserOut.json(updated)


@app.post("/api/owner/search")
def owner_search(body: UsernameIn, user: Any = Depends(auth)):
    # Owner-only lookup that, unlike /api/users/search, isn't limited to
    # friends and includes banned accounts - this is what powers the
    # special menu's "find people" box.
    owner_guard(user)
    q = (body.username or "").strip()
    if not q:
        return []
    conn = db()
    rows = execute(
        conn,
        "SELECT id, username, banned, is_admin, role FROM users WHERE username ILIKE %s LIMIT 25",
        (f"%{q}%",),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "username": r["username"],
            "banned": bool(r["banned"]),
            "is_owner": is_owner_user(r),
            "role": user_role(r),
        }
        for r in rows
    ]


@app.get("/api/owner/modlog")
def owner_modlog(user: Any = Depends(auth)):
    # Owner-only: a running history of kicks/bans/unbans/role changes, most
    # recent first, so the Owner can review what's happened without having
    # to remember it all. Capped at the last 200 entries.
    owner_guard(user)
    conn = db()
    rows = execute(
        conn,
        "SELECT actor_username, action, target_username, reason, ts FROM mod_log "
        "ORDER BY id DESC LIMIT 200",
    ).fetchall()
    conn.close()
    return [
        {
            "actor": r["actor_username"],
            "action": r["action"],
            "target": r["target_username"],
            "reason": r["reason"] or "",
            "ts": r["ts"],
        }
        for r in rows
    ]


@app.get("/api/messages")
def get_messages(with_user: str, after: float = 0, user: Any = Depends(auth)):
    conn = db()
    rows = execute(
        conn,
        "SELECT id, sender, recipient, text, ts FROM messages "
        "WHERE ((sender = %s AND recipient = %s) OR (sender = %s AND recipient = %s)) AND ts > %s "
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
def send_message(body: MessageIn, user: Any = Depends(auth)):
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
    linked = execute(
        conn,
        "SELECT 1 FROM friends WHERE (user_a = %s AND user_b = %s) OR (user_a = %s AND user_b = %s)",
        (user["id"], recipient["id"], recipient["id"], user["id"]),
    ).fetchone()
    if linked is None:
        conn.close()
        raise HTTPException(403, "You aren't connected to that user.")
    execute(
        conn,
        "INSERT INTO messages (sender, recipient, text, ts) VALUES (%s, %s, %s, %s)",
        (user["id"], recipient["id"], text, now()),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/api/call")
def call(body: CallIn, user: Any = Depends(auth)):
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
        execute(
            conn,
            "INSERT INTO calls (pair, state, since) VALUES (%s, 'calling', %s) "
            "ON CONFLICT (pair) DO UPDATE SET state='calling', since=%s",
            (pk, now(), now()),
        )
    elif action == "accept":
        execute(
            conn,
            "INSERT INTO calls (pair, state, since) VALUES (%s, 'live', %s) "
            "ON CONFLICT (pair) DO UPDATE SET state='live', since=%s",
            (pk, now(), now()),
        )
    else:
        execute(
            conn,
            "INSERT INTO calls (pair, state, since) VALUES (%s, 'ended', %s) "
            "ON CONFLICT (pair) DO UPDATE SET state='ended', since=%s",
            (pk, now(), now()),
        )
    conn.commit()
    conn.close()
    return {"state": action_to_state(action)}


def action_to_state(action: str) -> str:
    return {"start": "calling", "accept": "live", "end": "ended"}[action]


@app.get("/api/call")
def get_call(with_user: str, user: Any = Depends(auth)):
    pk = pair_key(user["id"], with_user)
    conn = db()
    row = execute(conn, "SELECT state, since FROM calls WHERE pair = %s", (pk,)).fetchone()
    conn.close()
    if row is None:
        return {"state": "none", "since": 0}
    return {"state": row["state"], "since": row["since"]}


@app.get("/api/notices")
def get_notices(user: Any = Depends(auth)):
    conn = db()
    rows = execute(
        conn, "SELECT id, text, ts FROM notices WHERE user_id = %s ORDER BY id ASC", (user["id"],)
    ).fetchall()
    execute(conn, "DELETE FROM notices WHERE user_id = %s", (user["id"],))
    conn.commit()
    conn.close()
    return [{"id": r["id"], "text": r["text"], "ts": r["ts"]} for r in rows]


@app.get("/api/settings")
def get_settings(user: Any = Depends(auth)):
    conn = db()
    row = execute(conn, "SELECT data, updated FROM settings WHERE user_id = %s", (user["id"],)).fetchone()
    conn.close()
    if row is None:
        return {"data": None, "updated": 0}
    try:
        data = json.loads(row["data"])
    except Exception:
        data = None
    return {"data": data, "updated": row["updated"]}


@app.post("/api/settings")
def set_settings(body: SettingsIn, user: Any = Depends(auth)):
    payload = json.dumps(body.data)
    if len(payload) > 200_000:
        raise HTTPException(400, "Settings payload too large.")
    conn = db()
    execute(
        conn,
        "INSERT INTO settings (user_id, data, updated) VALUES (%s, %s, %s) "
        "ON CONFLICT (user_id) DO UPDATE SET data = %s, updated = %s",
        (user["id"], payload, now(), payload, now()),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "updated": now()}


def _clear_relationship(a: str, b: str):
    conn = db()
    execute(
        conn,
        "DELETE FROM friends WHERE (user_a = %s AND user_b = %s) OR (user_a = %s AND user_b = %s)",
        (a, b, b, a),
    )
    execute(
        conn,
        "DELETE FROM messages WHERE (sender = %s AND recipient = %s) OR (sender = %s AND recipient = %s)",
        (a, b, b, a),
    )
    conn.commit()
    conn.close()


def _end_call_between(a: str, b: str):
    pk = pair_key(a, b)
    conn = db()
    execute(
        conn,
        "INSERT INTO calls (pair, state, since) VALUES (%s, 'ended', %s) "
        "ON CONFLICT (pair) DO UPDATE SET state='ended', since=%s",
        (pk, now(), now()),
    )
    conn.commit()
    conn.close()

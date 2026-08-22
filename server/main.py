import hashlib
import json
import os
import re
import secrets
import smtplib
import time
from email.mime.text import MIMEText
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
    # 0 (or NULL, for rows from before this column existed) means "not
    # muted"; otherwise a unix timestamp the mute expires at.
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS muted_until DOUBLE PRECISION NOT NULL DEFAULT 0;")
    # Email verification. email_verified defaults to TRUE so every account
    # that already existed before this feature shipped keeps working exactly
    # as before - only brand-new registrations get created with it FALSE and
    # have to confirm a code before they can sign in.
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT TRUE;")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verify_code TEXT;")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verify_code_expires DOUBLE PRECISION NOT NULL DEFAULT 0;")
    # 0 means "permanent once banned" (the original behavior - stays banned
    # until an explicit Unban); a nonzero value is a timestamp the ban
    # expires at, for timed bans.
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS banned_until DOUBLE PRECISION NOT NULL DEFAULT 0;")
    conn.commit()
    conn.close()


def expire_stale_bans():
    """Timed bans don't get their own background job - instead, every
    authenticated request (via auth() below) sweeps the whole table for any
    ban whose timer has run out and clears it. Cheap at this app's scale,
    and it means every other query that reads the plain `banned` column
    (friend search, the ban list, etc.) stays correct without each of them
    needing to know about banned_until."""
    conn = db()
    execute(
        conn,
        "UPDATE users SET banned = FALSE, banned_until = 0 "
        "WHERE banned = TRUE AND banned_until <> 0 AND banned_until < %s",
        (now(),),
    )
    conn.commit()
    conn.close()


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Gmail SMTP with an App Password is the default (matches the Owner's own
# Gmail account), but any SMTP provider works - just set these on Render the
# same way DATABASE_URL was set. If they're not set, registration still
# works but the code is only logged server-side (visible in Render's Events
# log), not emailed - useful for local testing, not for real use.
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
SMTP_FROM = os.environ.get("SMTP_FROM") or SMTP_USER


def send_verification_email(to_email: str, code: str, username: str):
    if not (SMTP_USER and SMTP_PASS):
        print(f"[email] SMTP not configured - verification code for {username} <{to_email}> is {code}")
        return
    msg = MIMEText(
        f"Hi {username},\n\n"
        f"Your App Launcher verification code is: {code}\n\n"
        f"Enter this code in App Launcher to finish creating your account. "
        f"It expires in 15 minutes.\n\n"
        f"If you didn't try to create an App Launcher account, you can safely ignore this email."
    )
    msg["Subject"] = "Your App Launcher verification code"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_FROM, [to_email], msg.as_string())
    except Exception as e:
        # Don't let a flaky mail provider break registration - the account
        # still exists, the user (or a resend) just needs SMTP working.
        print(f"[email] Failed to send verification email to {to_email}: {e}")


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
    expire_stale_bans()
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


# Muting is the same tier as kicking (Trial Mod and up) - it's a lighter
# touch than a kick, so it doesn't need a higher bar.
mute_guard = kick_guard


def is_muted(user: Any) -> bool:
    return (user.get("muted_until") or 0) > now()


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
    email: str


class LoginIn(BaseModel):
    username: str
    password: str


class VerifyEmailIn(BaseModel):
    username: str
    code: str


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


class MuteIn(BaseModel):
    id: str
    minutes: int
    reason: Optional[str] = None


class BanIn(BaseModel):
    id: str
    minutes: Optional[int] = 0  # 0 or omitted = permanent, like before
    reason: Optional[str] = None


class WarnIn(BaseModel):
    id: str
    reason: str


class BroadcastIn(BaseModel):
    text: str


class UserOut:
    @staticmethod
    def json(user):
        return {
            "id": user["id"],
            "username": user["username"],
            "is_owner": is_owner_user(user),
            "is_admin": is_admin_user(user),
            "role": user_role(user),
            "muted_until": user.get("muted_until") or 0,
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
    email = (body.email or "").strip()
    if not (3 <= len(username) <= 24) or not username.replace("_", "").isalnum():
        raise HTTPException(400, "Username must be 3-24 letters/numbers/underscores.")
    if len(password) < 4:
        raise HTTPException(400, "Password must be at least 4 characters.")
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Enter a valid email address.")
    if get_user_by_username(username) is not None:
        raise HTTPException(400, "That username is already taken.")
    user_id = new_id()
    salt = secrets.token_hex(8)
    conn = db()
    # Only block on emails already confirmed by another account - two
    # abandoned, never-verified signups sharing an email is a harmless edge
    # case, not worth a hard uniqueness constraint.
    taken = execute(
        conn, "SELECT 1 FROM users WHERE LOWER(email) = LOWER(%s) AND email_verified = TRUE", (email,)
    ).fetchone()
    if taken:
        conn.close()
        raise HTTPException(400, "An account with that email already exists.")
    total = execute(conn, "SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    is_owner = total == 0
    code = f"{secrets.randbelow(1000000):06d}"
    execute(
        conn,
        "INSERT INTO users (id, username, password_hash, salt, is_owner, banned, created, "
        "email, email_verified, verify_code, verify_code_expires) "
        "VALUES (%s, %s, %s, %s, %s, FALSE, %s, %s, FALSE, %s, %s)",
        (user_id, username, hash_password(password, salt), salt, is_owner, now(),
         email, code, now() + 15 * 60),
    )
    conn.commit()
    conn.close()
    send_verification_email(email, code, username)
    # No token yet - the account can't sign in until the code below is
    # confirmed via /api/verify-email.
    return {"pending_verification": True, "id": user_id, "username": username, "email": email}


@app.post("/api/verify-email")
def verify_email(body: VerifyEmailIn, x_client_version: Optional[str] = Header(None)):
    check_client_version(x_client_version)
    username = (body.username or "").strip()
    code = (body.code or "").strip()
    user = get_user_by_username(username)
    if user is None:
        raise HTTPException(400, "No account with that username.")
    if user["email_verified"]:
        # Already confirmed (e.g. a double-submit) - just sign them in.
        token = make_session(user["id"])
        return {**UserOut.json(user), "token": token}
    if not code or (user.get("verify_code") or "") != code:
        raise HTTPException(400, "That code isn't right. Check your email and try again.")
    if (user.get("verify_code_expires") or 0) < now():
        raise HTTPException(400, "That code has expired. Request a new one and try again.")
    conn = db()
    execute(conn, "UPDATE users SET email_verified = TRUE, verify_code = NULL WHERE id = %s", (user["id"],))
    conn.commit()
    conn.close()
    user = get_user(user["id"])
    token = make_session(user["id"])
    return {**UserOut.json(user), "token": token}


@app.post("/api/resend-code")
def resend_code(body: UsernameIn, x_client_version: Optional[str] = Header(None)):
    check_client_version(x_client_version)
    username = (body.username or "").strip()
    user = get_user_by_username(username)
    if user is None:
        raise HTTPException(400, "No account with that username.")
    if user["email_verified"]:
        return {"ok": True, "already_verified": True}
    if not user.get("email"):
        raise HTTPException(400, "This account has no email on file.")
    code = f"{secrets.randbelow(1000000):06d}"
    conn = db()
    execute(conn, "UPDATE users SET verify_code = %s, verify_code_expires = %s WHERE id = %s",
            (code, now() + 15 * 60, user["id"]))
    conn.commit()
    conn.close()
    send_verification_email(user["email"], code, user["username"])
    return {"ok": True}


@app.post("/api/login")
def login(body: LoginIn, x_client_version: Optional[str] = Header(None)):
    check_client_version(x_client_version)
    expire_stale_bans()
    username = (body.username or "").strip()
    password = body.password or ""
    user = get_user_by_username(username)
    if user is None:
        raise HTTPException(400, "No account with that username.")
    if user["banned"]:
        raise HTTPException(403, "You have been banned.")
    if user["password_hash"] != hash_password(password, user["salt"]):
        raise HTTPException(400, "Wrong password.")
    if not user["email_verified"]:
        # 428 ("Precondition Required") rather than a generic 400/403, so the
        # client can tell "wrong password" apart from "right password, but
        # this account still needs its email confirmed" and route the user
        # straight to the code-entry step instead of just showing an error.
        raise HTTPException(428, "Confirm your email before signing in - check your inbox for the code, or request a new one.")
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
        "SELECT u.id, u.username, u.banned, u.is_admin, u.role, u.muted_until FROM friends f "
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
            "muted": is_muted(r),
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
def ban(body: BanIn, user: Any = Depends(auth)):
    # Mod and up can ban, but protect_target still stops anyone from
    # banning the Owner or someone at/above their own rank.
    ban_guard(user)
    target = get_user(body.id or "")
    if target is None:
        raise HTTPException(404, "User not found.")
    if target["id"] == user["id"]:
        raise HTTPException(400, "You can't ban yourself.")
    protect_target(user, target)
    # minutes <= 0 (or omitted) means a permanent ban, same as before this
    # feature existed - banned_until stays 0 and only an explicit Unban
    # lifts it. A positive value expires on its own (see expire_stale_bans).
    minutes = max(0, int(body.minutes or 0))
    minutes = min(minutes, 365 * 24 * 60)  # cap at 1 year, just to be safe
    until = now() + minutes * 60 if minutes > 0 else 0
    conn = db()
    execute(conn, "UPDATE users SET banned = TRUE, banned_until = %s WHERE id = %s", (until, target["id"]))
    conn.commit()
    conn.close()
    _clear_relationship(user["id"], target["id"])
    _end_call_between(user["id"], target["id"])
    banner = "the Owner" if is_owner_user(user) else user_role(user).replace("_", "-").title()
    reason = (body.reason or "").strip()
    suffix = f" Reason: {reason}" if reason else ""
    when = f" for {minutes} minute(s)" if until else ""
    add_notice(target["id"], f"You have been banned by {banner} ({user['username']}){when}.{suffix}")
    add_mod_log(user, f"ban:{minutes}" if until else "ban", target, reason)
    return {"ok": True}


@app.post("/api/unban")
def unban(body: TargetIn, user: Any = Depends(auth)):
    ban_guard(user)
    target = get_user(body.id or "")
    if target is None:
        raise HTTPException(404, "User not found.")
    conn = db()
    execute(conn, "UPDATE users SET banned = FALSE, banned_until = 0 WHERE id = %s", (target["id"],))
    conn.commit()
    conn.close()
    add_notice(target["id"], "Your ban has been lifted.")
    add_mod_log(user, "unban", target, (body.reason or "").strip())
    return {"ok": True}


@app.post("/api/force-signout")
def force_signout(body: TargetIn, user: Any = Depends(auth)):
    # Same tier as Kick/Mute (Trial Mod and up). Doesn't kick (remove the
    # relationship), ban, or mute the account - it just ends every session
    # it's currently signed into, so it has to sign back in everywhere. The
    # notice below is waiting for them the next time they do.
    kick_guard(user)
    target = get_user(body.id or "")
    if target is None:
        raise HTTPException(404, "User not found.")
    protect_target(user, target)
    conn = db()
    execute(conn, "DELETE FROM tokens WHERE user_id = %s", (target["id"],))
    conn.commit()
    conn.close()
    actor_label = "the Owner" if is_owner_user(user) else user_role(user).replace("_", "-").title()
    reason = (body.reason or "").strip()
    suffix = f" Reason: {reason}" if reason else ""
    add_notice(target["id"], f"You were signed out of every device by {actor_label} ({user['username']}).{suffix}")
    add_mod_log(user, "force_signout", target, reason)
    return {"ok": True}


@app.post("/api/warn")
def warn(body: WarnIn, user: Any = Depends(auth)):
    # Same tier as Kick/Mute (Trial Mod and up) - the lightest touch in the
    # Special Menu. Doesn't restrict the account at all, just sends a
    # notice and leaves a mod-log entry, so there's a paper trail before
    # escalating to Mute/Kick/Ban.
    kick_guard(user)
    target = get_user(body.id or "")
    if target is None:
        raise HTTPException(404, "User not found.")
    protect_target(user, target)
    reason = (body.reason or "").strip()
    if not reason:
        raise HTTPException(400, "A warning needs a reason.")
    actor_label = "the Owner" if is_owner_user(user) else user_role(user).replace("_", "-").title()
    add_notice(target["id"], f"You were warned by {actor_label} ({user['username']}). Reason: {reason}")
    add_mod_log(user, "warn", target, reason)
    return {"ok": True}


@app.post("/api/broadcast")
def broadcast(body: BroadcastIn, user: Any = Depends(auth)):
    # Co-Owner and up, same tier as the rest of the Special Menu (View Log
    # is the one exception that stays Owner-only). Sends one notice to
    # every account on the server - capped in length like a reason, and
    # logged the same way everything else in this menu is.
    banlist_guard(user)
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(400, "Enter a message to broadcast.")
    text = text[:500]
    conn = db()
    rows = execute(conn, "SELECT id FROM users").fetchall()
    ts = now()
    sender = "the Owner" if is_owner_user(user) else user_role(user).replace("_", "-").title()
    message = f"\U0001f4e2 Announcement from {sender} ({user['username']}): {text}"
    for r in rows:
        execute(conn, "INSERT INTO notices (user_id, text, ts) VALUES (%s, %s, %s)", (r["id"], message, ts))
    conn.commit()
    conn.close()
    add_mod_log(user, "broadcast", {"id": "*", "username": "Everyone"}, text)
    return {"ok": True, "recipients": len(rows)}


@app.post("/api/mute")
def mute(body: MuteIn, user: Any = Depends(auth)):
    # Trial Mod and up can mute, but protect_target still stops anyone from
    # muting the Owner or someone at/above their own rank. A mute only
    # blocks sending messages - it doesn't kick or ban them from anything.
    mute_guard(user)
    target = get_user(body.id or "")
    if target is None:
        raise HTTPException(404, "User not found.")
    if target["id"] == user["id"]:
        raise HTTPException(400, "You can't mute yourself.")
    protect_target(user, target)
    minutes = max(1, min(int(body.minutes or 0), 7 * 24 * 60))  # 1 min .. 7 days
    until = now() + minutes * 60
    conn = db()
    execute(conn, "UPDATE users SET muted_until = %s WHERE id = %s", (until, target["id"]))
    conn.commit()
    conn.close()
    muter = "the Owner" if is_owner_user(user) else user_role(user).replace("_", "-").title()
    reason = (body.reason or "").strip()
    suffix = f" Reason: {reason}" if reason else ""
    add_notice(target["id"], f"You were muted for {minutes} minute(s) by {muter} ({user['username']}).{suffix}")
    add_mod_log(user, f"mute:{minutes}", target, reason)
    return {"ok": True}


@app.post("/api/unmute")
def unmute(body: TargetIn, user: Any = Depends(auth)):
    mute_guard(user)
    target = get_user(body.id or "")
    if target is None:
        raise HTTPException(404, "User not found.")
    conn = db()
    execute(conn, "UPDATE users SET muted_until = 0 WHERE id = %s", (target["id"],))
    conn.commit()
    conn.close()
    add_notice(target["id"], "Your mute has been lifted.")
    add_mod_log(user, "unmute", target, (body.reason or "").strip())
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
    # Co-Owner and up - same tier as the rest of the Special Menu. The Owner
    # rank itself is never affected: it isn't in VALID_ROLES, it's derived
    # purely from OWNER_USERNAME, and a role change can never be applied to
    # the Owner account (blocked below) - so even a Co-Owner granting roles
    # can never create a second Owner or touch the real one. This replaces
    # the old /api/admin/grant and /api/admin/revoke endpoints with a single
    # endpoint that covers the whole Trial Mod / Mod / Co-Owner ladder.
    banlist_guard(user)
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
    # Co-Owner and up (same tier as the ban list) - unlike /api/users/search,
    # isn't limited to friends and includes banned accounts. This is what
    # powers the special menu's "find people" box, so a Co-Owner needs it to
    # use the rest of that menu (Kick/Ban/Mute) on someone who isn't already
    # a friend. Role changes stay Owner-only regardless - see set_role below.
    banlist_guard(user)
    q = (body.username or "").strip()
    if not q:
        return []
    conn = db()
    rows = execute(
        conn,
        "SELECT id, username, banned, is_admin, role, muted_until FROM users WHERE username ILIKE %s LIMIT 25",
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
            "muted": is_muted(r),
        }
        for r in rows
    ]


@app.get("/api/owner/modlog")
def owner_modlog(user: Any = Depends(auth)):
    # Owner-only, unlike the rest of the Special Menu: a running history of
    # kicks/bans/unbans/role changes, most recent first, so the Owner can
    # review what's happened without having to remember it all. Capped at
    # the last 200 entries.
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
    if is_muted(user):
        remaining = int((user.get("muted_until") or 0) - now())
        mins = max(1, remaining // 60)
        raise HTTPException(403, f"You're muted for another {mins} minute(s).")
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

import json
import os
import urllib.error
import urllib.parse
import urllib.request

DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AppLauncher")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# Single source of truth for the app's version, sent with every
# register/login so the server can refuse to sign in copies old enough to
# predate a security fix. Bump this together with the root VERSION file and
# server/main.py's MIN_CLIENT_VERSION whenever you push a fix that must not
# keep running on older clients.
CLIENT_VERSION = "1.4.2"

SESSION_KEYS = ("net_url", "net_token", "net_id", "net_username", "net_owner", "net_admin", "net_role")


class NetError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.message = message
        self.status = status


def _load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_config(data):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def save_session(base_url, token, me):
    cfg = _load_config()
    cfg["net_url"] = base_url.rstrip("/")
    cfg["net_token"] = token
    cfg["net_id"] = me.get("id", "")
    cfg["net_username"] = me.get("username", "")
    cfg["net_owner"] = bool(me.get("is_owner"))
    cfg["net_admin"] = bool(me.get("is_admin"))
    cfg["net_role"] = me.get("role") or ("owner" if me.get("is_owner") else "member")
    _save_config(cfg)


def load_session():
    cfg = _load_config()
    if not cfg.get("net_token") or not cfg.get("net_url"):
        return None
    return {
        "url": cfg["net_url"],
        "token": cfg["net_token"],
        "id": cfg.get("net_id", ""),
        "username": cfg.get("net_username", ""),
        "is_owner": bool(cfg.get("net_owner")),
        "is_admin": bool(cfg.get("net_admin")),
        "role": cfg.get("net_role") or "member",
    }


def clear_session():
    cfg = _load_config()
    for k in SESSION_KEYS:
        cfg.pop(k, None)
    _save_config(cfg)


class Net:
    def __init__(self, base_url, token=None):
        self.base = (base_url or "").rstrip("/")
        self.token = token
        self.me = None

    @property
    def signed_in(self):
        return bool(self.base and self.token)

    def _req(self, method, path, data=None, timeout=8):
        if not self.base:
            raise NetError("No server set.")
        url = self.base + path
        r = urllib.request.Request(url, method=method)
        r.add_header("X-Client-Version", CLIENT_VERSION)
        if self.token:
            r.add_header("Authorization", "Bearer " + self.token)
        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            r.add_header("Content-Type", "application/json")
            r.data = body
        try:
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read().decode("utf-8")).get("detail", str(e))
            except Exception:
                detail = str(e)
            raise NetError(str(detail), e.code)
        except TimeoutError:
            raise NetError(
                "The server took too long to respond - free servers can take "
                "up to a minute to wake up after sitting idle. Try again.", None)
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                raise NetError(
                    "The server took too long to respond - free servers can take "
                    "up to a minute to wake up after sitting idle. Try again.", None)
            raise NetError("Can't reach the server. Is it online?", None)
        except Exception as e:
            raise NetError(str(e), None)

    def register(self, username, password):
        # Free-tier servers spin down after 15 min idle and can take up to
        # a minute to wake back up on the first request - give this one a
        # much longer timeout than the routine calls below.
        # Client version rides on the X-Client-Version header (added to every
        # request in _req), so the server can gate this the same way it
        # gates every other call - no need to duplicate it in the body.
        d = self._req("POST", "/api/register", {"username": username, "password": password}, timeout=60)
        self.token = d.get("token")
        self.me = {"id": d.get("id"), "username": d.get("username"),
                  "is_owner": d.get("is_owner"), "is_admin": d.get("is_admin"),
                  "role": d.get("role")}
        return self.me

    def login(self, username, password):
        d = self._req("POST", "/api/login", {"username": username, "password": password}, timeout=60)
        self.token = d.get("token")
        self.me = {"id": d.get("id"), "username": d.get("username"),
                  "is_owner": d.get("is_owner"), "is_admin": d.get("is_admin"),
                  "role": d.get("role")}
        return self.me

    def logout(self):
        try:
            if self.token:
                self._req("POST", "/api/logout")
        except NetError:
            pass
        self.token = None
        self.me = None

    def me_info(self):
        return self._req("GET", "/api/me")

    def search_users(self, q):
        return self._req("POST", "/api/users/search", {"username": q})

    def friends(self):
        return self._req("GET", "/api/friends")

    def add_friend(self, username):
        return self._req("POST", "/api/friends/add", {"username": username})

    def kick(self, user_id, reason=None):
        return self._req("POST", "/api/friends/kick", {"id": user_id, "reason": reason})

    def ban(self, user_id, reason=None):
        return self._req("POST", "/api/ban", {"id": user_id, "reason": reason})

    def unban(self, user_id, reason=None):
        return self._req("POST", "/api/unban", {"id": user_id, "reason": reason})

    def bans(self):
        return self._req("GET", "/api/bans")

    def mute(self, user_id, minutes, reason=None):
        return self._req("POST", "/api/mute", {"id": user_id, "minutes": minutes, "reason": reason})

    def unmute(self, user_id, reason=None):
        return self._req("POST", "/api/unmute", {"id": user_id, "reason": reason})

    def set_role(self, user_id, role, reason=None):
        return self._req("POST", "/api/roles/set", {"id": user_id, "role": role, "reason": reason})

    def search_any(self, q):
        # Owner-only lookup across every account (including banned ones),
        # unlike search_users() which only covers non-banned strangers.
        return self._req("POST", "/api/owner/search", {"username": q})

    def mod_log(self):
        # Owner-only moderation history - who kicked/banned/set roles on
        # whom, when, and why (if a reason was given).
        return self._req("GET", "/api/owner/modlog")

    def messages(self, with_user, after=0.0):
        q = urllib.parse.urlencode({"with_user": with_user, "after": float(after)})
        return self._req("GET", "/api/messages?" + q)

    def send(self, to, text):
        return self._req("POST", "/api/messages/send", {"to": to, "text": text})

    def call(self, to, action):
        return self._req("POST", "/api/call", {"to": to, "action": action})

    def call_state(self, with_user):
        q = urllib.parse.urlencode({"with_user": with_user})
        return self._req("GET", "/api/call?" + q)

    def notices(self):
        return self._req("GET", "/api/notices")

    def get_settings(self):
        return self._req("GET", "/api/settings", timeout=20)

    def set_settings(self, data):
        return self._req("POST", "/api/settings", {"data": data}, timeout=20)

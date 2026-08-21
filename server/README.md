# AppLauncher Network server

A small FastAPI backend that lets everyone's App Launcher talk to each other:
accounts, contacts, text messages, live calls, and **Owner-only kick/ban that is
enforced server-side** (banned users can't even sign in).

Data lives in a **Postgres** database (not a local file), so it survives the
server restarting or spinning down - which matters because Render's free
tier wipes its local disk every time the service goes idle. A free Postgres
database (e.g. from [Neon](https://neon.tech)) doesn't have that problem.

## 1. Get a free Postgres database

1. Go to https://neon.tech and sign up (free).
2. Create a new project (any name/region is fine).
3. Copy the **connection string** it gives you - it looks like:
   `postgresql://user:password@ep-xxxx.region.aws.neon.tech/dbname?sslmode=require`

Keep this handy - it's your `DATABASE_URL`.

## 2. Run it locally (for testing)

```
pip install -r requirements.txt
set DATABASE_URL=postgresql://user:password@ep-xxxx.region.aws.neon.tech/dbname?sslmode=require
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

(On macOS/Linux use `export DATABASE_URL=...` instead of `set`.)

The tables are created automatically on first startup - nothing else to run.

## 3. Deploy to Render (free tier)

1. Make sure this `server/` folder is pushed to your GitHub repo
   (repo: `davidangelo92023-tech/AppLauncher`).
2. Go to https://render.com and sign up (free account).
3. Click **New +** -> **Web Service** -> connect your GitHub repo.
4. Pick the repo and set:
   - **Root Directory**: `server`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free
5. Under **Environment**, add an environment variable:
   - **Key**: `DATABASE_URL`
   - **Value**: the Neon connection string from step 1
6. Click **Create Web Service**. When it says "Live", copy the URL
   (looks like `https://applauncher-network.onrender.com`).
7. Paste that URL into the **Sign in** window of the app (Settings ->
   Sign in, or the Contacts window) and everyone uses the same URL.

Render's free instance still spins down after 15 minutes of inactivity and
takes a few seconds to wake back up on the next request - that part is
normal and harmless. What changed is that the *data* (accounts, friends,
messages) now lives in Neon instead of the app's local disk, so it's still
there when it wakes up, instead of resetting to empty.

## Heads up: accounts reset

Since the old setup stored everything in a local SQLite file that Render
was wiping on every spin-down, there's no old data worth carrying over -
everyone (including the Owner) will need to register again once this is
live on the new database. After that, it sticks around.

## Owner rules

- The **first account ever registered** on the server becomes the Owner.
- Only the Owner can Kick and Ban. Bans are global: a banned account cannot
  sign in, send messages, call, or be added by anyone.

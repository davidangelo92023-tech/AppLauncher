# AppLauncher Network server

A small FastAPI backend that lets everyone's App Launcher talk to each other:
accounts, contacts, text messages, live calls, and **Owner-only kick/ban that is
enforced server-side** (banned users can't even sign in).

## Run it locally (for testing)

```
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Data is saved to `applauncher.db` (SQLite) in this folder.

## Deploy to Render (free tier)

1. Make sure this `server/` folder is pushed to your GitHub repo
   (repo: `davidangelo92023-tech/AppLauncher`).
2. Go to https://render.com and sign up (free account).
3. Click **New +** -> **Web Service** -> connect your GitHub repo.
4. Pick the repo and set:
   - **Root Directory**: `server`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free
5. Click **Create Web Service**. When it says "Live", copy the URL
   (looks like `https://applauncher-network.onrender.com`).
6. Paste that URL into the **Sign in** window of the app (Settings ->
   Sign in, or the Contacts window) and everyone uses the same URL.

## Owner rules

- The **first account ever registered** on the server becomes the Owner.
- Only the Owner can Kick and Ban. Bans are global: a banned account cannot
  sign in, send messages, call, or be added by anyone.

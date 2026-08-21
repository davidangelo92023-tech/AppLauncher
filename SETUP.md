# Running App Launcher on your own PC

This folder is self-contained - copy the whole `AppLauncher` folder to
anywhere on your computer, **except** it needs to sit directly on your
Desktop (not inside Downloads, not nested in another folder). The app
checks this at startup and refuses to run otherwise, so it can't end up
buried somewhere confusing. (This only applies to copies handed out as
the zip - your own working copy of the source, the one with the `.git`
folder that you edit and push from, is exempt and can live anywhere,
like `F:\AppLauncher`.)

## Quickest way: one-click setup

If you're sending this to a friend who doesn't have Python and doesn't
want to mess with installers, just tell them to unzip the folder **onto
their Desktop** and double-click **`Start Here.vbs`**. That's it - one
click. (If they unzip it somewhere else first, like Downloads, they just
need to drag the whole folder onto their Desktop before running it - the
app will tell them to do exactly that if they forget.)

Here's what it does under the hood:

- The very first time, it visibly runs `Install and Run.bat`, which
  checks for Python, silently downloads and installs it (official
  installer from python.org, no prompts, per-user install so no admin
  password needed) if it's missing, installs the couple of packages the
  app needs, and then launches the app. This step takes a minute or two
  and needs an internet connection.
- Every time after that, `Start Here.vbs` sees setup already happened and
  launches the app straight away, silently, just like `App Launcher.vbs`
  does today.

A few honest notes: this only handles Python itself, not things like a
missing internet connection or a locked-down work/school PC that blocks
installers - in either of those cases it'll say so and point them to
installing Python manually instead. I also can't run Windows scripts or
test this myself from here, so if a friend hits something unexpected,
have them screenshot the window and send it over.

If you (Ash) already have Python and packages installed, your existing
`App Launcher.vbs` shortcut still works exactly as before - you don't
need to switch to `Start Here.vbs`.

There are also two other ways to run it: installing Python yourself
(steps below), or as a standalone `.exe` that needs no Python at all
once it's built - see **"Building a standalone .exe"** further down.

## 1. Install Python

You need Python 3.10 or newer, for Windows.

1. Download it from https://www.python.org/downloads/
2. Run the installer, and make sure you check **"Add python.exe to PATH"**
   on the first screen before clicking Install. This step matters - without
   it, the launcher won't be able to find Python.

## 2. Install the required packages

Open a terminal (PowerShell or Command Prompt) in this folder and run:

```
pip install -r requirements.txt
```

This installs Pillow (image/icon handling) and pywebview (the built-in
browser window).

## 3. Launch the app

Double-click **`App Launcher.vbs`** - this starts the app silently, with no
console window.

(`App Launcher.bat` also works and does the same thing, but since it's a
batch file it will briefly flash a console window before the app opens -
use the `.vbs` shortcut if you want it fully silent.)

## Something not working?

If double-clicking `App Launcher.vbs` does nothing at all (no window, no
error), first make sure you fully **unzipped** the download into its own
folder rather than running it straight out of the `.zip` - Windows blocks
scripts from running inside a zip.

Then double-click **`Diagnose.bat`** in this folder. It's a one-click
checkup: it finds your Python install, checks for the three things App
Launcher needs (tkinter, Pillow, pywebview), installs whichever ones are
missing, and leaves a plain-English report on screen. If it still doesn't
work after that, copy everything the window shows and send it back.

## Building a standalone .exe (no Python needed for friends)

If you'd rather hand friends a plain app instead of asking them to install
Python, you (or anyone with Python) can build real `.exe` files once:

1. Do steps 1-2 above (install Python, `pip install -r requirements.txt`)
   on the machine doing the build.
2. Double-click **`build_exe.bat`** in this folder. It installs PyInstaller
   and packages the app - this takes a minute or two and needs internet
   access the first time.
3. When it finishes, you'll have `AppLauncher.exe`, `AppBrowser.exe`, and
   `AppFriends.exe` sitting in this folder.

From that point on, this folder (with those three `.exe` files in it) is a
real standalone app - `App Launcher.vbs`/`App Launcher.bat` will
automatically launch `AppLauncher.exe` instead of needing Python, and
that's also what you'd zip up and share with friends: they just unzip and
double-click, no Python or pip install required.

A couple of honest caveats: I can't run Windows build tools or test the
built `.exe` myself from here, so this is untested on my end - if
`build_exe.bat` errors out, paste me the output and I'll help fix it. The
browser feature (`AppBrowser.exe`) is the most likely one to need tweaking,
since the library it depends on (pywebview) can be picky about how
PyInstaller bundles it - if it's the only one that fails, `AppLauncher.exe`
and `AppFriends.exe` should still be fine to use on their own.

## Notes

- All your settings, launch stats, and saved friends/contacts are stored
  per-Windows-account under `%APPDATA%\AppLauncher`, so multiple people on
  the same PC (different Windows logins) each get their own separate setup
  automatically.
- The "Owner" tag (admin controls in Contacts) is claimed per-install, on a
  first-come basis - whoever opens Contacts and claims it first on a given
  PC becomes the Owner there.
- The online Friends/Contacts network already runs on a shared server, so
  you can add each other as friends and chat/call across separate
  installs/PCs without any extra setup.
- To add your own apps to the grid, use the **+** button in the app, or
  just drop shortcuts (`.lnk`, `.url`, `.exe`, `.bat`) or folders straight
  into this folder.

## What's new

- **Minesweeper** - a ninth game in the Games window: classic 9x9, 10-mine
  board. Left-click to clear a cell (the first click is never a mine),
  right-click to flag one you think is dangerous. Clearing every non-mine
  cell wins; your win count is remembered across sessions.
- **"Recent" filter chip** - a "\U0001f550 Recent" chip appears in the filter
  row (next to All/Favorites) once you've launched anything, showing your
  last 10 launched apps, most recent first. Local to this PC only, like
  your launch counts - it isn't part of cloud sync or export/import.
- **Mute (Special Menu)** - alongside Kick/Ban, the Special Menu now has a
  Mute/Unmute pair with a duration box (in minutes, defaults to 30). A
  muted account can still sign in, see contacts, and receive messages, but
  can't send any until the mute expires or an Unmute is issued. Same
  permission tier as Kick (Trial Mod and up can mute), and it's included in
  the Reason box and moderation log like everything else in the Special
  Menu. A quick 30-minute Mute button is also on the regular chat window
  itself (same tier as Kick) for muting without leaving the conversation -
  use the Special Menu for a custom duration.
- **Reasons + a moderation log** - Kick, Ban/Unban, and role changes in the
  Special Menu now have an optional "Reason" box. Whatever you type there
  gets included in the notice the person receives and saved to a running
  log. Click "View Log" at the top of the Special Menu to see the last 200
  moderation actions - who did what to whom, when, and why.
- **Special Menu (Owner only)** - a "⭐ Special Menu…" button appears next to
  Contacts' Bans button whenever you're signed in as the Owner account. It
  opens a panel where you can search for *any* account (not just your
  friends, and including banned ones), then Kick, Ban/Unban, or set their
  role: Trial Mod (can Kick), Mod (can Kick and Ban), or Co-Owner (can Kick,
  Ban, and manage the full ban list) - or set them back to Member to remove
  a role. Only the Owner account can ever grant or change anyone's role -
  nobody else can promote themself or anyone else, no matter what role they
  hold, so it can never be chained into more power. Roles have no
  expiration; they stay until the Owner changes them again. Regular
  Kick/Ban buttons in Contacts and chat windows now follow the same tiers
  (Trial Mod+ can Kick, Mod+ can Ban, Co-Owner+ can see the full ban list)
  instead of the old flat "admin" toggle.
- **One-click setup for friends** - `Start Here.vbs` checks for Python,
  silently installs it (and the required packages) if it's missing, then
  launches the app. See "Quickest way: one-click setup" above.
- **Keyboard navigation** - arrow keys move the selection, Enter/Space
  launches it (only when the search box isn't focused).
- **Favorites & categories** - right-click any card to pin it to
  Favorites or set a category; the chip row under the header title
  filters the grid by "All", "★ Favorites", or any category you've used.
- **Contacts unread dot** - a small red dot appears on the Contacts icon
  when a friend messages you while the app is running.
- **Start with Windows** - a checkbox in Settings → Options that
  registers/unregisters the app in your Windows startup items.
- **One-click updates** - if `VERSION` in this folder is older than the
  one in the GitHub repo, a "🔔 Update available" link shows up in the
  footer. Clicking it downloads the latest `AppLauncher.py`,
  `AppContacts.py`, `AppNet.py`, `AppBrowser.py`, `AppFriends.py`,
  `AppGames.py`, `run.py` and `VERSION` straight from the repo, writes
  them into this folder, and offers to restart. Apps, contacts, and
  settings are never touched. This is how everyone else's copy picks up
  new features and fixes without you sending them a new zip each time -
  it only fires once you bump the version and push (see "Releasing an
  update" below). Note: if someone is only running the built `.exe` (no
  Python installed), the update still downloads the new source files,
  but the wrapper script needs Python to actually run them - it'll show
  a "couldn't find Python" message until they install it, since the
  sandbox here can't rebuild and ship a new `.exe` for you
  automatically.
- **Desktop-only for distributed copies** - `run.py` (and so
  `AppLauncher.exe`, which is built from it) refuses to start unless the
  folder it's running from sits directly on the current Windows user's
  Desktop (either as a subfolder, or loose files with no subfolder at
  all - both count). Your own git working copy (has a `.git` folder next
  to `run.py`) is exempt and can live anywhere, like `F:\AppLauncher` -
  this only affects copies you hand out as the zip. Desktop detection
  checks the registry, the older Windows API, and the plain
  `%USERPROFILE%\Desktop` guess, and accepts a match against any of
  them, since things like OneDrive's Desktop redirection can make one
  method disagree with another on a given PC. If someone hits this
  error on a folder that really is on their Desktop, it's a detection
  bug, not intentional - **because this check runs before the app (and
  its in-app updater) ever starts, a fixed version can't reach them on
  its own.** Two ways to unblock them right away: have them create an
  empty file named `.desktop_override` in that folder (skips the check
  entirely, no new build needed), or send them a freshly-built zip once
  the detection logic has been improved. The error dialog itself shows
  the exact folder path and the Desktop path it detected, which is the
  first thing to check if this happens again.
- **Source files locked against editing on distributed copies** - every
  launch, `run.py` marks the app's own `.py` files, `run.py` itself,
  `VERSION`, and the `.vbs`/`.bat` launcher scripts read-only on disk
  (again, only for copies without a `.git` folder - never yours). It's a
  courtesy/tamper deterrent so a friend can't casually edit them in a
  text editor, not a real security boundary - Owner/admin status is
  always verified server-side regardless of what a local file claims.
  The in-app updater already knows how to temporarily clear this flag
  so it can still apply new versions; you don't need to do anything
  differently.
- **Mandatory update, even for already-signed-in accounts** - every
  request to the server (not just login/registration) carries the
  app's version, and the server refuses anything older than
  `MIN_CLIENT_VERSION` in `server/main.py` (a 426 error with a "please
  update" message). For login/registration that just means they can't
  get in. For someone who's already signed in on an old version, the
  server immediately revokes that session too - Contacts polls the
  server every few seconds while it's open, so within moments they're
  force-signed-out with an explanation, not just blocked from a future
  fresh login. The in-app updater above still works even while
  blocked, since downloading an update doesn't require being signed
  in, so they can fix it themselves in one click. Bump
  `MIN_CLIENT_VERSION` only for changes that genuinely must not keep
  running on old clients (like a security fix) - not every routine
  release, since it force-logs-out everyone who hasn't updated yet
  until they do.
- **Releasing an update** - three things need to move together, or the
  version checks get out of sync: the `VERSION` file in this folder,
  `CLIENT_VERSION` near the top of `AppNet.py` (this is what
  `AppLauncher.py`'s own `VERSION` reads from), and - only when the
  release is a mandatory one - `MIN_CLIENT_VERSION` in
  `server/main.py`. Bump whichever apply, then double-click
  **`Push Update.bat`** in this folder to commit and push everything to
  GitHub in one step (it's the same as running
  `git add -A && git commit -m "..." && git push` by hand). Render
  picks up server changes automatically within a minute or two;
  everyone else's app picks up the rest next time they check for
  updates.
- **Cloud sync** - Settings → Cloud sync lets you Push/Pull your
  favorites, categories, dock, schedules and look/feel settings to your
  account (sign in via Contacts first), plus an "auto-pull on launch /
  push on close" checkbox. Doesn't touch app shortcuts/icons themselves,
  since those are specific to each PC. Needs the server redeployed with
  the updated `server/main.py` (new `/api/settings` endpoint) - push it
  to the GitHub repo Render is watching.
- **Quick-launch dock** - right-click a card → "Pin to quick-launch dock"
  to keep it as a small icon at the end of the chip row, always visible
  even while scrolled or filtered (up to 8).
- **Scheduled launch** - right-click a card → "Schedule daily launch…"
  to have it auto-open at a set time every day.
- **Per-app custom color/icon** - right-click a card → "Custom color…" /
  "Custom icon…" to override its accent color or swap its icon.
- **Usage insights** - Settings → Usage insights shows a simple bar
  chart of your most-launched apps.
- **Export/Import settings** - Settings → Backup & restore saves your
  favorites/categories/dock/schedules/look to a `.json` file (same scope
  as cloud sync) and loads them back, e.g. to move to a new PC by hand.

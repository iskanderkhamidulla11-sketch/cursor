# Telegram Deal Bot + Mini App

This project contains:
- `backend/` - Telegram bot (aiogram + SQLite), running locally on your laptop.
- `frontend/` - Telegram Mini App static files for GitHub Pages.

## 1) Publish Mini App to GitHub Pages

1. Create GitHub repository.
2. Upload all project files.
3. In repository settings, enable GitHub Pages from branch (root or `/docs`).
4. Get URL like:
   - `https://YOUR_USERNAME.github.io/YOUR_REPO/`
5. Make sure `frontend/index.html` is available via Pages URL.

If your Pages serves repo root, copy `frontend/*` to root or configure Pages source folder appropriately.

## 2) Configure bot

In `backend/.env.example` fill values and copy to actual env variables:
- `BOT_TOKEN` - token from @BotFather
- `WEBAPP_URL` - your GitHub Pages URL to Mini App (must be HTTPS)

On Windows PowerShell example:

```powershell
$env:BOT_TOKEN="123456:ABC"
$env:WEBAPP_URL="https://YOUR_USERNAME.github.io/YOUR_REPO/frontend/"
```

## 3) Run bot locally

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## 4) How to test

1. User A opens bot and sends `/start`.
2. User B opens bot and sends `/start`.
3. User A taps `Open Mini App`.
4. User A enters username of User B and submits.
5. User B receives invitation message.

## Important

- Username lookup works only for users who already started this bot.
- Bot stays online only while your laptop process is running.

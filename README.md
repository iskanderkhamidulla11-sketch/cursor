<<<<<<< HEAD
# Telegram Escrow Bot + Mini App

Project includes:
- `backend/` - aiogram bot + SQLite, running locally.
- `frontend/` - Telegram Mini App for GitHub Pages.

## Features

- Escrow deal flow: create -> accept -> in progress -> delivered -> completed.
- Wallet with transaction history.
- Top up via Telegram Stars (invoice + successful payment handler).
- Top up via CryptoBot API (invoice creation + payment check).
- Withdraw requests with admin approval flow.
- Reviews (1..5 + text) after completed deals.

## 1) Deploy Mini App to GitHub Pages

1. Push repository to GitHub.
2. Enable Pages in repo settings (branch `main`, folder `/`).
3. Use Mini App URL:
   - `https://YOUR_USERNAME.github.io/YOUR_REPO/frontend/`

## 2) Configure environment

Create `backend/.env` (or set environment variables):

```env
BOT_TOKEN=123456:ABC
WEBAPP_URL=https://YOUR_USERNAME.github.io/YOUR_REPO/frontend/
STARS_PROVIDER_TOKEN=
CRYPTOBOT_TOKEN=
CRYPTOBOT_BASE_URL=https://pay.crypt.bot/api
ADMIN_IDS=123456789
```

## 3) Run locally
=======
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
>>>>>>> 812b10437b3ace4a467d917045a8e96128a6b6a4

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

<<<<<<< HEAD
## 4) Bot commands

- `/start` - register user and open Mini App button.
- `/balance` - show balance and latest transactions.
- `/deals` - show recent deals.
- `/admin_withdraws` - list pending withdraw requests (admin only).
- `/approve_withdraw <id>` - approve withdraw request (admin only).

## Notes

- Username lookup works only for users who already sent `/start`.
- Bot is online only while local process is running.
=======
## 4) How to test

1. User A opens bot and sends `/start`.
2. User B opens bot and sends `/start`.
3. User A taps `Open Mini App`.
4. User A enters username of User B and submits.
5. User B receives invitation message.

## Important

- Username lookup works only for users who already started this bot.
- Bot stays online only while your laptop process is running.
>>>>>>> 812b10437b3ace4a467d917045a8e96128a6b6a4

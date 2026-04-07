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

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## 4) Bot commands

- `/start` - register user and open Mini App button.
- `/balance` - show balance and latest transactions.
- `/deals` - show recent deals.
- `/admin_withdraws` - list pending withdraw requests (admin only).
- `/approve_withdraw <id>` - approve withdraw request (admin only).

## Notes

- Username lookup works only for users who already sent `/start`.
- Bot is online only while local process is running.

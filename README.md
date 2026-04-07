# FunPay Mini App + Telegram Escrow Bot

Коротко: мини‑приложение (frontend) и Telegram‑бот (backend) для эскроу‑сделок.

Быстрый запуск (Windows / PowerShell):

```powershell
cd "c:\Users\Искандер\Desktop\python)\попытка номер два2"
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Файлы и папки:
- `backend/` — бот на `aiogram`, база SQLite (`bot.db`), скрипт `main.py`.
- `frontend/` — Mini App (index.html, script.js, styles.css).
- `start_bot.cmd` — быстрый скрипт запуска (можно использовать локально).

Deploy / GitHub
- В `start_bot.cmd` указан `WEBAPP_URL` (Pages): `https://iskanderkhamidulla11-sketch.github.io/cursor/frontend/`.
- Чтобы залить в GitHub выполните в корне проекта:

```powershell
git init
git add .
git commit -m "Initial commit: FunPay MiniApp + bot"
git remote add origin https://github.com/iskanderkhamidulla11-sketch/cursor.git
git branch -M main
git push -u origin main
```

Безопасность:
- Не публикуйте `BOT_TOKEN` публично. Для продакшн лучше вынести в `.env` или CI secrets.

Если хотите, могу подготовить и отправить список точных команд для пуша (или создать репозиторий через `gh`), — скажите, и я подготовлю шаги.
# Telegram Escrow Bot + Mini App

Проект содержит:
- `backend/` — бот на `aiogram` + `SQLite`, запускается локально.
- `frontend/` — Mini App для Telegram, публикуется на GitHub Pages.

## Функционал

- Эскроу-сделки: создание -> принятие -> выполнение -> подтверждение -> завершение.
- Баланс и история операций.
- Пополнение через Telegram Stars и CryptoBot.
- Вывод: карта / Stars / USDT TRC20 со статусом "принята администрацией".
- Отзывы после завершенных сделок.
- Чат внутри сделки (обновление через polling в Mini App).
- Новый интерфейс Mini App: `Главная`, `Профиль`, `Сделки`, `Вывод`.

## Запуск

1. **Зарегистрируйся на ngrok**: https://dashboard.ngrok.com/signup (бесплатно).

2. **Получи authtoken**: https://dashboard.ngrok.com/get-started/your-authtoken.

3. **Установи authtoken**:
   ```powershell
   ngrok config add-authtoken YOUR_TOKEN_HERE
   ```

4. **Запусти бота**:
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python main.py
   ```

5. **В другом терминале запусти ngrok**:
   ```powershell
   ngrok http 8080
   ```
   Получи URL, например `https://abc.ngrok.io`.

6. **В `frontend/script.js` измени `apiBase`** на твой ngrok URL:
   ```javascript
   const apiBase = 'https://abc.ngrok.io';  // вместо 'http://localhost:8080'
   ```

Теперь Mini App сможет получать данные.

## API Endpoints

- `GET /api/profile?user_id=<id>` — профиль пользователя
- `GET /api/deals?user_id=<id>&status_filter=active` — список сделок
- `GET /api/deal/{deal_id}?user_id=<id>` — детали сделки
- `GET /api/chat/{deal_id}?user_id=<id>` — чат сделки

## Команды бота

- `/start` — регистрация и кнопка Mini App.
- `/balance` — баланс и последние операции.
- `/deals` — список последних сделок.
- `/admin_withdraws` — заявки на вывод (для админа).
- `/approve_withdraw <id>` — подтверждение вывода (для админа).

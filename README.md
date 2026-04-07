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

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Команды бота

- `/start` — регистрация и кнопка Mini App.
- `/balance` — баланс и последние операции.
- `/deals` — список последних сделок.
- `/admin_withdraws` — заявки на вывод (для админа).
- `/approve_withdraw <id>` — подтверждение вывода (для админа).

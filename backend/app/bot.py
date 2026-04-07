import json
import time
from typing import Any, Optional

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from app.config import settings
from app.db import (
    accept_deal,
    add_wallet_transaction,
    approve_withdraw_request,
    cancel_deal,
    confirm_deal,
    create_chat_message,
    create_deal,
    create_payment_intent,
    create_review,
    create_withdraw_request,
    get_deal,
    get_profile_stats,
    get_user_by_username,
    list_chat_messages,
    list_pending_withdraw_requests,
    list_user_deals,
    list_user_deals_by_filter,
    list_wallet_transactions,
    mark_delivered,
    mark_payment_intent_paid,
    set_admin_role,
    upsert_user,
    wallet_balance,
)

STARS_PAYLOAD_PREFIX = "stars_topup:"
CURRENCY = "RUB"


def build_main_keyboard() -> InlineKeyboardMarkup:
    # Use inline web_app button to avoid Telegram service message
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть FunPay", web_app=WebAppInfo(url=settings.webapp_url))]
    ])


def deal_actions_keyboard(deal_id: int, role: str, status: str) -> Optional[InlineKeyboardMarkup]:
    buttons: list[list[InlineKeyboardButton]] = []
    if role == "seller" and status == "created":
        buttons.append(
            [InlineKeyboardButton(text="Принять сделку", callback_data=f"deal:accept:{deal_id}")]
        )
    if role == "seller" and status == "in_progress":
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Mark delivered",
                    callback_data=f"deal:delivered:{deal_id}",
                )
            ]
        )
    if role == "buyer" and status == "delivered":
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Confirm deal",
                    callback_data=f"deal:confirm:{deal_id}",
                )
            ]
        )
    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def parse_int(payload: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(str(payload.get(key, default)).strip())
    except (TypeError, ValueError):
        return default


async def handle_start(message: Message) -> None:
    if message.from_user is None:
        return

    upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name or "User",
    )
    if message.from_user.id in settings.admin_ids:
        set_admin_role(message.from_user.id)

    await message.answer(
        "Вы подключены.\nИспользуйте Mini App для сделок, баланса, отзывов и вывода.",
        reply_markup=build_main_keyboard(),
    )


async def handle_balance(message: Message) -> None:
    if message.from_user is None:
        return
    balance = wallet_balance(message.from_user.id)
    tx = list_wallet_transactions(message.from_user.id, limit=8)
    lines = [f"Баланс: {balance} {CURRENCY}", "", "Последние операции:"]
    if not tx:
        lines.append("- пусто")
    for row in tx:
        lines.append(f"- {row['tx_type']}: {row['amount']} {row['currency']}")
    await message.answer("\n".join(lines))


async def handle_deals(message: Message) -> None:
    if message.from_user is None:
        return
    deals = list_user_deals(message.from_user.id, limit=10)
    if not deals:
        await message.answer("Список сделок пуст.")
        return
    lines = ["Ваши сделки:"]
    for row in deals:
        role = "buyer" if int(row["buyer_id"]) == message.from_user.id else "seller"
        counterpart = row["seller_id"] if role == "buyer" else row["buyer_id"]
        lines.append(
            f"- #{row['id']} {row['status']} | роль: {role} | сумма: {row['amount']} {CURRENCY} | c: {counterpart}"
        )
    await message.answer("\n".join(lines))


async def handle_bonus_code(message: Message) -> None:
    if message.from_user is None:
        return
    add_wallet_transaction(
        user_id=message.from_user.id,
        tx_type="deposit",
        amount=10000,
        currency=CURRENCY,
        meta={"source": "promo_code"},
    )
    await message.answer("Бонус активирован: +10000 RUB")


async def send_stars_invoice(message: Message, amount: int) -> None:
    if amount <= 0:
        await message.answer("Сумма пополнения должна быть больше 0.")
        return
    if not settings.stars_provider_token:
        await message.answer("Токен Telegram Stars не настроен.")
        return
    payload = f"{STARS_PAYLOAD_PREFIX}{message.from_user.id}:{amount}"
    create_payment_intent(
        user_id=message.from_user.id,
        provider="stars",
        external_id=payload,
        amount=amount,
        currency=CURRENCY,
        payload={"kind": "stars_topup"},
    )
    await message.answer_invoice(
        title="Пополнение баланса",
        description=f"Пополнение кошелька на {amount} {CURRENCY}",
        payload=payload,
        provider_token=settings.stars_provider_token,
        currency="XTR",
        prices=[LabeledPrice(label="Пополнение", amount=amount)],
    )


async def create_cryptobot_invoice(user_id: int, amount: int) -> tuple[Optional[str], Optional[str]]:
    if not settings.cryptobot_token:
        return None, None
    url = f"{settings.cryptobot_base_url}/createInvoice"
    headers = {"Crypto-Pay-API-Token": settings.cryptobot_token}
    payload = {
        "asset": "USDT",
        "amount": str(amount),
        "description": f"Пополнение для пользователя {user_id}",
        "hidden_message": "Баланс будет обновлен после оплаты.",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload, timeout=25) as resp:
            data = await resp.json()
            if not data.get("ok"):
                return None, None
            result = data.get("result", {})
            return str(result.get("invoice_id")), str(result.get("pay_url"))


async def check_cryptobot_invoice(invoice_id: str) -> bool:
    url = f"{settings.cryptobot_base_url}/getInvoices?invoice_ids={invoice_id}"
    headers = {"Crypto-Pay-API-Token": settings.cryptobot_token}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=25) as resp:
            data = await resp.json()
            if not data.get("ok"):
                return False
            items = data.get("result", {}).get("items", [])
            if not items:
                return False
            return items[0].get("status") == "paid"


async def process_webapp_action(message: Message, payload: dict[str, Any], bot: Bot) -> None:
    action = str(payload.get("action", "")).strip()
    user_id = message.from_user.id

    if action == "create_deal":
        target_username = str(payload.get("target_username", "")).strip().lstrip("@")
        amount = parse_int(payload, "amount")
        description = str(payload.get("description", "")).strip()
        if not target_username or amount <= 0:
            await message.answer("Некорректные параметры сделки.")
            return
        target_user = get_user_by_username(target_username)
        if not target_user:
            await message.answer(
                f"@{target_username} не найден в боте. Попросите пользователя выполнить /start."
            )
            return
        if target_user.telegram_id == user_id:
            await message.answer("Нельзя создать сделку с самим собой.")
            return
        try:
            deal_id = create_deal(
                buyer_id=user_id,
                seller_id=target_user.telegram_id,
                amount=amount,
                description=description,
            )
        except ValueError as exc:
            if str(exc) == "INSUFFICIENT_BALANCE":
                await message.answer("Недостаточно средств. Сначала пополните баланс.")
                return
            raise
        keyboard = deal_actions_keyboard(deal_id, role="seller", status="created")
        await bot.send_message(
            chat_id=target_user.telegram_id,
            text=(
                "Новая эскроу-сделка\n"
                f"Сделка #{deal_id}\n"
                f"Сумма: {amount} {CURRENCY}\n"
                f"Описание: {description or '-'}"
            ),
            reply_markup=keyboard,
        )
        await message.answer(f"Сделка #{deal_id} отправлена пользователю @{target_username}.")
        return

    if action == "list_deals":
        # Do not send periodic DATA_* messages to chat; they may close Mini App.
        return

    if action == "get_profile":
        # Reserved for future API transport without chat spam.
        return

    if action == "get_deal":
        # Reserved for future API transport without chat spam.
        return

    if action == "accept_deal":
        deal_id = parse_int(payload, "deal_id")
        try:
            deal = accept_deal(deal_id, user_id)
        except ValueError:
            await message.answer("Нельзя принять сделку в текущем статусе.")
            return
        await message.answer(f"Сделка #{deal_id} принята.")
        await bot.send_message(int(deal["buyer_id"]), f"Сделка #{deal_id} принята продавцом.")
        return

    if action == "mark_delivered":
        deal_id = parse_int(payload, "deal_id")
        try:
            deal = mark_delivered(deal_id, user_id)
        except ValueError:
            await message.answer("Нельзя отметить как выполнено в текущем статусе.")
            return
        await message.answer(f"Сделка #{deal_id} отмечена как выполненная.")
        await bot.send_message(int(deal["buyer_id"]), f"Сделка #{deal_id} отмечена как выполненная.")
        return

    if action == "confirm_deal":
        deal_id = parse_int(payload, "deal_id")
        try:
            deal = confirm_deal(deal_id, user_id)
        except ValueError:
            await message.answer("Нельзя подтвердить сделку в текущем статусе.")
            return
        await message.answer(f"Сделка #{deal_id} завершена.")
        await bot.send_message(int(deal["seller_id"]), f"Сделка #{deal_id} завершена, средства зачислены.")
        return

    if action == "cancel_deal":
        deal_id = parse_int(payload, "deal_id")
        try:
            deal = cancel_deal(deal_id, user_id)
        except ValueError:
            await message.answer("Нельзя отменить сделку в текущем статусе.")
            return
        other_user = int(deal["seller_id"]) if int(deal["buyer_id"]) == user_id else int(deal["buyer_id"])
        await message.answer(f"Сделка #{deal_id} отменена.")
        await bot.send_message(other_user, f"Сделка #{deal_id} была отменена.")
        return

    if action == "send_chat_message":
        deal_id = parse_int(payload, "deal_id")
        text = str(payload.get("text", "")).strip()
        if not text:
            await message.answer("Сообщение пустое.")
            return
        try:
            create_chat_message(deal_id, user_id, text)
        except ValueError:
            await message.answer("Ошибка отправки сообщения.")
            return
        deal = get_deal(deal_id)
        if deal:
            other_user = int(deal["seller_id"]) if int(deal["buyer_id"]) == user_id else int(deal["buyer_id"])
            await bot.send_message(other_user, f"Сообщение по сделке #{deal_id}: {text}")
        await message.answer("Сообщение отправлено.")
        return

    if action == "list_chat_messages":
        deal_id = parse_int(payload, "deal_id")
        try:
            rows = list_chat_messages(deal_id, user_id)
        except ValueError:
            await message.answer("Чат не найден или нет доступа.")
            return
        # Send compact chat history to user as messages (useful as fallback)
        if not rows:
            await message.answer("Чат пуст.")
            return
        lines = [f"Чат по сделке #{deal_id}:\n"]
        for r in rows:
            uname = r.get("username") or str(r.get("sender_id"))
            lines.append(f"{uname}: {r['text']}")
        # send as one message to avoid spam
        await message.answer("\n".join(lines))
        return

    if action == "topup_stars":
        amount = parse_int(payload, "amount")
        await send_stars_invoice(message, amount)
        return

    if action == "topup_cryptobot":
        amount = parse_int(payload, "amount")
        if amount <= 0:
            await message.answer("Некорректная сумма.")
            return
        invoice_id, pay_url = await create_cryptobot_invoice(user_id, amount)
        if not invoice_id or not pay_url:
            await message.answer("CryptoBot временно недоступен. Попробуйте позже.")
            return
        create_payment_intent(
            user_id=user_id,
            provider="cryptobot",
            external_id=invoice_id,
            amount=amount,
            currency=CURRENCY,
            payload={"pay_url": pay_url},
        )
        await message.answer(
            f"Счет CryptoBot создан.\nСсылка на оплату:\n{pay_url}\n\nПосле оплаты нажмите 'Проверить оплату CryptoBot' в Mini App."
        )
        return

    if action == "check_cryptobot_payment":
        invoice_id = str(payload.get("invoice_id", "")).strip()
        if not invoice_id:
            await message.answer("Нужно указать invoice_id.")
            return
        is_paid = await check_cryptobot_invoice(invoice_id)
        if not is_paid:
            await message.answer("Оплата пока не найдена.")
            return
        intent = mark_payment_intent_paid("cryptobot", invoice_id)
        if not intent:
            await message.answer("Платеж не найден.")
            return
        add_wallet_transaction(
            user_id=int(intent["user_id"]),
            tx_type="deposit",
            amount=int(intent["amount"]),
            currency=CURRENCY,
            meta={"provider": "cryptobot", "invoice_id": invoice_id},
        )
        await message.answer(f"Пополнение выполнено: +{int(intent['amount'])} {CURRENCY}")
        return

    if action == "withdraw_create":
        amount = parse_int(payload, "amount")
        destination = str(payload.get("destination", "")).strip()
        method = str(payload.get("method", "")).strip().lower()
        if method not in ("card", "stars", "usdt_trc20"):
            await message.answer("Выберите способ вывода: card, stars, usdt_trc20.")
            return
        if amount <= 0 or not destination:
            await message.answer("Некорректные параметры вывода.")
            return
        try:
            request_id = create_withdraw_request(user_id, amount, destination, method)
        except ValueError as exc:
            if str(exc) == "INSUFFICIENT_BALANCE":
                await message.answer("Недостаточно средств для вывода.")
                return
            raise
        await message.answer(
            f"Заявка на вывод #{request_id} создана.\nСтатус: принята администрацией."
        )
        return

    if action == "leave_review":
        deal_id = parse_int(payload, "deal_id")
        rating = parse_int(payload, "rating")
        text = str(payload.get("text", "")).strip()
        deal = get_deal(deal_id)
        if not deal:
            await message.answer("Сделка не найдена.")
            return
        if deal["status"] != "completed":
            await message.answer("Отзыв можно оставить только по завершенной сделке.")
            return
        if rating < 1 or rating > 5 or not text:
            await message.answer("Отзыв должен содержать оценку 1..5 и текст.")
            return
        if user_id == int(deal["buyer_id"]):
            target = int(deal["seller_id"])
        elif user_id == int(deal["seller_id"]):
            target = int(deal["buyer_id"])
        else:
            await message.answer("Нет доступа.")
            return
        try:
            create_review(deal_id, user_id, target, rating, text)
        except Exception:
            await message.answer("Отзыв по этой сделке уже отправлен.")
            return
        await message.answer("Отзыв отправлен.")
        return

    await message.answer("Неизвестное действие.")


async def handle_webapp_data(message: Message, bot: Bot) -> None:
    if message.from_user is None or message.web_app_data is None:
        return

    # Simple deduplication: ignore identical payloads from same user within 3 seconds
    # This prevents rapid repeated processing when the Mini App (or client) resends data.
    if not hasattr(handle_webapp_data, "_recent"):
        handle_webapp_data._recent = {}
    payload_raw = message.web_app_data.data
    try:
        now = time.time()
        key = (message.from_user.id, payload_raw)
        last = handle_webapp_data._recent.get(key)
        if last and now - last < 3.0:
            return
        handle_webapp_data._recent[key] = now
    except Exception:
        # If anything goes wrong with dedupe, continue normally.
        payload_raw = message.web_app_data.data

    upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name or "User",
    )

    payload_raw = message.web_app_data.data
    try:
        payload: dict[str, Any] = json.loads(payload_raw)
    except json.JSONDecodeError:
        await message.answer("Некорректные данные из Mini App.")
        return
    await process_webapp_action(message, payload, bot)


async def handle_pre_checkout_query(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


async def handle_successful_payment(message: Message) -> None:
    if message.from_user is None or message.successful_payment is None:
        return
    payload = message.successful_payment.invoice_payload
    if not payload.startswith(STARS_PAYLOAD_PREFIX):
        return
    intent = mark_payment_intent_paid("stars", payload)
    if not intent:
        return
    add_wallet_transaction(
        user_id=int(intent["user_id"]),
        tx_type="deposit",
        amount=int(intent["amount"]),
        currency=CURRENCY,
        meta={"provider": "stars", "payload": payload},
    )
    await message.answer(f"Пополнение выполнено: +{int(intent['amount'])} {CURRENCY}")


async def handle_deal_callback(callback: CallbackQuery, bot: Bot) -> None:
    if callback.data is None or callback.from_user is None:
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректное действие", show_alert=True)
        return
    _, action, deal_raw = parts
    if not deal_raw.isdigit():
        await callback.answer("Некорректный ID сделки", show_alert=True)
        return
    deal_id = int(deal_raw)
    try:
        if action == "accept":
            deal = accept_deal(deal_id, callback.from_user.id)
            await callback.answer("Сделка принята")
            await bot.send_message(
                int(deal["buyer_id"]),
                f"Сделка #{deal_id} принята продавцом.",
            )
        elif action == "delivered":
            deal = mark_delivered(deal_id, callback.from_user.id)
            await callback.answer("Отмечено как выполнено")
            await bot.send_message(
                int(deal["buyer_id"]),
                f"Сделка #{deal_id} отмечена как выполненная.",
                reply_markup=deal_actions_keyboard(deal_id, "buyer", "delivered"),
            )
        elif action == "confirm":
            deal = confirm_deal(deal_id, callback.from_user.id)
            await callback.answer("Сделка завершена")
            await bot.send_message(
                int(deal["seller_id"]),
                f"Сделка #{deal_id} завершена. Средства зачислены.",
            )
            await bot.send_message(
                int(deal["buyer_id"]),
                f"Сделка #{deal_id} завершена. Вы можете оставить отзыв в Mini App.",
            )
        else:
            await callback.answer("Неизвестное действие", show_alert=True)
            return
    except ValueError as exc:
        code = str(exc)
        friendly = {
            "DEAL_NOT_FOUND": "Сделка не найдена.",
            "FORBIDDEN": "У вас нет прав на это действие.",
            "INVALID_STATUS": "Нельзя выполнить действие в текущем статусе сделки.",
        }.get(code, code)
        await callback.answer(friendly, show_alert=True)


async def handle_admin_withdraws(message: Message) -> None:
    if message.from_user is None or message.from_user.id not in settings.admin_ids:
        await message.answer("Только для администратора.")
        return
    rows = list_pending_withdraw_requests()
    if not rows:
        await message.answer("Нет заявок на вывод в ожидании.")
        return
    lines = ["Заявки на вывод в ожидании:"]
    for row in rows:
        lines.append(
            f"#{row['id']} user:{row['user_id']} amount:{row['amount']} {CURRENCY} destination:{row['destination']}"
        )
    await message.answer("\n".join(lines))


async def handle_admin_approve(message: Message) -> None:
    if message.from_user is None or message.from_user.id not in settings.admin_ids:
        await message.answer("Только для администратора.")
        return
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /approve_withdraw <id>")
        return
    request_id = int(parts[1])
    row = approve_withdraw_request(request_id, admin_note="accepted by administration")
    if not row:
        await message.answer("Заявка не найдена или уже обработана.")
        return
    await message.answer(f"Вывод #{request_id} подтвержден.")
    await message.bot.send_message(
        int(row["user_id"]),
        f"Вывод #{request_id}: статус 'принят администрацией'.",
    )
def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.message.register(handle_start, CommandStart())
    dp.message.register(handle_bonus_code, F.text.casefold() == "нищий")
    dp.message.register(handle_balance, F.text == "/balance")
    dp.message.register(handle_deals, F.text == "/deals")
    dp.message.register(handle_admin_withdraws, F.text == "/admin_withdraws")
    dp.message.register(handle_admin_approve, F.text.startswith("/approve_withdraw"))
    dp.pre_checkout_query.register(handle_pre_checkout_query)
    dp.message.register(handle_successful_payment, F.successful_payment)
    dp.callback_query.register(handle_deal_callback, F.data.startswith("deal:"))
    dp.message.register(handle_webapp_data, F.web_app_data)
    return dp

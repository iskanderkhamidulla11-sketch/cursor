<<<<<<< HEAD
import json
from typing import Any, Optional

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    KeyboardButton,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)

from app.config import settings
from app.db import (
    add_wallet_transaction,
    approve_withdraw_request,
    confirm_deal,
    create_deal,
    create_payment_intent,
    create_review,
    create_withdraw_request,
    get_deal,
    get_user_by_username,
    list_pending_withdraw_requests,
    list_user_deals,
    list_wallet_transactions,
    mark_delivered,
    mark_payment_intent_paid,
    set_admin_role,
    upsert_user,
    wallet_balance,
    accept_deal,
)

STARS_PAYLOAD_PREFIX = "stars_topup:"
CURRENCY = "USDT"


def build_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="Open Mini App",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        ],
        resize_keyboard=True,
    )


def deal_actions_keyboard(deal_id: int, role: str, status: str) -> Optional[InlineKeyboardMarkup]:
    buttons: list[list[InlineKeyboardButton]] = []
    if role == "seller" and status == "created":
        buttons.append(
            [InlineKeyboardButton(text="Accept deal", callback_data=f"deal:accept:{deal_id}")]
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
        "Connected.\nUse Mini App for deals, wallet, reviews and withdrawals.",
        reply_markup=build_main_keyboard(),
    )


async def handle_balance(message: Message) -> None:
    if message.from_user is None:
        return
    balance = wallet_balance(message.from_user.id)
    tx = list_wallet_transactions(message.from_user.id, limit=8)
    lines = [f"Balance: {balance} {CURRENCY}", "", "Recent operations:"]
    if not tx:
        lines.append("- empty")
    for row in tx:
        lines.append(f"- {row['tx_type']}: {row['amount']} {row['currency']}")
    await message.answer("\n".join(lines))


async def handle_deals(message: Message) -> None:
    if message.from_user is None:
        return
    deals = list_user_deals(message.from_user.id, limit=10)
    if not deals:
        await message.answer("Deals list is empty.")
        return
    lines = ["Your deals:"]
    for row in deals:
        role = "buyer" if int(row["buyer_id"]) == message.from_user.id else "seller"
        counterpart = row["seller_id"] if role == "buyer" else row["buyer_id"]
        lines.append(
            f"- #{row['id']} {row['status']} | role: {role} | amount: {row['amount']} {CURRENCY} | with: {counterpart}"
        )
    await message.answer("\n".join(lines))


async def send_stars_invoice(message: Message, amount: int) -> None:
    if amount <= 0:
        await message.answer("Top up amount must be > 0")
        return
    if not settings.stars_provider_token:
        await message.answer("Stars provider token is not configured.")
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
        title="Balance top up",
        description=f"Top up wallet by {amount} {CURRENCY}",
        payload=payload,
        provider_token=settings.stars_provider_token,
        currency="XTR",
        prices=[LabeledPrice(label="Top up", amount=amount)],
    )


async def create_cryptobot_invoice(user_id: int, amount: int) -> tuple[Optional[str], Optional[str]]:
    if not settings.cryptobot_token:
        return None, None
    url = f"{settings.cryptobot_base_url}/createInvoice"
    headers = {"Crypto-Pay-API-Token": settings.cryptobot_token}
    payload = {
        "asset": "USDT",
        "amount": str(amount),
        "description": f"Top up for user {user_id}",
        "hidden_message": "Balance will be updated after payment.",
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
            await message.answer("Invalid deal params.")
            return
        target_user = get_user_by_username(target_username)
        if not target_user:
            await message.answer(
                f"@{target_username} not found in bot. Ask user to run /start."
            )
            return
        if target_user.telegram_id == user_id:
            await message.answer("You cannot create a deal with yourself.")
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
                await message.answer("Insufficient balance. Top up wallet first.")
                return
            raise
        keyboard = deal_actions_keyboard(deal_id, role="seller", status="created")
        await bot.send_message(
            chat_id=target_user.telegram_id,
            text=(
                "New escrow deal request\n"
                f"Deal #{deal_id}\n"
                f"Amount: {amount} {CURRENCY}\n"
                f"Description: {description or '-'}"
            ),
            reply_markup=keyboard,
        )
        await message.answer(f"Deal #{deal_id} sent to @{target_username}.")
        return

    if action == "topup_stars":
        amount = parse_int(payload, "amount")
        await send_stars_invoice(message, amount)
        return

    if action == "topup_cryptobot":
        amount = parse_int(payload, "amount")
        if amount <= 0:
            await message.answer("Invalid amount.")
            return
        invoice_id, pay_url = await create_cryptobot_invoice(user_id, amount)
        if not invoice_id or not pay_url:
            await message.answer("CryptoBot is unavailable. Try later.")
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
            f"CryptoBot invoice created.\nPay URL:\n{pay_url}\n\nAfter payment tap 'Check CryptoBot payment' in Mini App."
        )
        return

    if action == "check_cryptobot_payment":
        invoice_id = str(payload.get("invoice_id", "")).strip()
        if not invoice_id:
            await message.answer("invoice_id is required.")
            return
        is_paid = await check_cryptobot_invoice(invoice_id)
        if not is_paid:
            await message.answer("Payment not found yet.")
            return
        intent = mark_payment_intent_paid("cryptobot", invoice_id)
        if not intent:
            await message.answer("Payment intent not found.")
            return
        add_wallet_transaction(
            user_id=int(intent["user_id"]),
            tx_type="deposit",
            amount=int(intent["amount"]),
            currency=CURRENCY,
            meta={"provider": "cryptobot", "invoice_id": invoice_id},
        )
        await message.answer(f"Top up completed: +{int(intent['amount'])} {CURRENCY}")
        return

    if action == "withdraw_create":
        amount = parse_int(payload, "amount")
        destination = str(payload.get("destination", "")).strip()
        if amount <= 0 or not destination:
            await message.answer("Invalid withdraw params.")
            return
        try:
            request_id = create_withdraw_request(user_id, amount, destination)
        except ValueError as exc:
            if str(exc) == "INSUFFICIENT_BALANCE":
                await message.answer("Insufficient balance for withdrawal.")
                return
            raise
        await message.answer(
            f"Withdraw request #{request_id} created.\nStatus: accepted by administration."
        )
        return

    if action == "leave_review":
        deal_id = parse_int(payload, "deal_id")
        rating = parse_int(payload, "rating")
        text = str(payload.get("text", "")).strip()
        deal = get_deal(deal_id)
        if not deal:
            await message.answer("Deal not found.")
            return
        if deal["status"] != "completed":
            await message.answer("Review allowed only for completed deal.")
            return
        if rating < 1 or rating > 5 or not text:
            await message.answer("Review must include rating 1..5 and text.")
            return
        if user_id == int(deal["buyer_id"]):
            target = int(deal["seller_id"])
        elif user_id == int(deal["seller_id"]):
            target = int(deal["buyer_id"])
        else:
            await message.answer("Forbidden.")
            return
        try:
            create_review(deal_id, user_id, target, rating, text)
        except Exception:
            await message.answer("Review already submitted for this deal.")
            return
        await message.answer("Review sent.")
        return

    await message.answer("Unknown action.")


async def handle_webapp_data(message: Message, bot: Bot) -> None:
    if message.from_user is None or message.web_app_data is None:
        return

    upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name or "User",
    )

    payload_raw = message.web_app_data.data
    try:
        payload: dict[str, Any] = json.loads(payload_raw)
    except json.JSONDecodeError:
        await message.answer("Invalid data from Mini App.")
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
    await message.answer(f"Top up completed: +{int(intent['amount'])} {CURRENCY}")


async def handle_deal_callback(callback: CallbackQuery, bot: Bot) -> None:
    if callback.data is None or callback.from_user is None:
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Bad action", show_alert=True)
        return
    _, action, deal_raw = parts
    if not deal_raw.isdigit():
        await callback.answer("Bad deal id", show_alert=True)
        return
    deal_id = int(deal_raw)
    try:
        if action == "accept":
            deal = accept_deal(deal_id, callback.from_user.id)
            await callback.answer("Deal accepted")
            await bot.send_message(
                int(deal["buyer_id"]),
                f"Deal #{deal_id} accepted by seller.",
            )
        elif action == "delivered":
            deal = mark_delivered(deal_id, callback.from_user.id)
            await callback.answer("Marked as delivered")
            await bot.send_message(
                int(deal["buyer_id"]),
                f"Deal #{deal_id} marked as delivered.",
                reply_markup=deal_actions_keyboard(deal_id, "buyer", "delivered"),
            )
        elif action == "confirm":
            deal = confirm_deal(deal_id, callback.from_user.id)
            await callback.answer("Deal completed")
            await bot.send_message(
                int(deal["seller_id"]),
                f"Deal #{deal_id} completed. Funds released.",
            )
            await bot.send_message(
                int(deal["buyer_id"]),
                f"Deal #{deal_id} completed. You can leave a review in Mini App.",
            )
        else:
            await callback.answer("Unknown action", show_alert=True)
            return
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)


async def handle_admin_withdraws(message: Message) -> None:
    if message.from_user is None or message.from_user.id not in settings.admin_ids:
        await message.answer("Admin only.")
        return
    rows = list_pending_withdraw_requests()
    if not rows:
        await message.answer("No pending withdraw requests.")
        return
    lines = ["Pending withdrawals:"]
    for row in rows:
        lines.append(
            f"#{row['id']} user:{row['user_id']} amount:{row['amount']} {CURRENCY} destination:{row['destination']}"
        )
    await message.answer("\n".join(lines))


async def handle_admin_approve(message: Message) -> None:
    if message.from_user is None or message.from_user.id not in settings.admin_ids:
        await message.answer("Admin only.")
        return
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Usage: /approve_withdraw <id>")
        return
    request_id = int(parts[1])
    row = approve_withdraw_request(request_id, admin_note="accepted by administration")
    if not row:
        await message.answer("Request not found or already processed.")
        return
    await message.answer(f"Withdraw #{request_id} approved.")
    await message.bot.send_message(
        int(row["user_id"]),
        f"Withdraw #{request_id} status: accepted by administration.",
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.message.register(handle_start, CommandStart())
    dp.message.register(handle_balance, F.text == "/balance")
    dp.message.register(handle_deals, F.text == "/deals")
    dp.message.register(handle_admin_withdraws, F.text == "/admin_withdraws")
    dp.message.register(handle_admin_approve, F.text.startswith("/approve_withdraw"))
    dp.pre_checkout_query.register(handle_pre_checkout_query)
    dp.message.register(handle_successful_payment, F.successful_payment)
    dp.callback_query.register(handle_deal_callback, F.data.startswith("deal:"))
    dp.message.register(handle_webapp_data, F.web_app_data)
    return dp
=======
import json
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from app.config import settings
from app.db import create_deal, get_user_by_username, upsert_user


def build_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="Open Mini App",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        ],
        resize_keyboard=True,
    )


async def handle_start(message: Message) -> None:
    if message.from_user is None:
        return

    upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name or "User",
    )

    await message.answer(
        "You are connected.\nUse Mini App button to create a deal invitation.",
        reply_markup=build_main_keyboard(),
    )


async def handle_webapp_data(message: Message, bot: Bot) -> None:
    if message.from_user is None or message.web_app_data is None:
        return

    upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name or "User",
    )

    payload_raw = message.web_app_data.data
    try:
        payload: dict[str, Any] = json.loads(payload_raw)
    except json.JSONDecodeError:
        await message.answer("Invalid data from Mini App.")
        return

    target_username = str(payload.get("target_username", "")).strip().lstrip("@")
    if not target_username:
        await message.answer("Username is empty.")
        return

    target_user = get_user_by_username(target_username)
    if not target_user:
        await message.answer(
            f"@{target_username} not found in bot.\n"
            "Ask this user to run /start first."
        )
        return

    if target_user.telegram_id == message.from_user.id:
        await message.answer("You cannot create a deal with yourself.")
        return

    deal_id = create_deal(message.from_user.id, target_user.telegram_id)
    sender_username = message.from_user.username or str(message.from_user.id)

    await bot.send_message(
        chat_id=target_user.telegram_id,
        text=(
            "New deal invitation\n\n"
            f"Deal ID: {deal_id}\n"
            f"From: @{sender_username}\n\n"
            "Open Mini App to continue."
        ),
        reply_markup=build_main_keyboard(),
    )

    await message.answer(
        f"Invitation sent to @{target_username}. Deal ID: {deal_id}",
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.message.register(handle_start, CommandStart())
    dp.message.register(handle_webapp_data, F.web_app_data)
    return dp
>>>>>>> 812b10437b3ace4a467d917045a8e96128a6b6a4

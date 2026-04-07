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

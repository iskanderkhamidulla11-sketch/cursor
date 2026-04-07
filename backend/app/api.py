import json
from typing import Optional

import aiohttp_cors
from aiohttp import web

from app.config import settings
from app.db import (
    get_deal,
    get_profile_stats,
    list_chat_messages,
    list_user_deals_by_filter,
    wallet_balance,
)


async def get_profile(request: web.Request) -> web.Response:
    user_id = int(request.query.get("user_id", 0))
    if not user_id:
        return web.json_response({"error": "user_id required"}, status=400)
    stats = get_profile_stats(user_id)
    return web.json_response(stats)


async def get_deals(request: web.Request) -> web.Response:
    user_id = int(request.query.get("user_id", 0))
    status_filter = request.query.get("status_filter", "active")
    if not user_id:
        return web.json_response({"error": "user_id required"}, status=400)
    deals = list_user_deals_by_filter(user_id, status_filter)
    data = [dict(row) for row in deals]
    return web.json_response(data)


async def get_deal_detail(request: web.Request) -> web.Response:
    user_id = int(request.query.get("user_id", 0))
    deal_id = int(request.match_info.get("deal_id", 0))
    if not user_id or not deal_id:
        return web.json_response({"error": "user_id and deal_id required"}, status=400)
    deal = get_deal(deal_id)
    if not deal or user_id not in (int(deal["buyer_id"]), int(deal["seller_id"])):
        return web.json_response({"error": "not found"}, status=404)
    return web.json_response(dict(deal))


async def get_chat(request: web.Request) -> web.Response:
    user_id = int(request.query.get("user_id", 0))
    deal_id = int(request.match_info.get("deal_id", 0))
    if not user_id or not deal_id:
        return web.json_response({"error": "user_id and deal_id required"}, status=400)
    deal = get_deal(deal_id)
    if not deal or user_id not in (int(deal["buyer_id"]), int(deal["seller_id"])):
        return web.json_response({"error": "not found"}, status=404)
    messages = list_chat_messages(deal_id, user_id)
    data = [dict(row) for row in messages]
    return web.json_response(data)


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/profile", get_profile)
    app.router.add_get("/api/deals", get_deals)
    app.router.add_get("/api/deal/{deal_id}", get_deal_detail)
    app.router.add_get("/api/chat/{deal_id}", get_chat)

    # Enable CORS for all origins (for local development)
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    for route in list(app.router.routes()):
        cors.add(route)

    return app
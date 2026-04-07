import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot

from app.bot import create_dispatcher
from app.config import settings
from app.db import init_db, get_user, list_user_deals_by_filter, get_profile_stats, get_deal, list_chat_messages


async def api_deals(request):
    user_id = int(request.query.get('user_id', 0))
    status_filter = request.query.get('status_filter', 'active')
    if not user_id:
        return web.json_response({'error': 'user_id required'}, status=400)
    deals = list_user_deals_by_filter(user_id, status_filter)
    return web.json_response([dict(row) for row in deals])


async def api_profile(request):
    user_id = int(request.query.get('user_id', 0))
    if not user_id:
        return web.json_response({'error': 'user_id required'}, status=400)
    stats = get_profile_stats(user_id)
    return web.json_response(stats)


async def api_deal(request):
    user_id = int(request.query.get('user_id', 0))
    deal_id = int(request.match_info['deal_id'])
    if not user_id:
        return web.json_response({'error': 'user_id required'}, status=400)
    deal = get_deal(deal_id)
    if not deal or user_id not in (int(deal['buyer_id']), int(deal['seller_id'])):
        return web.json_response({'error': 'not found'}, status=404)
    return web.json_response(dict(deal))


async def api_chat(request):
    user_id = int(request.query.get('user_id', 0))
    deal_id = int(request.match_info['deal_id'])
    if not user_id:
        return web.json_response({'error': 'user_id required'}, status=400)
    deal = get_deal(deal_id)
    if not deal or user_id not in (int(deal['buyer_id']), int(deal['seller_id'])):
        return web.json_response({'error': 'not found'}, status=404)
    messages = list_chat_messages(deal_id, user_id)
    return web.json_response([dict(row) for row in messages])


async def run() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is empty. Set it in environment variables.")
    if not settings.webapp_url:
        raise RuntimeError("WEBAPP_URL is empty. Set GitHub Pages URL.")

    init_db()
    bot = Bot(token=settings.bot_token)
    dp = create_dispatcher()

    # Create aiohttp app for API
    from aiohttp import web
    from aiohttp.web_middlewares import middleware
    from aiohttp_cors import setup as setup_cors, ResourceOptions

    app = web.Application()
    app.router.add_get('/api/deals', api_deals)
    app.router.add_get('/api/profile', api_profile)
    app.router.add_get('/api/deal/{deal_id}', api_deal)
    app.router.add_get('/api/chat/{deal_id}', api_chat)

    # Enable CORS for all origins (for development)
    cors = setup_cors(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    # Run both bot and web server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    print("API server started on http://localhost:8080")

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())

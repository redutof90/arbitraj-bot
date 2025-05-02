# --- Установка библиотек автоматически (если их нет)
import os

try:
    import aiohttp
    import aiogram
    import apscheduler
    import flask
except ImportError:
    os.system('pip install aiogram aiohttp apscheduler flask')

# --- Основной код ---
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from flask import Flask
from threading import Thread
from datetime import datetime

BOT_TOKEN = "7463541137:AAH7p6_PpWJ96-jkG1qlcPzmTdJ6Ce8nBrU"
CHANNEL_ID = "@parserspred"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
scheduler = AsyncIOScheduler()

async def get_mexc_prices():
    url = "https://api.mexc.com/api/v3/ticker/bookTicker"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            prices = {item['symbol']: float(item['askPrice']) for item in data}
            return prices

async def get_gmgn_prices():
    url = "https://api.dexscreener.com/latest/dex/pairs/gmgn"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            prices = {}
            for pair in data['pairs']:
                token_symbol = pair['baseToken']['symbol']
                price_usd = pair['priceUsd']
                if price_usd:
                    prices[token_symbol] = float(price_usd)
            return prices

async def check_spreads():
    try:
        mexc_prices = await get_mexc_prices()
        gmgn_prices = await get_gmgn_prices()
        messages = []

        for symbol, gmgn_price in gmgn_prices.items():
            mexc_symbol = symbol.upper() + "USDT"
            mexc_price = mexc_prices.get(mexc_symbol)

            if mexc_price:
                spread = (mexc_price - gmgn_price) / gmgn_price * 100
                if spread >= 5:
                    msg = (
                        f"⚡ <b>Спред найден!</b>\n\n"
                        f"<b>Токен:</b> {symbol}\n"
                        f"<b>MEXC:</b> {mexc_price:.4f} USDT\n"
                        f"<b>GMGN:</b> {gmgn_price:.4f} USDT\n"
                        f"<b>Разница:</b> +{spread:.2f}%"
                    )
                    messages.append(msg)

        now = datetime.now().strftime("%d.%m.%Y %H:%M")

        if messages:
            full_message = "\n\n".join(messages)
            full_message += f"\n\n🕐 Проверка: {now}"
        else:
            full_message = (
                f"❌ <b>Нет выгодных спредов сейчас.</b>\n"
                f"🕐 Проверка: {now}"
            )

        sent_message = await bot.send_message(chat_id=CHANNEL_ID, text=full_message)
        await asyncio.sleep(600)
        await bot.delete_message(chat_id=CHANNEL_ID, message_id=sent_message.message_id)

    except Exception as e:
        print(f"Ошибка: {e}")

# --- Flask-сервер для поддержания активности ---
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- Запуск бота ---
async def start_bot():
    scheduler.add_job(check_spreads, "interval", minutes=5)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive()
    asyncio.run(start_bot())

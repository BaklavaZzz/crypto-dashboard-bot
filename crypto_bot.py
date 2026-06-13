import telebot
import requests
from telebot import types
from PIL import Image, ImageDraw, ImageFont
import io
import os
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

def get_crypto_data():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": "bitcoin,ethereum,solana,the-open-network,litecoin,monero,ripple,binancecoin,tron",
            "order": "market_cap_desc",
            "per_page": 250,
            "page": 1,
            "sparkline": False,
            "price_change_percentage": "24h"
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except:
        return None

def generate_dashboard_image(data):
    if not data:
        return None

    width, height = 1200, 1750
    img = Image.new('RGB', (width, height), '#0A0C10')
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 72)
        font_subtitle = ImageFont.truetype("DejaVuSans.ttf", 32)
        font_name = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
        font_price = ImageFont.truetype("DejaVuSans-Bold.ttf", 52)
        font_change = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 28)
    except:
        font_title = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()
        font_name = ImageFont.load_default()
        font_price = ImageFont.load_default()
        font_change = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # === Header ===
    draw.text((width//2, 50), "Crypto Dashboard", font=font_title, fill='#FFFFFF', anchor='mt')
    draw.text((width//2, 135), "Live Prices • 24h Change", font=font_subtitle, fill='#8B949E', anchor='mt')

    # === Cards ===
    card_w, card_h = 365, 255
    start_y = 210
    gap_x, gap_y = 28, 22
    margin_x = 38

    coin_dict = {c['id']: c for c in data}
    order = ['bitcoin', 'ethereum', 'solana', 'the-open-network',
             'litecoin', 'monero', 'ripple', 'binancecoin', 'tron']

    card_colors = {
        'bitcoin': '#C47E3A', 'ethereum': '#627EEA', 'solana': '#00D4FF',
        'the-open-network': '#0099FF', 'litecoin': '#345D9D',
        'monero': '#FF6B00', 'ripple': '#23292F', 'binancecoin': '#F0B90B',
        'tron': '#EF0027'
    }

    icons = {
        'bitcoin': '₿', 'ethereum': 'Ξ', 'solana': '◎',
        'the-open-network': 'TON', 'litecoin': 'Ł', 'monero': 'ɱ',
        'ripple': 'XRP', 'binancecoin': 'BNB', 'tron': 'TRX'
    }

    for idx, coin_id in enumerate(order):
        if coin_id not in coin_dict:
            continue
        coin = coin_dict[coin_id]
        col = idx % 3
        row = idx // 3

        x = margin_x + col * (card_w + gap_x)
        y = start_y + row * (card_h + gap_y)
        color = card_colors.get(coin_id, '#333333')

        # Shadow
        draw.rounded_rectangle([x+6, y+6, x+card_w+6, y+card_h+6], radius=30, fill='#000000')
        # Card
        draw.rounded_rectangle([x, y, x+card_w, y+card_h], radius=30, fill=color)

        # Icon circle with border
        cx, cy = x + 58, y + 58
        draw.ellipse([cx-42, cy-42, cx+42, cy+42], fill='#FFFFFF')
        draw.ellipse([cx-38, cy-38, cx+38, cy+38], outline=color, width=4)
        draw.text((cx, cy), icons.get(coin_id, '🪙'), font=font_name, fill=color, anchor='mm')

        # Name
        draw.text((x + 110, y + 32), coin['name'], font=font_name, fill='#FFFFFF')
        draw.text((x + 110, y + 75), f"({coin['symbol'].upper()})", font=font_small, fill='#E0E0E0')

        # Price
        price = coin['current_price']
        price_str = f"${price:,.2f}" if price >= 1 else f"${price:.4f}"
        draw.text((x + 35, y + 130), price_str, font=font_price, fill='#FFFFFF')

        # 24h Change
        change = coin.get('price_change_percentage_24h', 0) or 0
        if change >= 0:
            ch_color = '#00FF9F'
            ch_text = f"+{change:.2f}%"
        else:
            ch_color = '#FF4757'
            ch_text = f"{change:.2f}%"
        draw.text((x + 35, y + 195), ch_text, font=font_change, fill=ch_color)

    # === Footer ===
    now = datetime.now().strftime("%H:%M")
    draw.text((width//2, height - 70), f"Updated just now • {now}", 
              font=font_small, fill='#8B949E', anchor='ms')
    draw.text((width//2, height - 35), "Powered by CoinGecko", 
              font=font_small, fill='#6E7681', anchor='ms')

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

def send_dashboard(chat_id):
    data = get_crypto_data()
    img = generate_dashboard_image(data)
    if not img:
        bot.send_message(chat_id, "❌ Could not load prices right now.")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Refresh Dashboard", callback_data="refresh"))

    bot.send_photo(chat_id, img, caption="📊 Crypto Dashboard", reply_markup=markup)

@bot.message_handler(commands=['start', 'help'])
def start(message):
    bot.send_message(message.chat.id,
        "👋 Welcome to your beautiful Crypto Dashboard!\n\n"
        "Send /prices to see the live image.",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("📊 Show Dashboard", callback_data="show")
        ))

@bot.message_handler(commands=['prices'])
def prices_cmd(message):
    send_dashboard(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data in ["show", "refresh"])
def callback(call):
    send_dashboard(call.message.chat.id)
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    print("🚀 Beautiful Crypto Dashboard Bot is running...")
    bot.polling(none_stop=True)

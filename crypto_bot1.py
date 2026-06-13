import telebot
import requests
from telebot import types
from PIL import Image, ImageDraw, ImageFont
import io

TOKEN = "8939427736:AAGrJTd7jMsB3WFT3w4O5EbaJqO6LZe41AQ"   # ← Do NOT change this here
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

    width, height = 1200, 1700
    img = Image.new('RGB', (width, height), '#0D1117')
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 68)
        font_name = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
        font_price = ImageFont.truetype("DejaVuSans-Bold.ttf", 46)
        font_change = ImageFont.truetype("DejaVuSans.ttf", 30)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 26)
    except:
        font_title = ImageFont.load_default()
        font_name = ImageFont.load_default()
        font_price = ImageFont.load_default()
        font_change = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.text((width//2, 55), "Crypto Dashboard", font=font_title, fill='white', anchor='mt')
    draw.text((width//2, 130), "Live Prices • 24h Change", font=font_small, fill='#8B949E', anchor='mt')

    card_w, card_h = 360, 240
    start_y = 200
    gap_x, gap_y = 30, 25
    margin_x = 40

    coin_dict = {c['id']: c for c in data}
    order = ['bitcoin', 'ethereum', 'solana', 'the-open-network',
             'litecoin', 'monero', 'ripple', 'binancecoin', 'tron']

    card_colors = {
        'bitcoin': '#C47E3A', 'ethereum': '#627EEA', 'solana': '#00D4FF',
        'the-open-network': '#0099FF', 'litecoin': '#345D9D',
        'monero': '#FF6B00', 'ripple': '#1E252F', 'binancecoin': '#F0B90B',
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

        draw.rounded_rectangle([x+5, y+5, x+card_w+5, y+card_h+5], radius=28, fill='#000000')
        draw.rounded_rectangle([x, y, x+card_w, y+card_h], radius=28, fill=color)

        cx, cy = x + 55, y + 55
        draw.ellipse([cx-38, cy-38, cx+38, cy+38], fill='white')
        draw.text((cx, cy), icons.get(coin_id, '🪙'), font=font_name, fill=color, anchor='mm')

        draw.text((x + 105, y + 30), coin['name'], font=font_name, fill='white')
        draw.text((x + 105, y + 70), f"({coin['symbol'].upper()})", font=font_small, fill='#E0E0E0')

        price = coin['current_price']
        price_str = f"${price:,.2f}" if price >= 1 else f"${price:.4f}"
        draw.text((x + 30, y + 125), price_str, font=font_price, fill='white')

        change = coin.get('price_change_percentage_24h', 0) or 0
        if change >= 0:
            ch_color, ch_text = '#00FF9F', f"+{change:.2f}%"
        else:
            ch_color, ch_text = '#FF4757', f"{change:.2f}%"
        draw.text((x + 30, y + 185), ch_text, font=font_change, fill=ch_color)

    draw.text((width//2, height - 55), "Live via CoinGecko • Pull to refresh", 
              font=font_small, fill='#8B949E', anchor='ms')

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

def send_dashboard(chat_id):
    data = get_crypto_data()
    img = generate_dashboard_image(data)
    if not img:
        bot.send_message(chat_id, "❌ Could not load prices. Try again.")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Refresh Dashboard", callback_data="refresh"))

    bot.send_photo(chat_id, img, caption="📊 Crypto Dashboard • Live", reply_markup=markup)

@bot.message_handler(commands=['start', 'help'])
def start(message):
    bot.send_message(message.chat.id,
        "👋 Welcome!\n\nThis bot sends a beautiful crypto dashboard image.\nUse /prices",
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
    print("🚀 Crypto Image Dashboard Bot running...")
    bot.polling(none_stop=True)

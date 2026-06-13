import telebot
import requests
from telebot import types
from PIL import Image, ImageDraw, ImageFont
import io, math, os
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
COINS = [
    "bitcoin", "ethereum", "solana",
    "the-open-network", "litecoin", "monero",
    "ripple", "binancecoin", "tron",
]

CARD_META = {
    "bitcoin":          {"name":"Bitcoin",  "sym":"BTC", "icon":"₿",   "icon_bg":(230,135,0),   "glow":(180,90,5),   "grad_a":(95,50,5),   "grad_b":(18,10,2),   "price_col":(255,175,50)},
    "ethereum":         {"name":"Ethereum", "sym":"ETH", "icon":"Ξ",   "icon_bg":(90,120,220),  "glow":(55,80,190),  "grad_a":(35,48,125), "grad_b":(8,12,32),   "price_col":(120,155,255)},
    "solana":           {"name":"Solana",   "sym":"SOL", "icon":"◎",   "icon_bg":(120,70,215),  "glow":(80,35,175),  "grad_a":(45,20,105), "grad_b":(8,6,25),    "price_col":(165,115,255)},
    "the-open-network": {"name":"Toncoin",  "sym":"TON", "icon":"TON", "icon_bg":(35,125,215),  "glow":(18,75,175),  "grad_a":(14,48,120), "grad_b":(5,12,35),   "price_col":(75,165,255)},
    "litecoin":         {"name":"Litecoin", "sym":"LTC", "icon":"Ł",   "icon_bg":(70,115,200),  "glow":(38,75,165),  "grad_a":(25,48,110), "grad_b":(6,12,32),   "price_col":(115,155,240)},
    "monero":           {"name":"Monero",   "sym":"XMR", "icon":"ɱ",   "icon_bg":(215,95,25),   "glow":(175,55,8),   "grad_a":(100,32,5),  "grad_b":(15,6,2),    "price_col":(255,135,55)},
    "ripple":           {"name":"XRP",      "sym":"XRP", "icon":"✕",   "icon_bg":(75,85,108),   "glow":(38,46,66),   "grad_a":(22,26,38),  "grad_b":(6,8,14),    "price_col":(155,165,188)},
    "binancecoin":      {"name":"BNB",      "sym":"BNB", "icon":"BNB", "icon_bg":(205,160,15),  "glow":(155,115,6),  "grad_a":(90,62,3),   "grad_b":(15,11,1),   "price_col":(255,205,55)},
    "tron":             {"name":"Tron",     "sym":"TRX", "icon":"TRX", "icon_bg":(215,25,45),   "glow":(175,8,28),   "grad_a":(100,5,14),  "grad_b":(15,2,5),    "price_col":(255,85,95)},
}

LOGO_URLS = {
    "bitcoin":          "https://assets.coingecko.com/coins/images/1/large/bitcoin.png",
    "ethereum":         "https://assets.coingecko.com/coins/images/279/large/ethereum.png",
    "solana":           "https://assets.coingecko.com/coins/images/4128/large/solana.png",
    "the-open-network": "https://assets.coingecko.com/coins/images/17980/large/ton_symbol.png",
    "litecoin":         "https://assets.coingecko.com/coins/images/2/large/litecoin.png",
    "monero":           "https://assets.coingecko.com/coins/images/69/large/monero_logo.png",
    "ripple":           "https://assets.coingecko.com/coins/images/44/large/xrp-symbol-white-128.png",
    "binancecoin":      "https://assets.coingecko.com/coins/images/825/large/bnb-icon2_2x.png",
    "tron":             "https://assets.coingecko.com/coins/images/1094/large/tron-logo.png",
}

BG         = (6, 8, 12)
TEXT_WHITE = (255, 255, 255)
TEXT_DIM   = (155, 160, 175)
GREEN      = (35, 225, 135)
RED        = (255, 75, 75)

POPPINS  = "/usr/share/fonts/truetype/google-fonts/Poppins-{}.ttf"
DEJAVU_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def get_logo(coin_id):
    """Download logo (works even if can't save to disk on GitHub/deploy)"""
    path = f"icons/{coin_id}.png"
    
    # Try load from disk first
    if os.path.exists(path):
        try:
            return Image.open(path).convert("RGBA")
        except:
            pass

    # Download
    try:
        r = requests.get(LOGO_URLS[coin_id], timeout=15)
        if r.status_code == 200:
            logo_bytes = r.content
            logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
            
            # Try to save for next time (only if possible)
            try:
                os.makedirs("icons", exist_ok=True)
                with open(path, "wb") as f:
                    f.write(logo_bytes)
            except:
                pass  # Can't write (GitHub/deploy) → still works from memory
            
            return logo
    except:
        pass
    
    return None


def get_crypto_data():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": ",".join(COINS),
            "order": "market_cap_desc",
            "per_page": 50,
            "page": 1,
            "sparkline": False,
            "price_change_percentage": "24h",
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return {c["id"]: c for c in r.json()}
    except:
        return None


def pfont(weight, size):
    try:
        return ImageFont.truetype(POPPINS.format(weight), size)
    except:
        return ImageFont.truetype(DEJAVU_B, size)


def gradient_rect(img, x0, y0, x1, y1, top, bot, radius=22):
    h = y1 - y0
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(h):
        t = i / max(h - 1, 1)
        c = tuple(int(a + (b - a) * t) for a, b in zip(top, bot))
        d.line([(x0, y0 + i), (x1, y0 + i)], fill=c + (255,))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=255)
    img.paste(overlay.convert("RGB"), mask=mask)


def draw_glow(img, cx, cy, r, color):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(36, 0, -1):
        alpha = int(55 * (i / 36) ** 0.65)
        ri = int(r * i / 36)
        d.ellipse([cx-ri, cy-ri, cx+ri, cy+ri], fill=color + (alpha,))
    img.paste(overlay, mask=overlay.split()[3])


def fmt_price(p):
    if p is None: return "$—"
    if p >= 1000: return f"${p:,.2f}"
    if p >= 1:    return f"${p:.2f}"
    return f"${p:.4f}"


def generate_dashboard_image(data):
    if not data: return None

    COLS, CARD_W, CARD_H = 3, 370, 232
    GAP_X, GAP_Y, PAD = 20, 18, 26
    ROWS = math.ceil(len(COINS) / COLS)

    W = PAD * 2 + COLS * CARD_W + (COLS-1) * GAP_X
    H = PAD * 2 + ROWS * CARD_H + (ROWS-1) * GAP_Y

    img = Image.new("RGB", (W, H), BG)

    f_name  = pfont("Bold", 30)
    f_sym   = pfont("Regular", 17)
    f_price = pfont("Bold", 48)
    f_chg   = pfont("Bold", 18)
    f_fallback = pfont("Bold", 22)

    for idx, coin_id in enumerate(COINS):
        meta = CARD_META[coin_id]
        coin = data.get(coin_id, {})
        col = idx % COLS
        row = idx // COLS

        x = PAD + col * (CARD_W + GAP_X)
        y = PAD + row * (CARD_H + GAP_Y)

        draw_glow(img, x + CARD_W//2, y + CARD_H//2, CARD_W//2 + 8, meta["glow"])
        gradient_rect(img, x, y, x + CARD_W, y + CARD_H, meta["grad_a"], meta["grad_b"], radius=22)

        draw = ImageDraw.Draw(img, "RGBA")
        draw.rounded_rectangle([x, y, x+CARD_W, y+CARD_H], radius=22, outline=(255,255,255,20), width=1)

        # === REAL LOGO or FALLBACK ===
        logo = get_logo(coin_id)
        icx, icy = x + 48, y + 52
        logo_size = 58

        if logo:
            logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
            mask = Image.new("L", (logo_size, logo_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, logo_size-1, logo_size-1), fill=255)
            logo.putalpha(mask)
            img.paste(logo, (icx - logo_size//2, icy - logo_size//2), logo)
        else:
            # Fallback nice circle + symbol
            draw.ellipse([icx-32, icy-32, icx+32, icy+32], fill=meta["icon_bg"])
            draw.ellipse([icx-32, icy-32, icx+32, icy+32], outline=(255,255,255,40), width=2)
            draw.text((icx, icy), meta["icon"], font=f_fallback, fill=(255,255,255), anchor="mm")

        # Name + Ticker
        draw.text((x + 95, y + 28), meta["name"], font=f_name, fill=TEXT_WHITE)
        draw.text((x + 95, y + 62), meta["sym"], font=f_sym, fill=TEXT_DIM)

        # Price
        draw.text((x + 20, y + 108), fmt_price(coin.get("current_price")), font=f_price, fill=meta["price_col"])

        # Change badge
        chg = coin.get("price_change_percentage_24h") or 0
        up = chg >= 0
        color = GREEN if up else RED
        arrow = "▲" if up else "▼"
        text = f"{arrow} +{chg:.2f}%" if up else f"{arrow} {chg:.2f}%"

        badge_color = (0, 95, 55, 115) if up else (130, 25, 25, 115)
        bbox = draw.textbbox((0,0), text, font=f_chg)
        tw = bbox[2] - bbox[0]
        bx, by = x + 18, y + CARD_H - 44
        draw.rounded_rectangle([bx-6, by-3, bx + tw + 9, by + 26], radius=8, fill=badge_color)
        draw.text((bx, by), text, font=f_chg, fill=color)

    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf


# ── Bot handlers ──
def refresh_button():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="refresh"))
    return markup

def send_dashboard(chat_id, call=None):
    if call:
        bot.answer_callback_query(call.id, "Updating prices...")
    data = get_crypto_data()
    img = generate_dashboard_image(data)
    if not img:
        bot.send_message(chat_id, "Error loading prices.")
        return
    caption = f"📊 Crypto Dashboard • {datetime.now().strftime('%H:%M UTC')}"
    bot.send_photo(chat_id, img, caption=caption, reply_markup=refresh_button())

@bot.message_handler(commands=["start", "prices"])
def start(message):
    send_dashboard(message.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "refresh")
def refresh(call):
    send_dashboard(call.message.chat.id, call)

print("🚀 Bot running (GitHub/deploy friendly)...")
bot.infinity_polling()

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
    "bitcoin":          {"name":"Bitcoin",  "sym":"BTC", "icon_label":"₿",   "icon_bg":(230,135,0),   "glow":(180,90,5),   "grad_a":(95,50,5),   "grad_b":(20,12,3),  "price_col":(255,175,50)},
    "ethereum":         {"name":"Ethereum", "sym":"ETH", "icon_label":"Ξ",   "icon_bg":(90,120,220),  "glow":(55,80,190),  "grad_a":(38,52,130), "grad_b":(10,15,35), "price_col":(120,155,255)},
    "solana":           {"name":"Solana",   "sym":"SOL", "icon_label":"◎",   "icon_bg":(120,70,215),  "glow":(80,35,175),  "grad_a":(48,22,108), "grad_b":(10,7,28),  "price_col":(165,115,255)},
    "the-open-network": {"name":"Toncoin",  "sym":"TON", "icon_label":"TON", "icon_bg":(35,125,215),  "glow":(18,75,175),  "grad_a":(16,52,125), "grad_b":(6,15,38),  "price_col":(75,165,255)},
    "litecoin":         {"name":"Litecoin", "sym":"LTC", "icon_label":"Ł",   "icon_bg":(70,115,200),  "glow":(38,75,165),  "grad_a":(28,52,115), "grad_b":(8,15,34),  "price_col":(115,155,240)},
    "monero":           {"name":"Monero",   "sym":"XMR", "icon_label":"M",   "icon_bg":(215,95,25),   "glow":(175,55,8),   "grad_a":(105,35,6),  "grad_b":(18,8,3),   "price_col":(255,135,55)},
    "ripple":           {"name":"XRP",      "sym":"XRP", "icon_label":"✕",   "icon_bg":(75,85,108),   "glow":(38,46,66),   "grad_a":(26,30,42),  "grad_b":(8,10,16),  "price_col":(155,165,188)},
    "binancecoin":      {"name":"BNB",      "sym":"BNB", "icon_label":"BNB", "icon_bg":(205,160,15),  "glow":(155,115,6),  "grad_a":(95,68,4),   "grad_b":(18,14,2),  "price_col":(255,205,55)},
    "tron":             {"name":"Tron",     "sym":"TRX", "icon_label":"TRX", "icon_bg":(215,25,45),   "glow":(175,8,28),   "grad_a":(105,6,16),  "grad_b":(18,3,6),   "price_col":(255,85,95)},
}

BG         = (8, 10, 14)
TEXT_WHITE = (255, 255, 255)
TEXT_DIM   = (160, 165, 180)
GREEN      = (30, 220, 130)
RED        = (255, 80,  80)

POPPINS  = "/usr/share/fonts/truetype/google-fonts/Poppins-{}.ttf"
DEJAVU_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
DEJAVU   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


# ─────────────────────────────────────────────
#  DATA
# ─────────────────────────────────────────────
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
    except Exception:
        return None


# ─────────────────────────────────────────────
#  FONT HELPERS
# ─────────────────────────────────────────────
def pfont(weight, size):
    try:
        return ImageFont.truetype(POPPINS.format(weight), size)
    except Exception:
        try:
            f = DEJAVU_B if weight in ("Bold", "Medium", "SemiBold") else DEJAVU
            return ImageFont.truetype(f, size)
        except Exception:
            return ImageFont.load_default()

def dfont(size, bold=True):
    try:
        return ImageFont.truetype(DEJAVU_B if bold else DEJAVU, size)
    except Exception:
        return ImageFont.load_default()


# ─────────────────────────────────────────────
#  DRAWING HELPERS
# ─────────────────────────────────────────────
def blend(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))

def gradient_rect(img, x0, y0, x1, y1, top, bot, radius=26):
    h = y1 - y0
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(h):
        t = i / max(h - 1, 1)
        c = blend(top, bot, t)
        d.line([(x0, y0 + i), (x1, y0 + i)], fill=c + (255,))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=255)
    img.paste(overlay.convert("RGB"), mask=mask)

def draw_radial_glow(img, cx, cy, r, color, alpha=55, steps=40):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(steps, 0, -1):
        ri = int(r * i / steps)
        ai = int(alpha * (1 - i / steps) ** 0.65)
        d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=color + (ai,))
    img.paste(overlay, mask=overlay.split()[3])

def draw_subtle_pattern(draw, x, y, w, h, symbol, base_color, opacity=12):
    """Faint repeating watermark pattern like in the goal image"""
    f = pfont("Bold", 28)
    for i in range(0, w, 85):
        for j in range(0, h, 70):
            alpha = opacity
            pos_x = x + i + 15
            pos_y = y + j + 10
            # Draw very faint symbol
            draw.text((pos_x, pos_y), symbol, font=f, fill=base_color + (alpha,))

def draw_icon_circle(draw, cx, cy, r, bg, label, fnt):
    # Soft outer glow
    glow_c = blend(bg, (255, 255, 255), 0.25)
    draw.ellipse([cx-r-4, cy-r-4, cx+r+4, cy+r+4], fill=glow_c + (28,))
    # Main circle
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=bg)
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=blend(bg, (255,255,255), 0.35), width=2)
    # Icon text
    draw.text((cx, cy), label, font=fnt, fill=(255, 255, 255), anchor="mm")

def fmt_price(p):
    if p is None: return "$—"
    if p >= 10000: return f"${p:,.2f}"
    if p >= 1000:  return f"${p:,.2f}"
    if p >= 1:     return f"${p:.2f}"
    return f"${p:.4f}"


# ─────────────────────────────────────────────
#  MAIN IMAGE GENERATOR
# ─────────────────────────────────────────────
def generate_dashboard_image(data):
    if not data:
        return None

    COLS   = 3
    CARD_W = 368
    CARD_H = 226
    GAP_X  = 20
    GAP_Y  = 18
    PAD    = 28
    ROWS   = math.ceil(len(COINS) / COLS)

    W = PAD * 2 + COLS * CARD_W + (COLS - 1) * GAP_X
    H = PAD * 2 + ROWS * CARD_H + (ROWS - 1) * GAP_Y

    img = Image.new("RGB", (W, H), BG)

    f_name  = pfont("Bold",    32)
    f_sym   = pfont("Regular", 18)
    f_price = pfont("Bold",    50)
    f_chg   = dfont(20)
    f_icon  = pfont("Bold",    22)

    for idx, coin_id in enumerate(COINS):
        meta = CARD_META.get(coin_id, {})
        coin = data.get(coin_id, {})
        col  = idx % COLS
        row  = idx // COLS

        x = PAD + col * (CARD_W + GAP_X)
        y = PAD + row * (CARD_H + GAP_Y)

        grad_a   = meta.get("grad_a",   (30, 35, 50))
        grad_b   = meta.get("grad_b",   (12, 14, 20))
        glow_col = meta.get("glow",     (40, 60, 120))
        icon_bg  = meta.get("icon_bg",  (80, 90, 110))
        p_col    = meta.get("price_col", TEXT_WHITE)
        icon_label = meta.get("icon_label", meta.get("abbr", "?"))

        # 1. Radial glow
        draw_radial_glow(img, x + CARD_W // 2, y + CARD_H // 2, CARD_W // 2 + 8, glow_col)

        # 2. Card gradient
        gradient_rect(img, x, y, x + CARD_W, y + CARD_H, grad_a, grad_b, radius=24)

        draw = ImageDraw.Draw(img, "RGBA")

        # 3. Subtle background pattern (the modern look)
        draw_subtle_pattern(draw, x, y, CARD_W, CARD_H, icon_label, icon_bg, opacity=9)

        # 4. Thin border
        draw.rounded_rectangle([x, y, x + CARD_W, y + CARD_H],
                                radius=24, outline=(255, 255, 255, 22), width=1)

        # 5. Icon circle
        ICX, ICY, IR = x + 48, y + 52, 32
        draw_icon_circle(draw, ICX, ICY, IR, icon_bg, icon_label, f_icon)

        # 6. Coin name
        draw.text((x + 95, y + 30), meta.get("name", coin_id), font=f_name, fill=TEXT_WHITE)

        # 7. Ticker
        draw.text((x + 95, y + 68), meta.get("sym", "???"), font=f_sym, fill=(170, 175, 195))

        # 8. Price
        draw.text((x + 22, y + 108), fmt_price(coin.get("current_price")), font=f_price, fill=p_col)

        # 9. 24h change badge
        chg   = coin.get("price_change_percentage_24h") or 0.0
        up    = chg >= 0
        c_chg = GREEN if up else RED
        arrow = "▲" if up else "▼"
        chg_t = f"{arrow} {'+' if up else ''}{chg:.2f}%"

        badge_bg = (0, 90, 55, 110) if up else (120, 25, 25, 110)
        bbox  = draw.textbbox((0, 0), chg_t, font=f_chg)
        tw    = bbox[2] - bbox[0]
        bx, by = x + 20, y + CARD_H - 46
        draw.rounded_rectangle([bx - 6, by - 4, bx + tw + 10, by + 28], radius=9, fill=badge_bg)
        draw.text((bx, by), chg_t, font=f_chg, fill=c_chg)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────
#  BOT HANDLERS (unchanged)
# ─────────────────────────────────────────────
def refresh_button():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄  Refresh", callback_data="refresh"))
    return markup


def send_dashboard(chat_id, call=None):
    if call:
        bot.answer_callback_query(call.id, "⏳ Fetching live prices…")
    data = get_crypto_data()
    img  = generate_dashboard_image(data)
    if not img:
        bot.send_message(chat_id, "❌ Could not load prices right now. Try again in a moment.")
        return
    caption = f"📊 *Crypto Dashboard*\n_Live prices • {datetime.now().strftime('%H:%M UTC')}_"
    bot.send_photo(chat_id, img, caption=caption,
                   parse_mode="Markdown", reply_markup=refresh_button())


@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📊  Show Dashboard", callback_data="show"))
    bot.send_message(
        message.chat.id,
        "👋 *Welcome to Crypto Dashboard Bot!*\n\n"
        "Get a beautiful live image of the top crypto prices.\n\n"
        "• /prices — generate the dashboard\n"
        "• /help — show this message",
        parse_mode="Markdown",
        reply_markup=markup,
    )


@bot.message_handler(commands=["prices"])
def cmd_prices(message):
    send_dashboard(message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data in ("show", "refresh"))
def cb_handler(call):
    send_dashboard(call.message.chat_id, call)


if __name__ == "__main__":
    print("🚀 Crypto Dashboard Bot is running…")
    bot.infinity_polling()

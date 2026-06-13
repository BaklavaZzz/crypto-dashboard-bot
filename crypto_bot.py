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
    "bitcoin":          {"name":"Bitcoin",  "sym":"BTC", "abbr":"BTC", "icon_bg":(230,135,0),   "glow":(180,90,5),   "grad_a":(95,50,5),   "grad_b":(20,12,3),  "price_col":(255,175,50)},
    "ethereum":         {"name":"Ethereum", "sym":"ETH", "abbr":"ETH", "icon_bg":(90,120,220),  "glow":(55,80,190),  "grad_a":(38,52,130), "grad_b":(10,15,35), "price_col":(120,155,255)},
    "solana":           {"name":"Solana",   "sym":"SOL", "abbr":"SOL", "icon_bg":(120,70,215),  "glow":(80,35,175),  "grad_a":(48,22,108), "grad_b":(10,7,28),  "price_col":(165,115,255)},
    "the-open-network": {"name":"Toncoin",  "sym":"TON", "abbr":"TON", "icon_bg":(35,125,215),  "glow":(18,75,175),  "grad_a":(16,52,125), "grad_b":(6,15,38),  "price_col":(75,165,255)},
    "litecoin":         {"name":"Litecoin", "sym":"LTC", "abbr":"LTC", "icon_bg":(70,115,200),  "glow":(38,75,165),  "grad_a":(28,52,115), "grad_b":(8,15,34),  "price_col":(115,155,240)},
    "monero":           {"name":"Monero",   "sym":"XMR", "abbr":"XMR", "icon_bg":(215,95,25),   "glow":(175,55,8),   "grad_a":(105,35,6),  "grad_b":(18,8,3),   "price_col":(255,135,55)},
    "ripple":           {"name":"XRP",      "sym":"XRP", "abbr":"XRP", "icon_bg":(75,85,108),   "glow":(38,46,66),   "grad_a":(26,30,42),  "grad_b":(8,10,16),  "price_col":(155,165,188)},
    "binancecoin":      {"name":"BNB",      "sym":"BNB", "abbr":"BNB", "icon_bg":(205,160,15),  "glow":(155,115,6),  "grad_a":(95,68,4),   "grad_b":(18,14,2),  "price_col":(255,205,55)},
    "tron":             {"name":"Tron",     "sym":"TRX", "abbr":"TRX", "icon_bg":(215,25,45),   "glow":(175,8,28),   "grad_a":(105,6,16),  "grad_b":(18,3,6),   "price_col":(255,85,95)},
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
    """Poppins with DejaVu fallback."""
    try:
        return ImageFont.truetype(POPPINS.format(weight), size)
    except Exception:
        try:
            f = DEJAVU_B if weight in ("Bold", "Medium", "SemiBold") else DEJAVU
            return ImageFont.truetype(f, size)
        except Exception:
            return ImageFont.load_default()

def dfont(size, bold=True):
    """DejaVu (has ▲▼ glyphs)."""
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

def draw_radial_glow(img, cx, cy, r, color, alpha=65, steps=35):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(steps, 0, -1):
        ri = int(r * i / steps)
        ai = int(alpha * (1 - i / steps) ** 0.6)
        d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=color + (ai,))
    img.paste(overlay, mask=overlay.split()[3])

def draw_icon_circle(draw, cx, cy, r, bg, label, fnt):
    glow_c = blend(bg, (255, 255, 255), 0.3)
    draw.ellipse([cx-r-3, cy-r-3, cx+r+3, cy+r+3], fill=glow_c + (35,))
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=bg)
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=blend(bg, (255,255,255), 0.4), width=2)
    draw.text((cx, cy), label, font=fnt, fill=(255, 255, 255), anchor="mm")

def fmt_price(p):
    if p is None: return "$—"
    if p >= 10_000: return f"${p:,.2f}"
    if p >= 1_000:  return f"${p:,.2f}"
    if p >= 1:      return f"${p:.2f}"
    return f"${p:.4f}"


# ─────────────────────────────────────────────
#  MAIN IMAGE GENERATOR
# ─────────────────────────────────────────────
def generate_dashboard_image(data):
    if not data:
        return None

    COLS   = 3
    CARD_W = 370
    CARD_H = 228
    GAP_X  = 22
    GAP_Y  = 18
    PAD    = 30
    ROWS   = math.ceil(len(COINS) / COLS)

    W = PAD * 2 + COLS * CARD_W + (COLS - 1) * GAP_X
    H = PAD * 2 + ROWS * CARD_H + (ROWS - 1) * GAP_Y

    img = Image.new("RGB", (W, H), BG)

    f_name  = pfont("Bold",    36)
    f_sym   = pfont("Regular", 20)
    f_price = pfont("Bold",    54)
    f_chg   = dfont(22)           # DejaVu so ▲▼ glyphs render
    f_icon  = pfont("Bold",    18)

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

        # 1. Radial glow
        draw_radial_glow(img, x + CARD_W // 2, y + CARD_H // 2, CARD_W // 2 + 10, glow_col)

        # 2. Card gradient
        gradient_rect(img, x, y, x + CARD_W, y + CARD_H, grad_a, grad_b, radius=26)

        draw = ImageDraw.Draw(img, "RGBA")

        # 3. Subtle border
        draw.rounded_rectangle([x, y, x + CARD_W, y + CARD_H],
                                radius=26, outline=(255, 255, 255, 28), width=1)

        # 4. Icon circle
        ICX, ICY, IR = x + 52, y + 56, 34
        draw_icon_circle(draw, ICX, ICY, IR, icon_bg, meta.get("abbr", "?"), f_icon)

        # 5. Coin name
        draw.text((x + 100, y + 34), meta.get("name", coin_id), font=f_name, fill=TEXT_WHITE)

        # 6. Ticker
        draw.text((x + 100, y + 76), meta.get("sym", "???"), font=f_sym, fill=(175, 180, 198))

        # 7. Price
        draw.text((x + 24, y + 120), fmt_price(coin.get("current_price")), font=f_price, fill=p_col)

        # 8. 24h badge
        chg   = coin.get("price_change_percentage_24h") or 0.0
        up    = chg >= 0
        c_chg = GREEN if up else RED
        arrow = "\u25b2" if up else "\u25bc"
        chg_t = f"{arrow} {'+' if up else ''}{chg:.2f}%"

        badge_bg = (0, 85, 48, 95) if up else (105, 18, 18, 95)
        bbox  = draw.textbbox((0, 0), chg_t, font=f_chg)
        tw    = bbox[2] - bbox[0]
        bx, by = x + 22, y + CARD_H - 48
        draw.rounded_rectangle([bx - 8, by - 5, bx + tw + 12, by + 30], radius=10, fill=badge_bg)
        draw.text((bx, by), chg_t, font=f_chg, fill=c_chg)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────
#  BOT HANDLERS
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
    send_dashboard(call.message.chat.id, call)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Crypto Dashboard Bot is running…")
    bot.infinity_polling()

import telebot
import requests
from telebot import types
from PIL import Image, ImageDraw, ImageFont
import io
import os
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
COINS = [
    "bitcoin", "ethereum", "solana", "the-open-network",
    "litecoin", "monero", "ripple", "binancecoin", "tron"
]

CARD_META = {
    "bitcoin":          {"sym": "BTC", "label": "₿",   "color": (156, 92,  26),  "dark": (90,  50,  10)},
    "ethereum":         {"sym": "ETH", "label": "Ξ",   "color": (58,  79,  181), "dark": (35,  50,  120)},
    "solana":           {"sym": "SOL", "label": "◎",   "color": (16,  127, 163), "dark": (10,  80,  105)},
    "the-open-network": {"sym": "TON", "label": "TON", "color": (16,  88,  176), "dark": (10,  55,  115)},
    "litecoin":         {"sym": "LTC", "label": "Ł",   "color": (42,  80,  152), "dark": (28,  52,  100)},
    "monero":           {"sym": "XMR", "label": "ɱ",   "color": (192, 74,  10),  "dark": (130, 45,  6)},
    "ripple":           {"sym": "XRP", "label": "✕",   "color": (26,  30,  38),  "dark": (12,  15,  22)},
    "binancecoin":      {"sym": "BNB", "label": "◈",   "color": (176, 128, 16),  "dark": (110, 80,  8)},
    "tron":             {"sym": "TRX", "label": "◆",   "color": (184, 0,   32),  "dark": (120, 0,   20)},
}

BG_COLOR   = (10, 12, 16)
TEXT_WHITE = (255, 255, 255)
TEXT_DIM   = (160, 165, 175)
GREEN      = (0,   255, 155)
RED        = (255, 85,  85)


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
#  DRAWING HELPERS
# ─────────────────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def blend(c1, c2, t=0.5):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def draw_rrect(draw, xy, radius, fill):
    """Draw a rounded rectangle as filled shape."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)

def draw_gradient_card(img, xy, color_top, color_bot, radius=22):
    """Simulate a two-tone gradient card using pillow strips."""
    x0, y0, x1, y1 = xy
    h = y1 - y0
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(h):
        t = i / h
        c = blend(color_top, color_bot, t)
        d.line([(x0, y0 + i), (x1, y0 + i)], fill=c + (255,))
    # Mask to rounded rect
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=255)
    img.paste(Image.new("RGB", img.size, (0, 0, 0)), mask=mask)
    img.paste(overlay.convert("RGB"), mask=mask)

def draw_glow_circle(draw, cx, cy, r, color, alpha_max=60):
    """Subtle glow ring around icon circle."""
    for i in range(3, 0, -1):
        a = int(alpha_max * (4 - i) / 3)
        c = color + (a,)
        draw.ellipse([cx - r - i*3, cy - r - i*3, cx + r + i*3, cy + r + i*3],
                     fill=None, outline=c + (0,) if len(c) == 3 else None)

def load_fonts():
    sizes = {
        "title":    80,
        "sub":      30,
        "coinname": 32,
        "price":    46,
        "sym":      22,
        "change":   26,
        "footer":   24,
        "icon":     28,
    }
    fonts = {}
    for key, size in sizes.items():
        bold = key in ("title", "coinname", "price", "change")
        try:
            fname = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
            fonts[key] = ImageFont.truetype(fname, size)
        except Exception:
            fonts[key] = ImageFont.load_default()
    return fonts


def fmt_price(p):
    if p is None:
        return "$—"
    if p >= 1_000:
        return f"${p:,.2f}"
    if p >= 1:
        return f"${p:.2f}"
    return f"${p:.4f}"


# ─────────────────────────────────────────────
#  MAIN IMAGE GENERATOR
# ─────────────────────────────────────────────
def generate_dashboard_image(data):
    if not data:
        return None

    W, H = 1200, 1680
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")
    fonts = load_fonts()

    # ── Header ───────────────────────────────
    draw.text((W // 2, 52), "Crypto Dashboard",
              font=fonts["title"], fill=TEXT_WHITE, anchor="mt")
    draw.text((W // 2, 145), "Live prices  ·  24 h change",
              font=fonts["sub"], fill=TEXT_DIM, anchor="mt")

    # Thin separator line
    draw.line([(60, 188), (W - 60, 188)], fill=(40, 45, 55), width=1)

    # ── Cards ────────────────────────────────
    COLS = 3
    CARD_W, CARD_H = 360, 240
    GAP_X, GAP_Y = 30, 22
    START_Y = 210
    MARGIN_X = (W - COLS * CARD_W - (COLS - 1) * GAP_X) // 2

    for idx, coin_id in enumerate(COINS):
        meta = CARD_META.get(coin_id, {})
        coin = data.get(coin_id, {})
        col = idx % COLS
        row = idx // COLS

        x = MARGIN_X + col * (CARD_W + GAP_X)
        y = START_Y + row * (CARD_H + GAP_Y)

        c_top = meta.get("color", (50, 50, 60))
        c_bot = meta.get("dark",  (30, 30, 40))

        # ── Card gradient ──
        draw_gradient_card(img, (x, y, x + CARD_W, y + CARD_H), c_top, c_bot, radius=22)
        draw2 = ImageDraw.Draw(img, "RGBA")

        # Subtle highlight border
        draw2.rounded_rectangle([x, y, x + CARD_W, y + CARD_H],
                                 radius=22, outline=(255, 255, 255, 18), width=1)

        # Decorative circle top-right
        draw2.ellipse([x + CARD_W - 85, y - 40, x + CARD_W + 40, y + 85],
                      fill=(*blend(c_top, (255, 255, 255), 0.08), 40))

        # ── Icon circle ──
        icx, icy = x + 52, y + 52
        IR = 34
        draw2.ellipse([icx - IR, icy - IR, icx + IR, icy + IR],
                      fill=(255, 255, 255, 38))
        draw2.ellipse([icx - IR + 2, icy - IR + 2, icx + IR - 2, icy + IR - 2],
                      outline=(255, 255, 255, 70), width=1)
        lbl = meta.get("label", "?")
        draw2.text((icx, icy), lbl, font=fonts["icon"], fill=TEXT_WHITE, anchor="mm")

        # ── Coin name + symbol ──
        name = coin.get("name", coin_id.capitalize())
        sym  = meta.get("sym", "???")
        draw2.text((x + 100, y + 28), name, font=fonts["coinname"], fill=TEXT_WHITE)
        draw2.text((x + 100, y + 68), sym,  font=fonts["sym"],      fill=(220, 220, 220, 160))

        # ── Price ──
        price_str = fmt_price(coin.get("current_price"))
        draw2.text((x + 24, y + 120), price_str, font=fonts["price"], fill=TEXT_WHITE)

        # ── 24h change badge ──
        chg = coin.get("price_change_percentage_24h") or 0.0
        up  = chg >= 0
        chg_color = GREEN if up else RED
        chg_text  = f"{'+'if up else ''}{chg:.2f}%"
        arrow     = "▲" if up else "▼"

        badge_bg = (0, 80, 50, 80) if up else (100, 20, 20, 80)
        # Measure text width for badge
        bbox = draw2.textbbox((0, 0), f"{arrow} {chg_text}", font=fonts["change"])
        tw = bbox[2] - bbox[0]
        bx, by = x + 22, y + 185
        draw2.rounded_rectangle([bx - 6, by - 4, bx + tw + 10, by + 30],
                                 radius=10, fill=badge_bg)
        draw2.text((bx, by), f"{arrow} {chg_text}", font=fonts["change"], fill=chg_color)

    # ── Footer ───────────────────────────────
    now = datetime.now().strftime("%d %b %Y · %H:%M")
    draw.line([(60, H - 90), (W - 60, H - 90)], fill=(40, 45, 55), width=1)
    draw.text((W // 2, H - 62), f"Updated {now}",
              font=fonts["footer"], fill=TEXT_DIM, anchor="ms")
    draw.text((W // 2, H - 32), "Powered by CoinGecko",
              font=fonts["footer"], fill=(90, 95, 105), anchor="ms")

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

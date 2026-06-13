import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from playwright.async_api import async_playwright
import aiohttp

# ==================== CONFIG ====================
BOT_TOKEN = "8809560356:AAEjqC8RA_AVevRoOfO_4m-oGwNke4tOMBo"   # ← Replace with your token from @BotFather
# ===============================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# CoinGecko coin IDs
COIN_IDS = "bitcoin,ethereum,solana,the-open-network,litecoin,monero,ripple,binancecoin,tron"

# Full HTML (Liquid Glass style - matches the AI image)
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Crypto • Liquid Glass</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&display=swap');
  body { font-family: 'Inter', system_ui, sans-serif; }
  .glass {
    background: rgba(20, 20, 30, 0.55);
    backdrop-filter: blur(28px);
    -webkit-backdrop-filter: blur(28px);
    border: 1px solid rgba(255,255,255,0.18);
    box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.5),
                inset 0 1px 0 rgba(255,255,255,0.25),
                inset 0 -1px 0 rgba(0,0,0,0.4);
  }
  .price { font-family: 'Space Grotesk', system_ui, sans-serif; font-feature-settings: "tnum"; }
  .cosmic-bg { background: radial-gradient(circle at center, #0f0f17 0%, #0a0a0f 70%); }
</style>
</head>
<body class="cosmic-bg text-white min-h-screen flex items-center justify-center p-8">
  <div class="max-w-[1080px] w-full">
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      
      <!-- Bitcoin -->
      <div class="glass rounded-[28px] p-7">
        <div class="flex items-center gap-4 mb-5">
          <div class="w-11 h-11 rounded-2xl bg-[#F7931A] flex items-center justify-center text-3xl shadow-inner">₿</div>
          <div><div class="font-semibold text-2xl tracking-tight">Bitcoin</div><div class="text-white/50 text-sm -mt-1">BTC</div></div>
        </div>
        <div class="price text-[42px] font-semibold tracking-[-2.5px] leading-none">{{BTC_PRICE}}</div>
        <div class="text-red-400 text-lg font-medium mt-1">{{BTC_CHANGE}}</div>
      </div>

      <!-- Ethereum -->
      <div class="glass rounded-[28px] p-7">
        <div class="flex items-center gap-4 mb-5">
          <div class="w-11 h-11 rounded-2xl bg-[#627EEA] flex items-center justify-center text-3xl">Ξ</div>
          <div><div class="font-semibold text-2xl tracking-tight">Ethereum</div><div class="text-white/50 text-sm -mt-1">ETH</div></div>
        </div>
        <div class="price text-[42px] font-semibold tracking-[-2.5px] leading-none">{{ETH_PRICE}}</div>
        <div class="text-red-400 text-lg font-medium mt-1">{{ETH_CHANGE}}</div>
      </div>

      <!-- Solana -->
      <div class="glass rounded-[28px] p-7">
        <div class="flex items-center gap-4 mb-5">
          <div class="w-11 h-11 rounded-2xl bg-[#9945FF] flex items-center justify-center"><span class="text-white text-3xl font-bold">S</span></div>
          <div><div class="font-semibold text-2xl tracking-tight">Solana</div><div class="text-white/50 text-sm -mt-1">SOL</div></div>
        </div>
        <div class="price text-[42px] font-semibold tracking-[-2.5px] leading-none">{{SOL_PRICE}}</div>
        <div class="text-red-400 text-lg font-medium mt-1">{{SOL_CHANGE}}</div>
      </div>

      <!-- Toncoin -->
      <div class="glass rounded-[28px] p-7">
        <div class="flex items-center gap-4 mb-5">
          <div class="w-11 h-11 rounded-2xl bg-[#0098EA] flex items-center justify-center text-white text-3xl">💎</div>
          <div><div class="font-semibold text-2xl tracking-tight">Toncoin</div><div class="text-white/50 text-sm -mt-1">TON</div></div>
        </div>
        <div class="price text-[42px] font-semibold tracking-[-2.5px] leading-none">{{TON_PRICE}}</div>
        <div class="text-red-400 text-lg font-medium mt-1">{{TON_CHANGE}}</div>
      </div>

      <!-- Litecoin -->
      <div class="glass rounded-[28px] p-7">
        <div class="flex items-center gap-4 mb-5">
          <div class="w-11 h-11 rounded-2xl bg-[#345D9D] flex items-center justify-center text-white text-3xl">Ł</div>
          <div><div class="font-semibold text-2xl tracking-tight">Litecoin</div><div class="text-white/50 text-sm -mt-1">LTC</div></div>
        </div>
        <div class="price text-[42px] font-semibold tracking-[-2.5px] leading-none">{{LTC_PRICE}}</div>
        <div class="text-emerald-400 text-lg font-medium mt-1">{{LTC_CHANGE}}</div>
      </div>

      <!-- Monero -->
      <div class="glass rounded-[28px] p-7">
        <div class="flex items-center gap-4 mb-5">
          <div class="w-11 h-11 rounded-2xl bg-[#FF6600] flex items-center justify-center text-white text-3xl font-bold">M</div>
          <div><div class="font-semibold text-2xl tracking-tight">Monero</div><div class="text-white/50 text-sm -mt-1">XMR</div></div>
        </div>
        <div class="price text-[42px] font-semibold tracking-[-2.5px] leading-none">{{XMR_PRICE}}</div>
        <div class="text-red-400 text-lg font-medium mt-1">{{XMR_CHANGE}}</div>
      </div>

      <!-- XRP -->
      <div class="glass rounded-[28px] p-7">
        <div class="flex items-center gap-4 mb-5">
          <div class="w-11 h-11 rounded-2xl bg-[#23292F] flex items-center justify-center text-white text-3xl">X</div>
          <div><div class="font-semibold text-2xl tracking-tight">XRP</div><div class="text-white/50 text-sm -mt-1">XRP</div></div>
        </div>
        <div class="price text-[42px] font-semibold tracking-[-2.5px] leading-none">{{XRP_PRICE}}</div>
        <div class="text-red-400 text-lg font-medium mt-1">{{XRP_CHANGE}}</div>
      </div>

      <!-- BNB -->
      <div class="glass rounded-[28px] p-7">
        <div class="flex items-center gap-4 mb-5">
          <div class="w-11 h-11 rounded-2xl bg-[#F3BA2F] flex items-center justify-center text-black text-3xl font-bold">B</div>
          <div><div class="font-semibold text-2xl tracking-tight">BNB</div><div class="text-white/50 text-sm -mt-1">BNB</div></div>
        </div>
        <div class="price text-[42px] font-semibold tracking-[-2.5px] leading-none">{{BNB_PRICE}}</div>
        <div class="text-red-400 text-lg font-medium mt-1">{{BNB_CHANGE}}</div>
      </div>

      <!-- Tron -->
      <div class="glass rounded-[28px] p-7">
        <div class="flex items-center gap-4 mb-5">
          <div class="w-11 h-11 rounded-2xl bg-[#EF0027] flex items-center justify-center text-white text-3xl">T</div>
          <div><div class="font-semibold text-2xl tracking-tight">Tron</div><div class="text-white/50 text-sm -mt-1">TRX</div></div>
        </div>
        <div class="price text-[42px] font-semibold tracking-[-2.5px] leading-none">{{TRX_PRICE}}</div>
        <div class="text-emerald-400 text-lg font-medium mt-1">{{TRX_CHANGE}}</div>
      </div>

    </div>
  </div>
</body>
</html>"""

def format_change(change: float) -> str:
    if change is None:
        return "0.00%"
    sign = "+" if change >= 0 else ""
    color = "emerald" if change >= 0 else "red"
    return f'<span class="text-{color}-400">{sign}{change:.2f}%</span>'

@dp.message(Command("start", "prices", "crypto"))
async def send_crypto_image(message: types.Message):
    await message.answer("⏳ Generating latest Liquid Glass image with real prices...")

    # Fetch live prices from CoinGecko
    async with aiohttp.ClientSession() as session:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": COIN_IDS,
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        async with session.get(url, params=params) as resp:
            data = await resp.json()

    # Prepare replacements
    replacements = {
        "{{BTC_PRICE}}": f"${data['bitcoin']['usd']:,.2f}",
        "{{ETH_PRICE}}": f"${data['ethereum']['usd']:,.2f}",
        "{{SOL_PRICE}}": f"${data['solana']['usd']:,.2f}",
        "{{TON_PRICE}}": f"${data['the-open-network']['usd']:,.2f}",
        "{{LTC_PRICE}}": f"${data['litecoin']['usd']:,.2f}",
        "{{XMR_PRICE}}": f"${data['monero']['usd']:,.2f}",
        "{{XRP_PRICE}}": f"${data['ripple']['usd']:,.2f}",
        "{{BNB_PRICE}}": f"${data['binancecoin']['usd']:,.2f}",
        "{{TRX_PRICE}}": f"${data['tron']['usd']:.3f}",
        
        "{{BTC_CHANGE}}": format_change(data['bitcoin'].get('usd_24h_change')),
        "{{ETH_CHANGE}}": format_change(data['ethereum'].get('usd_24h_change')),
        "{{SOL_CHANGE}}": format_change(data['solana'].get('usd_24h_change')),
        "{{TON_CHANGE}}": format_change(data['the-open-network'].get('usd_24h_change')),
        "{{LTC_CHANGE}}": format_change(data['litecoin'].get('usd_24h_change')),
        "{{XMR_CHANGE}}": format_change(data['monero'].get('usd_24h_change')),
        "{{XRP_CHANGE}}": format_change(data['ripple'].get('usd_24h_change')),
        "{{BNB_CHANGE}}": format_change(data['binancecoin'].get('usd_24h_change')),
        "{{TRX_CHANGE}}": format_change(data['tron'].get('usd_24h_change')),
    }

    html_content = HTML_TEMPLATE
    for placeholder, value in replacements.items():
        html_content = html_content.replace(placeholder, value)

    # Render HTML to image using Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1200, "height": 900})
        await page.set_content(html_content, wait_until="networkidle")
        await page.wait_for_timeout(600)
        
        screenshot_path = "crypto_liquid_glass.png"
        await page.screenshot(path=screenshot_path, full_page=True, quality=95)
        await browser.close()

    # Send the image to user
    await message.answer_photo(
        types.FSInputFile(screenshot_path),
        caption="🚀 Live Crypto Prices • Liquid Glass Theme"
    )
    
    # Clean up
    if os.path.exists(screenshot_path):
        os.remove(screenshot_path)

async def main():
    print("✅ Bot is running... Send /prices to get the image")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

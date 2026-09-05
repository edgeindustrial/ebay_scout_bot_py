import logging
import io
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

from config import TELEGRAM_BOT_TOKEN
from ocr_engine import extract_part_number_from_image
from ebay_client import fetch_ebay_sold_stats

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🏭 *Sharjah eBay Scout Bot Online*\n\n"
        "• *Snap a photo* of any industrial part label\n"
        "• Or *type the part number* directly as text."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

def format_card(stats: dict, brand: str = "") -> str:
    part_no = stats["part_number"]
    ebay_link = f"https://www.ebay.com/sch/i.html?_nkw={part_no}&LH_Complete=1&LH_Sold=1"

    if stats.get("sold_count_90d", 0) == 0:
        return (
            f"❌ *NO RECENT SALES (90 Days)*\n\n"
            f"📦 *Part:* `{part_no}`\n"
            f"⚠️ Demand is cold or obsolete without active buyers.\n\n"
            f"🔗 [View Completed on eBay]({ebay_link})"
        )

    pass_badge = "🟢 *VIABLE (PASS)*" if stats["status"] == "PASS" else "🔴 *SLOW DEMAND (FAIL)*"

    return (
        f"{pass_badge}\n"
        f"🏷️ *Brand:* {brand or 'N/A'}\n"
        f"📦 *Part:* `{part_no}`\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📈 *Demand (90 Days):* `{stats['sold_count_90d']} units sold`\n\n"
        f"💰 *Sold Price Range:*\n"
        f"  • *Min:* `${stats['min_usd']:.0f}` (AED {stats['min_aed']:.0f})\n"
        f"  • *Avg:* `${stats['avg_usd']:.0f}` (AED {stats['avg_aed']:.0f})\n"
        f"  • *Max:* `${stats['max_usd']:.0f}` (AED {stats['max_aed']:.0f})\n\n"
        f"🎯 *Max Buy Target:* `AED {stats['target_buy_aed']:.0f}`\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 [Verify Sold Listings on eBay]({ebay_link})"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Reading label...")
    photo_file = await update.message.photo[-1].get_file()
    img_byte_array = io.BytesIO()
    await photo_file.download_to_memory(img_byte_array)
    
    ocr = extract_part_number_from_image(img_byte_array.getvalue())
    if not ocr["success"]:
        await update.message.reply_text(f"⚠️ {ocr['error']}. Please type the part number manually.")
        return

    brand, part_no = ocr["brand"], ocr["part_number"]
    await update.message.reply_text(f"🎯 Found: `{brand} {part_no}`. Checking eBay...")

    stats = fetch_ebay_sold_stats(part_no)
    if not stats.get("success"):
        await update.message.reply_text(f"⚠️ eBay Error: {stats.get('error')}")
        return

    await update.message.reply_text(format_card(stats, brand=brand), parse_mode="Markdown", disable_web_page_preview=True)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    part_no = update.message.text.strip()
    await update.message.reply_text(f"🔍 Searching eBay for `{part_no}`...")
    stats = fetch_ebay_sold_stats(part_no)
    if not stats.get("success"):
        await update.message.reply_text(f"⚠️ eBay Error: {stats.get('error')}")
        return
    await update.message.reply_text(format_card(stats), parse_mode="Markdown", disable_web_page_preview=True)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 Scout Bot is running! Open Telegram and message your bot.")
    app.run_polling()

if __name__ == "__main__":
    main()
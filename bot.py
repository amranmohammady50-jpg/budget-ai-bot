from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import re
import asyncio
import os
import requests
import threading
import time

def keep_alive():
    while True:
        try:
            requests.get("https://your-render-url.com/ping")  # URL Render رو بذار
            time.sleep(600)  # ۱۰ دقیقه
        except:
            pass

# در انتهای کد، قبل از run_polling:
threading.Thread(target=keep_alive, daemon=True).start()
# توکن از متغیر محیطی (Render)
TOKEN = os.getenv("TOKEN")

# اطلاعات کارت
CARD_NUMBER = "6037991812345678"  # عوض کن!
CARD_NAME = "علی محمدی"         # عوض کن!
REQUIRED_AMOUNT = 50000

# کاربران پرو
PRO_USERS = set()

# محاسبه بودجه
def calculate_budget(income):
    return {
        "خوراک": (0.30, int(income * 0.30)),
        "حمل": (0.15, int(income * 0.15)),
        "اجاره": (0.25, int(income * 0.25)),
        "پس‌انداز": (0.20, int(income * 0.20)),
        "تفریح": (0.10, int(income * 0.10))
    }

def format_budget(income, is_pro=False):
    budget = calculate_budget(income)
    lines = []
    for name, (percent, amount) in budget.items():
        emoji = {"خوراک": "🍲", "حمل": "🚗", "اجاره": "🏠", "پس‌انداز": "💰", "تفریح": "🎉"}[name]
        lines.append(f"• {emoji} {name}: {int(percent*100)}% = {amount:,}T")
    if is_pro:
        lines.append("• پیش‌بینی تورم ۳ ماهه")
        lines.append("• گزارش PDF هفتگی")
    return "\n".join(lines)

# تشخیص فیش
def detect_payment(text):
    text = text.replace(" ", "").replace("-", "")
    card_match = re.search(r"6037\d{12}|5892\d{12}", text)
    if not card_match or card_match.group(0) != CARD_NUMBER.replace("-", ""):
        return False, "شماره کارت اشتباه"
    if "50000" not in text and "۵۰,۰۰۰" not in text:
        return False, "مبلغ باید ۵۰,۰۰۰ تومان"
    if CARD_NAME not in text:
        return False, f"نام {CARD_NAME} پیدا نشد"
    return True, "تأیید شد"

# استخراج درآمد
def extract_income(text):
    if not text: return None
    text = text.lower()
    if "میلیون" in text:
        millions = ''.join(filter(str.isdigit, text.split("میلیون")[0]))
        return int(millions) * 1_000_000 if millions else None
    elif text.replace(",", "").replace(" ", "").isdigit():
        return int(text.replace(",", "").replace(" ", ""))
    return None

# هندلرها
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 بات بودجه AI پارسی\n"
        "درآمد ماهانه‌ت رو بگو (مثل: ۲۵ میلیون)"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message

    if user_id in PRO_USERS:
        income = extract_income(message.text)
        if income:
            await update.message.reply_text("🤖 در حال تحلیل... (۳ ثانیه)")
            await asyncio.sleep(3)
            await update.message.reply_text(
                f"💡 بودجه پیشنهادی برای {income:,} تومان:\n"
                f"{format_budget(income, is_pro=True)}\n\n"
                f"🔥 نسخه پرو فعال!"
            )
        return

    if message.photo or (message.text and any(x in message.text.lower() for x in ["فیش", "واریز", "پرداخت"])):
        text = (message.caption or message.text or "").strip()
        if not text:
            await message.reply_text("کپشن عکس رو پر کن (شماره کارت، مبلغ، نام)")
            return
        success, msg = detect_payment(text)
        if success:
            PRO_USERS.add(user_id)
            await message.reply_text(
                "✅ پرداخت تأیید شد!\n"
                "🔥 نسخه پرو فعال شد!\n"
                "حالا درآمدت رو بگو (مثل: ۲۰ میلیون)"
            )
        else:
            await message.reply_text(f"❌ فیش اشتباه:\n{msg}\n\nدوباره امتحان کن")
        return

    income = extract_income(message.text)
    if income:
        await update.message.reply_text("🤖 AvalAI در حال تحلیل... (۳ ثانیه)")
        await asyncio.sleep(3)
        await update.message.reply_text(
            f"💡 بودجه پیشنهادی برای {income:,} تومان:\n"
            f"{format_budget(income)}\n\n"
            f"🔥 پرو (تورم زنده + PDF): /pay"
        )

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💳 پرداخت ۵۰,۰۰۰ تومان (نسخه پرو)\n\n"
        f"کارت به کارت به:\n"
        f"`{CARD_NUMBER}`\n"
        f"نام: {CARD_NAME}\n\n"
        f"بعد از واریز، **اسکرین‌شات فیش** رو بفرست\n"
        f"بات خودش تشخیص می‌ده و فعال می‌کنه!",
        parse_mode='Markdown'
    )

# اجرا
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("pay", pay))
app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

print("بات ۲۴ ساعته در حال اجراست...")
app.run_polling()
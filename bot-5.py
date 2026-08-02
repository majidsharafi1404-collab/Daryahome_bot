# -*- coding: utf-8 -*-
"""
ربات تلگرامی پاسخ‌گوی مشتریان برای فروشگاه لوازم خانه و آشپزخانه.
از Google Gemini API استفاده می‌کنه (رایگان، بدون نیاز به کارت اعتباری).

نحوه اجرا:
1. pip install -r requirements.txt
2. مقادیر TELEGRAM_TOKEN و GEMINI_API_KEY رو در فایل .env قرار بدید (نگاه کنید به .env.example)
3. python bot.py
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import google.generativeai as genai

from business_info import SYSTEM_PROMPT

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=SYSTEM_PROMPT,
)

# نگهداری تاریخچه مکالمه هر کاربر در حافظه (ساده - برای شروع کافیه)
user_conversations: dict[int, list[dict]] = {}
MAX_HISTORY_MESSAGES = 10  # چند پیام آخر رو به یاد داشته باشه


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_conversations[update.effective_chat.id] = []
    await update.message.reply_text(
        "سلام! 👋 به دستیار فروشگاه خوش اومدید.\n"
        "هر سوالی درباره محصولات، قیمت‌ها، ارسال یا بازگشت کالا دارید بپرسید."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_conversations[update.effective_chat.id] = []
    await update.message.reply_text("مکالمه ریست شد. سوال جدیدتون رو بپرسید 🙂")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = update.message.text

    history = user_conversations.setdefault(chat_id, [])
    history.append({"role": "user", "parts": [user_text]})
    history = history[-MAX_HISTORY_MESSAGES:]

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response = gemini_model.generate_content(history)
        reply_text = (response.text or "").strip()
        if not reply_text:
            reply_text = "متاسفانه نتونستم جواب مناسبی پیدا کنم. لطفاً سوالتون رو واضح‌تر بپرسید."
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini API error: %s", exc)
        reply_text = (
            "در حال حاضر مشکلی در پاسخ‌گویی پیش اومده. لطفاً چند لحظه بعد دوباره امتحان کنید "
            "یا مستقیم با پشتیبانی تماس بگیرید."
        )

    history.append({"role": "model", "parts": [reply_text]})
    user_conversations[chat_id] = history[-MAX_HISTORY_MESSAGES:]

    await update.message.reply_text(reply_text)


def main() -> None:
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        raise RuntimeError(
            "لطفاً TELEGRAM_TOKEN و GEMINI_API_KEY رو در فایل .env تنظیم کنید."
        )

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("ربات در حال اجراست...")
    app.run_polling()


if __name__ == "__main__":
    main()

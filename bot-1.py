# -*- coding: utf-8 -*-
"""
ربات تلگرامی پاسخ‌گوی مشتریان برای فروشگاه لوازم خانه و آشپزخانه.

نحوه اجرا:
1. pip install -r requirements.txt
2. مقادیر TELEGRAM_TOKEN و ANTHROPIC_API_KEY رو در فایل .env قرار بدید (نگاه کنید به .env.example)
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
import anthropic

from business_info import SYSTEM_PROMPT

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

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
    history.append({"role": "user", "content": user_text})
    history = history[-MAX_HISTORY_MESSAGES:]

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response = claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=history,
        )
        reply_text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
        if not reply_text:
            reply_text = "متاسفانه نتونستم جواب مناسبی پیدا کنم. لطفاً سوالتون رو واضح‌تر بپرسید."
    except Exception as exc:  # noqa: BLE001
        logger.exception("Claude API error: %s", exc)
        reply_text = (
            "در حال حاضر مشکلی در پاسخ‌گویی پیش اومده. لطفاً چند لحظه بعد دوباره امتحان کنید "
            "یا مستقیم با پشتیبانی تماس بگیرید."
        )

    history.append({"role": "assistant", "content": reply_text})
    user_conversations[chat_id] = history[-MAX_HISTORY_MESSAGES:]

    await update.message.reply_text(reply_text)


def main() -> None:
    if not TELEGRAM_TOKEN or not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "لطفاً TELEGRAM_TOKEN و ANTHROPIC_API_KEY رو در فایل .env تنظیم کنید."
        )

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("ربات در حال اجراست...")
    app.run_polling()


if __name__ == "__main__":
    main()

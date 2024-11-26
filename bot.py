import logging
import random
import json
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from pymongo import MongoClient
import asyncio
import os
import time

HUGGING_FACE_API_TOKEN = "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"

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load KJV Bible Data
with open("kjv.json") as f:
    BIBLE = json.load(f)

# MongoDB Setup
MONGO_URI = "mongodb+srv://bible:bible@cluster0.uc77o.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
db_client = MongoClient(MONGO_URI)
db = db_client["bible_bot"]
users = db["users"]

# Scheduler Setup
scheduler = BackgroundScheduler()
scheduler.start()

# Logging Channel ID
LOG_CHANNEL_ID = -1002351224104  # Replace with your actual channel ID

# Helper Functions
def get_random_verse():
    """Fetch a random Bible verse."""
    book_data = random.choice(BIBLE)
    book_name = book_data["abbrev"]
    chapters = book_data["chapters"]
    chapter_index = random.randint(0, len(chapters) - 1)
    verses = chapters[chapter_index]
    verse_index = random.randint(0, len(verses) - 1)
    verse_text = verses[verse_index]
    return f"{verse_text}", book_name, chapter_index + 1, verse_index + 1

def analyze_tone(user_message):
    """Analyze the tone of the user's message using a sentiment model."""
    headers = {"Authorization": f"Bearer {HUGGING_FACE_API_TOKEN}"}
    payload = {"inputs": user_message}
    retries = 3

    for attempt in range(retries):
        try:
            response = requests.post(
                "https://api-inference.huggingface.co/models/nlptown/bert-base-multilingual-uncased-sentiment",
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            sentiment = response.json()[0]["label"]
            tone_map = {
                "very negative": "sadness",
                "negative": "sadness",
                "neutral": "neutral",
                "positive": "joy",
                "very positive": "joy",
            }
            return tone_map.get(sentiment, "neutral")
        except requests.HTTPError as e:
            logger.error(f"Hugging Face API error (attempt {attempt + 1}): {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
    return "neutral"


def explain_verse(verse_text, tone="uplifting"):
    """Generate an explanation for a verse using a text generation model."""
    headers = {"Authorization": f"Bearer {HUGGING_FACE_API_TOKEN}"}
    payload = {
        "inputs": f"Explain this Bible verse in an {tone} way: {verse_text}",
        "parameters": {"max_length": 100},
    }
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/EleutherAI/gpt-neo-1.3B",
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return response.json()[0]["generated_text"]
    except requests.RequestException as e:
        logger.error(f"Explanation generation failed: {e}")
        return "This verse speaks deeply to the soul, reflecting God's eternal wisdom."


async def log_message(context, user_id, user_message, bot_reply):
    """Log user messages and bot replies."""
    log_text = (
        f"<b>User ID:</b> {user_id}\n"
        f"<b>User Message:</b> {user_message}\n"
        f"<b>Bot Reply:</b> {bot_reply}"
    )
    try:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to log message: {e}")

# Command Handlers
async def start(update: Update, context):
    """Start command handler."""
    user = update.effective_user
    if not users.find_one({"user_id": user.id}):
        users.insert_one({"user_id": user.id, "username": user.username, "morning_subscribed": True})
    await update.message.reply_text(
        "🌟 Welcome to the KJV Bible Bot! 🌟\n\n"
        "Feel free to share your thoughts or ask questions, and I'll respond with a meaningful Bible verse to uplift your spirit."
    )

async def random_verse(update: Update, context):
    """Send a random Bible verse."""
    verse, book, chapter, verse_number = get_random_verse()
    context.user_data["last_verse"] = (verse, book, chapter, verse_number)
    reply = f"📖 <b>{book} {chapter}:{verse_number}</b>\n\n<i>{verse}</i>"
    await update.message.reply_text(reply, parse_mode="HTML")
    await log_message(context, update.effective_user.id, "/random", reply)

async def plain_text_response(update: Update, context):
    """Handle plain text messages with context-aware replies."""
    user_message = update.message.text
    tone = analyze_tone(user_message)
    verse, book, chapter, verse_number = get_random_verse()
    
    tone_map = {
        "sadness": "comforting",
        "joy": "celebratory",
        "frustration": "calming",
        "loneliness": "empathetic",
        "hopeful": "encouraging",
        "neutral": "informative",
    }
    explanation = explain_verse(verse, tone=tone_map.get(tone, "uplifting"))
    reply = (
        f"📖 <b>{book} {chapter}:{verse_number}</b>\n\n"
        f"<i>{verse}</i>\n\n"
        f"💡 <i>Reflection</i>: {explanation}"
    )
    await update.message.reply_text(reply, parse_mode="HTML")
    await log_message(context, update.effective_user.id, user_message, reply)

# Scheduler Job
async def send_morning_verses_async():
    """Send morning verses to all subscribed users."""
    subscribed_users = users.find({"morning_subscribed": True})
    verse, book, chapter, verse_number = get_random_verse()
    for user in subscribed_users:
        try:
            await app.bot.send_message(
                chat_id=user["user_id"],
                text=(
                    f"🌅 <b>Good Morning!</b>\n\n"
                    f"📖 <b>{book} {chapter}:{verse_number}</b>\n<i>{verse}</i>"
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send morning verse to {user['user_id']}: {e}")

# Wrapper for Async Function
def send_morning_verses_sync():
    asyncio.run(send_morning_verses_async())

# Add Job to Scheduler
scheduler.add_job(send_morning_verses_sync, "cron", hour=8, minute=0)

# Main Function
if __name__ == "__main__":
    bot_token = os.getenv("BOT_TOKEN")  # Ensure the bot token is stored in an environment variable
    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("random", random_verse))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text_response))

    port = int(os.environ.get("PORT", 8443))  # Default to 8443 for local testing
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=f"{bot_token}",  # Using the bot token as the URL path
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/{bot_token}"
    )

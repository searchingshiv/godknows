import openai
import logging
import random
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)
import os
from pymongo import MongoClient
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
import time

# Set up OpenAI API key
openai.api_key = os.getenv("API")
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

def explain_verse(verse_text, tone="uplifting"):
    """Generate an explanation for a verse using OpenAI's GPT-3."""
    try:
        prompt = f"Explain this Bible verse in an {tone} manner: {verse_text}"
        
        response = openai.Completion.create(
            engine="text-davinci-003",  
            prompt=prompt,
            max_tokens=150,
            temperature=0.7,
        )
        
        explanation = response.choices[0].text.strip()
        return explanation
    except Exception as e:
        logger.error(f"Failed to generate explanation: {e}")
        return "I'm sorry, I couldn't generate an explanation at the moment."

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

async def plain_text_response(update: Update, context):
    """Handle plain text messages with context-aware replies."""
    user_message = update.message.text
    verse, book, chapter, verse_number = get_random_verse()
    tone = "uplifting"  # You can also implement tone analysis if needed
    
    explanation = explain_verse(verse, tone)
    reply = (
        f"📖 <b>{book} {chapter}:{verse_number}</b>\n\n"
        f"<i>{verse}</i>\n\n"
        f"💡 <i>Reflection</i>: {explanation}"
    )
    await update.message.reply_text(reply, parse_mode="HTML")

# Main Function
if __name__ == "__main__":
    bot_token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("random", random_verse))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text_response))

    app.run_polling()

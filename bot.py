import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import time
import random
from dotenv import load_dotenv
import requests  # For API requests

# Load environment variables
load_dotenv()

# Define bot token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize the bot application
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
job_queue = application.job_queue  # Initialize the JobQueue

# Log user messages and bot responses to a channel
LOG_CHANNEL = '-1002351224104'

def log_to_channel(message, reply):
    """Logs the user message and bot reply to the channel"""
    bot = application.bot
    log_message = f"User: {message}\nBot: {reply}"
    bot.send_message(chat_id=LOG_CHANNEL, text=log_message)

# Get a random Bible verse from a free API
def get_random_bible_verse():
    """Fetches a random Bible verse dynamically from a free Bible API."""
    try:
        response = requests.get("https://labs.bible.org/api/?passage=random&type=json")
        if response.status_code == 200:
            data = response.json()[0]
            verse = f"{data['bookname']} {data['chapter']}:{data['verse']} - {data['text']}"
            return verse
        else:
            return "John 3:16 - For God so loved the world..."
    except Exception as e:
        print(f"Error fetching Bible verse: {e}")
        return "John 3:16 - For God so loved the world..."

# Get a Bible verse explanation dynamically using a free AI model
def get_bible_explanation(verse):
    """Generates an explanation for the given Bible verse using Hugging Face or similar."""
    prompt = f"Explain the meaning of the Bible verse: {verse}"
    try:
        # Replace with your free API endpoint or Hugging Face model
        response = requests.post(
            "https://api-inference.huggingface.co/models/bigscience/bloom",
            headers={"Authorization": f"Bearer {os.getenv('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')}"},
            json={"inputs": prompt},
        )
        if response.status_code == 200:
            return response.json()["generated_text"]
        else:
            return "This verse reminds us to reflect on God's love and teachings."
    except Exception as e:
        print(f"Error generating explanation: {e}")
        return "This verse reminds us to reflect on God's love and teachings."

# Handle text messages
async def handle_message(update: Update, context):
    user_message = update.message.text
    bot = context.bot
    user_id = update.message.chat_id

    verse = get_random_bible_verse()
    explanation = get_bible_explanation(verse)
    reply = f"Here's a verse for you: {verse}\nExplanation: {explanation}"

    await bot.send_message(chat_id=user_id, text=reply)
    log_to_channel(user_message, reply)

# Send a scheduled Bible verse every morning
async def send_morning_verse(context):
    bot = context.bot
    chat_id = context.job.context
    verse = get_random_bible_verse()
    explanation = get_bible_explanation(verse)
    await bot.send_message(chat_id=chat_id, text=f"Good morning! Here's your Bible verse: {verse}\nExplanation: {explanation}")

# Start command handler
async def start(update: Update, context):
    user_id = update.message.chat_id
    job_queue.run_daily(send_morning_verse, time=time(7, 0, 0), context=user_id)
    await update.message.reply_text("Welcome! I will send you a Bible verse every morning.")

# Random verse command handler
async def random_verse(update: Update, context):
    verse = get_random_bible_verse()
    explanation = get_bible_explanation(verse)
    await update.message.reply_text(f"Here's a random Bible verse: {verse}\nExplanation: {explanation}")

# Add handlers to the application
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("randomverse", random_verse))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Start the bot
if __name__ == "__main__":
    application.run_polling()

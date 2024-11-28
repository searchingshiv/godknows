import os
import logging
import threading
from datetime import time
from flask import Flask
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define bot token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")

# Verify environment variables
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in the environment variables.")
if not HUGGINGFACE_API_TOKEN:
    raise ValueError("HUGGINGFACE_API_TOKEN is not set in the environment variables.")

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the bot application
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
job_queue = application.job_queue  # Initialize the JobQueue

# Asynchronously fetch a random Bible verse
async def get_random_bible_verse():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://labs.bible.org/api/?passage=random&type=json") as response:
                if response.status == 200:
                    data = await response.json()
                    verse = f"{data[0]['bookname']} {data[0]['chapter']}:{data[0]['verse']} - {data[0]['text']}"
                    return verse
                else:
                    return "John 3:16 - For God so loved the world..."
        except Exception as e:
            logger.error(f"Error fetching Bible verse: {e}")
            return "John 3:16 - For God so loved the world..."

# Asynchronously fetch a Bible verse explanation
async def get_bible_explanation(verse):
    prompt = f"Explain the meaning of the Bible verse: {verse}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "https://api-inference.huggingface.co/models/bigscience/bloom",
                headers={"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"},
                json={"inputs": prompt},
            ) as response:
                if response.status == 200:
                    response_json = await response.json()
                    if isinstance(response_json, list) and "generated_text" in response_json[0]:
                        return response_json[0]["generated_text"]
                    else:
                        logger.warning(f"Unexpected API response: {response_json}")
                        return "This verse reminds us to reflect on God's love and teachings."
                else:
                    logger.error(f"API Error: {response.status} - {await response.text()}")
                    return "This verse reminds us to reflect on God's love and teachings."
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return "Unable to fetch a detailed explanation at the moment. Reflect on this verse and let it inspire you."

# Handle text messages
async def handle_message(update: Update, context):
    if update.message.from_user.is_bot:
        return

    user_message = update.message.text
    bot = context.bot
    user_id = update.message.chat_id

    verse = await get_random_bible_verse()
    explanation = await get_bible_explanation(verse)
    reply = f"Here's a verse for you: {verse}\nExplanation: {explanation}"

    await bot.send_message(chat_id=user_id, text=reply)

# Send a scheduled Bible verse every morning
async def send_morning_verse(context):
    chat_id = context.job.data["chat_id"]  # Extract chat_id from job.data
    bot = context.bot
    verse = await get_random_bible_verse()
    explanation = await get_bible_explanation(verse)
    await bot.send_message(chat_id=chat_id, text=f"Good morning! Here's your Bible verse: {verse}\nExplanation: {explanation}")

# Start command handler
async def start(update: Update, context):
    user_id = update.message.chat_id
    try:
        job_queue.run_daily(
            send_morning_verse,
            time=time(7, 0, 0),
            data={"chat_id": user_id},  # Pass chat_id using job.data
            name=f"morning_verse_{user_id}"  # Unique job name
        )
        await update.message.reply_text("Welcome! I will send you a Bible verse every morning.")
    except Exception as e:
        logger.error(f"Error scheduling daily verse: {e}")
        await update.message.reply_text("An error occurred while scheduling your daily Bible verses. Please try again.")

# Random verse command handler
async def random_verse(update: Update, context):
    verse = await get_random_bible_verse()
    explanation = await get_bible_explanation(verse)
    await update.message.reply_text(f"Here's a random Bible verse: {verse}\nExplanation: {explanation}")

# Add error handler
async def error_handler(update: Update, context):
    logger.error(f"Update {update} caused error {context.error}")

application.add_error_handler(error_handler)

# Add handlers to the application
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("randomverse", random_verse))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Dummy web server to satisfy Render's port requirement
app = Flask(__name__)

@app.route("/")
def home():
    return "Telegram Bot is running."

def run_server():
    app.run(host="0.0.0.0", port=5000)

# Start the bot
if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    application.run_polling()

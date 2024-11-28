import logging
import aiohttp
import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram.ext.filters import TEXT
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Replace these with your tokens
TELEGRAM_BOT_TOKEN = "7112230953:AAGXLw_K27M9YYhWR-uC9j4J8OHfZxQlnHk"
HUGGINGFACE_API_TOKEN = "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"

# Initialize the scheduler
scheduler = AsyncIOScheduler()

async def get_random_bible_verse():
    """Fetch a random Bible verse from the Bible API."""
    url = "https://labs.bible.org/api/?passage=random&type=json"
    for attempt in range(3):  # Retry logic
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return f"{data[0]['bookname']} {data[0]['chapter']}:{data[0]['verse']} - {data[0]['text']}"
                    else:
                        logger.error(f"Bible API error, status code: {response.status}")
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}: Failed to fetch Bible verse. Error: {e}")
    return "John 3:16 - For God so loved the world..."


async def get_bible_explanation(verse):
    """Fetch an explanation of the Bible verse using Hugging Face."""
    url = "https://api-inference.huggingface.co/models/bigscience/bloom"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
    payload = {"inputs": f"Explain the meaning of: {verse}"}
    for attempt in range(3):  # Retry logic
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data[0]["generated_text"]
                    else:
                        logger.error(f"Hugging Face API error, status code: {response.status}")
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}: Failed to fetch explanation. Error: {e}")
    return "I couldn't fetch an explanation for the verse at this time."


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler."""
    try:
        chat_id = update.message.chat_id
        job_name = f"morning_verse_{chat_id}"
        # Remove existing job if it exists
        try:
            scheduler.remove_job(job_name)
        except JobLookupError:
            pass

        scheduler.add_job(
            send_morning_verse,
            "cron",
            hour=9,
            minute=0,
            args=[context, chat_id],
            id=job_name,
        )
        await update.message.reply_text("You will receive a Bible verse every morning at 9 AM.")
    except Exception as e:
        logger.exception("Error scheduling daily verse")
        await update.message.reply_text("Failed to schedule daily Bible verses. Please try again.")


async def send_morning_verse(context, chat_id):
    """Send a morning Bible verse."""
    try:
        verse = await get_random_bible_verse()
        explanation = await get_bible_explanation(verse)
        await context.bot.send_message(chat_id=chat_id, text=f"Good morning! Here's your Bible verse:\n\n{verse}\n\nExplanation: {explanation}")
    except Exception as e:
        logger.exception("Error sending morning verse")
        await context.bot.send_message(chat_id=chat_id, text="Sorry, I couldn't fetch the verse this morning. Please try again later.")


async def random_verse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /randomverse command."""
    try:
        verse = await get_random_bible_verse()
        explanation = await get_bible_explanation(verse)
        await update.message.reply_text(f"Here's a random Bible verse:\n\n{verse}\n\nExplanation: {explanation}")
    except Exception as e:
        logger.exception("Failed to fetch random verse")
        await update.message.reply_text("Sorry, I couldn't fetch a verse right now. Please try again later.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user text messages."""
    try:
        user_message = update.message.text
        response = await get_bible_explanation(user_message)
        await update.message.reply_text(f"Here's an explanation:\n\n{response}")
    except Exception as e:
        logger.exception("Failed to handle text message")
        await update.message.reply_text("Sorry, I couldn't process your message. Please try again later.")


def main():
    """Run the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("randomverse", random_verse))
    application.add_handler(MessageHandler(TEXT, handle_text))

    # Start the scheduler
    scheduler.start()

    # Start the bot
    application.run_polling()


if __name__ == "__main__":
    main()

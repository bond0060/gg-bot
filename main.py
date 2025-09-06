
import logging
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from app.config.settings import settings
from app.handlers.message_handlers import MessageHandlers

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TravelBot:
    def __init__(self):
        # Build application with better network configuration
        self.application = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .connection_pool_size(1)
            .read_timeout(10)
            .write_timeout(10)
            .connect_timeout(10)
            .pool_timeout(10)
            .build()
        )
        self.handlers = MessageHandlers()
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup message handlers for the bot"""
        # Basic command handlers
        self.application.add_handler(CommandHandler("start", self.handlers.start_command))
        self.application.add_handler(CommandHandler("help", self.handlers.help_command))
        self.application.add_handler(CommandHandler("history", self.handlers.history_command))
        self.application.add_handler(CommandHandler("clear", self.handlers.clear_command))
        
        # Travel plan command handlers
        self.application.add_handler(CommandHandler("plan", self.handlers.plan_command))
        self.application.add_handler(CommandHandler("plans", self.handlers.plans_command))
        self.application.add_handler(CommandHandler("viewplan", self.handlers.viewplan_command))
        self.application.add_handler(CommandHandler("deleteplan", self.handlers.deleteplan_command))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handlers.handle_callback_query))
        
        # Message handlers
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_text)
        )
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handlers.handle_photo))
        self.application.add_handler(
            MessageHandler(filters.Document.IMAGE, self.handlers.handle_image_document)
        )

    def run(self):
        """Start the bot"""
        # Add error handler
        self.application.add_error_handler(self.handlers.error_handler)
        
        logger.info(f"Starting {settings.bot_name}...")
        logger.info(f"Using OpenAI model: {settings.openai_model}")
        
        try:
            # Run with better error handling and retry
            self.application.run_polling(
                drop_pending_updates=True,
                close_loop=False,
                stop_signals=None
            )
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            # Try to restart after a short delay
            import time
            time.sleep(5)
            logger.info("Attempting to restart bot...")
            self.application.run_polling(drop_pending_updates=True)


def main():
    try:
        # Validate settings (will raise validation error if missing required fields)
        logger.info(f"Initializing {settings.bot_name}...")
        logger.info(f"Bot description: {settings.bot_description}")
        
        # Create and run the bot
        bot = TravelBot()
        bot.run()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        logger.error("Please check your .env file has all required variables:")
        logger.error("TELEGRAM_BOT_TOKEN=your_telegram_bot_token")
        logger.error("OPENAI_API_KEY=your_openai_api_key")
        raise


if __name__ == "__main__":
    main()

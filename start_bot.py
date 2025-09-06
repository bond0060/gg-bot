#!/usr/bin/env python3
"""
简化的机器人启动脚本，用于解决网络连接问题
"""

import logging
import asyncio
import os
import sys
from dotenv import load_dotenv

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

def main():
    try:
        # Import after setting up logging
        from main import TravelBot
        
        logger.info("Starting simplified bot...")
        
        # Create and run the bot
        bot = TravelBot()
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        logger.error("Please check your .env file has all required variables:")
        logger.error("TELEGRAM_BOT_TOKEN=your_telegram_bot_token")
        logger.error("OPENAI_API_KEY=your_openai_api_key")
        sys.exit(1)

if __name__ == "__main__":
    main()


from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Telegram Bot Configuration
    telegram_bot_token: str = Field(..., description="Telegram bot token from @BotFather")
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    openai_max_tokens: int = Field(default=1000, description="Maximum tokens for OpenAI responses")
    openai_temperature: float = Field(default=0.7, description="Temperature for OpenAI responses")


    # Bot Configuration
    bot_name: str = Field(default="TravelBot", description="Bot display name")
    bot_description: str = Field(
        default="AI-powered travel planning assistant",
        description="Bot description"
    )

    tavily_token: str = Field(..., description="Tavily API key")
    amadeus_api_key: str = Field(default="", description="Amadeus API key")
    amadeus_api_secret: str = Field(default="", description="Amadeus API secret")


# Global settings instance
settings = Settings()
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # Claude / Anthropic
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    claude_model: str = Field("claude-opus-4-6", env="CLAUDE_MODEL")

    # Telegram
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_admin_chat_id: str = Field(..., env="TELEGRAM_ADMIN_CHAT_ID")
    telegram_alert_chat_id: str = Field("", env="TELEGRAM_ALERT_CHAT_ID")

    # CRM
    hubspot_api_key: str = Field("", env="HUBSPOT_API_KEY")
    salesforce_client_id: str = Field("", env="SALESFORCE_CLIENT_ID")
    salesforce_client_secret: str = Field("", env="SALESFORCE_CLIENT_SECRET")
    pipedrive_api_key: str = Field("", env="PIPEDRIVE_API_KEY")

    # Finance
    xero_client_id: str = Field("", env="XERO_CLIENT_ID")
    xero_client_secret: str = Field("", env="XERO_CLIENT_SECRET")
    stripe_secret_key: str = Field("", env="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field("", env="STRIPE_WEBHOOK_SECRET")

    # Scheduling
    calendly_api_key: str = Field("", env="CALENDLY_API_KEY")

    # Content / SEO
    wordpress_url: str = Field("", env="WORDPRESS_URL")
    wordpress_username: str = Field("", env="WORDPRESS_USERNAME")
    wordpress_app_password: str = Field("", env="WORDPRESS_APP_PASSWORD")
    webflow_api_key: str = Field("", env="WEBFLOW_API_KEY")
    shopify_store_url: str = Field("", env="SHOPIFY_STORE_URL")
    shopify_access_token: str = Field("", env="SHOPIFY_ACCESS_TOKEN")

    # Lead Sources
    facebook_access_token: str = Field("", env="FACEBOOK_ACCESS_TOKEN")
    facebook_page_id: str = Field("", env="FACEBOOK_PAGE_ID")
    google_ads_developer_token: str = Field("", env="GOOGLE_ADS_DEVELOPER_TOKEN")
    google_ads_customer_id: str = Field("", env="GOOGLE_ADS_CUSTOMER_ID")

    # Automation
    zapier_webhook_url: str = Field("", env="ZAPIER_WEBHOOK_URL")
    n8n_webhook_url: str = Field("", env="N8N_WEBHOOK_URL")

    # Voice (AVA)
    vapi_api_key: str = Field("", env="VAPI_API_KEY")
    vapi_phone_number_id: str = Field("", env="VAPI_PHONE_NUMBER_ID")
    twilio_account_sid: str = Field("", env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field("", env="TWILIO_AUTH_TOKEN")
    twilio_phone_number: str = Field("", env="TWILIO_PHONE_NUMBER")

    # Vector DB
    pinecone_api_key: str = Field("", env="PINECONE_API_KEY")
    pinecone_environment: str = Field("us-east-1-aws", env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field("synsystems-knowledge", env="PINECONE_INDEX_NAME")

    # App
    app_env: str = Field("development", env="APP_ENV")
    app_port: int = Field(8000, env="APP_PORT")
    app_secret_key: str = Field("changeme", env="APP_SECRET_KEY")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

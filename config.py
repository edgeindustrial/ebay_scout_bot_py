import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
EBAY_APP_ID = os.getenv("EBAY_APP_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Sourcing Logic Rules
MIN_SOLD_THRESHOLD = 2         # Minimum 2 units sold in last 90 days
TARGET_BUY_PERCENTAGE = 0.35   # Target buying at <= 35% of eBay average
USD_TO_AED_RATE = 3.6725       # Conversion multiplier

# eBay Finding API Endpoint
EBAY_FINDING_API_URL = "https://svcs.ebay.com/services/search/FindingService/v1"
EBAY_GLOBAL_ID = "EBAY-US"
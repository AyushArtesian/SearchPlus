"""Configuration management for Sports Card Tagger."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Database file
PRODUCTS_DB = DATA_DIR / "products.json"

# CollectorInvestor API
COLLECTOR_INVESTOR_USERNAME = "collectorinvestorapiuser"
COLLECTOR_INVESTOR_BASE64_TOKEN = "U4uRz/MrYA5O4lQNw/zHIlq7v5ez+Mv8ljw80oq3pVU="
COLLECTOR_INVESTOR_API_URI_TEMPLATE = "https://bid.collectorinvestorauctions.com/api/listing/search/{offset}/{limit}"
COLLECTOR_INVESTOR_CONTENT_TYPE = "application/json"
COLLECTOR_INVESTOR_DEFAULT_TIMEOUT = 45

# Azure OpenAI
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip()
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "").strip()

# API Server
API_HOST = "0.0.0.0"
API_PORT = 8000
API_RELOAD = True

# Tag generation
TAG_COUNT_MIN = 35
TAG_COUNT_MAX = 50
TAG_TEMPERATURE = 0.2
TAG_MAX_TOKENS = 320

import os
import base64
import logging
import requests
from dotenv import load_dotenv
from config import USD_TO_AED_RATE, TARGET_BUY_PERCENTAGE

load_dotenv()
logger = logging.getLogger(__name__)

EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")

# Cached token in memory
_CACHED_TOKEN = None


def get_ebay_oauth_token() -> str | None:
    """Fetches or refreshes an eBay Application Access Token (OAuth 2.0)."""
    global _CACHED_TOKEN
    if _CACHED_TOKEN:
        return _CACHED_TOKEN

    url = "https://api.ebay.com/identity/v1/oauth2/token"
    auth_str = f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {b64_auth}",
    }
    payload = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }

    try:
        res = requests.post(url, headers=headers, data=payload, timeout=10)
        res.raise_for_status()
        data = res.json()
        _CACHED_TOKEN = data.get("access_token")
        return _CACHED_TOKEN
    except Exception as e:
        logger.error(f"Failed to obtain eBay OAuth token: {e}")
        return None


def fetch_ebay_sold_stats(part_number: str) -> dict:
    """
    Searches eBay Browse API for active market listings and price distribution.
    """
    token = get_ebay_oauth_token()
    if not token:
        return {"success": False, "error": "Invalid eBay API Client ID / Secret."}

    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
    }
    params = {
        "q": part_number.strip(),
        "limit": 50,
        "filter": "buyingOptions:{FIXED_PRICE|AUCTION}",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        # If token expired, clear cache and retry once
        if response.status_code == 401:
            global _CACHED_TOKEN
            _CACHED_TOKEN = None
            token = get_ebay_oauth_token()
            headers["Authorization"] = f"Bearer {token}"
            response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code != 200:
            return {"success": False, "error": f"eBay Browse API error: {response.status_code} - {response.text}"}

        data = response.json()
        total_found = data.get("total", 0)
        items = data.get("itemSummaries", [])

        if total_found == 0 or not items:
            return {
                "success": True,
                "part_number": part_number,
                "active_count": 0,
                "status": "FAIL",
                "reason": "No active market listings found for this part."
            }

        prices_usd = []
        for item in items:
            price_info = item.get("price", {})
            val = float(price_info.get("value", 0))
            curr = price_info.get("currency", "USD")
            if curr == "USD" and val > 0:
                prices_usd.append(val)

        if not prices_usd:
            return {"success": False, "error": "No USD price points found in market listings."}

        min_usd = min(prices_usd)
        max_usd = max(prices_usd)
        avg_usd = sum(prices_usd) / len(prices_usd)

        max_buy_usd = min_usd * TARGET_BUY_PERCENTAGE  # Target buying at <35% of the LOWEST active comp
        max_buy_aed = max_buy_usd * USD_TO_AED_RATE

        return {
            "success": True,
            "part_number": part_number,
            "active_count": len(prices_usd),
            "min_usd": min_usd,
            "avg_usd": avg_usd,
            "max_usd": max_usd,
            "min_aed": min_usd * USD_TO_AED_RATE,
            "avg_aed": avg_usd * USD_TO_AED_RATE,
            "max_aed": max_usd * USD_TO_AED_RATE,
            "target_buy_aed": max_buy_aed,
            "status": "PASS",
            "reason": f"{len(prices_usd)} active market comps found."
        }

    except Exception as e:
        logger.error(f"Browse API Error: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    test_part = "Mettler Toledo PB1502-S"
    print(f"Testing Browse API on: {test_part}...")
    result = fetch_ebay_sold_stats(test_part)
    print(result)
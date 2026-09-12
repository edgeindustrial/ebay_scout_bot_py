import re
import logging
from bs4 import BeautifulSoup
from curl_cffi import requests
from config import USD_TO_AED_RATE, MIN_SOLD_THRESHOLD, TARGET_BUY_PERCENTAGE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_price(price_str: str) -> float | None:
    """Extracts a clean numeric float from strings like '$145.50' or '$120.00 to $150.00'."""
    try:
        # If there's a price range, take the lower bound
        if "to" in price_str.lower():
            price_str = price_str.lower().split("to")[0]

        cleaned = re.sub(r"[^\d.]", "", price_str)
        return float(cleaned) if cleaned else None
    except Exception:
        return None


def fetch_ebay_sold_stats(part_number: str) -> dict:
    """
    Scrapes eBay sold listings using Chrome browser impersonation (bypasses 403 blocks).
    """
    query = part_number.strip().replace(" ", "+")
    url = f"https://www.ebay.com/sch/i.html?_nkw={query}&LH_Complete=1&LH_Sold=1&_ipg=60"

    headers = {
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.ebay.com/",
    }

    try:
        # impersonate="chrome120" mimics genuine Chrome TLS & HTTP/2 signatures
        response = requests.get(
            url, 
            headers=headers, 
            impersonate="chrome120", 
            timeout=15
        )

        if response.status_code != 200:
            return {"success": False, "error": f"eBay returned HTTP status {response.status_code}"}

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select(".s-item")
        prices_usd = []

        for item in items:
            title_elem = item.select_one(".s-item__title")
            price_elem = item.select_one(".s-item__price")

            if not title_elem or not price_elem:
                continue

            title = title_elem.get_text(strip=True)
            # Skip the dummy promotional item eBay injects at index 0
            if "shop on ebay" in title.lower():
                continue

            price_raw = price_elem.get_text(strip=True)
            price_num = clean_price(price_raw)

            if price_num and price_num > 0:
                prices_usd.append(price_num)

        total_sold = len(prices_usd)

        if total_sold == 0:
            return {
                "success": True,
                "part_number": part_number,
                "sold_count_90d": 0,
                "status": "FAIL",
                "reason": "0 units sold on eBay in the last 90 days."
            }

        min_usd = min(prices_usd)
        max_usd = max(prices_usd)
        avg_usd = sum(prices_usd) / total_sold

        max_buy_usd = avg_usd * TARGET_BUY_PERCENTAGE
        max_buy_aed = max_buy_usd * USD_TO_AED_RATE
        is_viable = total_sold >= MIN_SOLD_THRESHOLD

        return {
            "success": True,
            "part_number": part_number,
            "sold_count_90d": total_sold,
            "min_usd": min_usd,
            "avg_usd": avg_usd,
            "max_usd": max_usd,
            "min_aed": min_usd * USD_TO_AED_RATE,
            "avg_aed": avg_usd * USD_TO_AED_RATE,
            "max_aed": max_usd * USD_TO_AED_RATE,
            "target_buy_aed": max_buy_aed,
            "status": "PASS" if is_viable else "FAIL",
            "reason": f"{total_sold} units found in recent sold history."
        }

    except Exception as e:
        logger.error(f"Scraper error: {e}")
        return {"success": False, "error": f"Failed to retrieve sold data: {str(e)}"}


# Direct test runner
if __name__ == "__main__":
    test_part = "PB1502-S"
    print(f"Testing Chrome impersonator on: {test_part}...")
    result = fetch_ebay_sold_stats(test_part)
    print(result)
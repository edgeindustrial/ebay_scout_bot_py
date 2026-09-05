import logging
import requests
from config import EBAY_APP_ID, EBAY_FINDING_API_URL, EBAY_GLOBAL_ID, USD_TO_AED_RATE, MIN_SOLD_THRESHOLD, TARGET_BUY_PERCENTAGE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_ebay_sold_stats(part_number: str) -> dict:
    headers = {
        "X-EBAY-SOA-OPERATION-NAME": "findCompletedItems",
        "X-EBAY-SOA-SERVICE-VERSION": "1.13.0",
        "X-EBAY-SOA-SECURITY-APPNAME": EBAY_APP_ID,
        "X-EBAY-SOA-RESPONSE-DATA-FORMAT": "JSON",
        "X-EBAY-SOA-GLOBAL-ID": EBAY_GLOBAL_ID,
    }

    params = {
        "keywords": part_number,
        "itemFilter(0).name": "SoldItemsOnly",
        "itemFilter(0).value": "true",
        "paginationInput.entriesPerPage": "100",
        "sortOrder": "EndTimeSoonest",
    }

    try:
        response = requests.get(EBAY_FINDING_API_URL, headers=headers, params=params, timeout=10)
        data = response.json()
        finding_resp = data.get("findCompletedItemsResponse", [{}])[0]
        
        if finding_resp.get("ack", ["Failure"])[0] != "Success":
            return {"success": False, "error": "eBay API rejected the search query."}

        search_result = finding_resp.get("searchResult", [{}])[0]
        items = search_result.get("item", [])

        if not items:
            return {
                "success": True,
                "part_number": part_number,
                "sold_count_90d": 0,
                "status": "FAIL",
                "reason": "0 units sold in the last 90 days."
            }

        prices_usd = []
        for item in items:
            price_val = float(item["sellingStatus"][0]["currentPrice"][0]["__value__"])
            curr = item["sellingStatus"][0]["currentPrice"][0]["@currencyId"]
            if curr == "USD" and price_val > 0:
                prices_usd.append(price_val)

        if not prices_usd:
            return {"success": False, "error": "No USD sales found for this item."}

        total_sold = len(prices_usd)
        min_usd = min(prices_usd)
        max_usd = max(prices_usd)
        avg_usd = sum(prices_usd) / total_sold

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
            "target_buy_aed": (avg_usd * TARGET_BUY_PERCENTAGE) * USD_TO_AED_RATE,
            "status": "PASS" if total_sold >= MIN_SOLD_THRESHOLD else "FAIL"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
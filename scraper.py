from playwright.sync_api import sync_playwright
import json
from pathlib import Path
from collections import Counter


def main():
    merchants = []
    menus = []
    promos = []
    shortcuts_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        api_responses = []

        def handle_response(response):
            url = response.url
            if "portal.grab.com" in url:
                try:
                    data = response.json()
                    api_responses.append({"url": url, "data": data})
                    if "shortcuts" in data:
                        shortcuts_data.extend(data.get("shortcuts", []))
                except:
                    pass

        page.on("response", handle_response)

        print("Loading Grab Food...")
        page.goto("https://food.grab.com/id/id/restaurants", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)

        for i in range(5):
            page.evaluate("window.scrollBy(0, 1500)")
            page.wait_for_timeout(1000)

        print(f"Captured {len(api_responses)} API responses")

        # Extract merchant list data
        for resp in api_responses:
            data = resp.get("data", {})
            if "searchResult" in data:
                for m in data["searchResult"].get("searchMerchants", []):
                    brief = m.get("merchantBrief", {})
                    merchant = {
                        "id": m.get("id"),
                        "name": brief.get("displayInfo", {}).get("primaryText")
                        or m.get("chainName"),
                        "chain_name": m.get("chainName"),
                        "branch": m.get("branchName"),
                        "cuisines": brief.get("cuisine", []),
                        "rating": brief.get("rating"),
                        "vote_count": brief.get("vote_count"),
                        "price_tag": brief.get("priceTag"),
                        "delivery_time_mins": m.get("estimatedDeliveryTime"),
                        "distance_km": brief.get("distanceInKm"),
                    }
                    merchants.append(merchant)

                    for promo in m.get("sideLabels", {}).get("data", []):
                        promos.append(
                            {
                                "merchant_id": m.get("id"),
                                "merchant_name": merchant["name"],
                                "type": promo.get("type"),
                                "text": promo.get("displayedText"),
                            }
                        )

        seen_ids = set()
        unique_merchants = []
        for m in merchants:
            if m["id"] not in seen_ids:
                seen_ids.add(m["id"])
                unique_merchants.append(m)
        merchants = unique_merchants

        print(f"Found {len(merchants)} unique merchants")

        # Get restaurant links
        restaurant_links = page.query_selector_all('a[href*="/restaurant/"]')
        sample_size = min(15, len(restaurant_links))

        print(f"\nScraping menus for {sample_size} restaurants...")

        menu_api_responses = []

        def handle_menu_response(response):
            url = response.url
            if "v2/merchants/" in url and "latlng" in url:
                try:
                    data = response.json()
                    menu_api_responses.append(data)
                except:
                    pass

        page.remove_listener("response", handle_response)
        page.on("response", handle_menu_response)

        for i in range(sample_size):
            page.goto("https://food.grab.com/id/id/restaurants", timeout=60000)
            page.wait_for_load_state("networkidle", timeout=20000)
            page.wait_for_timeout(2000)

            for _ in range(3):
                page.evaluate("window.scrollBy(0, 500)")
                page.wait_for_timeout(500)

            links = page.query_selector_all('a[href*="/restaurant/"]')

            if i < len(links):
                link = links[i]
                href = link.get_attribute("href")
                merchant_id = href.split("/")[-1].split("?")[0]
                print(f"  {i + 1}/{sample_size}: {merchant_id}")

                try:
                    link.click()
                    page.wait_for_url("**/restaurant/**", timeout=10000)
                    page.wait_for_timeout(3000)
                except Exception as e:
                    print(f"    Error: {e}")

        print(f"\nCaptured {len(menu_api_responses)} menu API responses")

        for resp in menu_api_responses:
            if "merchant" in resp:
                m = resp["merchant"]
                currency = m.get("currency", {})
                symbol = currency.get("symbol", "Rp")
                exponent = currency.get("exponent", 2)

                menu_categories = m.get("menu", {}).get("categories", [])
                for cat in menu_categories:
                    section_name = cat.get("name", "Unknown")
                    for item in cat.get("items", []):
                        price_minor = item.get("priceInMinorUnit", 0)
                        price_display = f"{symbol}{price_minor / (10**exponent):,.0f}"

                        discounted_minor = item.get("discountedPriceInMin")
                        if discounted_minor:
                            discounted_display = (
                                f"{symbol}{discounted_minor / (10**exponent):,.0f}"
                            )
                        else:
                            discounted_display = None

                        menus.append(
                            {
                                "merchant_id": m.get("ID"),
                                "merchant_name": m.get("chainName"),
                                "category": section_name,
                                "item_name": item.get("name"),
                                "description": item.get("description"),
                                "price": price_display,
                                "discounted_price": discounted_display,
                                "price_cents": int(
                                    price_minor / (10**exponent)
                                ),  # Divided: 14850000/100 = 148500
                                "discounted_price_cents": int(
                                    discounted_minor / (10**exponent)
                                )
                                if discounted_minor
                                else None,
                                "available": item.get("available"),
                            }
                        )

        print(
            f"Extracted {len(menus)} menu items from {len(menu_api_responses)} restaurants"
        )

        browser.close()

    # ANALYSIS
    print("\n" + "=" * 60)
    print("GRAB FOOD INDONESIA - MENU ANALYSIS")
    print("=" * 60)

    if menus:
        cat_counter = Counter()
        for item in menus:
            cat_counter[item["category"]] += 1

        print("\n[1] MENU CATEGORIES (by item count)")
        for cat, count in cat_counter.most_common(15):
            print(f"  {cat}: {count} items")

        print("\n[2] SAMPLE ITEMS BY RESTAURANT")
        by_restaurant = {}
        for item in menus:
            name = item["merchant_name"]
            if name not in by_restaurant:
                by_restaurant[name] = []
            by_restaurant[name].append(item)

        for rest, items in list(by_restaurant.items())[:5]:
            print(f"\n  {rest} ({len(items)} items):")
            for item in items[:5]:
                price = item["discounted_price"] or item["price"]
                print(f"    - {item['category']}: {item['item_name']} | {price}")

    # Save
    Path("output").mkdir(exist_ok=True)
    with open("output/merchants.json", "w") as f:
        json.dump(merchants, f, indent=2, default=str)
    with open("output/menus.json", "w") as f:
        json.dump(menus, f, indent=2, default=str)
    with open("output/promos.json", "w") as f:
        json.dump(promos, f, indent=2, default=str)
    with open("output/shortcuts.json", "w") as f:
        json.dump(shortcuts_data, f, indent=2, default=str)

    print(f"\nSaved: {len(merchants)} merchants, {len(menus)} menu items")


if __name__ == "__main__":
    main()

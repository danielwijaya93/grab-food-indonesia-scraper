# Grab Food Indonesia Scraper - Project Learnings

## Overview
Built a Playwright-based scraper for Grab Food Indonesia (Jakarta) to analyze market trends at restaurant and menu level.

## Key Learnings

### 1. Grab Food Web Architecture

**Dynamic Rendering**: Grab Food loads content dynamically via JavaScript after initial page load. HTML scraping failed because restaurant data is NOT in the initial HTML - it loads via API calls after `networkidle`.

**API Discovery**: The restaurant data comes from WAF-protected APIs at `portal.grab.com/foodweb/guest/v2/`. Direct `requests.get()` calls return 401 Unauthorized.

**API Endpoints Found**:
- `https://portal.grab.com/foodweb/guest/v2/recommended/merchants` - recommended restaurants
- `https://portal.grab.com/foodweb/guest/v2/search` - search results  
- `https://portal.grab.com/foodweb/guest/v2/category/shortcuts` - trending collections/promos
- `https://portal.grab.com/foodweb/guest/v2/merchants/{id}?latlng=...` - **restaurant detail with full menu**

### 2. Playwright Strategy

**Why Playwright over requests**: The API is behind Grab's WAF (Web Application Firewall) which blocks direct HTTP clients but allows browser-based requests.

**Key Implementation Details**:
```python
# Launch browser and intercept API responses
browser = p.chromium.launch(headless=True)
page.on("response", handle_response)  # Listen for API responses

page.goto("https://food.grab.com/id/id/restaurants", timeout=60000)
page.wait_for_load_state("networkidle", timeout=30000)
page.wait_for_timeout(5000)  # Extra wait for dynamic content
```

**Scrolling Required**: Grab Food lazy-loads content. Must scroll to trigger additional API calls:
```python
for i in range(5):
    page.evaluate("window.scrollBy(0, 2000)")
    page.wait_for_timeout(1500)
```

### 3. Restaurant Data Structure

**Merchant List API Response** (`searchResult.searchMerchants[]`):
```json
{
  "merchantBrief": {
    "cuisine": ["Western", "Fried Chicken"],
    "rating": 4.4,
    "vote_count": 2605,
    "priceTag": 1,  // 1=budget, 2=mid, 3=upscale, 4=premium
    "displayInfo": {"primaryText": "KFC - Stasiun Gambir"}
  },
  "sideLabels": {"data": [{"type": "omegaPromoTag", "displayedText": "Rp15.000 off"}]},
  "highlights": [{"type": "promoTag", "title": "25% off", "subtitle": "Min. spend Rp100.000"}]
}
```

### 4. Menu Data Structure

**Restaurant Detail API Response** (`merchant`):
```json
{
  "ID": "IDGFSTI00000fe5",
  "chainName": "KFC",
  "currency": {"code": "IDR", "symbol": "Rp", "exponent": 2},
  "menu": {
    "categories": [
      {
        "name": "Menu promo",
        "items": [
          {
            "ID": "item123",
            "name": "Puas Burger Extra",
            "priceInMinorUnit": 2900000,  // 29,000 IDR (exponent 2)
            "discountedPriceInMin": 2900000,
            "available": true
          }
        ]
      }
    ]
  }
}
```

**Price Calculation**: `priceInMinorUnit / (10 ** exponent)` gives actual price

### 5. Debugging Approach

**Iteration 1**: Tried BeautifulSoup on HTML → Found 0 cards (dynamic content)
**Iteration 2**: Inspected page classes → Found obfuscated class names like `RestaurantListCol___1FZ8V`
**Iteration 3**: Used response interceptor → Found API calls at `portal.grab.com`
**Iteration 4**: Tried direct requests with headers → 401 (WAF blocks non-browser)
**Iteration 5**: Playwright browser with response listener → Success capturing restaurant list API
**Iteration 6**: Clicked restaurant link → Found merchant detail API with full menu

### 6. Running the Scraper

```bash
# Install dependencies
uv add crawlee[playwright] playwright beautifulsoup4 lxml
playwright install chromium

# Run scraper (captures merchants + menus)
uv run python scraper.py
```

### 7. Output Files

- `output/merchants.json` - All restaurant data (id, name, cuisines, rating, vote_count, price_tag)
- `output/menus.json` - Menu items (merchant_name, category, item_name, price, discounted_price)
- `output/promos.json` - All promotions extracted
- `output/shortcuts.json` - Trending collections/promos

### 8. Menu-Level Insights

**Sample restaurants with menu depth:**

| Restaurant | Menu Items | Top Categories |
|------------|------------|----------------|
| McDonald's | 600 | Burger & McNuggets, Minuman, Ayam McD Spicy |
| Solaria | 390 | Menu promo, Lauk Saja, Nasi Bungkus |
| KFC | 259 | Menu promo, Untukmu, KFC to Go |
| FamilyMart | 179 | Untukmu, Minuman |
| HokBen | 175 | Menu promo |
| Nasi Padang Cinto Bundo | 112 | Menu promo |
| Ayam Goreng Mak Dura | 98 | - |
| Wingstop | 88 | - |
| Bakmi GM | 51 | - |
| Shihlin Taiwan Street Snacks | 40 | - |

**Common menu categories across all restaurants:**

| Category | Item Count |
|----------|------------|
| Menu promo | 145 |
| Burger & McNuggets | 135 |
| Minuman/Drinks | 104 |
| Ayam McD Spicy | 96 |
| Untukmu (P-for-You) | 88 |
| Ayam McD Krispy | 87 |
| Menu Porsi | 66 |
| Menu Paket | 66 |
| Menu Receh | 44 |
| Snack | 38 |

### 9. Limitations & Notes

- **Headless vs Headful**: `headless=False` shows browser window; `headless=True` runs faster
- **Pagination**: Data is loaded via infinite scroll, not traditional pagination
- **Rate Limiting**: Adding delays between runs helps avoid WAF blocks
- **Coordinates**: Hardcoded Jakarta coordinates (-6.1767352, 106.826504); different areas need different lat/lng
- **Menu Scraping**: Requires visiting each restaurant page individually to capture menu API

### 10. Market Insights Summary

| Metric | Finding |
|--------|---------|
| Top Cuisine | Kopi/Coffee (18.8% of restaurants) |
| Dominant Price Band | $$ Mid-level (43.8%) |
| Top Reviewed | McDonald's Gambir (22,802 votes) |
| Common Promo | 25% discount (most frequent) |
| Rising Competitors | McDonald's, Bakmi GM, HokBen, Chatime |
| Menu Item Range | 100-600 items per restaurant |

## Future Enhancements

### 1. Scheduled Scraping for Trend Detection

Currently: Single point-in-time snapshot
**Goal**: Capture temporal trends to identify truly *rising* vs declining categories

**Planned schedule**:
```
┌─────────────────────────────────────────────────────────────┐
│ Daily Run: 3x/day                                           │
│   - Breakfast:  6:00 AM  - 10:00 AM                          │
│   - Lunch:    11:00 AM -  2:00 PM                            │
│   - Dinner:    5:00 PM -  9:00 PM                            │
└─────────────────────────────────────────────────────────────┘
```

**Metrics to derive**:
- New restaurants appearing across time slots
- Restaurants with increasing/decreasing visibility in "recommended"
- Promo frequency changes by time of day
- Menu item availability shifts (sold out detection)

### 2. Multi-Location Scraping

Currently: Single coordinate (Gambir train station area)
**Goal**: Cover all of Jakarta's delivery zones

**Planned locations**:
| Area | Latitude | Longitude |
|------|----------|-----------|
| Gambir (current) | -6.1767352 | 106.826504 |
| Sudirman/Thamrin | -6.1900 | 106.8200 |
| Kemang | -6.2833 | 106.8167 |
| Blok M | -6.2400 | 106.7800 |
| Senayan | -6.2100 | 106.7900 |
| Kelapa Gading | -6.1600 | 106.9100 |
| PIK | -6.1100 | 106.8700 |
| Kemayoran | -6.1500 | 106.8400 |

**Benefits**:
- Geographic competitor density mapping
- Price band variations by neighborhood
- Cuisine preference differences across areas
- Delivery coverage analysis

### 3. Full Menu Pricing for All Restaurants

**Current state**: We capture pricing in IDR (`priceInMinorUnit`) for 15 sample restaurants = 2,019 items

**Planned**: Expand to all 154 restaurants

**Menu pricing analysis possibilities**:
- Average item price by cuisine category
- Price distribution histograms
- Discount depth analysis (compare `priceInMinorUnit` vs `discountedPriceInMin`)
- Price elasticity indicators (which items get discounted most often)
- "Value" menu identification by price band

### 4. Expanded Restaurant Coverage

**Current limitation**: Menu data limited to 15 sample restaurants because:
- Each restaurant requires a page visit
- Menu API only fires on actual navigation to restaurant page

**Solution approaches**:
1. **Parallel browser contexts** - visit multiple restaurants simultaneously
2. **Batch API calls** - if Grab exposes a bulk menu endpoint
3. **Prioritization** - focus on top 50 by rating/votes first
4. **Incremental scraping** - run continuously, adding menus over time

**Target**: 154 restaurants × ~100 menu items = ~15,400 menu items

## Commands Reference

```bash
# Install browser
playwright install chromium

# Run scraper
uv run python scraper.py

# View merchants
cat output/merchants.json | python3 -m json.tool | head -30

# View menus
cat output/menus.json | python3 -m json.tool | head -30
```

## Next Steps (when resuming)

```bash
# 1. Run scraper
cd grab_scraper && uv run python scraper.py

# 2. Load data into database
cd ../grab_data && uv run python -m grab_data.cli -i ../grab_scraper/output

# 3. Start analytics dashboard
cd ../grab_analytics && uv run streamlit run app.py
```
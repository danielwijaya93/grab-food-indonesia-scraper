# Grab Food Indonesia Market Intelligence

A data pipeline for scraping, storing, and analyzing Grab Food Indonesia restaurant and menu data.

## Architecture

```
scraper.py → grab_data pipeline → SQLite DB → Streamlit Dashboard
```

## Projects

| Project | Description |
|---------|-------------|
| `grab_scraper` | Playwright-based scraper for Grab Food Jakarta |
| `grab_data` | ETL pipeline to SQLite with time-series tracking |
| `grab_analytics` | Streamlit dashboard for market analysis |

## Quick Start

### 1. Scrape Data
```bash
cd grab_scraper
uv run python scraper.py
```

### 2. Load to Database
```bash
cd grab_data
uv run python -m grab_data.cli -i ../grab_scraper/output
```

### 3. Launch Dashboard
```bash
cd grab_analytics
uv run streamlit run app.py
```

## Features

- **154 restaurants** captured with cuisines, ratings, reviews
- **1,700+ menu items** with pricing
- **500+ promotions** tracked
- **Time-series tracking** - compare data across multiple scrape runs
- **Interactive dashboard** - 7 pages of market analysis

## Business Questions Answered

| Question | Analysis |
|----------|----------|
| Which cuisines are trending? | Kopi/Coffee leads (18.8%) |
| What price bands show growth? | $$ Mid-level dominates (39%) |
| Which products receive most reviews? | McDonald's Gambir (22.8K votes) |
| What promotional mechanics are common? | Rp15.000 off, 20-25% discounts |
| Which competitors are rising fastest? | McDonald's, Bakmi GM, HokBen, Chatime |

## Future Enhancements

1. **Scheduled scraping** - 3x daily (breakfast/lunch/dinner)
2. **Multi-location** - Cover all Jakarta areas
3. **Full menu coverage** - All 154 restaurants
4. **Trend detection** - Historical comparison over time

## License

MIT

# Board Game Geography

An interactive map showing the real-world locations associated with board games. Features a streamlined 3-step data processing pipeline and responsive web interface for exploring where your favorite games are set!

## ✨ Features

- **🗺️ Interactive World Map**: Leaflet.js with OpenStreetMap integration and marker clustering
- **🎲 BoardGameGeek Integration**: Direct BGG API integration with family tag validation and game links
- **⚡ Simple 3-Step Pipeline**: CSV processing without database complexity
- **🌍 Smart Geocoding**: 5-tier Nominatim fallback strategy with caching
- **📱 Responsive Design**: Works on desktop, tablet, and mobile
- **🔗 Game Links**: Direct links to BoardGameGeek for each game
- **📊 Data Export**: Clean JSON output in standardized format

## 🚀 Quick Start

### Option 1: Use Pre-processed Data (Recommended)
1. Clone the repository
2. Open `index.html` directly in your web browser
3. Games automatically load from the embedded dataset on first visit
4. Use BGG ranking filter (Top 100/500/1000/5000) and category filters
5. Explore the map with clustered markers and clickable game links

### Option 2: Run Simple Pipeline
1. **Download Required Data**:
   - [BoardGameGeek CSV](https://boardgamegeek.com/data_dumps/bg_ranks): `data/bgg/boardgames_ranks.csv`
   - [GeoNames dataset](https://www.geonames.org/export/): `data/geonames/cities500.txt`

2. **Run Simple Pipeline**:
   ```bash
   python bin/run_pipeline.py
   ```

3. **Launch Web App**: Open `index.html` in browser

## 📋 Pipeline Architecture

The project uses a streamlined 3-step approach:

### Step 1: Preprocessing (`preprocess_data.py`)
- Filters BGG CSV by basic city name matching against GeoNames dataset
- Always includes top 2,500 games for BGG family validation
- Skips expansions and low-rated games for quality
- **Output**: `data/processed/filtered_games.csv`

### Step 2: Cache Population (`get_bgg_info.py`)
- Populates BGG API cache for all filtered games
- Uses efficient batch API calls with rate limiting
- Comprehensive progress reporting
- **Output**: BGG cache files in `data/cache/bgg/`

### Step 3: Validation & Geocoding (`validate_and_geotag.py`)
- Finds games with exactly one BGG "Cities:" family tag
- Uses 5-tier Nominatim geocoding with fallback strategies
- Exports results in games.json format
- **Output**: `data/exports/bgg_family_games.json`

## 🛠️ Usage

### Complete Pipeline
```bash
python bin/run_pipeline.py
```

### Individual Steps
```bash
python bin/preprocess_data.py    # Step 1: Filter BGG CSV
python bin/get_bgg_info.py       # Step 2: Populate BGG cache  
python bin/validate_and_geotag.py # Step 3: Validate & geocode
```

### Testing
```bash
python bin/test_pipeline.py     # Test with sample data
```

### Custom Options
```bash
# Custom data sources and limits
python bin/run_pipeline.py data/bgg/boardgames_ranks.csv data/geonames/cities500.txt 5000

# View cache statistics
python bin/bgg_cache.py stats
```

## 📁 Project Structure

```
/
├── index.html              # Main web application
├── src/                    # Web application source code (4 files)
│   ├── app.js              # Core application logic
│   ├── pipeline-data.js    # Embedded approved games data
│   ├── pipeline-loader.js  # Loads pipeline data into IndexedDB
│   └── database.js         # IndexedDB storage layer
├── bin/                    # Simple 3-step data pipeline
│   ├── preprocess_data.py  # Step 1: Filter BGG CSV
│   ├── get_bgg_info.py     # Step 2: Populate BGG cache
│   ├── validate_and_geotag.py # Step 3: Validate & geocode
│   ├── run_pipeline.py     # Complete pipeline runner
│   ├── test_pipeline.py    # Pipeline testing
│   ├── bgg_cache.py        # BGG API caching layer
│   └── util.py             # Shared utilities
├── data/                   # Data files (mostly untracked)
│   ├── bgg/boardgames_ranks.csv
│   ├── geonames/cities500.txt
│   ├── cache/              # API response caches
│   ├── processed/filtered_games.csv
│   └── exports/bgg_family_games.json
└── ...
```

## 🎯 Key Benefits

### Simple Pipeline
- **Fast Execution**: Completes in minutes instead of hours
- **Easy Testing**: `test_pipeline.py` with sample data
- **Clear Steps**: 3 focused scripts with single responsibilities

### BGG Family Validation
- **High Confidence**: Uses BGG's manually curated "Cities:" family tags
- **Quality Data**: BGG families ensure geographical relevance
- **Direct Links**: Each game links to its BoardGameGeek page

### Static Web Interface
- **Auto-Loading**: Games load automatically on first visit
- **Smart Filtering**: BGG ranking filter + category filter with game counts
- **Marker Clustering**: Automatically groups overlapping city markers
- **No Dependencies**: Works offline with embedded data

### Smart Geocoding
- **5-Tier Fallback**: Multiple Nominatim query strategies
- **File Caching**: Both BGG and Nominatim responses cached locally
- **Rate Limiting**: Respects API limits (BGG: 2/sec, Nominatim: 1/sec)
- **Error Handling**: Graceful fallback for failed requests

## 🌍 How It Works

1. **City Name Matching**: Basic string normalization matches BGG game names against GeoNames cities
2. **BGG Family Discovery**: Games with exactly one "Cities: [location]" family tag are identified
3. **Geocoding**: Nominatim API converts city names to coordinates with multiple fallback strategies
4. **Web Display**: Interactive map shows games with color-coded confidence indicators

## 📊 Data Sources

- **BoardGameGeek**: Game metadata, ratings, and family classifications
- **GeoNames**: Comprehensive cities dataset with coordinates
- **Nominatim**: OpenStreetMap geocoding service

## 🚧 Known Limitations

- **Rate Limits**: API calls take time due to rate limiting (BGG: 2/sec, Nominatim: 1/sec)
- **Data Freshness**: Requires manual pipeline runs for new BGG data
- **BGG Dependencies**: Relies on BGG family tags for city identification
- **Local Processing**: Python pipeline runs on development machine

## 🤝 Contributing

1. Test changes with sample data: `python bin/test_pipeline.py`
2. Follow API rate limiting guidelines
3. Use file caching to avoid repeated API calls during development
4. Update documentation when changing architecture

## 🚧 TODO: Planned Enhancements

### Auto-Loading & Filtering
- [x] **Auto-load pipeline data** on page load (remove manual "Load Games" button)
- [x] **BGG ranking filter**: Dropdown for "Show BGG Top 100/500/1000/5000/All games"
- [x] **Category filtering**: Multi-select dropdown with major game categories (20+ games)

### Visual Enhancements
- [x] **Color-coded markers** by primary game category using priority hierarchy:
  - Wargame: Red markers (most distinctive)
  - Economic: Green markers  
  - Medieval/Ancient: Purple markers
  - Card Game: Blue markers
  - City Building: Orange markers
  - Other categories: Grey markers
- [x] **Updated legend** showing category colors instead of data source
- [x] **Enhanced popups** with essential information (BGG rank, location, year)

### Data Pipeline Updates
- [x] **Include categories** in `validate_and_geotag.py` export from BGG cache
- [x] **Preserve categories** in `update_pipeline_data.py` for web data
- [x] **Re-generate pipeline-data.js** with enriched category information
- [x] **Add expansion detection** using BGG family tags

### Implementation Notes
- BGG cache already contains categories/mechanics data at `data/cache/bgg/game_*.json`
- Current pipeline-data.js has 280+ games sorted by BGG rating
- Marker clustering already handles overlapping locations
- Static page approach maintained with embedded data

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **BoardGameGeek**: Comprehensive game database and API
- **GeoNames**: Free geographical database
- **OpenStreetMap**: Map data via Nominatim geocoding
- **Leaflet.js**: Interactive mapping library
# Board Game Geography - Project Instructions

## Project Overview
This is an interactive map application that displays real-world locations associated with board games. The project features a streamlined 3-step data pipeline for processing BoardGameGeek data and a web interface for exploring game locations. The system uses simple CSV processing with BGG API caching for efficient data handling.

## Current Architecture
- **Simple Pipeline**: 3-step CSV-based processing without database complexity
- **Frontend**: Vanilla HTML, CSS, JavaScript with Leaflet.js mapping
- **Data Sources**: BoardGameGeek XML API v2 + GeoNames cities dataset
- **Processing**: Direct CSV filtering with BGG family tag validation
- **Geocoding**: Nominatim API with 5-tier fallback strategy and caching
- **Web Interface**: Static files with embedded approved games data

## Project Structure
```
/
├── .gitignore              # Git ignore patterns
├── index.html              # Main web application
├── src/                    # Web application source code
│   ├── app.js              # Core application logic and UI management
│   ├── pipeline-loader.js  # Pipeline data import into IndexedDB
│   ├── pipeline-data.js    # Embedded approved games data (no CORS)
│   ├── bgg-api.js          # BoardGameGeek XML API integration (web)
│   ├── geocoding.js        # Nominatim geocoding pipeline (web)
│   ├── database.js         # IndexedDB schema and data management
│   ├── bulk-import.js      # Batch processing system for BGG data
│   ├── admin.js            # Validation tools and data export functionality
│   └── test-bgg-parsing.js # Unit tests for location parsing
├── bin/                    # Simple 3-step data pipeline
│   ├── preprocess_data.py  # Step 1: Filter BGG CSV by city name matching
│   ├── get_bgg_info.py     # Step 2: Populate BGG cache for filtered games
│   ├── validate_and_geotag.py # Step 3: Validate BGG families and geocode
│   ├── run_pipeline.py     # Complete 3-step pipeline runner
│   ├── test_pipeline.py    # Pipeline testing with sample data
│   ├── bgg_cache.py        # BGG API caching layer with file storage
│   └── util.py             # Shared utility functions and string normalization
├── data/                   # Data files (mostly untracked)
│   ├── bgg/                # BoardGameGeek CSV data
│   │   └── boardgames_ranks.csv
│   ├── geonames/           # GeoNames cities500.txt dataset
│   │   └── cities500.txt
│   ├── cache/              # API response caches
│   │   ├── bgg/            # BGG API cache files (game_*.json)
│   │   └── nominatim/      # Nominatim geocoding cache files
│   ├── processed/          # Intermediate pipeline files
│   │   └── filtered_games.csv # Step 1 output: filtered game data
│   ├── exports/            # Final pipeline outputs
│   │   └── bgg_family_games.json # Step 3 output: geocoded games
│   └── test/               # Test datasets and sample files
│       ├── cities_sample.txt
│       ├── games_sample.csv
│       └── test_games.json
├── CLAUDE.md               # Development guidelines (this file)
├── README.md               # Project documentation and roadmap
└── LICENSE                 # MIT License
```

## Development Guidelines

### Simple Pipeline Architecture
The project uses a streamlined 3-step approach that avoids database complexity:

**Step 1: Preprocessing** (`preprocess_data.py`):
- Filters BGG CSV by basic city name matching against GeoNames dataset
- Includes top N games (default 2,500) regardless of city match for BGG validation
- Skips expansions and low-rated games for quality
- Outputs: `data/processed/filtered_games.csv`

**Step 2: Cache Population** (`get_bgg_info.py`):
- Populates BGG API cache for all filtered games
- Uses efficient batch API calls with rate limiting
- Provides comprehensive progress reporting
- Outputs: BGG cache files in `data/cache/bgg/`

**Step 3: Validation & Geocoding** (`validate_and_geotag.py`):
- Finds games with exactly one BGG "Cities:" family tag
- Uses 5-tier Nominatim geocoding with fallback strategies
- Exports results in games.json format with rating/votes data
- Outputs: `data/exports/bgg_family_games.json`

**Web Application** (`src/` + `index.html`):
- Loads embedded approved games data for instant rendering
- Optional pipeline data import via JSON files
- Interactive map with Leaflet.js and responsive design

### Code Style
- **Python**: Use vanilla Python with minimal dependencies (urllib for HTTP)
- **JavaScript**: Vanilla JS, no frameworks
- **Rate Limiting**: BGG API (2 req/sec), Nominatim (1 req/sec)
- **Storage**: File-based caching, CSV processing, JSON export

### Simple Pipeline Execution

#### Complete Pipeline
```bash
python bin/run_pipeline.py  # Runs all 3 steps automatically
```

#### Individual Steps
```bash
python bin/preprocess_data.py    # Step 1: Filter BGG CSV
python bin/get_bgg_info.py       # Step 2: Populate BGG cache  
python bin/validate_and_geotag.py # Step 3: Validate & geocode
```

#### Testing
```bash
python bin/test_pipeline.py     # Test with sample data
```

### BGG Family Validation
- **Automatic Discovery**: Games with exactly one BGG "Cities:" family tag
- **High Confidence**: BGG families are manually curated, ensuring accuracy
- **No Manual Review**: Simplified validation based on BGG's own categorization
- **API Caching**: File-based cache with 30-day retention
- **Batch Processing**: Efficient BGG API usage with rate limiting

### City Name Preprocessing
- **Direct Matching**: Simple string normalization against GeoNames dataset
- **Top Games Inclusion**: Always process top N games for BGG family validation
- **Quality Filters**: Skip expansions and games with <100 ratings
- **Performance**: Fast CSV processing without database overhead

### Geocoding Strategy
The pipeline uses a 5-tier Nominatim geocoding strategy with fallback:

1. **Structured Query**: `city=Tokyo&country=Japan` (when region/country available)
2. **Simple Text Query**: "Tokyo, Japan" (comma-separated location)
3. **Primary Only**: "Tokyo" (city name only)
4. **Country Context**: "Tokyo Japan" (space-separated for context)

### Data Quality
- **BGG Family Validation**: Uses BGG's curated "Cities:" family tags
- **Confidence Scoring**: 0-1 scores based on geocoding tier and success
- **File Caching**: Both BGG and Nominatim responses cached locally
- **Error Handling**: Graceful fallback for failed geocoding or API errors
- **Export Format**: Clean JSON matching existing games.json structure

## Usage Instructions

### Simple Pipeline Setup
1. **Download Data**: 
   - BGG CSV: `data/bgg/boardgames_ranks.csv`
   - GeoNames: `data/geonames/cities500.txt`

2. **Run Complete Pipeline**:
   ```bash
   cd /path/to/bggeo
   python bin/run_pipeline.py
   ```

3. **Launch Web App**: Open `index.html` in browser

### Custom Pipeline Options
```bash
# Custom data sources and limits
python bin/run_pipeline.py data/bgg/boardgames_ranks.csv data/geonames/cities500.txt 5000

# Run individual steps
python bin/preprocess_data.py
python bin/get_bgg_info.py  
python bin/validate_and_geotag.py

# Test with sample data
python bin/test_pipeline.py
```

### Cache Management
```bash
# View BGG cache statistics  
python bin/bgg_cache.py stats

# Clear old cache files
python bin/bgg_cache.py clear

# Test specific BGG ID
python bin/bgg_cache.py test 1234
```

## Testing
- **Pipeline Testing**: `python bin/test_pipeline.py` with sample data
- **Sample Data**: `data/test/` contains smaller datasets for testing
- **Individual Steps**: Test each pipeline step independently
- **API Connectivity**: Built-in BGG and Nominatim API testing

## Deployment
- **Data Processing**: Run simple pipeline locally to generate datasets
- **Embedded Data**: Approved games included as `src/pipeline-data.js` (no server needed)
- **Web Development**: Open `index.html` directly, or serve via HTTP
- **Web Hosting**: Static site hosting (Netlify, Vercel, GitHub Pages)
- **No Backend**: All processing done offline, web app uses embedded + pipeline data
- **Performance**: Simple pipeline completes in minutes vs. hours

## Known Limitations
- **Rate Limits**: BGG (2/sec), Nominatim (1/sec) - pipeline takes time
- **Data Freshness**: Requires manual pipeline runs for new BGG data
- **Local Processing**: Python pipeline runs on development machine
- **BGG Dependencies**: Relies on BGG family tags for city identification
- **Geocoding Quality**: Dependent on Nominatim data accuracy

## Contributing
- Test changes with sample data first (`python bin/test_pipeline.py`)
- Follow rate limiting for all API requests
- Update both CLAUDE.md and README.md when changing architecture
- Use file caching to avoid repeated API calls during development

## Important Commands
- **Full Pipeline**: `python bin/run_pipeline.py`
- **Quick Test**: `python bin/test_pipeline.py`
- **Cache Stats**: `python bin/bgg_cache.py stats`
- **Individual Steps**: `python bin/preprocess_data.py`, `python bin/get_bgg_info.py`, `python bin/validate_and_geotag.py`
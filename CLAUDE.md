# Board Game Geography - Project Instructions

## Project Overview
This is an interactive map application that displays real-world locations associated with board games. The project features a comprehensive data pipeline for processing BoardGameGeek data and a web interface for exploring game locations. The system combines offline data processing with a responsive web frontend.

## Current Architecture
- **Data Pipeline**: Python scripts for BGG data processing and geocoding
- **Frontend**: Vanilla HTML, CSS, JavaScript with Leaflet.js mapping
- **Data Sources**: BoardGameGeek XML API v2 + GeoNames cities dataset
- **Processing**: SQLite database for local data processing and validation
- **Validation**: Hybrid approach (automated BGG validation + manual review interface)
- **Web Interface**: Static files with IndexedDB for browser storage

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
├── bin/                    # Data processing pipeline scripts
│   ├── init_database.py    # SQLite database schema creation
│   ├── load_bgg_data.py    # BoardGameGeek CSV data loader
│   ├── load_cities_data.py # GeoNames cities500.txt loader
│   ├── preprocess_data.py  # BGG game preprocessing and city name filtering
│   ├── simple_match.py     # Basic string matching algorithm
│   ├── fast_match.py       # Optimized matching for performance
│   ├── fuzzy_match.py      # Fuzzy string matching algorithm
│   ├── hybrid_match.py     # Combined matching strategies
│   ├── bgg_cache.py        # BGG API caching layer with file storage
│   ├── populate_cache.py   # Batch BGG API cache population
│   ├── validate_matches.py # BGG metadata validation for false positive detection
│   ├── manual_review.py    # Web-based manual review interface
│   ├── review_workflow.py  # Complete validation workflow orchestrator
│   ├── export_web_data.py  # Generate clean JSON for web application
│   ├── print_matches.py    # Human-readable match output formatter
│   ├── run_pipeline.py     # Complete pipeline execution script
│   ├── test_pipeline.py    # Pipeline testing and validation
│   ├── debug_bgg.py        # BGG API debugging utilities
│   ├── check_invalid_bgg_ids.py # Invalid BGG ID detection
│   ├── clean_invalid_games.py   # Remove invalid/deleted games
│   └── util.py             # Shared utility functions and string normalization
├── data/                   # Data files (mostly untracked)
│   ├── bgg/                # BoardGameGeek CSV data
│   │   └── boardgames_ranks.csv
│   ├── geonames/           # GeoNames cities500.txt dataset
│   │   └── cities500.txt
│   ├── cache/bgg/          # BGG API response cache (2,483+ files)
│   │   └── game_*.json     # Individual game cache files
│   ├── processed/          # SQLite database and intermediate files
│   │   ├── boardgames.db   # Main SQLite database
│   │   └── filtered_games.csv # Preprocessed game data
│   ├── exports/            # Generated web application data
│   │   ├── games.json      # Clean approved games for web app
│   │   ├── games_all.json  # All processed games with status
│   │   ├── matches_review.csv # Manual review export
│   │   └── summary_report.json # Pipeline execution summary
│   └── test/               # Test datasets and sample files
│       ├── cities_sample.txt
│       ├── games_sample.csv
│       ├── test_games.db
│       └── test_games.json
├── CLAUDE.md               # Development guidelines (this file)
├── README.md               # Project documentation and roadmap
└── LICENSE                 # MIT License
```

## Development Guidelines

### Data Pipeline Architecture
The project uses a two-phase approach:

1. **Offline Processing Phase** (`bin/` scripts):
   - Import BGG games and GeoNames cities data into SQLite
   - Run hybrid matching algorithm for performance
   - Validate matches using BGG API metadata
   - Manual review interface for remaining matches
   - Export clean JSON data for web application

2. **Web Application Phase** (`src/` + `index.html`):
   - Load pre-processed pipeline data via PipelineLoader for instant map rendering
   - Visual markers: green (approved), orange (pending/rejected), blue (real-time)
   - Optional real-time BGG integration for new games discovery
   - Interactive map with responsive design and data source legend

### Code Style
- **Python**: Use vanilla Python with minimal dependencies (requests → urllib)
- **JavaScript**: Vanilla JS, no frameworks
- **Rate Limiting**: BGG API (2 req/sec), Nominatim (1 req/sec)
- **Database**: SQLite for processing, IndexedDB for web storage

### Data Processing Pipeline

#### Step 1: Database Initialization
```bash
python bin/init_database.py  # Creates SQLite schema
```

#### Step 2: Data Loading
```bash
python bin/load_bgg_data.py      # Import boardgames_ranks.csv
python bin/load_cities_data.py   # Import cities500.txt
```

#### Step 3: Matching & Validation
```bash
python bin/hybrid_match.py       # Find game/city matches
python bin/populate_cache.py --matches-only  # Pre-populate BGG cache (NEW!)
python bin/review_workflow.py    # BGG validation + manual review
```

#### Step 4: Web Export
```bash
python bin/export_web_data.py    # Generate JSON for web app
```

### Hybrid Matching Strategy
- **Exact Matches**: Population ≥ 1,000 (catches smaller cities like Amalfi)
- **Substring Matches**: Population ≥ 500,000 (major cities only)
- **Performance**: ~2,891 total matches with good precision/recall balance

### BGG Validation System
- **Auto-Approval**: Very strict criteria (explicit "Cities: [city]" BGG families)
- **Auto-Rejection**: Abstract games with no geographical content
- **Manual Review**: Web interface with keyboard shortcuts (A/R/S)
- **Historical Detection**: Flags ancient/medieval games for review
- **API Caching**: 30-day file-based cache to avoid repeated requests
- **Batch Processing**: 20x faster cache population using BGG batch API
- **Invalid Game Cleanup**: Automatic detection and removal of deleted/unpublished games

### Manual Review Interface
- **Game-Based Review**: One interface card per game with radio button city selection
- **BGG Integration**: Full game descriptions, categories, families, and mechanics displayed
- **Smart Selection**: Radio buttons for city choices plus "no match" option
- **Keyboard Shortcuts**: 1-9 (select cities), 0 (no match), A (approve), S (skip)
- **Progress Tracking**: Real-time statistics and completion percentage
- **Data Display**: Rich BGG metadata with geographical context and visual feedback

### Geocoding Pipeline (Web App)
The web application maintains the 5-tier geocoding strategy:

1. **Structured Query**: `city=Tokyo&country=Japan`
2. **Simple Text Query**: "Tokyo, Japan"
3. **Primary Only**: "Tokyo"
4. **Full Location**: "Venice, Veneto, Italy"
5. **Country Only**: "Japan"

### Data Validation
- **BGG API Validation**: Metadata analysis for geographical indicators
- **Confidence Scoring**: 0-1 scores based on geocoding method and validation
- **Unit Tests**: Comprehensive test suite for parsing edge cases
- **Manual Review**: Web interface for human validation of uncertain matches
- **Export Quality**: Multiple formats (JSON, CSV, GeoJSON) for analysis

## Usage Instructions

### Data Pipeline Setup
1. **Download Data**: 
   - BGG CSV: `data/bgg/boardgames_ranks.csv`
   - GeoNames: `data/geonames/cities500.txt`

2. **Run Pipeline**:
   ```bash
   cd /path/to/bggeo
   python bin/init_database.py
   python bin/load_bgg_data.py
   python bin/load_cities_data.py
   python bin/hybrid_match.py
   python bin/review_workflow.py  # Interactive validation
   python bin/export_web_data.py
   ```

3. **Launch Web App**: Open `index.html` in browser

### Manual Review Workflow
1. **BGG Validation**: Auto-approves obvious matches, flags others
2. **Manual Review**: Web interface opens automatically
3. **Keyboard Shortcuts**: A (approve), R (reject), S (skip)
4. **Progress Tracking**: Real-time completion statistics

### Cache Management
```bash
python bin/populate_cache.py --matches-only  # Pre-populate cache (recommended)
python bin/bgg_cache.py stats               # View cache statistics
python bin/bgg_cache.py clear               # Clear old cache files
python bin/bgg_cache.py test 1234           # Test specific BGG ID
python bin/clean_invalid_games.py --ids X   # Remove invalid/deleted games
```

## Testing
- **Unit Tests**: `bin/test_*` scripts for core functionality
- **Sample Data**: `data/test/` contains smaller datasets for testing
- **Pipeline Validation**: End-to-end testing with sample games
- **API Connectivity**: BGG and Nominatim API testing tools

## Deployment
- **Data Processing**: Run pipeline locally to generate clean datasets
- **Embedded Data**: 69 approved games included as `src/pipeline-data.js` (no server needed)
- **Web Development**: Open `index.html` directly, or serve via HTTP for JSON imports
- **Web Hosting**: Static site hosting (Netlify, Vercel, GitHub Pages) with embedded data
- **No Backend**: All processing done offline, web app uses embedded data + IndexedDB
- **Performance**: Embedded data enables instant loading without CORS issues

## Known Limitations
- **Rate Limits**: BGG (2/sec), Nominatim (1/sec) - pipeline takes time
- **Data Freshness**: Requires manual pipeline runs for new BGG data
- **Local Processing**: Python pipeline runs on development machine
- **Storage**: SQLite database can become large with full BGG dataset
- **Manual Work**: Some matches require human validation

## Contributing
- Use validation tools to check data quality before committing
- Test changes with sample data first (`data/test/`)
- Follow rate limiting for all API requests
- Run manual review for any new matching algorithms
- Update both CLAUDE.md and README.md when changing architecture

## Important Commands
- **Full Pipeline**: `python bin/review_workflow.py`
- **Pre-populate Cache**: `python bin/populate_cache.py --matches-only`
- **Database Reset**: `rm data/processed/boardgames.db && python bin/init_database.py`
- **Quick Test**: `python bin/test_pipeline.py`
- **Web Export**: `python bin/export_web_data.py`
- **Cache Stats**: `python bin/bgg_cache.py stats`
- **Clean Invalid Games**: `python bin/clean_invalid_games.py --ids X --execute`
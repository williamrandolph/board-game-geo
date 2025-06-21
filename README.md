# Board Game Geography

An interactive map showing the real-world locations associated with board games. Features a comprehensive data processing pipeline and responsive web interface for exploring where your favorite games are set!

## ✨ Features

- **🗺️ Interactive World Map**: Leaflet.js with OpenStreetMap integration
- **🎲 Comprehensive Game Database**: BoardGameGeek integration with 2,500+ games
- **🎯 Intelligent Matching**: Hybrid algorithm for precise game-location matching
- **🤖 Smart Validation**: BGG metadata analysis + manual review interface
- **⚡ High Performance**: Pre-processed data for instant map loading
- **📱 Responsive Design**: Works on desktop, tablet, and mobile
- **🔍 Advanced Filtering**: Search and filter by game categories
- **📊 Data Export**: JSON, CSV, and GeoJSON export capabilities

## 🚀 Quick Start

### Option 1: Use Pre-processed Data (Recommended)
1. Clone the repository
2. Open `index.html` in your web browser
3. Explore the map with pre-loaded game locations

### Option 2: Run Full Data Pipeline
1. **Download Required Data**:
   - BoardGameGeek CSV: `data/bgg/boardgames_ranks.csv`
   - GeoNames dataset: `data/geonames/cities500.txt`

2. **Run Data Pipeline**:
   ```bash
   # Initialize database
   python bin/init_database.py
   
   # Load raw data
   python bin/load_bgg_data.py
   python bin/load_cities_data.py
   
   # Process matches
   python bin/hybrid_match.py
   
   # Pre-populate BGG cache (NEW - 20x faster!)
   python bin/populate_cache.py --matches-only
   
   # Validate and review (interactive)
   python bin/review_workflow.py
   
   # Export for web app
   python bin/export_web_data.py
   ```

3. **Launch Web App**: Open `index.html` in browser

## 🏗️ Architecture

### Two-Phase Design

**Phase 1: Offline Data Processing** (`bin/` scripts)
- Import BoardGameGeek and GeoNames datasets
- Run optimized matching algorithms  
- Validate matches using BGG API metadata
- Manual review interface for quality control
- Export clean JSON data for web application

**Phase 2: Web Application** (`src/` + `index.html`)
- Load pre-processed data for instant rendering
- Interactive map with responsive design
- Real-time search and filtering
- Optional live BGG integration for new games

### Data Pipeline Flow

```
BGG CSV Data → SQLite Database ← GeoNames Cities
     ↓
Hybrid Matching Algorithm (1K+ exact, 500K+ substring)
     ↓
Batch BGG Cache Population (20x faster than individual requests)
     ↓
BGG API Validation (auto-approve slam dunks)
     ↓
Manual Review Interface (web-based, keyboard shortcuts)
     ↓
Clean JSON Export → Web Application
```

## 📊 Matching Algorithm

### Hybrid Strategy for Performance + Accuracy
- **Exact Matches**: Cities with population ≥ 1,000 (catches smaller cities like Amalfi)
- **Substring Matches**: Cities with population ≥ 500,000 (major cities only)
- **Result**: ~2,891 total matches with optimal precision/recall balance

### BGG Validation System
- **Batch Cache Population**: 20x faster using BGG's batch API (up to 20 games per request)
- **Auto-Approval**: Very strict criteria (explicit "Cities: [city]" in BGG families)
- **Auto-Rejection**: Abstract games with no geographical indicators
- **Invalid Game Detection**: Automatically identifies deleted/unpublished games
- **Manual Review**: Web interface for human validation of uncertain matches
- **Historical Detection**: Flags ancient/medieval games to prevent modern city mismatches

## 🛠️ Tech Stack

### Data Processing
- **Language**: Python 3.x (minimal dependencies)
- **Database**: SQLite for local processing
- **APIs**: BoardGameGeek XML API v2, Nominatim geocoding
- **Caching**: File-based BGG API cache (30-day duration)
- **Validation**: Web-based manual review interface

### Web Application  
- **Frontend**: HTML, CSS, JavaScript (Vanilla - no frameworks)
- **Maps**: Leaflet.js with OpenStreetMap tiles
- **Storage**: IndexedDB for browser persistence
- **Hosting**: Static site compatible (Netlify/Vercel/GitHub Pages)

## 📁 Project Structure

```
board-game-geography/
├── 🌐 index.html              # Main web application
├── 📂 src/                    # Web application source
│   ├── app.js                 # Core app logic & UI
│   ├── bgg-api.js             # BGG integration (web)
│   ├── geocoding.js           # Nominatim geocoding
│   ├── database.js            # IndexedDB operations
│   └── admin.js               # Admin tools & export
├── 🔧 bin/                    # Data processing pipeline  
│   ├── init_database.py       # SQLite schema creation
│   ├── load_bgg_data.py       # BGG CSV importer
│   ├── load_cities_data.py    # GeoNames importer
│   ├── hybrid_match.py        # Matching algorithm
│   ├── bgg_cache.py           # API caching system
│   ├── validate_matches.py    # BGG metadata validation
│   ├── manual_review.py       # Web review interface
│   ├── review_workflow.py     # Complete workflow
│   └── export_web_data.py     # JSON export for web
├── 📁 data/                   # Data files (untracked)
│   ├── bgg/                   # BoardGameGeek CSV
│   ├── geonames/              # Cities dataset  
│   ├── cache/                 # BGG API cache
│   ├── processed/             # SQLite database
│   └── exports/               # Web app JSON
├── 📋 CLAUDE.md               # Development guidelines
└── 📄 README.md               # This file
```

## 🎮 Game Categories Supported

- **🏛️ Historical**: Ancient civilizations, medieval empires
- **🌍 Geographical**: City building, exploration, travel
- **💰 Economic**: Trade routes, empire building
- **🗺️ Area Control**: Territory conquest, civilization
- **🚂 Transportation**: Railways, shipping, logistics

## 📈 Data Quality & Validation

### Automated Validation
- **BGG Metadata Analysis**: Categories, families, and descriptions
- **Geographical Indicators**: Scoring system for location relevance
- **False Positive Detection**: Historical theme analysis
- **Confidence Scoring**: 0-1 scale based on validation strength

### Manual Review System
- **Web Interface**: Clean, responsive design with keyboard shortcuts
- **Progress Tracking**: Real-time completion statistics
- **Smart Prioritization**: BGG rank-based ordering
- **Batch Processing**: Efficient workflow for large datasets

### Quality Metrics
- **Precision**: High accuracy through strict auto-approval criteria
- **Recall**: Comprehensive matching with fallback strategies  
- **Performance**: Optimized for datasets with 50K+ games
- **Maintainability**: Clear separation of automated vs manual validation

## 🔄 Development Workflow

### Adding New Games
1. Update BGG CSV data
2. Run `python bin/load_bgg_data.py`
3. Run `python bin/hybrid_match.py`
4. Review matches with `python bin/review_workflow.py`
5. Export with `python bin/export_web_data.py`

### Testing Changes
```bash
# Test with sample data
python bin/test_pipeline.py

# Check cache performance  
python bin/bgg_cache.py stats

# Validate specific matches
python bin/print_matches.py --top 100
```

### Cache Management
```bash
python bin/populate_cache.py --matches-only  # Pre-populate cache (recommended)
python bin/bgg_cache.py stats               # View statistics
python bin/bgg_cache.py clear 7             # Clear files older than 7 days  
python bin/bgg_cache.py test 1234           # Test specific BGG ID
python bin/clean_invalid_games.py --ids X   # Remove deleted/unpublished games
```

## 🚀 Deployment

### Static Site Hosting
1. Run complete data pipeline to generate clean JSON
2. Upload entire project to static host (Netlify, Vercel, GitHub Pages)
3. No backend or database required for production
4. CDN recommended for global performance

### Performance Optimizations
- **Batch BGG API Caching**: 20x faster cache population (0.8 vs 24 minutes)
- **Pre-processed data** eliminates API rate limits during validation
- **Invalid game cleanup** removes deleted/unpublished games automatically
- Compressed JSON for faster loading
- Lazy loading for large datasets
- Browser caching via IndexedDB

## 🎯 Roadmap

### ✅ Phase 1: Core Features (Complete)
- [x] Interactive map with Leaflet.js
- [x] BoardGameGeek API integration
- [x] Hybrid matching algorithm
- [x] BGG validation system with batch caching
- [x] Manual review interface
- [x] Invalid game cleanup system
- [x] Data export capabilities

### 🚧 Phase 2: Enhanced Features (In Progress) 
- [ ] Advanced search and filtering
- [ ] Game detail pages with BGG links
- [ ] Multiple locations per game
- [ ] Historical accuracy indicators
- [ ] Mobile app development

### 🔮 Phase 3: Advanced Features
- [ ] User favorites and collections
- [ ] Community contributions
- [ ] Game route visualization (Ticket to Ride style)
- [ ] Location photos and descriptions
- [ ] Internationalization support

### 📊 Phase 4: Scaling & Analytics
- [ ] Performance optimization for 10K+ games
- [ ] Usage analytics and insights
- [ ] API for third-party integrations
- [ ] Offline map support
- [ ] Advanced data visualization

## 🤝 Contributing

We welcome contributions! Here's how to help:

### 🐛 Report Issues
- Game location inaccuracies
- Missing popular games  
- UI/UX improvements
- Performance issues

### 💻 Code Contributions
1. Fork the repository
2. Test changes with sample data first
3. Follow existing code style (vanilla JS/Python)
4. Update documentation if needed
5. Submit pull request

### 🎲 Data Contributions
- Suggest games with interesting locations
- Verify location accuracy
- Help with manual review process
- Contribute to BGG family data quality

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **BoardGameGeek**: Game data and community
- **GeoNames**: Comprehensive cities dataset
- **OpenStreetMap**: Map tiles and geographic data
- **Leaflet.js**: Interactive mapping library
- **Nominatim**: Free geocoding service

---

**🎯 Ready to explore where your favorite games are set? [Start here!](index.html)**
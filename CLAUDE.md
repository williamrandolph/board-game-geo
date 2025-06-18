# Board Game Geography - Project Instructions

## Project Overview
This is an interactive map application that displays real-world locations associated with board games. Users can explore where their favorite games are set by clicking on map markers. The app now features full BoardGameGeek integration for dynamic data import.

## Current Architecture
- **Frontend**: Vanilla HTML, CSS, JavaScript
- **Map Library**: Leaflet.js with OpenStreetMap tiles
- **Data Source**: BoardGameGeek XML API v2
- **Geocoding**: Nominatim API (free, 1 req/sec limit)
- **Database**: IndexedDB for local storage
- **Hosting**: Static files (can be served from any web server)

## Key Files
- `index.html` - Main application page with admin controls
- `app.js` - Core application logic and UI management
- `bgg-api.js` - BoardGameGeek XML API integration
- `geocoding.js` - Nominatim geocoding pipeline with caching
- `database.js` - IndexedDB schema and data management
- `bulk-import.js` - Batch processing system for BGG data
- `admin.js` - Validation tools and data export functionality
- `README.md` - Project documentation and roadmap

## Development Guidelines

### Code Style
- Use vanilla JavaScript (no frameworks currently)
- Maintain rate limiting for both BGG API (2 req/sec) and Nominatim (1 req/sec)
- Keep responsive design principles
- Use semantic HTML and accessible design

### BGG Integration Architecture
The app uses BGG's structured "game families" metadata to extract location data:
- **Location Family Types**: Cities, Country, Regions, States, Provinces
- **Format**: "Cities: Bordeaux (France)" → parsed to {primary: "Bordeaux", secondary: "France"}
- **Geocoding Strategy**: Try primary location first, then full string, then secondary
- **Confidence Scoring**: Based on type matching and name similarity

### Adding Games
Use the admin interface to import games:
1. **Popular Games**: Click "Import Popular Games" for curated list
2. **Specific Games**: Search BGG by name and import matches
3. **Bulk Import**: Use `BulkImportSystem` class for large datasets

### API Rate Limits & Caching
- **BGG API**: 2 requests per second, enforced in `bgg-api.js`
- **Nominatim**: 1 request per second, enforced in `geocoding.js`
- **Caching**: Geocoding results cached in-memory and IndexedDB
- **Batch Processing**: Configurable delays between batches

### Data Validation
- **Confidence Scores**: Geocoding confidence (0-1) based on type/name matching
- **Validation Tools**: `AdminTools.validateLocations()` identifies low-confidence results
- **Export Formats**: JSON, CSV, GeoJSON for data analysis

## Usage Instructions

### Initial Setup
1. Open `index.html` in web browser
2. Use admin panel (top-right) to import games
3. Data persists locally via IndexedDB

### Import Options
- **Import Popular Games**: 20 popular games with location data
- **Import Specific Game**: Search BGG by name
- **Clear All Data**: Reset local database
- **Export Data**: Download as JSON/CSV/GeoJSON

### System Monitoring
- **Stats Panel**: Shows games/locations/relationships count
- **Progress Tracking**: Real-time import progress
- **Error Handling**: Continues processing if individual games fail

## Testing
- Test BGG API connectivity with diagnostics
- Verify geocoding accuracy for sample locations
- Check rate limiting compliance
- Test IndexedDB operations across browser sessions

## Deployment
- Static site hosting (Netlify, Vercel, GitHub Pages)
- No backend required
- All data stored locally in browser
- CDN recommended for production

## Known Limitations
- **Rate Limits**: BGG (2/sec), Nominatim (1/sec) - imports take time
- **Local Storage**: Data tied to browser, no cloud sync
- **BGG Dependencies**: Requires BGG API availability
- **Location Accuracy**: Depends on BGG family metadata quality

## Contributing
- Use admin validation tools to check data quality
- Report location inaccuracies via GitHub issues
- Follow rate limiting for API requests
- Test changes with sample imports before committing
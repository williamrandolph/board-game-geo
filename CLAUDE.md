# Board Game Geography - Development Instructions

## Quick Reference
- **Pipeline**: 3 steps (preprocess → cache → geocode)
- **Test safely**: `python bin/test_pipeline.py` (uses data/test/ paths)
- **Rate limits**: BGG 2/sec, Nominatim 1/sec
- **Key files**: bin/ (8 scripts), src/ (web app), data/ (untracked)

## Development Patterns

### Adding Pipeline Features
- Modify individual scripts, not run_pipeline.py
- Always add output path parameters for test isolation
- Use file caching to avoid repeated API calls
- Follow existing error handling patterns

### Code Conventions
- Python: vanilla stdlib, minimal dependencies
- JavaScript: vanilla JS, no frameworks  
- Error handling: print errors, return False/None, graceful degradation
- File paths: always absolute, use os.makedirs(exist_ok=True)

### API Integration
- BGG: Use bgg_cache.py, respect 2/sec limit, handle batch responses
- Nominatim: 5-tier fallback strategy, 1/sec limit, cache results
- Always check for cached data first

### Testing
- Use test_pipeline.py for safe testing with sample data
- Test files in data/test/ (games_sample.csv, cities_sample.txt)
- Never commit API keys or large data files

### Common Tasks
- **New pipeline step**: Add to bin/, update run_pipeline.py and test_pipeline.py
- **Fix rate limiting**: Check sleep intervals in API calls
- **Debug geocoding**: Check data/cache/nominatim/ for cached results
- **Reset pipeline**: Delete data/processed/ and data/exports/, keep data/cache/

### Important Constraints
- SQLite removed - use CSV processing only
- BGG families are source of truth for city validation
- File-based caching prevents duplicate API calls
- Production vs test isolation via output path arguments

## Quick Commands
```bash
# Safe testing
python bin/test_pipeline.py

# Production pipeline
python bin/run_pipeline.py

# Individual steps
python bin/preprocess_data.py [input] [cities] [limit] [output]
python bin/get_bgg_info.py [filtered_csv]
python bin/validate_and_geotag.py [filtered_csv] [output_json]
python bin/update_pipeline_data.py [input_json] [output_js]
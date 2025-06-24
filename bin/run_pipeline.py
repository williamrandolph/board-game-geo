"""Simple 3-step pipeline for BGG city game processing

This script runs the simplified pipeline that processes BGG game data
without requiring SQLite, using only CSV files and BGG API cache.

Pipeline steps:
1. preprocess_data.py - Filter BGG CSV by city name matching
2. get_bgg_info.py - Populate BGG cache for filtered games
3. validate_and_geotag.py - Find games with BGG family tags and geocode them
4. update_pipeline_data.py - Update web app with latest data (optional)
"""

import subprocess
import sys
from datetime import datetime

def run_simple_pipeline(games_csv=None, cities_txt=None, filter_after_row=None, 
                        filtered_csv=None, output_json=None, update_web_data=True):
    """Run the complete simple pipeline
    
    Args:
        games_csv: Path to BGG games CSV (default: data/bgg/boardgames_ranks.csv)
        cities_txt: Path to cities data (default: data/geonames/cities500.txt) 
        filter_after_row: Row limit for preprocessing (default: 2500)
        filtered_csv: Output path for filtered CSV (default: data/processed/filtered_games.csv)
        output_json: Output path for final JSON (default: data/exports/bgg_family_games.json)
        update_web_data: Update src/pipeline-data.js with results (default: True)
    """
    print("🚀 Starting Simple BGG Pipeline")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Default paths
    games_csv = games_csv or "data/bgg/boardgames_ranks.csv"
    cities_txt = cities_txt or "data/geonames/cities500.txt"
    filter_after_row = filter_after_row or "2500"
    filtered_csv = filtered_csv or "data/processed/filtered_games.csv"
    output_json = output_json or "data/exports/bgg_family_games.json"
    
    try:
        # Step 1: Preprocess BGG data
        print("📝 Step 1: Preprocessing BGG data...")
        print(f"   Input: {games_csv}")
        print(f"   Cities: {cities_txt}")
        print(f"   Filter after row: {filter_after_row}")
        
        result = subprocess.run([
            "python3", "bin/preprocess_data.py",
            games_csv, cities_txt, str(filter_after_row), filtered_csv
        ], check=True, capture_output=True, text=True)
        
        if result.stdout:
            print("   " + result.stdout.replace('\n', '\n   ').strip())
        print("   ✅ Preprocessing complete")
        print()
        
        # Step 2: Populate BGG cache
        print("💾 Step 2: Populating BGG cache...")
        print(f"   Input: {filtered_csv}")
        
        result = subprocess.run([
            "python3", "bin/get_bgg_info.py",
            filtered_csv
        ], check=True, capture_output=True, text=True)
        
        if result.stdout:
            print("   " + result.stdout.replace('\n', '\n   ').strip())
        print("   ✅ Cache population complete")
        print()
        
        # Step 3: Validate and geocode
        print("🌍 Step 3: Validating and geocoding...")
        print(f"   Input: {filtered_csv}")
        print(f"   Output: {output_json}")
        
        result = subprocess.run([
            "python3", "bin/validate_and_geotag.py",
            filtered_csv, output_json
        ], check=True, capture_output=True, text=True)
        
        if result.stdout:
            print("   " + result.stdout.replace('\n', '\n   ').strip())
        print("   ✅ Validation and geocoding complete")
        print()
        
        # Step 4: Update web application data (optional)
        if update_web_data:
            print("📱 Step 4: Updating web application data...")
            print(f"   Input: {output_json}")
            print("   Output: src/pipeline-data.js")
            
            result = subprocess.run([
                "python3", "bin/update_pipeline_data.py",
                output_json, "src/pipeline-data.js"
            ], check=True, capture_output=True, text=True)
            
            if result.stdout:
                print("   " + result.stdout.replace('\n', '\n   ').strip())
            print("   ✅ Web data update complete")
            print()
        
        print("🎉 Simple pipeline completed successfully!")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print("📁 Output files:")
        print(f"   - {filtered_csv}")
        print(f"   - {output_json}")
        if update_web_data:
            print("   - src/pipeline-data.js")
        print("   - data/cache/bgg/ (BGG API cache)")
        print("   - data/cache/nominatim/ (Nominatim geocoding cache)")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Pipeline failed at step: {e.cmd[1]}")
        print(f"   Error: {e.stderr if e.stderr else 'Unknown error'}")
        if e.stdout:
            print(f"   Output: {e.stdout}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"❌ Required file not found: {e}")
        print("   Make sure data files are in place:")
        print(f"   - {games_csv}")
        print(f"   - {cities_txt}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Parse command line arguments
    games_csv = sys.argv[1] if len(sys.argv) > 1 else None
    cities_txt = sys.argv[2] if len(sys.argv) > 2 else None
    filter_after_row = sys.argv[3] if len(sys.argv) > 3 else None
    filtered_csv = sys.argv[4] if len(sys.argv) > 4 else None
    output_json = sys.argv[5] if len(sys.argv) > 5 else None
    
    # Check for --no-web-update flag
    update_web_data = "--no-web-update" not in sys.argv
    
    run_simple_pipeline(games_csv, cities_txt, filter_after_row, filtered_csv, output_json, update_web_data)
#!/usr/bin/env python3
"""
Run the complete data processing pipeline from raw data to web exports.
"""

import os
import sys
import subprocess
import time

def run_command(command, description):
    """Run a shell command and report results."""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"COMMAND: {command}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        
        duration = time.time() - start_time
        print(f"✅ SUCCESS ({duration:.1f}s)")
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        print(f"❌ FAILED ({duration:.1f}s)")
        print(f"Return code: {e.returncode}")
        
        if e.stdout:
            print("STDOUT:")
            print(e.stdout)
        
        if e.stderr:
            print("STDERR:")
            print(e.stderr)
        
        return False

def check_data_files():
    """Check that required data files exist."""
    required_files = [
        "data/bgg/boardgames_ranks.csv",
        "data/geonames/cities500.txt"
    ]
    
    missing_files = []
    for filepath in required_files:
        if not os.path.exists(filepath):
            missing_files.append(filepath)
    
    if missing_files:
        print("❌ Missing required data files:")
        for filepath in missing_files:
            print(f"   - {filepath}")
        print("\nPlease download the required data files first.")
        return False
    
    print("✅ All required data files found")
    return True

def run_full_pipeline(use_fuzzy_matching="simple"):
    """Run the complete pipeline."""
    
    print(f"🚀 Starting Board Game Geography Data Pipeline ({use_fuzzy_matching} matching)")
    print(f"Working directory: {os.getcwd()}")
    
    # Check prerequisites
    if not check_data_files():
        return False
    
    # Ensure Python scripts are executable
    os.chmod("bin/init_database.py", 0o755)
    os.chmod("bin/load_bgg_data.py", 0o755)
    os.chmod("bin/load_cities_data.py", 0o755)
    os.chmod("bin/fuzzy_match.py", 0o755)
    os.chmod("bin/simple_match.py", 0o755)
    os.chmod("bin/hybrid_match.py", 0o755)
    os.chmod("bin/export_web_data.py", 0o755)
    
    # Choose matching script based on flag
    if use_fuzzy_matching == "fuzzy":
        match_script = "python3 bin/fuzzy_match.py"
        match_description = "Run fuzzy matching (slower, most comprehensive)"
    elif use_fuzzy_matching == "hybrid":
        match_script = "python3 bin/hybrid_match.py"
        match_description = "Run hybrid matching (fast, good coverage)"
    else:
        match_script = "python3 bin/simple_match.py"
        match_description = "Run simple exact matching (fastest)"
    
    # Pipeline steps
    steps = [
        ("python3 bin/init_database.py", "Initialize SQLite database"),
        ("python3 bin/load_bgg_data.py", "Load BoardGameGeek data"),
        ("python3 bin/load_cities_data.py", "Load cities data"),
        (match_script, match_description),
        ("python3 bin/export_web_data.py all", "Export data for web app")
    ]
    
    # Run each step
    for command, description in steps:
        success = run_command(command, description)
        if not success:
            print(f"\n❌ Pipeline failed at step: {description}")
            return False
    
    print(f"\n{'='*60}")
    print("🎉 PIPELINE COMPLETE!")
    print(f"{'='*60}")
    print("Generated files:")
    print("  - data/processed/boardgames.db (SQLite database)")
    print("  - data/exports/games.json (High-confidence matches for web app)")
    print("  - data/exports/games_all.json (All matches)")
    print("  - data/exports/matches_review.csv (Matches needing review)")
    print("  - data/exports/summary_report.json (Statistics and summary)")
    print("\nNext steps:")
    print("  1. Review matches_review.csv for accuracy")
    print("  2. Update your web app to use games.json")
    print("  3. Test the web application")
    
    return True

def run_quick_test(use_fuzzy_matching="simple"):
    """Run a quick test with limited data."""
    print(f"🧪 Running quick test pipeline with limited data ({use_fuzzy_matching} matching)...")
    
    if not check_data_files():
        return False
    
    # Choose matching script
    if use_fuzzy_matching == "fuzzy":
        match_command = "python3 bin/fuzzy_match.py data/processed/boardgames.db 60.0"
        match_description = "Run fuzzy matching (higher threshold)"
    elif use_fuzzy_matching == "hybrid":
        match_command = "python3 bin/hybrid_match.py data/processed/boardgames.db"
        match_description = "Run hybrid matching"
    else:
        match_command = "python3 bin/simple_match.py data/processed/boardgames.db"
        match_description = "Run simple exact matching"
    
    # Pipeline steps with limited data
    steps = [
        ("python3 bin/init_database.py", "Initialize database"),
        ("python3 bin/load_bgg_data.py", "Load BGG data (limited)"),
        ("python3 bin/load_cities_data.py data/geonames/cities500.txt data/processed/boardgames.db 50000", "Load major cities only"),
        (match_command, match_description),
        ("python3 bin/export_web_data.py json data/exports/games_test.json", "Export test data")
    ]
    
    for command, description in steps:
        success = run_command(command, description)
        if not success:
            print(f"\n❌ Test failed at step: {description}")
            return False
    
    print("\n🎉 Quick test complete! Check data/exports/games_test.json")
    return True

if __name__ == "__main__":
    # Parse command line arguments
    matching_mode = "simple"  # default
    command = "full"
    
    for arg in sys.argv[1:]:
        if arg == "test":
            command = "test"
        elif arg == "--simple":
            matching_mode = "simple"
        elif arg == "--hybrid":
            matching_mode = "hybrid"
        elif arg == "--fuzzy":
            matching_mode = "fuzzy"
        elif arg in ["--help", "-h"]:
            print("Usage: python run_pipeline.py [command] [options]")
            print()
            print("Commands:")
            print("  (none)    Run full pipeline")
            print("  test      Run quick test with limited data")
            print()
            print("Matching Options:")
            print("  --simple  Use simple exact matching (default, fastest)")
            print("  --hybrid  Use hybrid matching (fast, better coverage)")
            print("  --fuzzy   Use fuzzy matching (slower, most comprehensive)")
            print("  --help    Show this help message")
            print()
            print("Examples:")
            print("  python run_pipeline.py --hybrid")
            print("  python run_pipeline.py test --fuzzy")
            sys.exit(0)
    
    # Run the appropriate pipeline
    if command == "test":
        success = run_quick_test(matching_mode)
    else:
        success = run_full_pipeline(matching_mode)
    
    sys.exit(0 if success else 1)
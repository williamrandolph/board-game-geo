#!/usr/bin/env python3
"""
Test the pipeline with a small sample dataset for development.
"""

import os
import sys
import subprocess
import time

def run_command(command, description):
    """Run a shell command and report results."""
    print(f"\n{'='*50}")
    print(f"STEP: {description}")
    print(f"COMMAND: {command}")
    print(f"{'='*50}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        
        duration = time.time() - start_time
        print(f"✅ SUCCESS ({duration:.1f}s)")
        
        if result.stdout:
            print("OUTPUT:")
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

def test_pipeline():
    """Test with sample data."""
    
    print("🧪 Testing Board Game Geography Pipeline with Sample Data")
    print(f"Working directory: {os.getcwd()}")
    
    # Check that test files exist
    test_files = [
        "data/test/games_sample.csv",
        "data/test/cities_sample.txt"
    ]
    
    for filepath in test_files:
        if not os.path.exists(filepath):
            print(f"❌ Missing test file: {filepath}")
            return False
    
    print("✅ Test files found")
    
    # Use test database
    test_db = "data/test/test_games.db"
    
    # Clean up previous test
    if os.path.exists(test_db):
        os.remove(test_db)
        print("🧹 Cleaned up previous test database")
    
    # Pipeline steps with test data
    steps = [
        (f"python3 bin/init_database.py {test_db}", "Initialize test database"),
        (f"python3 bin/load_bgg_data.py data/test/games_sample.csv {test_db}", "Load sample games"),
        (f"python3 bin/load_cities_data.py data/test/cities_sample.txt {test_db} 0", "Load sample cities"),
        (f"python3 bin/simple_match.py {test_db}", "Run simple exact matching"),
        (f"python3 bin/export_web_data.py json data/test/test_games.json very_high,high {test_db}", "Export test data")
    ]
    
    # Run each step
    for command, description in steps:
        success = run_command(command, description)
        if not success:
            print(f"\n❌ Test failed at step: {description}")
            return False
    
    # Show results
    print(f"\n{'='*50}")
    print("🎉 TEST COMPLETE!")
    print(f"{'='*50}")
    
    # Display the exported JSON
    json_file = "data/test/test_games.json"
    if os.path.exists(json_file):
        print(f"\nGenerated test file: {json_file}")
        
        # Show a summary of the JSON content
        import json
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            print(f"Total games in export: {data['metadata']['total_games']}")
            print("\nGames found:")
            for game in data['games']:
                match_info = game['match']
                print(f"  - {game['name']} → {game['location']['city']}, {game['location']['country']}")
                print(f"    Score: {match_info['score']}, Confidence: {match_info['confidence']}")
                
        except Exception as e:
            print(f"Error reading JSON: {e}")
    
    print("\nNext steps:")
    print("  1. Review the matches above")
    print("  2. Check if Birmingham matched correctly")
    print("  3. Verify Amalfi matched correctly") 
    print("  4. Confirm Gloomhaven didn't match anything")
    
    return True

if __name__ == "__main__":
    success = test_pipeline()
    sys.exit(0 if success else 1)
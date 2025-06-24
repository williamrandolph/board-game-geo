"""Test the simple 3-step BGG pipeline with sample data

This script tests the simplified pipeline using smaller test datasets
to verify functionality without processing the full BGG dataset.
"""

import subprocess
import sys
import os
import json
from datetime import datetime

def test_simple_pipeline():
    """Test the simple pipeline with sample data"""
    print("🧪 Testing Simple BGG Pipeline")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test data paths
    test_games_csv = "data/test/games_sample.csv"
    test_cities_txt = "data/test/cities_sample.txt" 
    test_filter_limit = "100"  # Process only first 100 games for testing
    
    # Test output paths (separate from production)
    test_filtered_csv = "data/test/filtered_games_test.csv"
    test_output_json = "data/test/bgg_family_games_test.json"
    
    # Verify test data exists
    print("📋 Verifying test data...")
    test_files = [test_games_csv, test_cities_txt]
    for file_path in test_files:
        if not os.path.exists(file_path):
            print(f"❌ Test file missing: {file_path}")
            print("   Please ensure test data is available")
            return False
        else:
            print(f"   ✅ Found: {file_path}")
    print()
    
    try:
        # Test Step 1: Preprocess test data
        print("📝 Testing Step 1: Preprocessing...")
        result = subprocess.run([
            "python3", "bin/preprocess_data.py",
            test_games_csv, test_cities_txt, test_filter_limit, test_filtered_csv
        ], check=True, capture_output=True, text=True)
        
        print("   " + result.stdout.replace('\n', '\n   ').strip())
        
        # Check if filtered output was created
        if os.path.exists(test_filtered_csv):
            with open(test_filtered_csv, 'r') as f:
                lines = sum(1 for line in f) - 1  # Subtract header
            print(f"   ✅ Created {test_filtered_csv} with {lines} games")
        else:
            print(f"   ❌ No filtered output created at {test_filtered_csv}")
            return False
        print()
        
        # Test Step 2: Cache population (if filtered games exist)
        if lines > 0:
            print("💾 Testing Step 2: BGG cache population...")
            result = subprocess.run([
                "python3", "bin/get_bgg_info.py",
                test_filtered_csv
            ], check=True, capture_output=True, text=True)
            
            print("   " + result.stdout.replace('\n', '\n   ').strip())
            print("   ✅ Cache population test complete")
            print()
            
            # Test Step 3: Validation and geocoding
            print("🌍 Testing Step 3: Validation and geocoding...")
            result = subprocess.run([
                "python3", "bin/validate_and_geotag.py",
                test_filtered_csv, test_output_json
            ], check=True, capture_output=True, text=True)
            
            print("   " + result.stdout.replace('\n', '\n   ').strip())
            
            # Check output file
            if os.path.exists(test_output_json):
                with open(test_output_json, 'r') as f:
                    data = json.load(f)
                    game_count = data.get('metadata', {}).get('total_games', 0)
                print(f"   ✅ Created {test_output_json} with {game_count} geocoded games")
            else:
                print("   ⚠️  No geocoded output created (may be normal if no BGG family matches)")
            print()
        else:
            print("💾 Skipping Steps 2-3: No games in filtered output")
            print()
        
        print("🎉 Pipeline test completed successfully!")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Test summary
        print("📊 Test Summary:")
        print(f"   - Filtered games: {lines}")
        if os.path.exists(test_output_json):
            with open(test_output_json, 'r') as f:
                data = json.load(f)
                geocoded_count = data.get('metadata', {}).get('total_games', 0)
            print(f"   - Geocoded games: {geocoded_count}")
        print("   - Cache files created in data/cache/")
        print(f"   - Test output: {test_filtered_csv}, {test_output_json}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Test failed at: {e.cmd[1]}")
        print(f"   Error: {e.stderr if e.stderr else 'Unknown error'}")
        if e.stdout:
            print(f"   Output: {e.stdout}")
        return False
    except Exception as e:
        print(f"❌ Unexpected test error: {e}")
        return False

def verify_pipeline_scripts():
    """Verify all required pipeline scripts exist"""
    print("🔍 Verifying pipeline scripts...")
    
    required_scripts = [
        "bin/preprocess_data.py",
        "bin/get_bgg_info.py", 
        "bin/validate_and_geotag.py",
        "bin/bgg_cache.py",
        "bin/util.py"
    ]
    
    all_present = True
    for script in required_scripts:
        if os.path.exists(script):
            print(f"   ✅ {script}")
        else:
            print(f"   ❌ {script} - MISSING")
            all_present = False
    
    print()
    return all_present

def create_test_data():
    """Create minimal test data if it doesn't exist"""
    print("📋 Checking test data...")
    
    os.makedirs("data/test", exist_ok=True)
    
    # Create minimal test games CSV if missing
    test_games_csv = "data/test/games_sample.csv"
    if not os.path.exists(test_games_csv):
        print(f"   Creating minimal {test_games_csv}...")
        with open(test_games_csv, 'w') as f:
            f.write("id,name,yearpublished,rank,bayesaverage,average,usersrated,is_expansion\n")
            f.write("224517,Brass: Birmingham,2018,1,8.40157,8.57623,52461,0\n")
            f.write("174430,Gloomhaven,2017,4,8.32263,8.56104,65016,0\n")
            f.write("1261,Medina,2001,1500,6.12345,6.45678,1234,0\n")
        print(f"   ✅ Created {test_games_csv}")
    
    # Create minimal test cities file if missing  
    test_cities_txt = "data/test/cities_sample.txt"
    if not os.path.exists(test_cities_txt):
        print(f"   Creating minimal {test_cities_txt}...")
        with open(test_cities_txt, 'w') as f:
            # Format: geonameid, name, asciiname, alternatenames, latitude, longitude, feature class, feature code, country code, cc2, admin1 code, admin2 code, admin3 code, admin4 code, population, elevation, dem, timezone, modification date
            f.write("2655984\tBirmingham\tBirmingham\t\t52.48142\t-1.89983\tP\tPPLA2\tGB\t\tENG\tBIR\t\t\t984333\t\t124\tEurope/London\t2019-09-05\n")
            f.write("5746545\tGloomhaven\tGloomhaven\t\t45.0\t-93.0\tP\tPPL\tUS\t\tMN\t\t\t\t1000\t\t300\tAmerica/Chicago\t2019-09-05\n")
            f.write("108410\tMedina\tMedina\t\t24.46861\t39.61417\tP\tPPLA\tSA\t\t\t\t\t\t1500000\t\t631\tAsia/Riyadh\t2019-09-05\n")
        print(f"   ✅ Created {test_cities_txt}")
    
    print()

if __name__ == "__main__":
    print("🧪 BGG Pipeline Test Suite")
    print("=" * 50)
    print()
    
    # Verify pipeline scripts exist
    if not verify_pipeline_scripts():
        print("❌ Missing required pipeline scripts. Cannot run tests.")
        sys.exit(1)
    
    # Create test data if needed
    create_test_data()
    
    # Run the pipeline test
    success = test_simple_pipeline()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)
"""Preprocess the BGG ranked data CSV"""

from util import normalize_string
import csv
import os
import sys

def preprocess_games(games_csv_path: str, city_txt_path: str, filter_after_row: int):
    city_names = get_city_names(city_txt_path)

    print(f"Loading BGG data from {games_csv_path}...")
    
    if not os.path.exists(games_csv_path):
        print(f"Error: CSV file not found at {games_csv_path}")
        return False
    
    # Read and process CSV
    games_loaded = 0
    games_skipped = 0
    
    with open("data/processed/filtered_games.csv", 'w') as outfile:
        with open(games_csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            writer = csv.DictWriter(outfile, reader.fieldnames)
            writer.writeheader()
            for i, row in enumerate(rows):
                if i < filter_after_row:
                    writer.writerow(row)
                    games_loaded += 1
                    continue
                try:
                    # Extract data from CSV
                    name = row['name'].strip()
                    num_votes = int(row['usersrated']) if row['usersrated'] else None
                    is_expansion = bool(int(row['is_expansion'])) if row['is_expansion'] else False
                    
                    # Skip expansions for now - focus on base games
                    if is_expansion:
                        games_skipped += 1
                        continue
                    
                    # Skip games with very few ratings (likely incomplete data)
                    if num_votes and num_votes < 100:
                        games_skipped += 1
                        continue
                    
                    # Normalize name for matching
                    normalized_name = normalize_string(name)

                    if normalized_name in city_names:
                        writer.writerow(row)
                        games_loaded += 1
                    else:
                        games_skipped += 1
                        
                except (ValueError, KeyError) as e:
                    print(f"  Skipping row due to error: {e}")
                    games_skipped += 1
                    continue
    

    print(f"\nProcessing complete:")
    print(f"  Games added: {games_loaded:,}")
    print(f"  Games skipped: {games_skipped:,}")

def get_city_names(city_txt_path: str) -> set[str]:
    city_names = set()

    print(f"Loading cities data from {city_txt_path}...")
    
    if not os.path.exists(city_txt_path):
        print(f"Error: Cities file not found at {city_txt_path}")
        return False

    # Read and process cities file
    cities_loaded = 0
    cities_skipped = 0
    
    with open(city_txt_path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            try:
                # Split tab-separated values
                fields = line.strip().split('\t')
                
                if len(fields) < 19:
                    cities_skipped += 1
                    continue
                
                # Parse fields according to GeoNames format
                name = fields[1].strip()
                ascii_name = fields[2].strip()
                alternate_names = fields[3].strip()
                feature_class = fields[6].strip()
                
                # Focus on populated places (cities, towns, villages)
                if feature_class != 'P':
                    cities_skipped += 1
                    continue
                
                # Normalize name for matching
                normalized_name = normalize_string(name)
                
                # Use ASCII name if available and different
                if ascii_name and ascii_name != name:
                    ascii_normalized = normalize_string(ascii_name)
                else:
                    ascii_normalized = normalized_name

                cities_loaded += 1
                city_names.add(ascii_normalized)

                for alt_name in alternate_names.split(','):
                    if alt_name.isascii():
                        city_names.add(normalize_string(alt_name))

            except (ValueError, IndexError) as e:
                print(f"  Skipping line {line_num} due to error: {e}")
                cities_skipped += 1
                continue
                
    
    # Report results
    print(f"\nLoading complete:")
    print(f"  Cities loaded: {cities_loaded:,}")
    print(f"  Cities skipped: {cities_skipped:,}")
    print(f"  City names (including alts): {len(city_names):,}")
    
    return city_names

if __name__ == "__main__":
    # Default paths
    games_csv_path = "data/bgg/boardgames_ranks.csv"
    city_txt_path = "data/geonames/cities500.txt"
    filter_after_row = 2500
    
    # Allow custom paths and population filter as command line arguments
    if len(sys.argv) > 1:
        games_csv_path = sys.argv[1]
    if len(sys.argv) > 2:
        city_txt_path = sys.argv[2]
    if len(sys.argv) > 3:
        filter_after_row = int(sys.argv[3])
    
    success = preprocess_games(games_csv_path, city_txt_path, filter_after_row)
    if not success:
        sys.exit(1)
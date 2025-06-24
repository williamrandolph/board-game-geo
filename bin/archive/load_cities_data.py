#!/usr/bin/env python3
"""
Load GeoNames cities data from cities500.txt into SQLite database.
"""

import sqlite3
import sys
import os
from util import normalize_string

def get_country_name(country_code):
    """Convert country code to country name."""
    # Common country codes - can be expanded
    country_map = {
        'US': 'United States', 'CA': 'Canada', 'GB': 'United Kingdom',
        'FR': 'France', 'DE': 'Germany', 'IT': 'Italy', 'ES': 'Spain',
        'AU': 'Australia', 'JP': 'Japan', 'CN': 'China', 'IN': 'India',
        'BR': 'Brazil', 'RU': 'Russia', 'MX': 'Mexico', 'AR': 'Argentina',
        'ZA': 'South Africa', 'EG': 'Egypt', 'NG': 'Nigeria', 'KE': 'Kenya',
        'GR': 'Greece', 'TR': 'Turkey', 'SE': 'Sweden', 'NO': 'Norway',
        'DK': 'Denmark', 'FI': 'Finland', 'NL': 'Netherlands', 'BE': 'Belgium',
        'CH': 'Switzerland', 'AT': 'Austria', 'PT': 'Portugal', 'IE': 'Ireland',
        'PL': 'Poland', 'CZ': 'Czech Republic', 'HU': 'Hungary', 'RO': 'Romania',
        'BG': 'Bulgaria', 'HR': 'Croatia', 'SI': 'Slovenia', 'SK': 'Slovakia',
        'LT': 'Lithuania', 'LV': 'Latvia', 'EE': 'Estonia', 'IS': 'Iceland',
        'TH': 'Thailand', 'VN': 'Vietnam', 'MY': 'Malaysia', 'SG': 'Singapore',
        'PH': 'Philippines', 'ID': 'Indonesia', 'KR': 'South Korea', 'TW': 'Taiwan',
        'NZ': 'New Zealand', 'CL': 'Chile', 'PE': 'Peru', 'CO': 'Colombia',
        'VE': 'Venezuela', 'UY': 'Uruguay', 'PY': 'Paraguay', 'BO': 'Bolivia',
        'EC': 'Ecuador', 'CR': 'Costa Rica', 'PA': 'Panama', 'GT': 'Guatemala',
        'HN': 'Honduras', 'NI': 'Nicaragua', 'SV': 'El Salvador', 'BZ': 'Belize',
        'JM': 'Jamaica', 'CU': 'Cuba', 'DO': 'Dominican Republic', 'HT': 'Haiti',
        'TT': 'Trinidad and Tobago', 'BB': 'Barbados', 'GD': 'Grenada',
        'LC': 'Saint Lucia', 'VC': 'Saint Vincent and the Grenadines',
        'KN': 'Saint Kitts and Nevis', 'AG': 'Antigua and Barbuda', 'DM': 'Dominica'
    }
    return country_map.get(country_code, country_code)

def load_cities_data(txt_path, db_path, min_population=500):
    """Load cities data from GeoNames text file into database."""
    
    print(f"Loading cities data from {txt_path}...")
    print(f"Minimum population filter: {min_population:,}")
    
    if not os.path.exists(txt_path):
        print(f"Error: Cities file not found at {txt_path}")
        return False
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        print("Run init_database.py first to create the database schema.")
        return False
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing cities data
    cursor.execute("DELETE FROM cities")
    print("Cleared existing cities data")
    
    # Read and process cities file
    cities_loaded = 0
    cities_skipped = 0
    
    with open(txt_path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            try:
                # Split tab-separated values
                fields = line.strip().split('\t')
                
                if len(fields) < 19:
                    cities_skipped += 1
                    continue
                
                # Parse fields according to GeoNames format
                geonameid = int(fields[0])
                name = fields[1].strip()
                ascii_name = fields[2].strip()
                alternatenames = fields[3].strip()
                latitude = float(fields[4])
                longitude = float(fields[5])
                feature_class = fields[6].strip()
                feature_code = fields[7].strip()
                country_code = fields[8].strip()
                # Skip cc2, admin codes for now
                population = int(fields[14]) if fields[14] else 0
                # Skip elevation, dem
                timezone = fields[17].strip() if len(fields) > 17 else ""
                
                # Filter by population
                if population < min_population:
                    cities_skipped += 1
                    continue
                
                # Focus on populated places (cities, towns, villages)
                if feature_class != 'P':
                    cities_skipped += 1
                    continue
                
                # Convert country code to name
                country_name = get_country_name(country_code)
                
                # Normalize name for matching
                normalized_name = normalize_string(name)
                
                # Use ASCII name if available and different
                if ascii_name and ascii_name != name:
                    ascii_normalized = normalize_string(ascii_name)
                else:
                    ascii_normalized = normalized_name
                
                # Insert into database
                cursor.execute('''
                    INSERT INTO cities (name, normalized_name, ascii_name, country_code, 
                                      country_name, latitude, longitude, population, timezone)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, normalized_name, ascii_normalized, country_code, country_name,
                      latitude, longitude, population, timezone))
                
                cities_loaded += 1
                
                # Progress indicator
                if cities_loaded % 5000 == 0:
                    print(f"  Loaded {cities_loaded:,} cities...")
                    
            except (ValueError, IndexError) as e:
                print(f"  Skipping line {line_num} due to error: {e}")
                cities_skipped += 1
                continue
    
    # Commit changes
    conn.commit()
    
    # Report results
    print(f"\nLoading complete:")
    print(f"  Cities loaded: {cities_loaded:,}")
    print(f"  Cities skipped: {cities_skipped:,}")
    
    # Show some statistics
    cursor.execute('''
        SELECT country_name, COUNT(*) as city_count
        FROM cities 
        GROUP BY country_name 
        ORDER BY city_count DESC 
        LIMIT 10
    ''')
    
    print(f"\nTop 10 countries by city count:")
    for country, count in cursor.fetchall():
        print(f"  {country}: {count:,} cities")
    
    # Show largest cities
    cursor.execute('''
        SELECT name, country_name, population
        FROM cities 
        ORDER BY population DESC 
        LIMIT 10
    ''')
    
    print(f"\nLargest cities by population:")
    for name, country, pop in cursor.fetchall():
        print(f"  {name}, {country}: {pop:,}")
    
    # Show cities with short names (potential game matches)
    cursor.execute('''
        SELECT name, normalized_name, country_name, population
        FROM cities 
        WHERE LENGTH(normalized_name) <= 12
        AND population > 50000
        ORDER BY population DESC
        LIMIT 15
    ''')
    
    print(f"\nCities with short names (potential game matches):")
    for name, normalized, country, pop in cursor.fetchall():
        print(f"  {name} → '{normalized}' ({country}) - {pop:,}")
    
    conn.close()
    return True

if __name__ == "__main__":
    # Default paths
    txt_path = "data/geonames/cities500.txt"
    db_path = "data/processed/boardgames.db"
    min_population = 500
    
    # Allow custom paths and population filter as command line arguments
    if len(sys.argv) > 1:
        txt_path = sys.argv[1]
    if len(sys.argv) > 2:
        db_path = sys.argv[2]
    if len(sys.argv) > 3:
        min_population = int(sys.argv[3])
    
    success = load_cities_data(txt_path, db_path, min_population)
    if not success:
        sys.exit(1)
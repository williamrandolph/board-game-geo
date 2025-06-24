#!/usr/bin/env python3
"""
Hybrid matching pipeline optimized for both speed and coverage.
- Exact matches: All cities 50K+ population (fast operation)
- Substring matches: Only major cities 500K+ population (expensive operation)
"""

import sqlite3
import sys
import os

def find_hybrid_matches(db_path, min_population_exact=1000, min_population_substring=500000):
    """Find games using hybrid matching strategy for optimal speed/coverage."""
    
    print(f"Finding hybrid matches in {db_path}...")
    print(f"Exact matches: cities with population >= {min_population_exact:,}")
    print(f"Substring matches: cities with population >= {min_population_substring:,}")
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return False
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing matches
    cursor.execute("DELETE FROM matches")
    print("Cleared existing matches")
    
    # Count cities in each tier
    cursor.execute("SELECT COUNT(*) FROM cities WHERE population >= ?", (min_population_exact,))
    exact_cities = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cities WHERE population >= ?", (min_population_substring,))
    substring_cities = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games")
    total_games = cursor.fetchone()[0]
    
    print(f"Cities for exact matching: {exact_cities:,}")
    print(f"Cities for substring matching: {substring_cities:,}")
    print(f"Games: {total_games:,}")
    print(f"Strategy: {total_games * exact_cities:,} exact comparisons + {total_games * substring_cities:,} substring comparisons")
    
    # STEP 1: Find exact matches (50K+ cities - fast operation)
    print("\n🔍 Step 1: Finding exact matches...")
    cursor.execute('''
        INSERT INTO matches (game_id, city_id, match_type, score, confidence, manual_review)
        SELECT 
            g.id as game_id,
            c.id as city_id,
            'exact' as match_type,
            100.0 as score,
            'very_high' as confidence,
            0 as manual_review
        FROM games g
        JOIN cities c ON g.normalized_name = c.normalized_name
        WHERE g.normalized_name != ''
        AND c.normalized_name != ''
        AND c.population >= ?
    ''', (min_population_exact,))
    
    exact_matches = cursor.rowcount
    print(f"Found {exact_matches} exact matches")
    
    # STEP 2: Find substring matches (500K+ cities only - expensive operation)
    print("\n🔍 Step 2: Finding substring matches (major cities only)...")
    cursor.execute('''
        INSERT INTO matches (game_id, city_id, match_type, score, confidence, manual_review)
        SELECT 
            g.id as game_id,
            c.id as city_id,
            'game_contains_city' as match_type,
            80.0 as score,
            'high' as confidence,
            0 as manual_review
        FROM games g
        JOIN cities c ON g.normalized_name LIKE '%' || c.normalized_name || '%'
        WHERE g.normalized_name != c.normalized_name  -- Don't duplicate exact matches
        AND g.normalized_name != ''
        AND c.normalized_name != ''
        AND LENGTH(c.normalized_name) >= 5  -- Only longer city names to avoid false matches
        AND c.population >= ?  -- Only major cities for substring matching
        AND NOT EXISTS (
            SELECT 1 FROM matches m 
            WHERE m.game_id = g.id AND m.city_id = c.id
        )
    ''', (min_population_substring,))
    
    substring_matches = cursor.rowcount
    print(f"Found {substring_matches} substring matches")
    
    # Commit changes
    conn.commit()
    
    total_matches = exact_matches + substring_matches
    
    # Report results
    print(f"\n{'='*50}")
    print(f"HYBRID MATCHING COMPLETE")
    print(f"{'='*50}")
    print(f"  Exact matches: {exact_matches}")
    print(f"  Substring matches: {substring_matches}")
    print(f"  Total matches: {total_matches}")
    
    if total_matches == 0:
        print("\nNo matches found. Debugging info:")
        
        # Show sample cities for each tier
        cursor.execute('''
            SELECT name, normalized_name, population 
            FROM cities 
            WHERE population >= ? 
            AND LENGTH(normalized_name) <= 12
            ORDER BY population DESC 
            LIMIT 5
        ''', (min_population_exact,))
        
        print(f"\nSample cities (pop >= {min_population_exact:,}):")
        for name, normalized, pop in cursor.fetchall():
            print(f"  '{name}' → '{normalized}' ({pop:,})")
            
        cursor.execute('''
            SELECT name, normalized_name, population 
            FROM cities 
            WHERE population >= ? 
            AND LENGTH(normalized_name) <= 12
            ORDER BY population DESC 
            LIMIT 5
        ''', (min_population_substring,))
        
        print(f"\nSample major cities (pop >= {min_population_substring:,}):")
        for name, normalized, pop in cursor.fetchall():
            print(f"  '{name}' → '{normalized}' ({pop:,})")
    else:
        # Show matches by type and confidence
        cursor.execute('''
            SELECT match_type, confidence, COUNT(*) as count
            FROM matches
            GROUP BY match_type, confidence
            ORDER BY match_type, confidence
        ''')
        
        print(f"\nMatches by type and confidence:")
        for match_type, confidence, count in cursor.fetchall():
            print(f"  {match_type} ({confidence}): {count}")
        
        # Show top exact matches
        cursor.execute('''
            SELECT g.name, c.name, c.country_name, c.population
            FROM matches m
            JOIN games g ON m.game_id = g.id
            JOIN cities c ON m.city_id = c.id
            WHERE m.match_type = 'exact'
            ORDER BY c.population DESC
            LIMIT 10
        ''')
        
        print(f"\nTop exact matches (by city size):")
        for game, city, country, pop in cursor.fetchall():
            print(f"  {game} → {city}, {country} ({pop:,})")
        
        # Show interesting substring matches
        cursor.execute('''
            SELECT g.name, c.name, c.country_name, c.population
            FROM matches m
            JOIN games g ON m.game_id = g.id
            JOIN cities c ON m.city_id = c.id
            WHERE m.match_type = 'game_contains_city'
            ORDER BY c.population DESC
            LIMIT 10
        ''')
        
        if cursor.fetchall():
            print(f"\nTop substring matches (by city size):")
            cursor.execute('''
                SELECT g.name, c.name, c.country_name, c.population
                FROM matches m
                JOIN games g ON m.game_id = g.id
                JOIN cities c ON m.city_id = c.id
                WHERE m.match_type = 'game_contains_city'
                ORDER BY c.population DESC
                LIMIT 10
            ''')
            for game, city, country, pop in cursor.fetchall():
                print(f"  {game} → {city}, {country} ({pop:,})")
    
    conn.close()
    return True

if __name__ == "__main__":
    # Default settings
    db_path = "data/processed/boardgames.db"
    min_pop_exact = 1000      # 1K+ for exact matches (to catch small cities like Amalfi)
    min_pop_substring = 500000  # 500K+ for substring matches
    
    # Allow custom settings
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    if len(sys.argv) > 2:
        min_pop_exact = int(sys.argv[2])
    if len(sys.argv) > 3:
        min_pop_substring = int(sys.argv[3])
    
    success = find_hybrid_matches(db_path, min_pop_exact, min_pop_substring)
    if not success:
        sys.exit(1)
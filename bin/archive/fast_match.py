#!/usr/bin/env python3
"""
Fast exact matching pipeline optimized for performance.
Only matches against major cities to reduce processing time.
"""

import sqlite3
import sys
import os

def find_fast_matches(db_path, min_population=50000):
    """Find games that match city names, using only major cities for speed."""
    
    print(f"Finding fast matches in {db_path}...")
    print(f"Using cities with population >= {min_population:,}")
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return False
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing matches
    cursor.execute("DELETE FROM matches")
    print("Cleared existing matches")
    
    # Count total cities and filtered cities
    cursor.execute("SELECT COUNT(*) FROM cities")
    total_cities = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cities WHERE population >= ?", (min_population,))
    filtered_cities = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games")
    total_games = cursor.fetchone()[0]
    
    print(f"Cities: {filtered_cities:,} (filtered) of {total_cities:,} total")
    print(f"Games: {total_games:,}")
    print(f"Comparisons: {total_games * filtered_cities:,} (much faster!)")
    
    # Find exact matches using SQL join (only major cities)
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
    ''', (min_population,))
    
    exact_matches = cursor.rowcount
    
    # Find substring matches (game contains city name) - only for major cities and longer city names
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
        AND c.population >= ?  -- Only major cities
        AND NOT EXISTS (
            SELECT 1 FROM matches m 
            WHERE m.game_id = g.id AND m.city_id = c.id
        )
    ''', (min_population,))
    
    substring_matches = cursor.rowcount
    
    # Commit changes
    conn.commit()
    
    total_matches = exact_matches + substring_matches
    
    # Report results
    print(f"\nMatching complete:")
    print(f"  Exact matches: {exact_matches}")
    print(f"  Substring matches: {substring_matches}")
    print(f"  Total matches: {total_matches}")
    
    if total_matches == 0:
        print("No matches found. Try:")
        print("  - Lower minimum population threshold")
        print("  - Check normalization differences")
        
        # Show sample data for debugging
        cursor.execute('''
            SELECT name, normalized_name, population 
            FROM cities 
            WHERE population >= ? 
            AND LENGTH(normalized_name) <= 12
            ORDER BY population DESC 
            LIMIT 10
        ''', (min_population,))
        
        print(f"\nSample major cities (pop >= {min_population:,}):")
        for name, normalized, pop in cursor.fetchall():
            print(f"  '{name}' → '{normalized}' ({pop:,})")
        
        cursor.execute('''
            SELECT name, normalized_name 
            FROM games 
            WHERE LENGTH(normalized_name) <= 12
            ORDER BY rating DESC 
            LIMIT 10
        ''')
        
        print(f"\nSample game names:")
        for name, normalized in cursor.fetchall():
            print(f"  '{name}' → '{normalized}'")
    else:
        # Show matches by confidence
        cursor.execute('''
            SELECT confidence, COUNT(*) as count
            FROM matches
            GROUP BY confidence
            ORDER BY 
                CASE confidence
                    WHEN 'very_high' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                    WHEN 'very_low' THEN 5
                END
        ''')
        
        print(f"\nMatches by confidence:")
        for confidence, count in cursor.fetchall():
            print(f"  {confidence}: {count}")
        
        # Show top matches
        cursor.execute('''
            SELECT g.name, c.name, c.country_name, c.population, m.match_type, m.score
            FROM matches m
            JOIN games g ON m.game_id = g.id
            JOIN cities c ON m.city_id = c.id
            ORDER BY m.score DESC, c.population DESC
            LIMIT 15
        ''')
        
        print(f"\nTop matches:")
        for game, city, country, pop, match_type, score in cursor.fetchall():
            print(f"  {score:5.1f} | {game} → {city}, {country} ({pop:,}) | {match_type}")
    
    conn.close()
    return True

if __name__ == "__main__":
    # Default settings
    db_path = "data/processed/boardgames.db"
    min_population = 50000  # Only cities with 50K+ population
    
    # Allow custom settings
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    if len(sys.argv) > 2:
        min_population = int(sys.argv[2])
    
    success = find_fast_matches(db_path, min_population)
    if not success:
        sys.exit(1)
#!/usr/bin/env python3
"""
Simple exact matching pipeline for board games and city names.
Much faster than fuzzy matching for development and testing.
"""

import sqlite3
import sys
import os

def find_exact_matches(db_path):
    """Find games that exactly match city names (after normalization)."""
    
    print(f"Finding exact matches in {db_path}...")
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return False
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing matches
    cursor.execute("DELETE FROM matches")
    print("Cleared existing matches")
    
    # Find exact matches using SQL join
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
    ''')
    
    exact_matches = cursor.rowcount
    
    # Also find substring matches (game contains city name)
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
        AND LENGTH(c.normalized_name) >= 4  -- Avoid matching very short city names
        AND NOT EXISTS (
            SELECT 1 FROM matches m 
            WHERE m.game_id = g.id AND m.city_id = c.id
        )
    ''')
    
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
        print("No matches found. This might indicate:")
        print("  - Normalization differences between games and cities")
        print("  - Very few games actually match real place names")
        print("  - Need to check sample data")
        
        # Debug: show some normalized names
        cursor.execute("SELECT name, normalized_name FROM games WHERE LENGTH(normalized_name) <= 15 LIMIT 10")
        games_sample = cursor.fetchall()
        cursor.execute("SELECT name, normalized_name FROM cities WHERE LENGTH(normalized_name) <= 15 LIMIT 10")
        cities_sample = cursor.fetchall()
        
        print(f"\nSample normalized game names:")
        for name, normalized in games_sample:
            print(f"  '{name}' → '{normalized}'")
        
        print(f"\nSample normalized city names:")
        for name, normalized in cities_sample:
            print(f"  '{name}' → '{normalized}'")
        
        conn.close()
        return True
    
    # Show match statistics
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
    
    print(f"\nMatches by confidence level:")
    for confidence, count in cursor.fetchall():
        print(f"  {confidence}: {count}")
    
    # Show top matches
    cursor.execute('''
        SELECT g.name, c.name, c.country_name, m.match_type, m.score, m.confidence
        FROM matches m
        JOIN games g ON m.game_id = g.id
        JOIN cities c ON m.city_id = c.id
        ORDER BY m.score DESC, g.rating DESC
        LIMIT 20
    ''')
    
    print(f"\nTop matches:")
    for game, city, country, match_type, score, confidence in cursor.fetchall():
        print(f"  {score:5.1f} | {game} → {city}, {country} | {match_type}")
    
    conn.close()
    return True

if __name__ == "__main__":
    # Default settings
    db_path = "data/processed/boardgames.db"
    
    # Allow custom database path
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    success = find_exact_matches(db_path)
    if not success:
        sys.exit(1)
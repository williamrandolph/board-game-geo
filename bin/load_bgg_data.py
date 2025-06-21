#!/usr/bin/env python3
"""
Load BoardGameGeek data from CSV into SQLite database.
"""

import csv
import sqlite3
import sys
import os
from init_database import normalize_string

def load_bgg_data(csv_path, db_path):
    """Load BGG data from CSV file into database."""
    
    print(f"Loading BGG data from {csv_path}...")
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return False
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        print("Run init_database.py first to create the database schema.")
        return False
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing games data
    cursor.execute("DELETE FROM games")
    print("Cleared existing games data")
    
    # Read and process CSV
    games_loaded = 0
    games_skipped = 0
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            try:
                # Extract data from CSV
                name = row['name'].strip()
                bgg_id = int(row['id'])
                year = int(row['yearpublished']) if row['yearpublished'] else None
                rating = float(row['bayesaverage']) if row['bayesaverage'] else None
                num_votes = int(row['usersrated']) if row['usersrated'] else None
                rank_position = int(row['rank']) if row['rank'] and row['rank'].strip() and row['rank'].strip() != '0' else None
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
                
                # Insert into database
                cursor.execute('''
                    INSERT INTO games (name, normalized_name, bgg_id, year, rating, num_votes, rank_position)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, normalized_name, bgg_id, year, rating, num_votes, rank_position))
                
                games_loaded += 1
                
                # Progress indicator
                if games_loaded % 1000 == 0:
                    print(f"  Loaded {games_loaded} games...")
                    
            except (ValueError, KeyError) as e:
                print(f"  Skipping row due to error: {e}")
                games_skipped += 1
                continue
    
    # Commit changes
    conn.commit()
    
    # Report results
    print(f"\nLoading complete:")
    print(f"  Games loaded: {games_loaded}")
    print(f"  Games skipped: {games_skipped}")
    
    # Show some sample data
    cursor.execute('''
        SELECT name, year, rating, num_votes, rank_position 
        FROM games 
        WHERE rank_position IS NOT NULL
        ORDER BY rank_position 
        LIMIT 10
    ''')
    
    print(f"\nTop 10 games by rank:")
    for game in cursor.fetchall():
        name, year, rating, votes, rank = game
        print(f"  {rank:3d}. {name} ({year}) - {rating:.2f} ({votes:,} votes)")
    
    # Show games that might match city names (short names)
    cursor.execute('''
        SELECT name, normalized_name, year, rating
        FROM games 
        WHERE LENGTH(normalized_name) <= 15
        AND normalized_name NOT LIKE '%:%'
        AND normalized_name NOT LIKE '%the %'
        ORDER BY rating DESC
        LIMIT 20
    ''')
    
    print(f"\nGames with short names (potential city matches):")
    for game in cursor.fetchall():
        name, normalized, year, rating = game
        print(f"  {name} → '{normalized}' ({year}) - {rating:.2f}")
    
    conn.close()
    return True

if __name__ == "__main__":
    # Default paths
    csv_path = "data/bgg/boardgames_ranks.csv"
    db_path = "data/processed/boardgames.db"
    
    # Allow custom paths as command line arguments
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    if len(sys.argv) > 2:
        db_path = sys.argv[2]
    
    success = load_bgg_data(csv_path, db_path)
    if not success:
        sys.exit(1)
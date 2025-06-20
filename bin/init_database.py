#!/usr/bin/env python3
"""
Initialize SQLite database for board game geography matching.
Creates tables for games, cities, and matches.
"""

import sqlite3
import sys
import os

def create_database(db_path):
    """Create the SQLite database with all necessary tables."""
    
    print(f"Creating database at {db_path}...")
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Connect to database (creates file if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create games table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            bgg_id INTEGER,
            year INTEGER,
            rating REAL,
            num_votes INTEGER,
            rank_position INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create cities table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            ascii_name TEXT,
            country_code TEXT,
            country_name TEXT,
            latitude REAL,
            longitude REAL,
            population INTEGER,
            timezone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create matches table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            city_id INTEGER NOT NULL,
            match_type TEXT NOT NULL,
            score REAL NOT NULL,
            confidence TEXT NOT NULL,
            manual_review BOOLEAN DEFAULT FALSE,
            approved BOOLEAN DEFAULT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games(id),
            FOREIGN KEY (city_id) REFERENCES cities(id)
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_normalized ON games(normalized_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_bgg_id ON games(bgg_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cities_normalized ON cities(normalized_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cities_country ON cities(country_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_game_id ON matches(game_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_city_id ON matches(city_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_score ON matches(score)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_confidence ON matches(confidence)')
    
    # Commit changes
    conn.commit()
    
    # Display table info
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Created {len(tables)} tables:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  - {table[0]}: {count} records")
    
    conn.close()
    print("Database initialization complete!")

def normalize_string(text):
    """Normalize string for matching - used by other scripts."""
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove common articles and prefixes
    articles = ['the ', 'a ', 'an ', 'le ', 'la ', 'les ', 'el ', 'los ', 'las ']
    for article in articles:
        if text.startswith(article):
            text = text[len(article):]
            break
    
    # Remove punctuation and extra whitespace
    import re
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

if __name__ == "__main__":
    # Default database path
    db_path = "data/processed/boardgames.db"
    
    # Allow custom path as command line argument
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    create_database(db_path)
#!/usr/bin/env python3
"""
Print matches in a readable format, ordered by BGG rank.
Shows game names with their ranks and all matching cities underneath.
"""

import sqlite3
import sys
import os

def print_matches_by_rank(db_path, limit=None, min_confidence=None):
    """Print matches ordered by BGG rank in a readable format."""
    
    print(f"📋 Board Game Geography Matches")
    print(f"Database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Error: Database not found at {db_path}")
        return False
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Count total matches
    cursor.execute("SELECT COUNT(*) FROM matches")
    total_matches = cursor.fetchone()[0]
    
    if total_matches == 0:
        print("❌ No matches found in database. Run matching first.")
        return False
    
    # Build WHERE clause for confidence filter
    confidence_filter = ""
    params = []
    if min_confidence:
        if min_confidence == "high":
            confidence_filter = "AND m.confidence IN ('very_high', 'high')"
        elif min_confidence == "very_high":
            confidence_filter = "AND m.confidence = 'very_high'"
        else:
            confidence_filter = "AND m.confidence = ?"
            params.append(min_confidence)
    
    # Query for games with matches, ordered by rank
    query = f'''
        SELECT DISTINCT
            g.id,
            g.name,
            g.year,
            g.rank_position,
            g.rating,
            g.num_votes,
            COUNT(m.id) as match_count
        FROM games g
        JOIN matches m ON g.id = m.game_id
        WHERE 1=1 {confidence_filter}
        GROUP BY g.id, g.name, g.year, g.rank_position, g.rating, g.num_votes
        ORDER BY 
            CASE WHEN g.rank_position IS NULL THEN 1 ELSE 0 END,
            g.rank_position ASC,
            g.rating DESC
    '''
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query, params)
    games = cursor.fetchall()
    
    print(f"🎲 Found {len(games)} games with matches (total matches: {total_matches})")
    if min_confidence:
        print(f"📊 Filtered to {min_confidence}+ confidence")
    if limit:
        print(f"📑 Showing top {limit} games")
    print("=" * 80)
    
    for game in games:
        game_id, name, year, rank, rating, votes, match_count = game
        
        # Format rank display
        if rank:
            rank_display = f"#{rank:,}"
        else:
            rank_display = "Unranked"
        
        # Format rating and votes
        rating_display = f"{rating:.2f}" if rating else "N/A"
        votes_display = f"{votes:,}" if votes else "0"
        
        # Print game header
        print(f"\n🎮 {name} ({year})")
        print(f"   📊 {rank_display} | ⭐ {rating_display} | 👥 {votes_display} votes | 🌍 {match_count} location(s)")
        
        # Get all cities for this game
        city_query = f'''
            SELECT 
                c.name,
                c.country_name,
                c.population,
                m.match_type,
                m.score,
                m.confidence
            FROM matches m
            JOIN cities c ON m.city_id = c.id
            WHERE m.game_id = ? {confidence_filter.replace('AND', 'AND')}
            ORDER BY m.score DESC, c.population DESC
        '''
        
        cursor.execute(city_query, [game_id] + params)
        cities = cursor.fetchall()
        
        for city in cities:
            city_name, country, population, match_type, score, confidence = city
            
            # Format population
            if population >= 1000000:
                pop_display = f"{population/1000000:.1f}M"
            elif population >= 1000:
                pop_display = f"{population/1000:.0f}K"
            else:
                pop_display = f"{population}"
            
            # Match type icons
            type_icons = {
                'exact': '🎯',
                'game_contains_city': '📍',
                'city_contains_game': '🔍',
                'high_similarity': '🔄',
                'medium_similarity': '🔄',
                'token_overlap': '🧩'
            }
            
            # Confidence colors (using text symbols)
            confidence_icons = {
                'very_high': '🟢',
                'high': '🟡',
                'medium': '🟠',
                'low': '🔴',
                'very_low': '⚫'
            }
            
            icon = type_icons.get(match_type, '📌')
            conf_icon = confidence_icons.get(confidence, '⚪')
            
            print(f"     {icon} {city_name}, {country} ({pop_display} people) {conf_icon}")
            print(f"        💯 Score: {score:.1f} | 🏷️  {match_type} | 🎯 {confidence}")
    
    print("\n" + "=" * 80)
    
    # Summary statistics
    cursor.execute(f'''
        SELECT confidence, COUNT(*) 
        FROM matches m 
        WHERE 1=1 {confidence_filter}
        GROUP BY confidence
        ORDER BY 
            CASE confidence
                WHEN 'very_high' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
                WHEN 'very_low' THEN 5
            END
    ''', params)
    
    print("📈 Match Summary:")
    for confidence, count in cursor.fetchall():
        print(f"   {confidence}: {count:,} matches")
    
    conn.close()
    return True

if __name__ == "__main__":
    # Default settings
    db_path = "data/processed/boardgames.db"
    limit = None
    min_confidence = None
    
    # Parse command line arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == "--db" and i + 1 < len(sys.argv):
            db_path = sys.argv[i + 1]
            i += 2
        elif arg == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            i += 2
        elif arg == "--confidence" and i + 1 < len(sys.argv):
            min_confidence = sys.argv[i + 1]
            i += 2
        elif arg in ["--help", "-h"]:
            print("Usage: python print_matches.py [options]")
            print()
            print("Options:")
            print("  --db PATH           Database path (default: data/processed/boardgames.db)")
            print("  --limit N           Show only top N games")
            print("  --confidence LEVEL  Filter by confidence (very_high, high, medium, low)")
            print("  --help              Show this help message")
            print()
            print("Examples:")
            print("  python print_matches.py --limit 20")
            print("  python print_matches.py --confidence high --limit 10")
            print("  python print_matches.py --db data/test/test_games.db")
            sys.exit(0)
        else:
            print(f"Unknown argument: {arg}")
            print("Use --help for usage information")
            sys.exit(1)
    
    success = print_matches_by_rank(db_path, limit, min_confidence)
    if not success:
        sys.exit(1)
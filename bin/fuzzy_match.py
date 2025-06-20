#!/usr/bin/env python3
"""
Fuzzy matching pipeline to find board games that match city names.
Uses multiple matching strategies and confidence scoring.
"""

import sqlite3
import sys
import os
import re
from difflib import SequenceMatcher

def calculate_levenshtein_similarity(s1, s2):
    """Calculate similarity ratio using SequenceMatcher (similar to Levenshtein)."""
    return SequenceMatcher(None, s1, s2).ratio()

def calculate_token_overlap(s1, s2):
    """Calculate token overlap ratio between two strings."""
    tokens1 = set(s1.split())
    tokens2 = set(s2.split())
    
    if not tokens1 or not tokens2:
        return 0.0
    
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    
    return len(intersection) / len(union)

def calculate_match_score(game_name, city_name, game_normalized, city_normalized):
    """Calculate match score using multiple strategies."""
    
    score = 0.0
    match_type = "none"
    
    # Strategy 1: Exact match (highest score)
    if game_normalized == city_normalized:
        score = 100.0
        match_type = "exact"
    
    # Strategy 2: Substring matches
    elif city_normalized in game_normalized:
        score = 85.0
        match_type = "game_contains_city"
    elif game_normalized in city_normalized:
        score = 80.0
        match_type = "city_contains_game"
    
    # Strategy 3: High similarity match
    else:
        similarity = calculate_levenshtein_similarity(game_normalized, city_normalized)
        if similarity >= 0.8:
            score = similarity * 75.0
            match_type = "high_similarity"
        elif similarity >= 0.6:
            score = similarity * 60.0
            match_type = "medium_similarity"
        
        # Strategy 4: Token overlap for multi-word matches
        token_overlap = calculate_token_overlap(game_normalized, city_normalized)
        if token_overlap >= 0.5:
            token_score = token_overlap * 70.0
            if token_score > score:
                score = token_score
                match_type = "token_overlap"
    
    # Bonus points for certain characteristics
    if score > 0:
        # Bonus for similar lengths (avoid matching very short to very long strings)
        len_ratio = min(len(game_normalized), len(city_normalized)) / max(len(game_normalized), len(city_normalized))
        if len_ratio >= 0.7:
            score += 5.0
        
        # Small penalty for very short strings (less reliable matches)
        if len(game_normalized) <= 3 or len(city_normalized) <= 3:
            score -= 10.0
    
    return max(0.0, score), match_type

def assign_confidence(score, match_type, game_votes, city_population):
    """Assign confidence level based on score and context."""
    
    # Base confidence from score
    if score >= 95:
        confidence = "very_high"
    elif score >= 80:
        confidence = "high"
    elif score >= 60:
        confidence = "medium"
    elif score >= 40:
        confidence = "low"
    else:
        confidence = "very_low"
    
    # Adjust based on context
    if match_type == "exact" and score >= 100:
        confidence = "very_high"
    elif match_type in ["game_contains_city", "city_contains_game"] and score >= 75:
        confidence = "high"
    
    # Consider game popularity and city size
    if game_votes and game_votes > 10000 and city_population and city_population > 100000:
        # Popular game + major city = higher confidence
        if confidence == "medium":
            confidence = "high"
    elif game_votes and game_votes < 1000 and city_population and city_population < 10000:
        # Obscure game + small city = lower confidence
        if confidence == "high":
            confidence = "medium"
        elif confidence == "medium":
            confidence = "low"
    
    return confidence

def find_matches(db_path, min_score=40.0):
    """Find all potential game-city matches above minimum score."""
    
    print(f"Finding matches with minimum score: {min_score}")
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return False
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing matches
    cursor.execute("DELETE FROM matches")
    print("Cleared existing matches")
    
    # Get all games and cities for comparison
    cursor.execute('''
        SELECT id, name, normalized_name, num_votes, rating
        FROM games
        ORDER BY rating DESC
    ''')
    games = cursor.fetchall()
    
    cursor.execute('''
        SELECT id, name, normalized_name, country_name, population
        FROM cities
        ORDER BY population DESC
    ''')
    cities = cursor.fetchall()
    
    print(f"Comparing {len(games):,} games against {len(cities):,} cities...")
    
    matches_found = 0
    total_comparisons = 0
    
    # Compare every game against every city
    for game_idx, game in enumerate(games):
        game_id, game_name, game_normalized, game_votes, game_rating = game
        
        # Progress indicator
        if game_idx % 500 == 0:
            print(f"  Processing game {game_idx + 1:,} of {len(games):,}...")
        
        for city in cities:
            city_id, city_name, city_normalized, country_name, city_population = city
            total_comparisons += 1
            
            # Calculate match score
            score, match_type = calculate_match_score(
                game_name, city_name, game_normalized, city_normalized
            )
            
            # Only keep matches above threshold
            if score >= min_score:
                # Assign confidence level
                confidence = assign_confidence(
                    score, match_type, game_votes, city_population
                )
                
                # Determine if manual review is needed
                manual_review = (
                    confidence in ["low", "very_low"] or
                    score < 70.0 or
                    match_type in ["medium_similarity", "token_overlap"]
                )
                
                # Insert match into database
                cursor.execute('''
                    INSERT INTO matches (game_id, city_id, match_type, score, confidence, manual_review)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (game_id, city_id, match_type, score, confidence, manual_review))
                
                matches_found += 1
    
    # Commit changes
    conn.commit()
    
    # Report results
    print(f"\nMatching complete:")
    print(f"  Total comparisons: {total_comparisons:,}")
    print(f"  Matches found: {matches_found:,}")
    
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
        print(f"  {confidence}: {count:,}")
    
    # Show top matches
    cursor.execute('''
        SELECT g.name, c.name, c.country_name, m.match_type, m.score, m.confidence
        FROM matches m
        JOIN games g ON m.game_id = g.id
        JOIN cities c ON m.city_id = c.id
        ORDER BY m.score DESC
        LIMIT 20
    ''')
    
    print(f"\nTop 20 matches by score:")
    for game, city, country, match_type, score, confidence in cursor.fetchall():
        print(f"  {score:5.1f} | {game} → {city}, {country} | {match_type} | {confidence}")
    
    # Show matches that need manual review
    cursor.execute('''
        SELECT COUNT(*) FROM matches WHERE manual_review = 1
    ''')
    review_count = cursor.fetchone()[0]
    print(f"\nMatches requiring manual review: {review_count:,}")
    
    if review_count > 0:
        cursor.execute('''
            SELECT g.name, c.name, c.country_name, m.score, m.confidence
            FROM matches m
            JOIN games g ON m.game_id = g.id
            JOIN cities c ON m.city_id = c.id
            WHERE m.manual_review = 1
            ORDER BY m.score DESC
            LIMIT 10
        ''')
        
        print(f"\nTop matches needing review:")
        for game, city, country, score, confidence in cursor.fetchall():
            print(f"  {score:5.1f} | {game} → {city}, {country} | {confidence}")
    
    conn.close()
    return True

if __name__ == "__main__":
    # Default settings
    db_path = "data/processed/boardgames.db"
    min_score = 40.0
    
    # Allow custom settings as command line arguments
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    if len(sys.argv) > 2:
        min_score = float(sys.argv[2])
    
    success = find_matches(db_path, min_score)
    if not success:
        sys.exit(1)
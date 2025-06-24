#!/usr/bin/env python3
"""
Validate matches using BGG API metadata to filter false positives.
Implements hybrid approach: automated filtering + targeted manual review.
"""

import sqlite3
import sys
import os

# Import the cached BGG API function
from bgg_cache import get_bgg_game_details


def analyze_geographical_indicators(game_data):
    """Analyze BGG metadata for geographical indicators."""
    
    if not game_data:
        return {'score': 0, 'indicators': [], 'confidence': 'unknown'}
    
    indicators = []
    score = 0
    
    # Check categories for geographical themes
    geo_categories = [
        'civilization', 'city building', 'exploration', 'travel', 
        'territory building', 'area control', 'economic'
    ]
    
    for category in game_data['categories']:
        category_lower = category.lower()
        for geo_cat in geo_categories:
            if geo_cat in category_lower:
                indicators.append(f"Category: {category}")
                score += 2
    
    # Check families for location-specific content
    location_families = []
    for family in game_data['families']:
        family_lower = family.lower()
        # Look for location-related families
        location_keywords = ['country:', 'region:', 'city:', 'cities:', 'continent:', 'countries:']
        if any(keyword in family_lower for keyword in location_keywords):
            location_families.append(family)
            indicators.append(f"Location Family: {family}")
            score += 3
    
    # Check description for geographical terms
    if game_data['description']:
        desc_lower = game_data['description'].lower()
        geo_terms = [
            'ancient rome', 'roman empire', 'mediterranean', 'europe', 'asia',
            'trade routes', 'empire', 'civilization', 'exploration', 'colonial',
            'cities', 'city', 'region', 'continent', 'country', 'nation'
        ]
        
        found_terms = []
        for term in geo_terms:
            if term in desc_lower:
                found_terms.append(term)
        
        if found_terms:
            indicators.append(f"Description mentions: {', '.join(found_terms[:3])}")
            score += len(found_terms)
    
    # Determine confidence level
    if score >= 8:
        confidence = 'very_high'
    elif score >= 5:
        confidence = 'high'
    elif score >= 2:
        confidence = 'medium'
    elif score > 0:
        confidence = 'low'
    else:
        confidence = 'very_low'
    
    return {
        'score': score,
        'indicators': indicators,
        'confidence': confidence,
        'location_families': location_families
    }

def classify_match_confidence(game_data, city_name, city_country, match_type, match_score):
    """Classify overall match confidence combining BGG data and matching data."""
    
    geo_analysis = analyze_geographical_indicators(game_data)
    
    # Auto-approve criteria (EXTREMELY strict - only absolute slam dunks)
    auto_approve = False
    
    # ONLY auto-approve in these very specific cases:
    
    # Case 1: BGG family explicitly mentions "Cities: [city_name]"
    if geo_analysis['location_families']:
        for family in geo_analysis['location_families']:
            family_lower = family.lower()
            city_lower = city_name.lower()
            
            # Must be EXACTLY "Cities: cityname" pattern
            if (f'cities: {city_lower}' in family_lower or 
                f'cities: {city_lower} (' in family_lower):
                auto_approve = True
                break
    
    # Case 2: Game name obviously contains the city name
    if game_data:
        game_name_lower = game_data['name'].lower()
        city_lower = city_name.lower()
        
        # Famous city games where the connection is obvious
        obvious_patterns = [
            f'{city_lower}:',  # "Istanbul: Big Box"
            f'{city_lower} ',  # "London Bridge" 
            f'{city_lower}(',   # "Birmingham(something)"
        ]
        
        if any(pattern in game_name_lower for pattern in obvious_patterns):
            auto_approve = True
    
    # Obvious false positives (more aggressive)
    auto_reject = False
    
    # Games with clearly non-geographical themes
    non_geo_categories = [
        'abstract strategy', 'party game', 'trivia', 'word game', 
        'memory', 'bluffing', 'real-time', 'dice', 'card game'
    ]
    
    if game_data and any(cat.lower() in [c.lower() for c in game_data['categories']] 
                        for cat in non_geo_categories):
        if geo_analysis['score'] <= 2:  # More aggressive rejection
            auto_reject = True
    
    # Check for historical themes (these are suspicious for modern city matches)
    if game_data:
        # Historical categories
        historical_categories = ['ancient', 'medieval', 'renaissance', 'classical antiquity']
        has_historical_category = any(cat.lower() in historical_categories for cat in game_data['categories'])
        
        # Historical families  
        historical_families = ['ancient:', 'medieval:', 'renaissance:']
        has_historical_family = any(any(hist in family.lower() for hist in historical_families) 
                                   for family in game_data['families'])
        
        # If it's clearly historical, don't auto-approve
        if has_historical_category or has_historical_family:
            auto_approve = False
    
    # Classification
    if auto_approve:
        classification = 'auto_approve'
    elif auto_reject:
        classification = 'auto_reject'
    elif geo_analysis['confidence'] in ['very_low', 'low']:
        classification = 'manual_review_likely_false'
    elif geo_analysis['confidence'] == 'medium':
        classification = 'manual_review_uncertain'
    else:
        classification = 'manual_review_likely_true'
    
    return {
        'classification': classification,
        'geo_analysis': geo_analysis,
        'reasoning': f"Match: {match_type} ({match_score:.1f}), Geo: {geo_analysis['confidence']} ({geo_analysis['score']})"
    }

def validate_matches_batch(db_path, limit=None, start_rank=None, end_rank=None):
    """Validate matches using BGG API data."""
    
    print("🔍 Starting BGG metadata validation...")
    print(f"Database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Error: Database not found")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Build query with optional filters
    where_conditions = ["m.game_id = g.id", "m.city_id = c.id"]
    params = []
    
    if start_rank and end_rank:
        where_conditions.append("g.rank_position BETWEEN ? AND ?")
        params.extend([start_rank, end_rank])
        print(f"📊 Filtering to BGG ranks {start_rank}-{end_rank}")
    elif start_rank:
        where_conditions.append("g.rank_position >= ?")
        params.append(start_rank)
        print(f"📊 Filtering to BGG ranks {start_rank}+")
    
    where_clause = " AND ".join(where_conditions)
    
    query = f'''
        SELECT DISTINCT
            g.id, g.name, g.bgg_id, g.rank_position, g.rating,
            c.name, c.country_name,
            m.match_type, m.score, m.confidence
        FROM matches m, games g, cities c
        WHERE {where_clause}
        ORDER BY 
            CASE WHEN g.rank_position IS NULL THEN 999999 ELSE g.rank_position END,
            g.rating DESC
    '''
    
    if limit:
        query += f" LIMIT {limit}"
        print(f"📑 Processing first {limit} matches")
    
    cursor.execute(query, params)
    matches = cursor.fetchall()
    
    total_matches = len(matches)
    print(f"🎲 Found {total_matches} matches to validate")
    
    if total_matches == 0:
        return True
    
    # Estimate time
    estimated_minutes = (total_matches * 0.6) / 60  # 0.6 seconds per request
    print(f"⏱️  Estimated time: {estimated_minutes:.1f} minutes")
    print("=" * 60)
    
    # Process matches
    results = {
        'auto_approve': [],
        'auto_reject': [],
        'manual_review_likely_true': [],
        'manual_review_uncertain': [],
        'manual_review_likely_false': [],
        'api_errors': []
    }
    
    for i, match in enumerate(matches, 1):
        (game_id, game_name, bgg_id, rank, rating, 
         city_name, city_country, match_type, match_score, match_confidence) = match
        
        rank_display = f"#{rank:,}" if rank else "Unranked"
        print(f"\n[{i}/{total_matches}] {rank_display} {game_name} → {city_name}, {city_country}")
        
        # Fetch BGG data
        bgg_data = get_bgg_game_details(bgg_id)
        
        if bgg_data is None:
            print("  ❌ Failed to fetch BGG data")
            results['api_errors'].append((game_name, city_name, city_country))
            continue
        
        # Classify match
        classification_result = classify_match_confidence(
            bgg_data, city_name, city_country, match_type, match_score
        )
        
        classification = classification_result['classification']
        geo_analysis = classification_result['geo_analysis']
        
        # Icons for classification
        icons = {
            'auto_approve': '✅',
            'auto_reject': '❌',
            'manual_review_likely_true': '🟢',
            'manual_review_uncertain': '🟡', 
            'manual_review_likely_false': '🔴'
        }
        
        icon = icons.get(classification, '❓')
        print(f"  {icon} {classification.replace('_', ' ').title()}")
        print(f"  📊 {classification_result['reasoning']}")
        
        if geo_analysis['indicators']:
            print(f"  🔍 Indicators: {'; '.join(geo_analysis['indicators'][:2])}")
        
        # Store result
        match_data = {
            'game_id': game_id,
            'game_name': game_name,
            'bgg_id': bgg_id,
            'rank': rank,
            'rating': rating,
            'city_name': city_name,
            'city_country': city_country,
            'match_type': match_type,
            'match_score': match_score,
            'geo_score': geo_analysis['score'],
            'indicators': geo_analysis['indicators'],
            'bgg_categories': bgg_data['categories'],
            'reasoning': classification_result['reasoning']
        }
        
        results[classification].append(match_data)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    # Icons for summary
    summary_icons = {
        'auto_approve': '✅',
        'auto_reject': '❌',
        'manual_review_likely_true': '🟢',
        'manual_review_uncertain': '🟡', 
        'manual_review_likely_false': '🔴'
    }
    
    for category, matches in results.items():
        if matches:
            icon = summary_icons.get(category, '📋')
            print(f"{icon} {category.replace('_', ' ').title()}: {len(matches)}")
    
    if results['api_errors']:
        print(f"❌ API Errors: {len(results['api_errors'])}")
    
    # Show some examples
    if results['auto_approve']:
        print(f"\n✅ Auto-approved examples:")
        for match in results['auto_approve'][:3]:
            print(f"  {match['game_name']} → {match['city_name']}, {match['city_country']}")
    
    if results['auto_reject']:
        print(f"\n❌ Auto-rejected examples:")
        for match in results['auto_reject'][:3]:
            print(f"  {match['game_name']} → {match['city_name']}, {match['city_country']}")
    
    manual_review_total = (len(results['manual_review_likely_true']) + 
                          len(results['manual_review_uncertain']) + 
                          len(results['manual_review_likely_false']))
    
    if manual_review_total > 0:
        print(f"\n🔍 Manual review needed: {manual_review_total} matches")
        print("  Next step: Use manual review interface for remaining matches")
    
    conn.close()
    return results

if __name__ == "__main__":
    # Default settings
    db_path = "data/processed/boardgames.db"
    limit = None
    start_rank = None
    end_rank = None
    
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
        elif arg == "--rank-range" and i + 2 < len(sys.argv):
            start_rank = int(sys.argv[i + 1])
            end_rank = int(sys.argv[i + 2])
            i += 3
        elif arg == "--top" and i + 1 < len(sys.argv):
            end_rank = int(sys.argv[i + 1])
            start_rank = 1
            i += 2
        elif arg in ["--help", "-h"]:
            print("Usage: python validate_matches.py [options]")
            print()
            print("Options:")
            print("  --db PATH              Database path")
            print("  --limit N              Process only first N matches")
            print("  --top N                Process only top N ranked games")
            print("  --rank-range START END Process games in rank range")
            print("  --help                 Show this help")
            print()
            print("Examples:")
            print("  python validate_matches.py --top 100")
            print("  python validate_matches.py --limit 50")
            print("  python validate_matches.py --rank-range 1 500")
            sys.exit(0)
        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)
    
    results = validate_matches_batch(db_path, limit, start_rank, end_rank)
    if not results:
        sys.exit(1)
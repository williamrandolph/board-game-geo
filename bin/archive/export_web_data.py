#!/usr/bin/env python3
"""
Export processed matches to JSON format for the web application.
Generates clean, filtered data for map display.
Defaults to exporting only manually approved matches for production use.
"""

import sqlite3
import json
import csv
import sys
import os
from datetime import datetime

def export_matches_json(db_path, output_path, confidence_filter=None, manual_approved_only=False):
    """Export matches to JSON format for web app."""
    
    print(f"Exporting matches to {output_path}...")
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return False
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Build WHERE clause for filtering
    where_conditions = []
    params = []
    
    if confidence_filter:
        if isinstance(confidence_filter, list):
            placeholders = ','.join(['?' for _ in confidence_filter])
            where_conditions.append(f"m.confidence IN ({placeholders})")
            params.extend(confidence_filter)
        else:
            where_conditions.append("m.confidence = ?")
            params.append(confidence_filter)
    
    if manual_approved_only:
        where_conditions.append("m.approved = 1")
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # Query for web export
    query = f'''
        SELECT 
            g.name as game_name,
            g.year,
            g.rating,
            g.num_votes,
            c.name as city_name,
            c.country_name,
            c.latitude,
            c.longitude,
            c.population,
            m.match_type,
            m.score,
            m.confidence,
            m.approved
        FROM matches m
        JOIN games g ON m.game_id = g.id
        JOIN cities c ON m.city_id = c.id
        WHERE {where_clause}
        ORDER BY m.score DESC, g.rating DESC
    '''
    
    cursor.execute(query, params)
    matches = cursor.fetchall()
    
    print(f"Found {len(matches)} matches for export")
    
    # Convert to JSON structure
    games_data = []
    
    for match in matches:
        (game_name, year, rating, num_votes, city_name, country_name,
         latitude, longitude, population, match_type, score, confidence, approved) = match
        
        game_entry = {
            "name": game_name,
            "year": year,
            "rating": round(rating, 2) if rating else None,
            "votes": num_votes,
            "location": {
                "city": city_name,
                "country": country_name,
                "coordinates": {
                    "lat": latitude,
                    "lng": longitude
                }
            },
            "population": population,
            "match": {
                "type": match_type,
                "score": round(score, 1),
                "confidence": confidence,
                "approved": bool(approved) if approved is not None else None
            }
        }
        
        games_data.append(game_entry)
    
    # Create export data structure
    export_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_games": len(games_data),
            "filters_applied": {
                "confidence": confidence_filter,
                "manual_approved_only": manual_approved_only
            }
        },
        "games": games_data
    }
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"Exported {len(games_data)} games to {output_path}")
    
    conn.close()
    return True

def export_matches_csv(db_path, output_path, confidence_filter=None):
    """Export matches to CSV format for manual review."""
    
    print(f"Exporting matches to CSV: {output_path}...")
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return False
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Build WHERE clause
    where_conditions = []
    params = []
    
    if confidence_filter:
        if isinstance(confidence_filter, list):
            placeholders = ','.join(['?' for _ in confidence_filter])
            where_conditions.append(f"m.confidence IN ({placeholders})")
            params.extend(confidence_filter)
        else:
            where_conditions.append("m.confidence = ?")
            params.append(confidence_filter)
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # Query for CSV export
    query = f'''
        SELECT 
            g.name,
            g.year,
            g.rating,
            g.num_votes,
            c.name,
            c.country_name,
            c.population,
            m.match_type,
            m.score,
            m.confidence,
            m.manual_review,
            m.approved,
            m.notes
        FROM matches m
        JOIN games g ON m.game_id = g.id
        JOIN cities c ON m.city_id = c.id
        WHERE {where_clause}
        ORDER BY m.score DESC
    '''
    
    cursor.execute(query, params)
    matches = cursor.fetchall()
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write CSV file
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'Game Name', 'Year', 'Rating', 'Votes',
            'City', 'Country', 'Population',
            'Match Type', 'Score', 'Confidence',
            'Manual Review', 'Approved', 'Notes'
        ])
        
        # Write data
        for match in matches:
            writer.writerow(match)
    
    print(f"Exported {len(matches)} matches to CSV")
    
    conn.close()
    return True

def generate_summary_report(db_path, output_path):
    """Generate a summary report of the matching results."""
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Collect various statistics
    stats = {}
    
    # Basic counts
    cursor.execute("SELECT COUNT(*) FROM games")
    stats['total_games'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cities")
    stats['total_cities'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM matches")
    stats['total_matches'] = cursor.fetchone()[0]
    
    # Matches by confidence
    cursor.execute('''
        SELECT confidence, COUNT(*) 
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
    stats['matches_by_confidence'] = dict(cursor.fetchall())
    
    # Matches by approval status
    cursor.execute('''
        SELECT 
            CASE 
                WHEN approved = 1 THEN 'approved'
                WHEN approved = 0 THEN 'rejected'
                ELSE 'pending'
            END as status,
            COUNT(*) 
        FROM matches 
        GROUP BY 
            CASE 
                WHEN approved = 1 THEN 'approved'
                WHEN approved = 0 THEN 'rejected'
                ELSE 'pending'
            END
    ''')
    stats['matches_by_approval'] = dict(cursor.fetchall())
    
    # Top scoring approved matches
    cursor.execute('''
        SELECT g.name, c.name, c.country_name, m.score, m.confidence
        FROM matches m
        JOIN games g ON m.game_id = g.id
        JOIN cities c ON m.city_id = c.id
        WHERE m.approved = 1
        ORDER BY m.score DESC
        LIMIT 10
    ''')
    stats['top_matches'] = cursor.fetchall()
    
    # Countries with most approved matches
    cursor.execute('''
        SELECT c.country_name, COUNT(*) as match_count
        FROM matches m
        JOIN cities c ON m.city_id = c.id
        WHERE m.approved = 1
        GROUP BY c.country_name
        ORDER BY match_count DESC
        LIMIT 10
    ''')
    stats['countries_most_matches'] = cursor.fetchall()
    
    # Create report
    report = {
        "summary": {
            "generated_at": datetime.now().isoformat(),
            "total_games": stats['total_games'],
            "total_cities": stats['total_cities'],
            "total_matches": stats['total_matches']
        },
        "confidence_breakdown": stats['matches_by_confidence'],
        "approval_breakdown": stats['matches_by_approval'],
        "top_matches": [
            {
                "game": match[0],
                "city": match[1],
                "country": match[2],
                "score": match[3],
                "confidence": match[4]
            }
            for match in stats['top_matches']
        ],
        "countries_with_most_matches": [
            {"country": country, "matches": count}
            for country, count in stats['countries_most_matches']
        ]
    }
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write report
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Generated summary report: {output_path}")
    
    conn.close()
    return True

if __name__ == "__main__":
    # Default settings
    db_path = "data/processed/boardgames.db"
    
    if len(sys.argv) < 2:
        print("Usage: python export_web_data.py <command> [options]")
        print("Commands:")
        print("  json <output_path> [confidence_filter]  - Export approved matches to JSON for web app")
        print("  json-all <output_path> [confidence_filter] - Export all matches to JSON (testing)")
        print("  csv <output_path> [confidence_filter]   - Export to CSV for review")
        print("  summary <output_path>                   - Generate summary report")
        print("  all                                     - Export all formats (approved for web)")
        print("")
        print("Note: JSON exports now default to manual_approved_only=True for production web app use")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "json":
        output_path = sys.argv[2] if len(sys.argv) > 2 else "data/exports/games.json"
        confidence_filter = sys.argv[3].split(',') if len(sys.argv) > 3 else None
        if len(sys.argv) > 4:
            db_path = sys.argv[4]
        # Default to only approved matches for web export
        export_matches_json(db_path, output_path, confidence_filter, manual_approved_only=True)
        
    elif command == "json-all":
        output_path = sys.argv[2] if len(sys.argv) > 2 else "data/exports/games_all.json"
        confidence_filter = sys.argv[3].split(',') if len(sys.argv) > 3 else None
        if len(sys.argv) > 4:
            db_path = sys.argv[4]
        # Export all matches (for testing/development)
        export_matches_json(db_path, output_path, confidence_filter, manual_approved_only=False)
        
    elif command == "csv":
        output_path = sys.argv[2] if len(sys.argv) > 2 else "data/exports/matches_review.csv"
        confidence_filter = sys.argv[3].split(',') if len(sys.argv) > 3 else None
        export_matches_csv(db_path, output_path, confidence_filter)
        
    elif command == "summary":
        output_path = sys.argv[2] if len(sys.argv) > 2 else "data/exports/summary_report.json"
        generate_summary_report(db_path, output_path)
        
    elif command == "all":
        print("Exporting all formats...")
        # Export only approved matches for web use
        export_matches_json(db_path, "data/exports/games.json", None, manual_approved_only=True)
        # Export all matches for review/analysis
        export_matches_json(db_path, "data/exports/games_all.json", None, manual_approved_only=False)
        export_matches_csv(db_path, "data/exports/matches_review.csv", None)
        generate_summary_report(db_path, "data/exports/summary_report.json")
        print("All exports complete!")
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
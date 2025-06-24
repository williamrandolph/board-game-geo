#!/usr/bin/env python3
"""
Check for invalid BGG IDs in the database.
Some games may have been deleted from BGG or have incorrect IDs.
"""

import sqlite3
import sys
import os

# Import the caching functionality
from bgg_cache import get_bgg_game_details

def check_invalid_bgg_ids(db_path, limit=None):
    """
    Check for BGG IDs that return no data from the API.
    
    Args:
        db_path: Path to SQLite database
        limit: Optional limit on number of IDs to check
    
    Returns:
        dict: Statistics about invalid IDs found
    """
    
    print("🔍 Checking for Invalid BGG IDs")
    print(f"📊 Database: {db_path}")
    print("=" * 60)
    
    if not os.path.exists(db_path):
        print(f"❌ Error: Database not found")
        return False
    
    # Get BGG IDs that have matches (most important to validate)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = """
        SELECT DISTINCT g.bgg_id, g.name, g.rank_position
        FROM games g
        INNER JOIN matches m ON g.id = m.game_id
        WHERE g.bgg_id IS NOT NULL
        ORDER BY 
            CASE WHEN g.rank_position IS NULL THEN 999999 ELSE g.rank_position END,
            g.rating DESC
    """
    
    if limit:
        query += f" LIMIT {limit}"
        print(f"📑 Checking first {limit} BGG IDs with matches")
    else:
        print("🎯 Checking all BGG IDs with matches")
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("❌ No BGG IDs found for games with matches")
        return False
    
    print(f"📊 Found {len(rows)} BGG IDs to check")
    print()
    
    stats = {
        'total_checked': len(rows),
        'valid_ids': [],
        'invalid_ids': [],
        'errors': []
    }
    
    # Check each BGG ID
    for i, (bgg_id, game_name, rank) in enumerate(rows, 1):
        rank_display = f"#{rank:,}" if rank else "Unranked"
        print(f"[{i}/{len(rows)}] Checking BGG ID {bgg_id} - {rank_display} {game_name}")
        
        try:
            game_data = get_bgg_game_details(bgg_id)
            
            if game_data and game_data.get('name'):
                stats['valid_ids'].append({
                    'bgg_id': bgg_id,
                    'db_name': game_name,
                    'bgg_name': game_data['name'],
                    'rank': rank
                })
                print(f"  ✅ Valid: {game_data['name']}")
                
                # Check if names match
                if game_data['name'].lower() != game_name.lower():
                    print(f"  ⚠️  Name mismatch: DB='{game_name}' vs BGG='{game_data['name']}'")
            else:
                stats['invalid_ids'].append({
                    'bgg_id': bgg_id,
                    'db_name': game_name,
                    'rank': rank
                })
                print(f"  ❌ Invalid: No data returned from BGG")
                
        except Exception as e:
            stats['errors'].append({
                'bgg_id': bgg_id,
                'db_name': game_name,
                'rank': rank,
                'error': str(e)
            })
            print(f"  💥 Error: {e}")
    
    # Show results
    print()
    print("=" * 60)
    print("📊 INVALID BGG ID CHECK RESULTS")
    print("=" * 60)
    print(f"✅ Valid IDs: {len(stats['valid_ids'])}")
    print(f"❌ Invalid IDs: {len(stats['invalid_ids'])}")
    print(f"💥 Errors: {len(stats['errors'])}")
    
    if stats['invalid_ids']:
        print(f"\n❌ Invalid BGG IDs found:")
        for invalid in stats['invalid_ids'][:10]:  # Show first 10
            rank_display = f"#{invalid['rank']:,}" if invalid['rank'] else "Unranked"
            print(f"  BGG ID {invalid['bgg_id']}: {rank_display} {invalid['db_name']}")
        
        if len(stats['invalid_ids']) > 10:
            print(f"  ... and {len(stats['invalid_ids']) - 10} more")
    
    if stats['errors']:
        print(f"\n💥 Errors encountered:")
        for error in stats['errors'][:5]:  # Show first 5
            print(f"  BGG ID {error['bgg_id']}: {error['error']}")
    
    invalid_rate = len(stats['invalid_ids']) / len(rows) * 100
    print(f"\n📊 Invalid rate: {invalid_rate:.1f}% ({len(stats['invalid_ids'])}/{len(rows)})")
    
    if stats['invalid_ids']:
        print(f"\n💡 Recommendation: Consider removing or fixing these invalid BGG IDs")
        print(f"   They may cause validation failures or slow down the process.")
    
    return stats

if __name__ == "__main__":
    # Default settings
    db_path = "data/processed/boardgames.db"
    limit = None
    
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
        elif arg in ["--help", "-h"]:
            print("Usage: python check_invalid_bgg_ids.py [options]")
            print()
            print("Check for invalid BGG IDs in the database that return no data from BGG API.")
            print("This helps identify deleted games or incorrect IDs that could cause issues.")
            print()
            print("Options:")
            print("  --db PATH     Database path (default: data/processed/boardgames.db)")
            print("  --limit N     Limit number of IDs to check (for testing)")
            print("  --help        Show this help")
            print()
            print("Examples:")
            print("  python check_invalid_bgg_ids.py              # Check all matched games")
            print("  python check_invalid_bgg_ids.py --limit 50   # Check first 50 games")
            sys.exit(0)
        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)
    
    results = check_invalid_bgg_ids(db_path, limit)
    if not results:
        sys.exit(1)
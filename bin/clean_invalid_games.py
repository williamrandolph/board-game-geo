#!/usr/bin/env python3
"""
Clean invalid BGG IDs from the database.
Removes games and their matches when BGG IDs are no longer valid.
"""

import sqlite3
import sys
import os

def clean_invalid_games(db_path, invalid_bgg_ids, dry_run=True):
    """
    Remove invalid games and their matches from the database.
    
    Args:
        db_path: Path to SQLite database
        invalid_bgg_ids: List of invalid BGG IDs to remove
        dry_run: If True, only show what would be removed without making changes
    
    Returns:
        dict: Statistics about the cleanup operation
    """
    
    if dry_run:
        print("🔍 DRY RUN - No changes will be made")
    else:
        print("⚠️  LIVE RUN - Changes will be made to database")
        
    print(f"📊 Database: {db_path}")
    print(f"🎯 Invalid BGG IDs to remove: {len(invalid_bgg_ids)}")
    print("=" * 60)
    
    if not os.path.exists(db_path):
        print(f"❌ Error: Database not found")
        return False
    
    if not invalid_bgg_ids:
        print("✅ No invalid BGG IDs to remove")
        return {'games_removed': 0, 'matches_removed': 0}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    stats = {
        'games_removed': 0,
        'matches_removed': 0,
        'details': []
    }
    
    # Process each invalid BGG ID
    for bgg_id in invalid_bgg_ids:
        # Get game info
        cursor.execute("""
            SELECT id, name, rank_position 
            FROM games 
            WHERE bgg_id = ?
        """, (bgg_id,))
        
        game_row = cursor.fetchone()
        if not game_row:
            print(f"⚠️  BGG ID {bgg_id} not found in games table")
            continue
            
        game_id, game_name, rank = game_row
        rank_display = f"#{rank:,}" if rank else "Unranked"
        
        # Count matches for this game
        cursor.execute("""
            SELECT COUNT(*) 
            FROM matches 
            WHERE game_id = ?
        """, (game_id,))
        
        match_count = cursor.fetchone()[0]
        
        print(f"🎯 {rank_display} {game_name} (BGG ID: {bgg_id})")
        print(f"   Game ID: {game_id}, Matches: {match_count}")
        
        if not dry_run:
            # Remove matches first (foreign key constraint)
            cursor.execute("DELETE FROM matches WHERE game_id = ?", (game_id,))
            matches_deleted = cursor.rowcount
            
            # Remove game
            cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
            games_deleted = cursor.rowcount
            
            print(f"   ✅ Removed {games_deleted} game, {matches_deleted} matches")
            
            stats['games_removed'] += games_deleted
            stats['matches_removed'] += matches_deleted
        else:
            print(f"   📋 Would remove 1 game, {match_count} matches")
            stats['games_removed'] += 1
            stats['matches_removed'] += match_count
        
        stats['details'].append({
            'bgg_id': bgg_id,
            'game_id': game_id,
            'name': game_name,
            'rank': rank,
            'match_count': match_count
        })
    
    if not dry_run:
        conn.commit()
        print(f"\n✅ Database changes committed")
    else:
        print(f"\n📋 Dry run complete - no changes made")
    
    conn.close()
    
    # Show summary
    print()
    print("=" * 60)
    print("📊 CLEANUP SUMMARY")
    print("=" * 60)
    print(f"🎮 Games {'removed' if not dry_run else 'to remove'}: {stats['games_removed']}")
    print(f"📍 Matches {'removed' if not dry_run else 'to remove'}: {stats['matches_removed']}")
    
    if stats['details']:
        print(f"\n📋 Details:")
        for detail in stats['details']:
            rank_display = f"#{detail['rank']:,}" if detail['rank'] else "Unranked"
            print(f"  BGG {detail['bgg_id']}: {rank_display} {detail['name']} ({detail['match_count']} matches)")
    
    return stats

if __name__ == "__main__":
    # Default settings
    db_path = "data/processed/boardgames.db"
    invalid_ids = []
    dry_run = True
    
    # Parse command line arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == "--db" and i + 1 < len(sys.argv):
            db_path = sys.argv[i + 1]
            i += 2
        elif arg == "--ids" and i + 1 < len(sys.argv):
            # Parse comma-separated BGG IDs
            ids_str = sys.argv[i + 1]
            invalid_ids = [int(id.strip()) for id in ids_str.split(',')]
            i += 2
        elif arg == "--execute":
            dry_run = False
            i += 1
        elif arg in ["--help", "-h"]:
            print("Usage: python clean_invalid_games.py [options]")
            print()
            print("Remove invalid BGG IDs and their matches from the database.")
            print("Use this after finding invalid IDs through cache population or validation.")
            print()
            print("Options:")
            print("  --db PATH         Database path (default: data/processed/boardgames.db)")
            print("  --ids ID1,ID2,... Comma-separated list of invalid BGG IDs to remove")
            print("  --execute         Actually perform the removal (default: dry run)")
            print("  --help            Show this help")
            print()
            print("Examples:")
            print("  python clean_invalid_games.py --ids 151734,123456")
            print("  python clean_invalid_games.py --ids 151734 --execute")
            print()
            print("Safety:")
            print("  • Default mode is dry run (no changes made)")
            print("  • Use --execute to actually remove data")
            print("  • Always backup your database before running with --execute")
            sys.exit(0)
        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)
    
    if not invalid_ids:
        print("❌ Error: No invalid BGG IDs specified")
        print("Use --ids to specify comma-separated BGG IDs to remove")
        print("Example: python clean_invalid_games.py --ids 151734,123456")
        sys.exit(1)
    
    results = clean_invalid_games(db_path, invalid_ids, dry_run)
    if not results:
        sys.exit(1)
#!/usr/bin/env python3
"""
Pre-populate BGG API cache using batch requests for faster validation.
This script should be run before validate_matches.py to speed up the process.
"""

import sqlite3
import sys
import os

# Import the batch caching functionality
from bgg_cache import populate_cache_batch, get_cache_stats

def populate_cache_from_database(db_path, batch_size=20, limit=None, matches_only=False):
    """
    Populate BGG cache from games in the database.
    
    Args:
        db_path: Path to SQLite database
        batch_size: Number of games per API request (max 20)
        limit: Optional limit on number of games to cache (for testing)
        matches_only: If True, only cache games that have matches
    
    Returns:
        dict: Statistics about the caching operation
    """
    
    print("🚀 BGG Cache Pre-Population")
    print(f"📊 Database: {db_path}")
    print("=" * 60)
    
    if not os.path.exists(db_path):
        print(f"❌ Error: Database not found")
        return False
    
    # Get BGG IDs from database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if matches_only:
        # Only get BGG IDs for games that have matches
        query = """
            SELECT DISTINCT g.bgg_id, g.name, g.rank_position
            FROM games g
            INNER JOIN matches m ON g.id = m.game_id
            WHERE g.bgg_id IS NOT NULL
            ORDER BY 
                CASE WHEN g.rank_position IS NULL THEN 999999 ELSE g.rank_position END,
                g.rating DESC
        """
        print("🎯 Targeting only games with location matches")
    else:
        # Get all unique BGG IDs, prioritizing games with matches
        query = """
            SELECT DISTINCT g.bgg_id, g.name, g.rank_position
            FROM games g
            LEFT JOIN matches m ON g.id = m.game_id
            WHERE g.bgg_id IS NOT NULL
            ORDER BY 
                CASE WHEN m.game_id IS NOT NULL THEN 0 ELSE 1 END,  -- Prioritize games with matches
                CASE WHEN g.rank_position IS NULL THEN 999999 ELSE g.rank_position END,
                g.rating DESC
        """
        print("📋 Including all games in database")
    
    if limit:
        query += f" LIMIT {limit}"
        print(f"📑 Limiting to first {limit} games for testing")
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        if matches_only:
            print("❌ No BGG IDs found for games with matches")
        else:
            print("❌ No BGG IDs found in database")
        return False
    
    bgg_ids = [row[0] for row in rows]
    
    if matches_only:
        print(f"📊 Found {len(bgg_ids)} games with location matches")
    else:
        print(f"📊 Found {len(bgg_ids)} unique BGG IDs in database")
    
    # Show time savings estimate
    estimated_individual_time = len(bgg_ids) * 0.6 / 60  # 0.6 seconds per request
    estimated_batch_time = (len(bgg_ids) / batch_size) * 0.6 / 60  # batch_size per batch
    time_saved = estimated_individual_time - estimated_batch_time
    efficiency = time_saved / estimated_individual_time * 100
    
    print(f"⏱️  Individual requests would take: {estimated_individual_time:.1f} minutes")
    print(f"⚡ Batch requests will take: {estimated_batch_time:.1f} minutes")
    print(f"💾 Time saved: {time_saved:.1f} minutes ({efficiency:.0f}% faster)")
    print()
    
    # Show initial cache stats
    initial_stats = get_cache_stats()
    print(f"📊 Cache before: {initial_stats['cached_games']} games cached")
    print()
    
    # Populate cache
    print("🔄 Starting batch cache population...")
    stats = populate_cache_batch(bgg_ids, batch_size)
    
    # Handle invalid BGG IDs
    if stats.get('invalid_ids'):
        print()
        print("⚠️  Found invalid BGG IDs (deleted/unpublished games):")
        for invalid_id in stats['invalid_ids']:
            print(f"  BGG ID {invalid_id}")
        
        print()
        print("💡 Recommendation: Remove these invalid games from database:")
        ids_str = ','.join(str(id) for id in stats['invalid_ids'])
        print(f"   python bin/clean_invalid_games.py --ids {ids_str} --execute")
        print()
        print("   This will clean up deleted/unpublished games and their matches.")
    
    # Show results
    print()
    print("=" * 60)
    print("📊 CACHE POPULATION RESULTS")
    print("=" * 60)
    print(f"✅ Total games requested: {stats['total_requested']:,}")
    print(f"💾 Already cached: {stats['already_cached']:,}")
    print(f"🆕 Newly fetched: {stats['fetched']:,}")
    print(f"❌ Errors: {stats['errors']:,}")
    
    invalid_count = len(stats.get('invalid_ids', []))
    if invalid_count > 0:
        print(f"⚠️  Invalid/deleted games: {invalid_count:,}")
    
    batches = stats.get('batches', 0)
    print(f"📦 API batches used: {batches:,}")
    
    if batches > 0 and stats['fetched'] > 0:
        avg_per_batch = stats['fetched'] / batches
        print(f"📈 Average games per batch: {avg_per_batch:.1f}")
    
    # Show final cache stats
    final_stats = get_cache_stats()
    print(f"📊 Cache after: {final_stats['cached_games']} games cached")
    
    # Calculate actual time saved
    if stats['fetched'] > 0:
        batches_used = stats.get('batches', 0)
        actual_time_saved = stats['fetched'] * 0.6 / 60 - batches_used * 0.6 / 60
        print(f"⏱️  Actual time saved: {actual_time_saved:.1f} minutes")
    
    print()
    print("🎯 Cache population complete! Validation will now be much faster.")
    
    return stats

if __name__ == "__main__":
    # Default settings
    db_path = "data/processed/boardgames.db"
    batch_size = 20
    limit = None
    matches_only = False
    
    # Parse command line arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == "--db" and i + 1 < len(sys.argv):
            db_path = sys.argv[i + 1]
            i += 2
        elif arg == "--batch-size" and i + 1 < len(sys.argv):
            batch_size = int(sys.argv[i + 1])
            if batch_size > 20:
                print("Warning: BGG API supports max 20 IDs per request, using 20")
                batch_size = 20
            i += 2
        elif arg == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            i += 2
        elif arg == "--matches-only":
            matches_only = True
            i += 1
        elif arg in ["--help", "-h"]:
            print("Usage: python populate_cache.py [options]")
            print()
            print("Pre-populate BGG API cache using batch requests for faster validation.")
            print("This significantly speeds up the validation process by reducing API calls.")
            print()
            print("Options:")
            print("  --db PATH         Database path (default: data/processed/boardgames.db)")
            print("  --batch-size N    Games per API request, max 20 (default: 20)")
            print("  --limit N         Limit number of games to cache (for testing)")
            print("  --matches-only    Only cache games that have location matches")
            print("  --help            Show this help")
            print()
            print("Examples:")
            print("  python populate_cache.py                    # Cache all games")
            print("  python populate_cache.py --matches-only     # Cache only matched games")
            print("  python populate_cache.py --limit 100        # Cache first 100 games")
            print("  python populate_cache.py --batch-size 10    # Use smaller batches")
            print()
            print("Time savings:")
            print("  • Individual requests: ~0.6 seconds per game")
            print("  • Batch requests: ~0.6 seconds per 20 games")
            print("  • Efficiency gain: ~95% faster for large datasets")
            sys.exit(0)
        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)
    
    results = populate_cache_from_database(db_path, batch_size, limit, matches_only)
    if not results:
        sys.exit(1)
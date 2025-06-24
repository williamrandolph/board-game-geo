"""Load info from BGG into the local cache"""

from bgg_cache import populate_cache_batch, get_cache_stats
import csv
import sys

def cache_bgg_info(input_csv: str):
    # get all IDs
    with open(input_csv, 'r', encoding='utf-8') as in_file:
        reader = csv.DictReader(in_file)
        ids = [int(row['id']) for row in reader]

    # Show initial cache stats
    initial_stats = get_cache_stats()
    print(f"📊 Cache before: {initial_stats['cached_games']} games cached")
    print()

    # call bgg_cache for each group of IDs
    stats = populate_cache_batch(ids)

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

if __name__ == "__main__":
    input_csv = "data/processed/filtered_games.csv"
    # sysargs -- target file, cache directory?

    if len(sys.argv) > 1:
        input_csv = sys.argv[1]

    cache_bgg_info(input_csv)
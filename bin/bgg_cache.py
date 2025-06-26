#!/usr/bin/env python3
"""
BGG API caching layer for board game geography matching.
Saves API responses to local files to avoid repeated requests.
"""

import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import time
import os
import json
import gzip
from datetime import datetime, timedelta

class BGGCache:
    def __init__(self, cache_dir="data/cache/bgg", cache_duration_days=30):
        """
        Initialize BGG cache.
        
        Args:
            cache_dir: Directory to store cached responses
            cache_duration_days: How long to keep cached responses (default: 30 days)
        """
        self.cache_dir = cache_dir
        self.cache_duration = timedelta(days=cache_duration_days)
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize metadata file
        self.metadata_file = os.path.join(cache_dir, "cache_metadata.json")
        self.metadata = self._load_metadata()
    
    def _load_metadata(self):
        """Load cache metadata (statistics, timestamps, etc.)."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "created": datetime.now().isoformat(),
            "stats": {
                "total_requests": 0,
                "cache_hits": 0,
                "api_calls": 0,
                "errors": 0
            },
            "games": {}
        }
    
    def _save_metadata(self):
        """Save cache metadata to disk."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    def _get_cache_path(self, bgg_id):
        """Get the file path for a cached game response."""
        return os.path.join(self.cache_dir, f"game_{bgg_id}.json")
    
    def _is_cache_valid(self, cache_path):
        """Check if cached file is still valid (not expired)."""
        if not os.path.exists(cache_path):
            return False
        
        # Check file age
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        return datetime.now() - file_time < self.cache_duration
    
    def _fetch_from_api(self, bgg_id, max_retries=3):
        """Fetch game data from BGG API with rate limiting."""
        
        for attempt in range(max_retries):
            try:
                # BGG API rate limit: 2 requests per second
                time.sleep(0.6)  # 600ms delay to be safe
                
                url = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}&stats=1"
                
                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'BoardGameGeography/1.0')
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        content = response.read()
                        
                        # Check if response is gzip-compressed
                        if content.startswith(b'\x1f\x8b'):
                            try:
                                content = gzip.decompress(content)
                            except Exception as e:
                                print(f"  Gzip decompression error: {e}")
                                continue
                        
                        # Validate XML
                        if len(content) < 50:
                            print(f"  Warning: Short response ({len(content)} bytes)")
                            continue
                        
                        # Try to parse XML to ensure it's valid
                        try:
                            root = ET.fromstring(content)
                            item = root.find('item')
                            
                            if item is not None:
                                # Extract and return structured data
                                return self._parse_xml_response(content)
                            else:
                                print(f"  No item found in XML response")
                                continue
                                
                        except ET.ParseError as e:
                            print(f"  XML parse error: {e}")
                            continue
                    
                    elif response.status == 429:  # Rate limited
                        print(f"  Rate limited, waiting 5 seconds...")
                        time.sleep(5)
                        continue
                    else:
                        print(f"  BGG API error {response.status}")
                        return None
                        
            except urllib.error.HTTPError as e:
                if e.code == 429:  # Rate limited
                    print(f"  Rate limited, waiting 5 seconds...")
                    time.sleep(5)
                    continue
                else:
                    print(f"  BGG API error {e.code}")
                    return None
            except Exception as e:
                print(f"  Error fetching BGG data: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return None
        
        return None
    
    def _fetch_batch_from_api(self, bgg_ids, max_retries=3):
        """Fetch multiple games from BGG API in a single request (up to 20 IDs)."""
        
        if len(bgg_ids) > 20:
            raise ValueError("BGG API supports maximum 20 IDs per request")
        
        if not bgg_ids:
            return {}
        
        ids_str = ','.join(str(id) for id in bgg_ids)
        
        for attempt in range(max_retries):
            try:
                # BGG API rate limit: 2 requests per second
                time.sleep(0.6)  # 600ms delay to be safe
                
                url = f"https://boardgamegeek.com/xmlapi2/thing?id={ids_str}&stats=1"
                
                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'BoardGameGeography/1.0')
                
                with urllib.request.urlopen(req, timeout=15) as response:
                    if response.status == 200:
                        content = response.read()
                        
                        # Check if response is gzip-compressed
                        if content.startswith(b'\x1f\x8b'):
                            try:
                                content = gzip.decompress(content)
                            except Exception as e:
                                print(f"  Gzip decompression error: {e}")
                                continue
                        
                        # Validate XML
                        if len(content) < 50:
                            print(f"  Warning: Short response ({len(content)} bytes)")
                            continue
                        
                        # Try to parse XML to ensure it's valid
                        try:
                            games = self._parse_batch_xml_response(content)
                            if not games:
                                print(f"  Warning: No valid games found in batch response")
                                # Check if any games were actually invalid
                                content_str = content.decode('utf-8') if isinstance(content, bytes) else content
                                if 'This item has been deleted' in content_str or len(content_str) < 100:
                                    print(f"  Some games in batch may be deleted or invalid")
                            return games
                                
                        except ET.ParseError as e:
                            print(f"  XML parse error: {e}")
                            continue
                    
                    elif response.status == 429:  # Rate limited
                        print(f"  Rate limited, waiting 5 seconds...")
                        time.sleep(5)
                        continue
                    else:
                        print(f"  BGG API error {response.status}")
                        return {}
                        
            except urllib.error.HTTPError as e:
                if e.code == 429:  # Rate limited
                    print(f"  Rate limited, waiting 5 seconds...")
                    time.sleep(5)
                    continue
                else:
                    print(f"  BGG API error {e.code}")
                    return {}
            except Exception as e:
                print(f"  Error fetching BGG batch data: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {}
        
        return {}
    
    def _parse_xml_response(self, xml_content):
        """Parse XML response and extract structured data."""
        root = ET.fromstring(xml_content)
        item = root.find('item')
        
        if item is None:
            return None
        
        # Extract relevant metadata
        name = item.find('.//name[@type="primary"]')
        year = item.find('yearpublished')
        description = item.find('description')
        
        # Categories and mechanics
        categories = [link.get('value') for link in item.findall('.//link[@type="boardgamecategory"]')]
        mechanics = [link.get('value') for link in item.findall('.//link[@type="boardgamemechanic"]')]
        families = [link.get('value') for link in item.findall('.//link[@type="boardgamefamily"]')]
        
        return {
            'bgg_id': int(item.get('id')),
            'name': name.get('value') if name is not None else '',
            'year': int(year.get('value')) if year is not None else None,
            'description': description.text if description is not None else '',
            'categories': categories,
            'mechanics': mechanics,
            'families': families,
            'cached_at': datetime.now().isoformat(),
            'raw_xml': xml_content.decode('utf-8')  # Store raw XML for debugging
        }
    
    def _parse_batch_xml_response(self, xml_content):
        """Parse batch XML response and extract structured data for multiple games."""
        root = ET.fromstring(xml_content)
        items = root.findall('item')
        
        games = {}
        cached_at = datetime.now().isoformat()
        
        for item in items:
            try:
                # Extract relevant metadata
                name = item.find('.//name[@type="primary"]')
                year = item.find('yearpublished')
                description = item.find('description')
                
                # Categories and mechanics
                categories = [link.get('value') for link in item.findall('.//link[@type="boardgamecategory"]')]
                mechanics = [link.get('value') for link in item.findall('.//link[@type="boardgamemechanic"]')]
                families = [link.get('value') for link in item.findall('.//link[@type="boardgamefamily"]')]
                
                bgg_id = int(item.get('id'))
                games[bgg_id] = {
                    'bgg_id': bgg_id,
                    'name': name.get('value') if name is not None else '',
                    'year': int(year.get('value')) if year is not None else None,
                    'description': description.text if description is not None else '',
                    'categories': categories,
                    'mechanics': mechanics,
                    'families': families,
                    'cached_at': cached_at,
                    # 'raw_xml': xml_content.decode('utf-8')  # Store raw XML for debugging
                }
            except Exception as e:
                print(f"  Error parsing item {item.get('id', 'unknown')}: {e}")
                continue
        
        return games
    
    def get_game_details(self, bgg_id):
        """
        Get game details, using cache if available, otherwise fetch from API.
        
        Returns the same format as the original get_bgg_game_details function.
        """
        self.metadata["stats"]["total_requests"] += 1
        
        cache_path = self._get_cache_path(bgg_id)
        
        # Try to load from cache first
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                self.metadata["stats"]["cache_hits"] += 1
                # print(f"  📁 Cache hit for BGG ID {bgg_id}")
                
                # Return in the expected format
                return {
                    'name': cached_data['name'],
                    'year': cached_data['year'],
                    'description': cached_data['description'],
                    'categories': cached_data['categories'],
                    'mechanics': cached_data['mechanics'],
                    'families': cached_data['families']
                }
                
            except Exception as e:
                print(f"  ⚠️  Cache read error for {bgg_id}: {e}")
                # Fall through to API call
        
        # Fetch from API
        print(f"  🌐 Fetching BGG ID {bgg_id} from API...")
        self.metadata["stats"]["api_calls"] += 1
        
        game_data = self._fetch_from_api(bgg_id)
        
        if game_data:
            # Save to cache
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(game_data, f, indent=2, ensure_ascii=False)
                
                # Update metadata
                self.metadata["games"][str(bgg_id)] = {
                    "name": game_data['name'],
                    "cached_at": game_data['cached_at'],
                    "cache_file": os.path.basename(cache_path)
                }
                
                print(f"  💾 Cached BGG ID {bgg_id}: {game_data['name']}")
                
            except Exception as e:
                print(f"  ⚠️  Cache write error for {bgg_id}: {e}")
            
            # Return in the expected format
            return {
                'name': game_data['name'],
                'year': game_data['year'],
                'description': game_data['description'],
                'categories': game_data['categories'],
                'mechanics': game_data['mechanics'],
                'families': game_data['families']
            }
        else:
            self.metadata["stats"]["errors"] += 1
            return None
    
    def get_cache_stats(self):
        """Get cache statistics."""
        stats = self.metadata["stats"].copy()
        
        # Calculate cache hit rate
        if stats["total_requests"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["total_requests"]
        else:
            stats["cache_hit_rate"] = 0.0
        
        # Count cached files
        stats["cached_games"] = len([f for f in os.listdir(self.cache_dir) 
                                   if f.startswith('game_') and f.endswith('.json')])
        
        return stats
    
    def clear_cache(self, older_than_days=None):
        """Clear cache files, optionally only those older than specified days."""
        cleared = 0
        
        for filename in os.listdir(self.cache_dir):
            if filename.startswith('game_') and filename.endswith('.json'):
                filepath = os.path.join(self.cache_dir, filename)
                
                should_clear = True
                if older_than_days:
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    should_clear = datetime.now() - file_time > timedelta(days=older_than_days)
                
                if should_clear:
                    try:
                        os.remove(filepath)
                        cleared += 1
                    except Exception as e:
                        print(f"Error removing {filepath}: {e}")
        
        print(f"Cleared {cleared} cache files")
        return cleared
    
    def populate_cache_batch(self, bgg_ids, batch_size=20, remove_invalid=True):
        """
        Populate cache for multiple BGG IDs using batch API requests.
        
        Args:
            bgg_ids: List of BGG IDs to cache
            batch_size: Number of IDs per API request (max 20)
            remove_invalid: If True, track invalid BGG IDs for removal
        
        Returns:
            dict: Statistics about the operation
        """
        if batch_size > 20:
            batch_size = 20
            print("  Warning: BGG API supports max 20 IDs per request, using batch_size=20")
        
        # Filter out already cached IDs
        uncached_ids = []
        for bgg_id in bgg_ids:
            cache_path = self._get_cache_path(bgg_id)
            if not self._is_cache_valid(cache_path):
                uncached_ids.append(bgg_id)
        
        if not uncached_ids:
            print(f"  All {len(bgg_ids)} games already cached!")
            return {'total_requested': len(bgg_ids), 'already_cached': len(bgg_ids), 'fetched': 0, 'errors': 0}
        
        print(f"  Need to fetch {len(uncached_ids)} games ({len(bgg_ids) - len(uncached_ids)} already cached)")
        
        stats = {
            'total_requested': len(bgg_ids),
            'already_cached': len(bgg_ids) - len(uncached_ids),
            'fetched': 0,
            'errors': 0,
            'batches': 0,
            'invalid_ids': []
        }
        
        # Process in batches
        for i in range(0, len(uncached_ids), batch_size):
            batch = uncached_ids[i:i + batch_size]
            stats['batches'] += 1
            
            print(f"  Batch {stats['batches']}: Fetching {len(batch)} games (IDs: {batch[0]}-{batch[-1]})")
            
            # Fetch batch from API
            games_data = self._fetch_batch_from_api(batch)
            
            if games_data:
                # Save each game to cache
                for bgg_id, game_data in games_data.items():
                    try:
                        cache_path = self._get_cache_path(bgg_id)
                        with open(cache_path, 'w', encoding='utf-8') as f:
                            json.dump(game_data, f, indent=2, ensure_ascii=False)
                        
                        # Update metadata
                        self.metadata["games"][str(bgg_id)] = {
                            "name": game_data['name'],
                            "cached_at": game_data['cached_at'],
                            "cache_file": os.path.basename(cache_path)
                        }
                        
                        stats['fetched'] += 1
                        
                    except Exception as e:
                        print(f"    Error caching game {bgg_id}: {e}")
                        stats['errors'] += 1
                
                # Check for invalid IDs (requested but not returned)
                if remove_invalid:
                    returned_ids = set(games_data.keys())
                    requested_ids = set(batch)
                    missing_ids = requested_ids - returned_ids
                    
                    if missing_ids:
                        for missing_id in missing_ids:
                            stats['invalid_ids'].append(missing_id)
                            print(f"    ⚠️  BGG ID {missing_id} not found - likely deleted/unpublished")
                
                print(f"    ✅ Cached {len(games_data)} games from this batch")
                
                if len(games_data) < len(batch):
                    missing_count = len(batch) - len(games_data)
                    print(f"    ⚠️  {missing_count} games not found in BGG response")
            else:
                print(f"    ❌ Failed to fetch batch")
                # If no games returned, all IDs in batch might be invalid
                if remove_invalid:
                    for bgg_id in batch:
                        stats['invalid_ids'].append(bgg_id)
                        print(f"    ⚠️  BGG ID {bgg_id} likely invalid (no response)")
                stats['errors'] += len(batch)
        
        # Update API call statistics
        self.metadata["stats"]["api_calls"] += stats['batches']
        self.metadata["stats"]["total_requests"] += len(bgg_ids)
        
        return stats
    
    def __del__(self):
        """Save metadata when cache object is destroyed."""
        try:
            self._save_metadata()
        except:
            pass

# Global cache instance
_bgg_cache = None

def get_bgg_game_details(bgg_id, max_retries=3):
    """
    Drop-in replacement for the original get_bgg_game_details function.
    Uses caching to avoid repeated API calls.
    """
    global _bgg_cache
    
    if _bgg_cache is None:
        _bgg_cache = BGGCache()
    
    return _bgg_cache.get_game_details(bgg_id)

def get_cache_stats():
    """Get cache statistics."""
    global _bgg_cache
    
    if _bgg_cache is None:
        _bgg_cache = BGGCache()
    
    return _bgg_cache.get_cache_stats()

def clear_cache(older_than_days=None):
    """Clear cache files."""
    global _bgg_cache
    
    if _bgg_cache is None:
        _bgg_cache = BGGCache()
    
    return _bgg_cache.clear_cache(older_than_days)

def populate_cache_batch(bgg_ids, batch_size=20):
    """Populate cache for multiple BGG IDs using batch API requests."""
    global _bgg_cache
    
    if _bgg_cache is None:
        _bgg_cache = BGGCache()
    
    return _bgg_cache.populate_cache_batch(bgg_ids, batch_size)

if __name__ == "__main__":
    # Command line interface for cache management
    import sys
    
    if len(sys.argv) < 2:
        print("BGG Cache Management")
        print("Usage:")
        print("  python bgg_cache.py stats              - Show cache statistics")
        print("  python bgg_cache.py clear [days]       - Clear cache (optionally older than days)")
        print("  python bgg_cache.py test <bgg_id>      - Test fetching a specific game")
        print("  python bgg_cache.py populate <db_path> - Populate cache from database BGG IDs")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "stats":
        stats = get_cache_stats()
        print("📊 BGG Cache Statistics:")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Cache hits: {stats['cache_hits']}")
        print(f"  API calls: {stats['api_calls']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Cache hit rate: {stats['cache_hit_rate']:.1%}")
        print(f"  Cached games: {stats['cached_games']}")
    
    elif command == "clear":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else None
        cleared = clear_cache(days)
        
    elif command == "test":
        if len(sys.argv) < 3:
            print("Usage: python bgg_cache.py test <bgg_id>")
            sys.exit(1)
        
        bgg_id = int(sys.argv[2])
        print(f"Testing BGG API fetch for game ID {bgg_id}...")
        
        game_data = get_bgg_game_details(bgg_id)
        if game_data:
            print(f"✅ Success!")
            print(f"  Name: {game_data['name']}")
            print(f"  Year: {game_data['year']}")
            print(f"  Categories: {', '.join(game_data['categories'][:3])}...")
            print(f"  Families: {', '.join(game_data['families'][:3])}...")
        else:
            print("❌ Failed to fetch game data")
        
        # Show stats
        stats = get_cache_stats()
        print(f"\n📊 Cache stats: {stats['cache_hits']}/{stats['total_requests']} hits ({stats['cache_hit_rate']:.1%})")
    
    elif command == "populate":
        if len(sys.argv) < 3:
            print("Usage: python bgg_cache.py populate <db_path>")
            sys.exit(1)
        
        import sqlite3
        
        db_path = sys.argv[2]
        print(f"🔄 Populating cache from database: {db_path}")
        
        if not os.path.exists(db_path):
            print(f"❌ Database not found: {db_path}")
            sys.exit(1)
        
        # Get all BGG IDs from database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT bgg_id FROM games WHERE bgg_id IS NOT NULL ORDER BY bgg_id")
        rows = cursor.fetchall()
        conn.close()
        
        bgg_ids = [row[0] for row in rows]
        
        if not bgg_ids:
            print("❌ No BGG IDs found in database")
            sys.exit(1)
        
        print(f"📊 Found {len(bgg_ids)} unique BGG IDs in database")
        
        # Estimate time savings
        estimated_individual_time = len(bgg_ids) * 0.6 / 60  # 0.6 seconds per request
        estimated_batch_time = (len(bgg_ids) / 20) * 0.6 / 60  # 20 per batch
        time_saved = estimated_individual_time - estimated_batch_time
        
        print(f"⏱️  Estimated time with individual requests: {estimated_individual_time:.1f} minutes")
        print(f"⚡ Estimated time with batch requests: {estimated_batch_time:.1f} minutes")
        print(f"💾 Time saved: {time_saved:.1f} minutes ({time_saved/estimated_individual_time*100:.0f}% faster)")
        print()
        
        # Populate cache
        stats = populate_cache_batch(bgg_ids)
        
        print(f"\n📊 Cache Population Results:")
        print(f"  Total requested: {stats['total_requested']}")
        print(f"  Already cached: {stats['already_cached']}")
        print(f"  Newly fetched: {stats['fetched']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  API batches used: {stats['batches']}")
        
        # Show final stats
        final_stats = get_cache_stats()
        print(f"\n📊 Final cache stats: {final_stats['cached_games']} games cached")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
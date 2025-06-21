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
import hashlib
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
                print(f"  📁 Cache hit for BGG ID {bgg_id}")
                
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

if __name__ == "__main__":
    # Command line interface for cache management
    import sys
    
    if len(sys.argv) < 2:
        print("BGG Cache Management")
        print("Usage:")
        print("  python bgg_cache.py stats              - Show cache statistics")
        print("  python bgg_cache.py clear [days]       - Clear cache (optionally older than days)")
        print("  python bgg_cache.py test <bgg_id>      - Test fetching a specific game")
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
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
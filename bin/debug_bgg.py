#!/usr/bin/env python3
"""
Debug BGG API response for specific games
"""

import urllib.request
import xml.etree.ElementTree as ET
import gzip

def debug_bgg_game(bgg_id):
    """Debug BGG API response for a specific game."""
    
    url = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}&stats=1"
    
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'BoardGameGeography/1.0')
    
    with urllib.request.urlopen(req, timeout=10) as response:
        content = response.read()
        
        # Check if response is gzip-compressed
        if content.startswith(b'\x1f\x8b'):
            content = gzip.decompress(content)
        
        root = ET.fromstring(content)
        item = root.find('item')
        
        if item is not None:
            name = item.find('.//name[@type="primary"]')
            description = item.find('description')
            
            categories = [link.get('value') for link in item.findall('.//link[@type="boardgamecategory"]')]
            families = [link.get('value') for link in item.findall('.//link[@type="boardgamefamily"]')]
            
            print(f"Game: {name.get('value') if name is not None else 'Unknown'}")
            print(f"Categories: {categories}")
            print(f"Families: {families}")
            print(f"Description preview: {description.text[:200] if description is not None else 'None'}...")

if __name__ == "__main__":
    # Test Concordia
    print("=== CONCORDIA ===")
    debug_bgg_game(124361)
    
    print("\n=== BRASS: BIRMINGHAM ===")
    debug_bgg_game(224517)
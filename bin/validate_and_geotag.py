"""Get games with exactly one BGG city tag and geotag them."""

from bgg_cache import get_bgg_game_details
import csv
import re
import sys

def validate_and_geotag(filtered_csv: str, output_json_path: str = "data/exports/bgg_family_games.json"):
    skipped = 0
    routes = 0
    bgg_games = []    # BGG game details with single city families + CSV data
    final_games = []  # Final geocoded game entries

    with open(filtered_csv, 'r', encoding='utf-8') as in_file:
        reader = csv.DictReader(in_file)
        for row in reader:
            try:
                id = int(row['id'])
            except (ValueError, KeyError) as e:
                print(f"ERROR: Failed to read from ID column: {e}")
                return
            
            game_details = get_bgg_game_details(id)
            
            if not game_details:
                skipped += 1
                continue

            cities = []
            monopoly_series = False
            for family in game_details["families"]:
                if family == "Series: Monopoly-like":
                    monopoly_series = True
                    break
                if family.startswith("Cities:"):
                    cities.append(family)

            if monopoly_series:
                skipped += 1
                continue
            
            if len(cities) == 0:
                skipped += 1
                continue
            elif len(cities) >= 2:
                routes += 1
                continue
            
            # Combine BGG details with CSV data
            game_with_csv = {
                **game_details,
                'csv_data': row  # Store CSV row for rating/votes access
            }
            bgg_games.append(game_with_csv)


    print(f"skipped: {skipped}")
    print(f"routes: {routes}")
    print(f"matched: {len(bgg_games)}")

    print(f'\nGeo-tagging matches:')

    for match in bgg_games:
        city_tags = [tag for tag in match["families"] if tag.startswith("Cities: ")]
        if not city_tags:
            print(f"No city tags found for {match['name']}")
            continue
        city_tag = city_tags[0]
        
        cities_pattern = r'^Cities:\s*([^()]+?)\s*(?:\(([^,()]+(?:,\s*[^,()]+)*)\))?$'
        matcher = re.match(cities_pattern, city_tag)
        if not matcher:
            print(f"failed to match: {city_tag}")
            continue

        city = matcher.group(1).strip()
        location_info = matcher.group(2).strip() if matcher.group(2) else None
        
        # Parse region and country from location_info
        if location_info:
            parts = [part.strip() for part in location_info.split(',')]
            if len(parts) == 1:
                # Only country: "Cities: Charlotte (USA)"
                region = None
                country = parts[0]
            elif len(parts) == 2:
                # Region and country: "Cities: Asheville (North Carolina, USA)"
                region = parts[0]
                country = parts[1]
            else:
                # Handle edge cases with more commas
                region = ', '.join(parts[:-1])
                country = parts[-1]
        else:
            # No parentheses: "Cities: Birmingham"
            region = None
            country = None

        if city == "Jerusalem" and country == None:
            country = "Israel"

        geocoding_result = get_geotag(city, region, country)
        
        # Create game entry in games.json format
        if geocoding_result and geocoding_result.get('coordinates'):
            # Extract rating and votes from CSV data
            csv_row = match['csv_data']
            try:
                rating = float(csv_row.get('bayesaverage')) if csv_row.get('bayesaverage') else None
                votes = int(csv_row.get('usersrated')) if csv_row.get('usersrated') else None
                bgg_id = int(csv_row.get('id')) if csv_row.get('id') else None
                bgg_rank = int(csv_row.get('rank') if csv_row.get('rank') else None)
            except (ValueError, TypeError):
                rating = None
                votes = None
                bgg_id = None
                bgg_rank = None
            
            # Check if game is an expansion
            is_expansion = "Expansion for Base-game" in match.get("categories", [])
            
            game_entry = {
                "name": match["name"],
                "id": bgg_id,
                "year": match["year"],
                "rating": rating,
                "votes": votes,
                "bggRank": bgg_rank,
                "is_expansion": is_expansion,
                "location": {
                    "city": geocoding_result["city"],
                    "country": geocoding_result.get("address", {}).get("country") or geocoding_result["country"],
                    "coordinates": geocoding_result["coordinates"]
                },
                "match": {
                    "type": "bgg_family",  # Different from pipeline matches
                    "score": geocoding_result["confidence"] * 100,
                    "confidence": "high" if geocoding_result["confidence"] > 0.8 else "medium" if geocoding_result["confidence"] > 0.5 else "low",
                    "approved": True,  # Manual validation via BGG families
                    "tier": geocoding_result["tier"]
                }
            }
            final_games.append(game_entry)
        else:
            print(f"    ❌ Failed to geocode {match['name']} -> {city}")
    
    # Export results in games.json format
    export_results(final_games, output_json_path)

def get_geotag(city: str, region: str, country: str) -> dict[str, any]:
    """Geocode a city using Nominatim API with 5-tier fallback strategy"""
    import urllib.parse
    import urllib.request
    import json
    import time
    import os
    
    # Create cache directory if it doesn't exist
    cache_dir = "data/cache/nominatim"
    os.makedirs(cache_dir, exist_ok=True)
    
    # Create cache key
    cache_parts = [city]
    if region:
        cache_parts.append(region)
    if country:
        cache_parts.append(country)
    cache_key = "_".join(cache_parts).replace(" ", "_").replace("/", "_")
    cache_file = f"{cache_dir}/{cache_key}.json"
    
    # Check cache first
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_result = json.load(f)
                print(f"  📁 Cache hit for {city}")
                return cached_result
        except (json.JSONDecodeError, IOError):
            pass
    
    print(f"  🌐 Geocoding {city}")
    
    # 5-tier geocoding strategy (from project docs)
    queries = []
    
    # Tier 1: Structured query
    if country:
        if region:
            queries.append(f"city={urllib.parse.quote(city)}&state={urllib.parse.quote(region)}&country={urllib.parse.quote(country)}")
        else:
            queries.append(f"city={urllib.parse.quote(city)}&country={urllib.parse.quote(country)}")
    
    # Tier 2: Simple text query
    if country:
        if region:
            queries.append(f"q={urllib.parse.quote(f'{city}, {region}, {country}')}")
        else:
            queries.append(f"q={urllib.parse.quote(f'{city}, {country}')}")
    
    # Tier 3: Primary only
    queries.append(f"q={urllib.parse.quote(city)}")
    
    # Tier 4: Country only (as fallback context)
    if country:
        queries.append(f"q={urllib.parse.quote(f'{city} {country}')}")
    
    base_url = "https://nominatim.openstreetmap.org/search"
    headers = {
        'User-Agent': 'BoardGameGeography/1.0 (https://github.com/user/bggeo)'
    }
    
    result = None
    
    for i, query in enumerate(queries):
        try:
            url = f"{base_url}?{query}&format=json&limit=1&addressdetails=1"
            
            request = urllib.request.Request(url, headers=headers)
            
            # Rate limiting: 1 request per second for Nominatim
            time.sleep(1.1)
            
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                if data and len(data) > 0:
                    location = data[0]
                    
                    # Extract address components
                    address = location.get('address', {})
                    
                    result = {
                        "city": city,
                        "region": region,
                        "country": country,
                        "matched_name": location.get('display_name', ''),
                        "coordinates": {
                            "lat": float(location['lat']),
                            "lng": float(location['lon'])
                        },
                        "confidence": 1.0 - (i * 0.2),  # Higher confidence for earlier tiers
                        "tier": i + 1,
                        "address": {
                            "city": address.get('city') or address.get('town') or address.get('village'),
                            "state": address.get('state'),
                            "country": address.get('country'),
                            "country_code": address.get('country_code')
                        }
                    }
                    
                    print(f"    ✅ Found via tier {i+1}: {location.get('display_name', '')}")
                    break
                    
        except Exception as e:
            print(f"    ⚠️  Tier {i+1} failed: {e}")
            continue
    
    # If no result found, return None result
    if not result:
        result = {
            "city": city,
            "region": region, 
            "country": country,
            "matched_name": None,
            "coordinates": None,
            "confidence": 0.0,
            "tier": None,
            "address": None,
            "error": "No geocoding results found"
        }
        print(f"    ❌ No results found for {city}")
    
    # Cache the result
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
    except IOError as e:
        print(f"    ⚠️  Failed to cache result: {e}")
    
    return result

def export_results(games: list, output_json_path: str):
    """Export games in the same format as games.json"""
    import json
    from datetime import datetime
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    
    # Create output in games.json format
    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_games": len(games),
            "filters_applied": {
                "confidence": None,
                "manual_approved_only": False,
                "source": "bgg_families"
            }
        },
        "games": games
    }
    
    # Write to file
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Exported {len(games)} games to {output_json_path}")
    print(f"✅ Successfully geocoded {len([g for g in games if g['location']['coordinates']])} games")

if __name__ == "__main__":
    filtered_csv = "data/processed/filtered_games.csv"
    output_json_path = "data/exports/bgg_family_games.json"
    
    if len(sys.argv) > 1:
        filtered_csv = sys.argv[1]
    if len(sys.argv) > 2:
        output_json_path = sys.argv[2]
    
    validate_and_geotag(filtered_csv, output_json_path)
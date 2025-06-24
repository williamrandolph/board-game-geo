"""Update pipeline-data.js with latest BGG family games data

This script converts the JSON output from validate_and_geotag.py into the 
JavaScript format used by the web application for embedded game data.
"""

import json
import sys
import os
from datetime import datetime

def update_pipeline_data(input_json_path: str = "data/exports/bgg_family_games.json", 
                        output_js_path: str = "src/pipeline-data.js"):
    """Convert JSON data to JavaScript pipeline-data.js format
    
    Args:
        input_json_path: Path to BGG family games JSON file
        output_js_path: Path to output JavaScript file
    """
    
    print(f"📥 Reading data from {input_json_path}...")
    
    if not os.path.exists(input_json_path):
        print(f"❌ Input file not found: {input_json_path}")
        return False
    
    try:
        # Read the BGG family games JSON
        with open(input_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract metadata
        total_games = data['metadata']['total_games']
        generated_at = data['metadata']['generated_at']
        
        print(f"📊 Processing {total_games} games...")
        
        # Create the JavaScript content
        js_content = f'''// Pipeline data export - {total_games} BGG family games
// Generated: {generated_at}

const PIPELINE_DATA = {json.dumps(data, indent=2, ensure_ascii=False)};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {{
    module.exports = PIPELINE_DATA;
}}
'''
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_js_path), exist_ok=True)
        
        # Write to pipeline-data.js
        with open(output_js_path, 'w', encoding='utf-8') as f:
            f.write(js_content)
        
        # Get file size for reporting
        file_size = os.path.getsize(output_js_path)
        file_size_kb = file_size / 1024
        
        print(f"✅ Updated {output_js_path}")
        print(f"   - Games: {total_games}")
        print(f"   - File size: {file_size_kb:.1f} KB")
        print(f"   - Generated: {generated_at}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {input_json_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error updating pipeline data: {e}")
        return False

if __name__ == "__main__":
    input_json_path = "data/exports/bgg_family_games.json"
    output_js_path = "src/pipeline-data.js"
    
    # Allow custom paths as command line arguments
    if len(sys.argv) > 1:
        input_json_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_js_path = sys.argv[2]
    
    success = update_pipeline_data(input_json_path, output_js_path)
    if not success:
        sys.exit(1)
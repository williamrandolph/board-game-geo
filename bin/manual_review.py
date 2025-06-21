#!/usr/bin/env python3
"""
Manual review interface for board game geography matches.
Creates a simple web interface for approving/rejecting matches.
"""

import sqlite3
import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
import webbrowser
import threading
import time

class ReviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, db_path=None, **kwargs):
        self.db_path = db_path
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/':
            self.serve_review_interface()
        elif self.path == '/api/matches':
            self.serve_matches_data()
        elif self.path.startswith('/api/update'):
            self.handle_match_update()
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path == '/api/update':
            self.handle_match_update()
        else:
            self.send_error(404)
    
    def serve_review_interface(self):
        """Serve the manual review HTML interface."""
        html_content = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Board Game Geography - Manual Review</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .progress-bar {
            background: #e0e0e0;
            border-radius: 10px;
            height: 20px;
            margin: 10px 0;
            overflow: hidden;
        }
        
        .progress-fill {
            background: #4CAF50;
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s ease;
        }
        
        .match-card {
            background: white;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 5px solid #2196F3;
        }
        
        .match-card.approved {
            border-left-color: #4CAF50;
            opacity: 0.7;
        }
        
        .match-card.rejected {
            border-left-color: #f44336;
            opacity: 0.7;
        }
        
        .game-title {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .game-info {
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        .info-item {
            background: #f8f9fa;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 14px;
        }
        
        .location-match {
            font-size: 18px;
            color: #e74c3c;
            margin: 15px 0;
            font-weight: 500;
        }
        
        .bgg-data {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            font-size: 14px;
        }
        
        .categories, .families {
            margin: 5px 0;
        }
        
        .tag {
            display: inline-block;
            background: #e3f2fd;
            color: #1976d2;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            margin: 2px;
        }
        
        .historical {
            background: #fff3e0;
            color: #f57c00;
        }
        
        .geographical {
            background: #e8f5e8;
            color: #388e3c;
        }
        
        .actions {
            display: flex;
            gap: 15px;
            margin-top: 20px;
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .btn-approve {
            background: #4CAF50;
            color: white;
        }
        
        .btn-approve:hover {
            background: #45a049;
        }
        
        .btn-reject {
            background: #f44336;
            color: white;
        }
        
        .btn-reject:hover {
            background: #da190b;
        }
        
        .btn-skip {
            background: #9e9e9e;
            color: white;
        }
        
        .btn-skip:hover {
            background: #757575;
        }
        
        .keyboard-help {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #333;
            color: white;
            padding: 15px;
            border-radius: 8px;
            font-size: 14px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        
        .hidden {
            display: none;
        }
        
        .reasoning {
            background: #fff9c4;
            border: 1px solid #f9e79f;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗺️ Board Game Geography - Manual Review</h1>
            <div class="progress-bar">
                <div class="progress-fill" id="progressBar"></div>
            </div>
            <p id="progressText">Loading matches...</p>
        </div>
        
        <div id="matchesContainer">
            <!-- Matches will be loaded here -->
        </div>
    </div>
    
    <div class="keyboard-help">
        <strong>Keyboard Shortcuts:</strong><br>
        <kbd>A</kbd> Approve • <kbd>R</kbd> Reject • <kbd>S</kbd> Skip<br>
        <kbd>↑</kbd>/<kbd>↓</kbd> Navigate • <kbd>?</kbd> Toggle help
    </div>
    
    <script>
        let matches = [];
        let currentIndex = 0;
        let reviewed = { approved: 0, rejected: 0, skipped: 0 };
        
        // Load matches from API
        async function loadMatches() {
            try {
                const response = await fetch('/api/matches');
                matches = await response.json();
                renderMatches();
                updateProgress();
            } catch (error) {
                console.error('Error loading matches:', error);
                document.getElementById('progressText').textContent = 'Error loading matches';
            }
        }
        
        function renderMatches() {
            const container = document.getElementById('matchesContainer');
            container.innerHTML = '';
            
            matches.forEach((match, index) => {
                const card = createMatchCard(match, index);
                container.appendChild(card);
            });
            
            // Scroll to current match
            if (matches.length > 0) {
                scrollToMatch(currentIndex);
            }
        }
        
        function createMatchCard(match, index) {
            const card = document.createElement('div');
            card.className = `match-card ${match.status || ''}`;
            card.id = `match-${index}`;
            
            const categories = match.bgg_categories || [];
            const families = match.bgg_families || [];
            
            // Identify special categories
            const historicalCategories = categories.filter(cat => 
                ['ancient', 'medieval', 'renaissance'].some(hist => 
                    cat.toLowerCase().includes(hist)
                )
            );
            
            const geographicalCategories = categories.filter(cat =>
                ['economic', 'city building', 'exploration', 'travel'].some(geo =>
                    cat.toLowerCase().includes(geo)
                )
            );
            
            card.innerHTML = `
                <div class="game-title">${match.game_name}</div>
                <div class="game-info">
                    <div class="info-item">BGG Rank: #${match.rank || 'Unranked'}</div>
                    <div class="info-item">Year: ${match.year || 'Unknown'}</div>
                    <div class="info-item">Rating: ${match.rating ? match.rating.toFixed(2) : 'N/A'}</div>
                    <div class="info-item">Match Type: ${match.match_type}</div>
                    <div class="info-item">Score: ${match.match_score.toFixed(1)}</div>
                </div>
                
                <div class="location-match">
                    🎮 "${match.game_name}" → 📍 ${match.city_name}, ${match.city_country}
                    <br><small>Population: ${match.city_population ? match.city_population.toLocaleString() : 'Unknown'}</small>
                </div>
                
                ${match.reasoning ? `<div class="reasoning">🤖 AI Analysis: ${match.reasoning}</div>` : ''}
                
                <div class="bgg-data">
                    <div class="categories">
                        <strong>Categories:</strong>
                        ${categories.map(cat => {
                            const isHistorical = historicalCategories.includes(cat);
                            const isGeographical = geographicalCategories.includes(cat);
                            const className = isHistorical ? 'tag historical' : 
                                            isGeographical ? 'tag geographical' : 'tag';
                            return `<span class="${className}">${cat}</span>`;
                        }).join('')}
                    </div>
                    
                    <div class="families">
                        <strong>Families:</strong>
                        ${families.slice(0, 8).map(family => 
                            `<span class="tag">${family}</span>`
                        ).join('')}
                        ${families.length > 8 ? `<span class="tag">+${families.length - 8} more</span>` : ''}
                    </div>
                    
                    ${match.indicators && match.indicators.length > 0 ? `
                        <div style="margin-top: 10px;">
                            <strong>Geographical Indicators:</strong><br>
                            ${match.indicators.slice(0, 3).join('<br>')}
                        </div>
                    ` : ''}
                </div>
                
                <div class="actions">
                    <button class="btn btn-approve" onclick="updateMatch(${index}, 'approved')">
                        ✅ Approve (A)
                    </button>
                    <button class="btn btn-reject" onclick="updateMatch(${index}, 'rejected')">
                        ❌ Reject (R)
                    </button>
                    <button class="btn btn-skip" onclick="updateMatch(${index}, 'skipped')">
                        ⏭️ Skip (S)
                    </button>
                </div>
            `;
            
            return card;
        }
        
        async function updateMatch(index, status) {
            const match = matches[index];
            
            try {
                const response = await fetch('/api/update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        game_id: match.game_id,
                        city_id: match.city_id,
                        status: status
                    })
                });
                
                if (response.ok) {
                    // Update local state
                    const oldStatus = match.status;
                    match.status = status;
                    
                    // Update counters
                    if (oldStatus) reviewed[oldStatus]--;
                    if (!reviewed[status]) reviewed[status] = 0;
                    reviewed[status]++;
                    
                    // Update UI
                    const card = document.getElementById(`match-${index}`);
                    card.className = `match-card ${status}`;
                    
                    updateProgress();
                    
                    // Move to next unreviewed match
                    moveToNextMatch();
                } else {
                    alert('Error updating match');
                }
            } catch (error) {
                console.error('Error updating match:', error);
                alert('Error updating match');
            }
        }
        
        function moveToNextMatch() {
            // Find next unreviewed match
            for (let i = currentIndex + 1; i < matches.length; i++) {
                if (!matches[i].status) {
                    currentIndex = i;
                    scrollToMatch(i);
                    return;
                }
            }
            
            // If no more unreviewed matches after current, look from beginning
            for (let i = 0; i < currentIndex; i++) {
                if (!matches[i].status) {
                    currentIndex = i;
                    scrollToMatch(i);
                    return;
                }
            }
            
            // All matches reviewed
            alert('All matches have been reviewed! 🎉');
        }
        
        function scrollToMatch(index) {
            const card = document.getElementById(`match-${index}`);
            if (card) {
                card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                
                // Highlight current match
                document.querySelectorAll('.match-card').forEach(c => c.style.outline = '');
                card.style.outline = '3px solid #2196F3';
            }
        }
        
        function updateProgress() {
            const total = matches.length;
            const reviewedCount = reviewed.approved + reviewed.rejected + reviewed.skipped;
            const percentage = total > 0 ? (reviewedCount / total) * 100 : 0;
            
            document.getElementById('progressBar').style.width = percentage + '%';
            document.getElementById('progressText').textContent = 
                `Progress: ${reviewedCount}/${total} matches reviewed ` +
                `(${reviewed.approved} approved, ${reviewed.rejected} rejected, ${reviewed.skipped} skipped)`;
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', function(event) {
            if (matches.length === 0) return;
            
            switch(event.key.toLowerCase()) {
                case 'a':
                    event.preventDefault();
                    updateMatch(currentIndex, 'approved');
                    break;
                case 'r':
                    event.preventDefault();
                    updateMatch(currentIndex, 'rejected');
                    break;
                case 's':
                    event.preventDefault();
                    updateMatch(currentIndex, 'skipped');
                    break;
                case 'arrowup':
                    event.preventDefault();
                    if (currentIndex > 0) {
                        currentIndex--;
                        scrollToMatch(currentIndex);
                    }
                    break;
                case 'arrowdown':
                    event.preventDefault();
                    if (currentIndex < matches.length - 1) {
                        currentIndex++;
                        scrollToMatch(currentIndex);
                    }
                    break;
                case '?':
                    event.preventDefault();
                    const help = document.querySelector('.keyboard-help');
                    help.style.display = help.style.display === 'none' ? 'block' : 'none';
                    break;
            }
        });
        
        // Initialize
        loadMatches();
    </script>
</body>
</html>
        '''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def serve_matches_data(self):
        """Serve matches data as JSON."""
        try:
            matches = get_review_matches(self.db_path)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(matches).encode())
        except Exception as e:
            self.send_error(500, str(e))
    
    def handle_match_update(self):
        """Handle match status updates."""
        try:
            if self.command == 'POST':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode())
            else:
                # GET request with query parameters
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                data = {
                    'game_id': int(params['game_id'][0]),
                    'city_id': int(params['city_id'][0]),
                    'status': params['status'][0]
                }
            
            # Update database
            update_match_status(self.db_path, data['game_id'], data['city_id'], data['status'])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
        except Exception as e:
            self.send_error(500, str(e))

def get_review_matches(db_path):
    """Get matches that need manual review."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get matches that haven't been manually reviewed yet
    query = '''
        SELECT 
            m.game_id,
            m.city_id,
            g.name as game_name,
            g.rank_position as rank,
            g.year,
            g.rating,
            c.name as city_name,
            c.country_name as city_country,
            c.population as city_population,
            m.match_type,
            m.score as match_score,
            m.approved,
            '' as bgg_categories,
            '' as bgg_families,
            '' as indicators,
            '' as reasoning
        FROM matches m
        JOIN games g ON m.game_id = g.id
        JOIN cities c ON m.city_id = c.id
        WHERE m.approved IS NULL
        ORDER BY 
            CASE WHEN g.rank_position IS NULL THEN 999999 ELSE g.rank_position END,
            m.score DESC
    '''
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    matches = []
    for row in rows:
        match = {
            'game_id': row[0],
            'city_id': row[1],
            'game_name': row[2],
            'rank': row[3],
            'year': row[4],
            'rating': row[5],
            'city_name': row[6],
            'city_country': row[7],
            'city_population': row[8],
            'match_type': row[9],
            'match_score': row[10],
            'approved': row[11],
            'bgg_categories': [],
            'bgg_families': [],
            'indicators': [],
            'reasoning': ''
        }
        
        matches.append(match)
    
    conn.close()
    return matches

def update_match_status(db_path, game_id, city_id, status):
    """Update match approval status."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Convert status to approved value
    approved_value = None
    if status == 'approved':
        approved_value = 1
    elif status == 'rejected':
        approved_value = 0
    # skipped leaves it as NULL
    
    cursor.execute('''
        UPDATE matches 
        SET approved = ?, notes = ?
        WHERE game_id = ? AND city_id = ?
    ''', (approved_value, status, game_id, city_id))
    
    conn.commit()
    conn.close()

def start_review_server(db_path, port=8000):
    """Start the manual review web server."""
    
    class CustomHandler(ReviewHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, db_path=db_path, **kwargs)
    
    server = HTTPServer(('localhost', port), CustomHandler)
    
    print(f"🌐 Starting manual review server at http://localhost:{port}")
    print(f"📋 Database: {db_path}")
    
    # Count pending matches
    matches = get_review_matches(db_path)
    print(f"🎯 Found {len(matches)} matches needing review")
    
    if len(matches) == 0:
        print("✅ No matches need review!")
        return
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(1)
        webbrowser.open(f'http://localhost:{port}')
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    print("\n🚀 Manual review interface is ready!")
    print("💡 Use keyboard shortcuts: A (approve), R (reject), S (skip)")
    print("🛑 Press Ctrl+C to stop the server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down review server...")
        server.shutdown()

if __name__ == "__main__":
    # Default settings
    db_path = "data/processed/boardgames.db"
    port = 8000
    
    # Parse command line arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == "--db" and i + 1 < len(sys.argv):
            db_path = sys.argv[i + 1]
            i += 2
        elif arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
            i += 2
        elif arg in ["--help", "-h"]:
            print("Usage: python manual_review.py [options]")
            print()
            print("Options:")
            print("  --db PATH    Database path (default: data/processed/boardgames.db)")
            print("  --port PORT  Server port (default: 8000)")
            print("  --help       Show this help")
            print()
            print("The web interface will open automatically in your browser.")
            print("Use keyboard shortcuts A/R/S for quick review.")
            sys.exit(0)
        else:
            print(f"Unknown argument: {arg}")
            sys.exit(1)
    
    start_review_server(db_path, port)
#!/usr/bin/env python3
"""
Manual review interface for board game geography matches.
Creates a simple web interface for approving/rejecting matches.
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
import sqlite3
import sys
import threading
import time
import urllib.parse
import webbrowser

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
        
        .location-options {
            margin: 15px 0;
        }
        
        .city-option {
            display: flex;
            align-items: center;
            margin: 10px 0;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            background: #fafafa;
            transition: all 0.2s;
        }
        
        .city-option:hover {
            background: #f0f0f0;
            border-color: #2196F3;
        }
        
        .city-option.selected {
            background: #e3f2fd;
            border-color: #2196F3;
        }
        
        .city-option input[type="radio"] {
            margin-right: 12px;
            transform: scale(1.2);
        }
        
        .city-info {
            flex-grow: 1;
        }
        
        .city-name {
            font-size: 16px;
            font-weight: 500;
            color: #2c3e50;
        }
        
        .city-details {
            font-size: 14px;
            color: #666;
            margin-top: 4px;
        }
        
        .match-score {
            font-size: 12px;
            background: #e8f5e8;
            color: #388e3c;
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: 10px;
        }
        
        .no-match-option {
            background: #ffebee;
            border-color: #f44336;
        }
        
        .no-match-option:hover {
            background: #ffcdd2;
        }
        
        .no-match-option.selected {
            background: #ffcdd2;
            border-color: #f44336;
        }
        
        .game-description {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            font-size: 14px;
            line-height: 1.5;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .description-title {
            font-weight: bold;
            margin-bottom: 8px;
            color: #2c3e50;
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
        <kbd>1-9</kbd> Select city • <kbd>0</kbd> No match<br>
        <kbd>A</kbd> Approve • <kbd>S</kbd> Skip<br>
        <kbd>↑</kbd>/<kbd>↓</kbd> Navigate • <kbd>?</kbd> Toggle help
    </div>
    
    <script>
        let games = [];
        let currentIndex = 0;
        let reviewed = { approved: 0, rejected: 0, skipped: 0 };
        
        // Load games from API
        async function loadMatches() {
            try {
                const response = await fetch('/api/matches');
                games = await response.json();
                renderGames();
                updateProgress();
            } catch (error) {
                console.error('Error loading games:', error);
                document.getElementById('progressText').textContent = 'Error loading games';
            }
        }
        
        function renderGames() {
            const container = document.getElementById('matchesContainer');
            container.innerHTML = '';
            
            games.forEach((game, index) => {
                const card = createGameCard(game, index);
                container.appendChild(card);
            });
            
            // Scroll to current game
            if (games.length > 0) {
                scrollToGame(currentIndex);
            }
        }
        
        function createGameCard(game, index) {
            const card = document.createElement('div');
            card.className = `match-card ${game.status || ''}`;
            card.id = `game-${index}`;
            
            const categories = game.bgg_categories || [];
            const families = game.bgg_families || [];
            const mechanics = game.bgg_mechanics || [];
            
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
            
            // Create city options
            const cityOptionsHtml = game.cities.map(city => `
                <div class="city-option" onclick="selectCity(${index}, ${city.city_id})">
                    <input type="radio" name="game-${game.game_id}" value="${city.city_id}" 
                           id="city-${game.game_id}-${city.city_id}">
                    <div class="city-info">
                        <div class="city-name">${city.city_name}, ${city.city_country}</div>
                        <div class="city-details">
                            Population: ${city.city_population ? city.city_population.toLocaleString() : 'Unknown'} • 
                            ${city.match_type}
                        </div>
                    </div>
                    <div class="match-score">Score: ${city.match_score.toFixed(1)}</div>
                </div>
            `).join('');
            
            card.innerHTML = `
                <div class="game-title">${game.game_name}</div>
                <div class="game-info">
                    <div class="info-item">BGG Rank: #${game.rank || 'Unranked'}</div>
                    <div class="info-item">Year: ${game.year || 'Unknown'}</div>
                    <div class="info-item">Rating: ${game.rating ? game.rating.toFixed(2) : 'N/A'}</div>
                    <div class="info-item">BGG ID: ${game.bgg_id || 'N/A'}</div>
                </div>
                
                ${game.bgg_description ? `
                    <div class="game-description">
                        <div class="description-title">📋 Game Description</div>
                        ${game.bgg_description}
                    </div>
                ` : ''}
                
                <div class="location-options">
                    <h4>📍 Select matching city or no match:</h4>
                    ${cityOptionsHtml}
                    
                    <div class="city-option no-match-option" onclick="selectNoMatch(${index})">
                        <input type="radio" name="game-${game.game_id}" value="no-match" 
                               id="no-match-${game.game_id}">
                        <div class="city-info">
                            <div class="city-name">No geographical match</div>
                            <div class="city-details">This game does not correspond to a real-world location</div>
                        </div>
                    </div>
                </div>
                
                ${game.reasoning ? `<div class="reasoning">🤖 AI Analysis: ${game.reasoning}</div>` : ''}
                
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
                        ${categories.length === 0 ? '<span class="tag">No categories available</span>' : ''}
                    </div>
                    
                    <div class="families">
                        <strong>Families:</strong>
                        ${families.slice(0, 8).map(family => 
                            `<span class="tag">${family}</span>`
                        ).join('')}
                        ${families.length > 8 ? `<span class="tag">+${families.length - 8} more</span>` : ''}
                        ${families.length === 0 ? '<span class="tag">No families available</span>' : ''}
                    </div>
                    
                    ${mechanics.length > 0 ? `
                        <div class="mechanics" style="margin: 5px 0;">
                            <strong>Mechanics:</strong>
                            ${mechanics.slice(0, 6).map(mechanic => 
                                `<span class="tag">${mechanic}</span>`
                            ).join('')}
                            ${mechanics.length > 6 ? `<span class="tag">+${mechanics.length - 6} more</span>` : ''}
                        </div>
                    ` : ''}
                    
                    ${game.indicators && game.indicators.length > 0 ? `
                        <div style="margin-top: 10px;">
                            <strong>Geographical Indicators:</strong><br>
                            ${game.indicators.slice(0, 3).join('<br>')}
                        </div>
                    ` : ''}
                </div>
                
                <div class="actions">
                    <button class="btn btn-approve" onclick="approveGame(${index})" disabled id="approve-btn-${index}">
                        ✅ Approve Selection (A)
                    </button>
                    <button class="btn btn-skip" onclick="skipGame(${index})">
                        ⏭️ Skip (S)
                    </button>
                </div>
            `;
            
            return card;
        }
        
        // Radio button selection handlers
        function selectCity(gameIndex, cityId) {
            const radio = document.getElementById(`city-${games[gameIndex].game_id}-${cityId}`);
            radio.checked = true;
            
            // Update visual selection
            updateCitySelection(gameIndex);
            
            // Enable approve button
            document.getElementById(`approve-btn-${gameIndex}`).disabled = false;
        }
        
        function selectNoMatch(gameIndex) {
            const radio = document.getElementById(`no-match-${games[gameIndex].game_id}`);
            radio.checked = true;
            
            // Update visual selection
            updateCitySelection(gameIndex);
            
            // Enable approve button
            document.getElementById(`approve-btn-${gameIndex}`).disabled = false;
        }
        
        function updateCitySelection(gameIndex) {
            const gameId = games[gameIndex].game_id;
            const options = document.querySelectorAll(`input[name="game-${gameId}"]`);
            
            options.forEach(option => {
                const cityOption = option.closest('.city-option');
                if (option.checked) {
                    cityOption.classList.add('selected');
                } else {
                    cityOption.classList.remove('selected');
                }
            });
        }
        
        async function approveGame(index) {
            const game = games[index];
            const selectedOption = document.querySelector(`input[name="game-${game.game_id}"]:checked`);
            
            if (!selectedOption) {
                alert('Please select a city or "no match" option');
                return;
            }
            
            const selectedCityId = selectedOption.value === 'no-match' ? null : parseInt(selectedOption.value);
            const status = selectedOption.value === 'no-match' ? 'no_match' : 'approved';
            
            try {
                const response = await fetch('/api/update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        game_id: game.game_id,
                        city_id: selectedCityId,
                        status: status
                    })
                });
                
                if (response.ok) {
                    // Update local state
                    const oldStatus = game.status;
                    game.status = status;
                    game.selected_city_id = selectedCityId;
                    
                    // Update counters
                    if (oldStatus) reviewed[oldStatus]--;
                    if (!reviewed[status]) reviewed[status] = 0;
                    reviewed[status]++;
                    
                    // Update UI
                    const card = document.getElementById(`game-${index}`);
                    card.className = `match-card ${status}`;
                    
                    updateProgress();
                    
                    // Move to next unreviewed game
                    moveToNextGame();
                } else {
                    alert('Error updating game');
                }
            } catch (error) {
                console.error('Error updating game:', error);
                alert('Error updating game');
            }
        }
        
        async function skipGame(index) {
            const game = games[index];
            
            try {
                const response = await fetch('/api/update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        game_id: game.game_id,
                        city_id: null,
                        status: 'skipped'
                    })
                });
                
                if (response.ok) {
                    // Update local state
                    const oldStatus = game.status;
                    game.status = 'skipped';
                    
                    // Update counters
                    if (oldStatus) reviewed[oldStatus]--;
                    if (!reviewed.skipped) reviewed.skipped = 0;
                    reviewed.skipped++;
                    
                    // Update UI
                    const card = document.getElementById(`game-${index}`);
                    card.className = 'match-card skipped';
                    
                    updateProgress();
                    
                    // Move to next unreviewed game
                    moveToNextGame();
                } else {
                    alert('Error skipping game');
                }
            } catch (error) {
                console.error('Error skipping game:', error);
                alert('Error skipping game');
            }
        }
        
        function moveToNextGame() {
            // Find next unreviewed game
            for (let i = currentIndex + 1; i < games.length; i++) {
                if (!games[i].status) {
                    currentIndex = i;
                    scrollToGame(i);
                    return;
                }
            }
            
            // If no more unreviewed games after current, look from beginning
            for (let i = 0; i < currentIndex; i++) {
                if (!games[i].status) {
                    currentIndex = i;
                    scrollToGame(i);
                    return;
                }
            }
            
            // All games reviewed
            alert('All games have been reviewed! 🎉');
        }
        
        function scrollToGame(index) {
            const card = document.getElementById(`game-${index}`);
            if (card) {
                card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                
                // Highlight current game
                document.querySelectorAll('.match-card').forEach(c => c.style.outline = '');
                card.style.outline = '3px solid #2196F3';
            }
        }
        
        function updateProgress() {
            const total = games.length;
            const reviewedCount = (reviewed.approved || 0) + (reviewed.no_match || 0) + (reviewed.skipped || 0);
            const percentage = total > 0 ? (reviewedCount / total) * 100 : 0;
            
            document.getElementById('progressBar').style.width = percentage + '%';
            document.getElementById('progressText').textContent = 
                `Progress: ${reviewedCount}/${total} games reviewed ` +
                `(${reviewed.approved || 0} approved, ${reviewed.no_match || 0} no match, ${reviewed.skipped || 0} skipped)`;
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', function(event) {
            if (games.length === 0) return;
            
            switch(event.key.toLowerCase()) {
                case 'a':
                    event.preventDefault();
                    approveGame(currentIndex);
                    break;
                case 's':
                    event.preventDefault();
                    skipGame(currentIndex);
                    break;
                case '1':
                case '2':
                case '3':
                case '4':
                case '5':
                case '6':
                case '7':
                case '8':
                case '9':
                    event.preventDefault();
                    const optionIndex = parseInt(event.key) - 1;
                    const game = games[currentIndex];
                    if (game && game.cities && optionIndex < game.cities.length) {
                        selectCity(currentIndex, game.cities[optionIndex].city_id);
                    }
                    break;
                case '0':
                    event.preventDefault();
                    selectNoMatch(currentIndex);
                    break;
                case 'arrowup':
                    event.preventDefault();
                    if (currentIndex > 0) {
                        currentIndex--;
                        scrollToGame(currentIndex);
                    }
                    break;
                case 'arrowdown':
                    event.preventDefault();
                    if (currentIndex < games.length - 1) {
                        currentIndex++;
                        scrollToGame(currentIndex);
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
            games = get_review_matches(self.db_path)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(games).encode())
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
                    'city_id': int(params.get('city_id', [None])[0]) if params.get('city_id', [None])[0] else None,
                    'status': params['status'][0]
                }
            
            # Update database using new game-based approach
            selected_city_id = data.get('city_id')
            if selected_city_id:
                selected_city_id = int(selected_city_id)
            
            update_game_match_status(self.db_path, data['game_id'], selected_city_id, data['status'])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
        except Exception as e:
            self.send_error(500, str(e))

def get_review_matches(db_path):
    """Get games with their potential city matches for manual review."""
    import os
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get games that have unreviewed matches, grouped by game
    query = '''
        SELECT DISTINCT
            g.id as game_id,
            g.name as game_name,
            g.bgg_id,
            g.rank_position as rank,
            g.year,
            g.rating
        FROM matches m
        JOIN games g ON m.game_id = g.id
        WHERE m.approved IS NULL
        ORDER BY 
            CASE WHEN g.rank_position IS NULL THEN 999999 ELSE g.rank_position END
    '''
    
    cursor.execute(query)
    game_rows = cursor.fetchall()
    
    games = []
    cache_dir = os.path.join(os.path.dirname(db_path), '..', '..', 'data', 'cache', 'bgg')
    
    for game_row in game_rows:
        game_id, game_name, bgg_id, rank, year, rating = game_row
        
        # Get all potential cities for this game
        city_query = '''
            SELECT 
                m.city_id,
                c.name as city_name,
                c.country_name as city_country,
                c.population as city_population,
                m.match_type,
                m.score as match_score,
                m.approved
            FROM matches m
            JOIN cities c ON m.city_id = c.id
            WHERE m.game_id = ? AND m.approved IS NULL
            ORDER BY m.score DESC
        '''
        
        cursor.execute(city_query, (game_id,))
        city_rows = cursor.fetchall()
        
        cities = []
        for city_row in city_rows:
            city_id, city_name, city_country, city_population, match_type, match_score, approved = city_row
            cities.append({
                'city_id': city_id,
                'city_name': city_name,
                'city_country': city_country,
                'city_population': city_population,
                'match_type': match_type,
                'match_score': match_score,
                'approved': approved
            })
        
        # Load BGG cache data if available
        bgg_data = load_bgg_cache_data(cache_dir, bgg_id)
        
        game = {
            'game_id': game_id,
            'game_name': game_name,
            'bgg_id': bgg_id,
            'rank': rank,
            'year': year,
            'rating': rating,
            'cities': cities,
            'bgg_description': bgg_data.get('description', ''),
            'bgg_categories': bgg_data.get('categories', []),
            'bgg_families': bgg_data.get('families', []),
            'bgg_mechanics': bgg_data.get('mechanics', []),
            'indicators': bgg_data.get('indicators', []),
            'reasoning': bgg_data.get('reasoning', '')
        }
        
        games.append(game)
    
    conn.close()
    return games

def load_bgg_cache_data(cache_dir, bgg_id):
    """Load BGG cache data for a game."""
    if not bgg_id:
        return {}
    
    cache_file = os.path.join(cache_dir, f'game_{bgg_id}.json')
    if not os.path.exists(cache_file):
        return {}
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except (json.JSONDecodeError, IOError):
        return {}

def update_game_match_status(db_path, game_id, selected_city_id, status):
    """Update match approval status for a game - approve one city, reject others."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if status == 'approved' and selected_city_id:
        # Approve the selected city
        cursor.execute('''
            UPDATE matches 
            SET approved = 1, notes = 'approved'
            WHERE game_id = ? AND city_id = ?
        ''', (game_id, selected_city_id))
        
        # Reject all other cities for this game
        cursor.execute('''
            UPDATE matches 
            SET approved = 0, notes = 'rejected_other_city_selected'
            WHERE game_id = ? AND city_id != ?
        ''', (game_id, selected_city_id))
        
    elif status == 'no_match':
        # Reject all cities for this game
        cursor.execute('''
            UPDATE matches 
            SET approved = 0, notes = 'no_match'
            WHERE game_id = ?
        ''', (game_id,))
        
    elif status == 'skipped':
        # Leave all matches as NULL (unreviewed) but add skip note
        cursor.execute('''
            UPDATE matches 
            SET notes = 'skipped'
            WHERE game_id = ?
        ''', (game_id,))
    
    conn.commit()
    conn.close()

def update_match_status(db_path, game_id, city_id, status):
    """Legacy function for backward compatibility."""
    # This is kept for any existing calls, but the new interface uses update_game_match_status
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
    
    # Count pending games
    games = get_review_matches(db_path)
    print(f"🎯 Found {len(games)} games needing review")
    
    if len(games) == 0:
        print("✅ No games need review!")
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
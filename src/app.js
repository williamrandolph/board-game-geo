// Global application state
let database;
let importSystem;
let adminTools;
let isImporting = false;

// Initialize map
let map;
let markers = [];
let markerGroup;

// Initialize all systems
async function initSystems() {
    try {
        database = new GameDatabase();
        await database.init();
        
        importSystem = new BulkImportSystem();
        await importSystem.init();
        
        adminTools = new AdminTools();
        await adminTools.init();
        
        console.log('✅ All systems initialized');
        await updateStats();
        
    } catch (error) {
        console.error('❌ System initialization failed:', error);
        showError('Failed to initialize systems: ' + error.message);
    }
}

// Initialize the map
function initMap() {
    map = L.map('map').setView([45.0, 10.0], 4);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
}

// Add marker to map from database game
function addGameMarker(game, location) {
    const marker = L.marker([location.lat, location.lng]);
    
    const popupContent = `
        <div class="popup-content">
            <h3>${game.name}</h3>
            <p><strong>Year:</strong> ${game.yearPublished || 'Unknown'}</p>
            <p><strong>Location:</strong> ${location.locationString}</p>
            <p><strong>Type:</strong> ${location.type}</p>
            <p><strong>Confidence:</strong> ${(location.confidence * 100).toFixed(0)}%</p>
            <p><strong>Rating:</strong> ${game.rating?.average ? game.rating.average.toFixed(1) : 'Unrated'}</p>
            ${game.description ? `<p><em>${game.description.substring(0, 100)}...</em></p>` : ''}
        </div>
    `;
    
    marker.bindPopup(popupContent);
    markers.push(marker);
    
    if (markerGroup) {
        markerGroup.addLayer(marker);
    } else {
        marker.addTo(map);
    }
}

// Load games from database and display on map
async function loadGamesFromDatabase() {
    const loading = document.getElementById('loading');
    const loadingDetails = document.getElementById('loading-details');
    
    try {
        loadingDetails.textContent = 'Loading games from database...';
        
        const games = await database.getAllGamesWithLocations();
        
        if (games.length === 0) {
            loadingDetails.textContent = 'No games found. Import some games to get started!';
            setTimeout(() => {
                loading.style.display = 'none';
            }, 2000);
            return;
        }
        
        // Clear existing markers
        clearMarkers();
        
        // Create marker group for better performance
        markerGroup = L.featureGroup();
        
        let totalLocations = 0;
        games.forEach(game => {
            game.locations.forEach(location => {
                addGameMarker(game, location);
                totalLocations++;
            });
        });
        
        // Add marker group to map
        markerGroup.addTo(map);
        
        // Fit map to show all markers
        if (totalLocations > 0) {
            map.fitBounds(markerGroup.getBounds().pad(0.1));
        }
        
        console.log(`✅ Loaded ${games.length} games with ${totalLocations} locations`);
        
    } catch (error) {
        console.error('Error loading games:', error);
        loadingDetails.textContent = 'Error loading games: ' + error.message;
    } finally {
        setTimeout(() => {
            loading.style.display = 'none';
        }, 1000);
    }
}

// Clear all markers from map
function clearMarkers() {
    if (markerGroup) {
        map.removeLayer(markerGroup);
        markerGroup = null;
    }
    markers.forEach(marker => {
        if (map.hasLayer(marker)) {
            map.removeLayer(marker);
        }
    });
    markers = [];
}

// Update stats display
async function updateStats() {
    try {
        const stats = await database.getStats();
        const statsDiv = document.getElementById('stats');
        
        statsDiv.innerHTML = `
            <div>Games: ${stats.games}</div>
            <div>Locations: ${stats.locations}</div>
            <div>Games with locations: ${stats.gamesWithLocations}</div>
        `;
    } catch (error) {
        console.error('Error updating stats:', error);
    }
}

// Import popular games
async function importPopularGames() {
    if (isImporting) return;
    
    const button = document.getElementById('import-popular');
    const progress = document.getElementById('progress');
    
    try {
        isImporting = true;
        button.disabled = true;
        progress.style.display = 'block';
        
        const options = {
            batchSize: 5,
            delayBetweenBatches: 3000,
            onProgress: (status) => {
                const progressElement = document.getElementById('progress-text');
                if (progressElement) {
                    progressElement.textContent = `Processing ${status.currentGameId}... (${status.processed}/${status.total})`;
                }
            },
            onError: (error) => {
                console.warn('Import error:', error);
            }
        };
        
        const result = await importSystem.importTopGames(20, options);
        
        showSuccess(`Import completed! ${result.successful} games imported, ${result.failed} failed.`);
        
        // Refresh the map
        await loadGamesFromDatabase();
        await updateStats();
        
    } catch (error) {
        console.error('Import failed:', error);
        showError('Import failed: ' + error.message);
    } finally {
        isImporting = false;
        button.disabled = false;
        progress.style.display = 'none';
    }
}

// Import specific game
async function importSpecificGame() {
    const gameName = prompt('Enter game name to search for:');
    if (!gameName) return;
    
    if (isImporting) return;
    
    const button = document.getElementById('import-specific');
    const progress = document.getElementById('progress');
    
    try {
        isImporting = true;
        button.disabled = true;
        progress.style.display = 'block';
        
        const progressElement = document.getElementById('progress-text');
        if (progressElement) {
            progressElement.textContent = `Searching for "${gameName}"...`;
        }
        
        const options = {
            batchSize: 3,
            delayBetweenBatches: 2000,
            onProgress: (status) => {
                const progressElement = document.getElementById('progress-text');
                if (progressElement) {
                    progressElement.textContent = `Processing ${status.currentGameId}... (${status.processed}/${status.total})`;
                }
            }
        };
        
        const result = await importSystem.searchAndImportGames(gameName, 10, options);
        
        showSuccess(`Import completed! ${result.successful} games imported, ${result.failed} failed.`);
        
        // Refresh the map
        await loadGamesFromDatabase();
        await updateStats();
        
    } catch (error) {
        console.error('Import failed:', error);
        showError('Import failed: ' + error.message);
    } finally {
        isImporting = false;
        button.disabled = false;
        progress.style.display = 'none';
    }
}

// Clear all data
async function clearAllData() {
    if (!confirm('Are you sure you want to clear all data? This cannot be undone.')) {
        return;
    }
    
    try {
        await database.clearAllData();
        clearMarkers();
        await updateStats();
        showSuccess('All data cleared.');
    } catch (error) {
        console.error('Error clearing data:', error);
        showError('Error clearing data: ' + error.message);
    }
}

// Export data
async function exportData() {
    try {
        const data = await adminTools.exportData('json');
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `board-game-geo-export-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        
        URL.revokeObjectURL(url);
        showSuccess('Data exported successfully.');
    } catch (error) {
        console.error('Export failed:', error);
        showError('Export failed: ' + error.message);
    }
}

// Show success message
function showSuccess(message) {
    const progress = document.getElementById('progress');
    progress.style.display = 'block';
    progress.innerHTML = `<div class="success">✅ ${message}</div>`;
    setTimeout(() => {
        progress.style.display = 'none';
    }, 3000);
}

// Show error message
function showError(message) {
    const progress = document.getElementById('progress');
    progress.style.display = 'block';
    progress.innerHTML = `<div class="error">❌ ${message}</div>`;
    setTimeout(() => {
        progress.style.display = 'none';
    }, 5000);
}

// Run parsing tests
function runTests() {
    console.clear();
    try {
        const results = runAllBGGTests();
        if (results.failed === 0) {
            showSuccess(`All ${results.passed} parsing tests passed! Check console for details.`);
        } else {
            showError(`${results.failed} tests failed. Check console for details.`);
        }
    } catch (error) {
        console.error('Test execution failed:', error);
        showError('Test execution failed: ' + error.message);
    }
}

// Initialize everything when page loads
document.addEventListener('DOMContentLoaded', async function() {
    initMap();
    await initSystems();
    await loadGamesFromDatabase();
});
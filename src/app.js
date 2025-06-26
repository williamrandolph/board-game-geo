// Global application state
let database;
let pipelineLoader;
let isImporting = false;

// Filter state
let currentFilters = {
    topN: 'all', // 'all', '50', '100', '250'
    categories: []
};

// Update filters from UI controls
function updateFilters() {
    const topNSelect = document.getElementById('top-n-select');
    const categorySelect = document.getElementById('category-select');
    
    currentFilters.topN = topNSelect.value;
    
    // Get selected categories
    const selectedCategories = Array.from(categorySelect.selectedOptions).map(option => option.value);
    currentFilters.categories = selectedCategories;
    
    console.log('🔄 Filters updated:', currentFilters);
    
    // Reload the map with new filters
    loadGamesFromDatabase();
}

// Initialize map
let map;
let markers = [];
let markerClusterGroup;

// Initialize all systems
async function initSystems() {
    try {
        database = new GameDatabase();
        await database.init();
        
        pipelineLoader = new PipelineLoader(database);
        
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
    
    // Initialize marker cluster group
    markerClusterGroup = L.markerClusterGroup({
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        maxClusterRadius: 50,
        iconCreateFunction: function(cluster) {
            const childCount = cluster.getChildCount();
            let c = ' marker-cluster-';
            if (childCount < 10) {
                c += 'small';
            } else if (childCount < 100) {
                c += 'medium';
            } else {
                c += 'large';
            }
            return new L.DivIcon({ 
                html: '<div><span>' + childCount + '</span></div>', 
                className: 'marker-cluster' + c, 
                iconSize: new L.Point(40, 40) 
            });
        }
    });
    
    map.addLayer(markerClusterGroup);
}

// Apply filters to games list
function applyFilters(games) {
    let filteredGames = [...games];
    
    // Apply BGG ranking filter first
    if (currentFilters.topN !== 'all') {
        const rankLimit = parseInt(currentFilters.topN);
        filteredGames = filteredGames.filter(game => {
            // Check if game has BGG rank data (from CSV)
            const bggRank = game.bggRank || game.rank;
            return bggRank && bggRank <= rankLimit;
        });
    }
    
    // Apply category filter
    if (currentFilters.categories.length > 0) {
        filteredGames = filteredGames.filter(game => {
            const gameCategories = game.categories || [];
            // Show game if it has ANY of the selected categories
            return currentFilters.categories.some(selectedCategory => 
                gameCategories.includes(selectedCategory)
            );
        });
    }
    
    // Sort by BGG rank ascending (lower rank number = higher position)
    filteredGames.sort((a, b) => {
        const rankA = a.bggRank || a.rank || 999999;
        const rankB = b.bggRank || b.rank || 999999;
        return rankA - rankB;
    });
    
    return filteredGames;
}

// Add marker to map from database game
function addGameMarker(game, location) {
    // Create different icons for pipeline vs real-time data
    const isPipelineData = game.source === 'pipeline';
    const isApproved = location.approved === true;
    
    let iconUrl = 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png';
    let iconLabel = '🎮';
    
    if (isPipelineData) {
        if (isApproved) {
            iconUrl = 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png';
            iconLabel = '✅';
        } else {
            iconUrl = 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-orange.png';
            iconLabel = '⚠️';
        }
    }
    
    const customIcon = L.icon({
        iconUrl: iconUrl,
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });
    
    const marker = L.marker([location.lat, location.lng], { icon: customIcon });
    
    const dataSource = isPipelineData ? 'Pipeline Data' : 'Real-time Import';
    const approvalStatus = isPipelineData ? 
        (isApproved ? 'Approved' : 'Pending/Rejected') : 
        'N/A';
    
    const bggId = game.id || (game.name && game.yearPublished ? `${game.name.replace(/\s+/g, '-').toLowerCase()}-${game.yearPublished}` : null);
    const bggLink = bggId ? `https://boardgamegeek.com/boardgame/${bggId}` : null;
    
    const popupContent = `
        <div class="popup-content">
            <h3>${bggLink ? `<a href="${bggLink}" target="_blank" rel="noopener">${game.name}</a>` : game.name} ${iconLabel}</h3>
            <p><strong>Year:</strong> ${game.yearPublished || 'Unknown'}</p>
            <p><strong>Location:</strong> ${location.locationString}</p>
            <p><strong>Type:</strong> ${location.type}</p>
            <p><strong>Confidence:</strong> ${(location.confidence * 100).toFixed(0)}%</p>
            <p><strong>Rating:</strong> ${game.rating?.average ? game.rating.average.toFixed(1) : 'Unrated'}</p>
            <p><strong>Source:</strong> ${dataSource}</p>
            ${isPipelineData ? `<p><strong>Status:</strong> ${approvalStatus}</p>` : ''}
            ${isPipelineData && location.matchType ? `<p><strong>Match Type:</strong> ${location.matchType}</p>` : ''}
            ${isPipelineData && location.score ? `<p><strong>Score:</strong> ${location.score.toFixed(1)}</p>` : ''}
            ${game.description ? `<p><em>${game.description.substring(0, 100)}...</em></p>` : ''}
        </div>
    `;
    
    marker.bindPopup(popupContent);
    markers.push(marker);
    
    // Add marker to cluster group
    markerClusterGroup.addLayer(marker);
}

// Update stats display with filter information
function updateFilterStats(totalGames, filteredGames, totalLocations) {
    const statsDiv = document.getElementById('stats');
    
    let statsText = `Games: ${filteredGames}`;
    if (filteredGames !== totalGames) {
        statsText += ` of ${totalGames}`;
    }
    statsText += `<br>Locations: ${totalLocations}`;
    
    const filters = [];
    if (currentFilters.topN !== 'all') {
        filters.push(`BGG Top ${currentFilters.topN}`);
    }
    if (currentFilters.categories.length > 0) {
        const categoryText = currentFilters.categories.length === 1 
            ? currentFilters.categories[0] 
            : `${currentFilters.categories.length} categories`;
        filters.push(categoryText);
    }
    
    if (filters.length > 0) {
        statsText += `<br>Filters: ${filters.join(', ')}`;
    }
    
    statsDiv.innerHTML = statsText;
}

// Load games from database and display on map
async function loadGamesFromDatabase() {
    const loading = document.getElementById('loading');
    const loadingDetails = document.getElementById('loading-details');
    
    try {
        loadingDetails.textContent = 'Loading games from database...';
        
        const allGames = await database.getAllGamesWithLocations();
        
        if (allGames.length === 0) {
            loadingDetails.textContent = 'No games found. Loading pipeline data...';
            setTimeout(() => {
                loading.style.display = 'none';
            }, 2000);
            return;
        }
        
        // Apply current filters
        const filteredGames = applyFilters(allGames);
        
        // Clear existing markers
        clearMarkers();
        
        let totalLocations = 0;
        filteredGames.forEach(game => {
            game.locations.forEach(location => {
                addGameMarker(game, location);
                totalLocations++;
            });
        });
        
        // Fit map to show all markers
        if (totalLocations > 0 && markers.length > 0) {
            const group = new L.featureGroup(markers);
            map.fitBounds(group.getBounds().pad(0.1));
        }
        
        console.log(`✅ Loaded ${filteredGames.length}/${allGames.length} games with ${totalLocations} locations`);
        
        // Update stats to show filtered results
        updateFilterStats(allGames.length, filteredGames.length, totalLocations);
        
        // Populate category filter dropdown (only if not already populated)
        const categorySelect = document.getElementById('category-select');
        if (categorySelect.options.length === 0) {
            populateCategoryFilter(allGames);
        }
        
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
    if (markerClusterGroup) {
        markerClusterGroup.clearLayers();
    }
    markers = [];
}

// Populate category filter dropdown with available categories
function populateCategoryFilter(games) {
    const categorySelect = document.getElementById('category-select');
    
    // Count category occurrences
    const categoryCount = {};
    games.forEach(game => {
        if (game.categories) {
            game.categories.forEach(category => {
                categoryCount[category] = (categoryCount[category] || 0) + 1;
            });
        }
    });
    
    // Filter categories with at least 20 games and sort by count (descending)
    const significantCategories = Object.entries(categoryCount)
        .filter(([category, count]) => count >= 20)
        .sort((a, b) => b[1] - a[1]); // Sort by count descending
    
    // Clear existing options
    categorySelect.innerHTML = '';
    
    // Add options for each significant category with counts
    significantCategories.forEach(([category, count]) => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = `${category} (${count})`;
        categorySelect.appendChild(option);
    });
    
    console.log(`📋 Populated ${significantCategories.length} categories (20+ games) in filter dropdown`);
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

// Load pipeline data (approved games only)
async function loadPipelineData() {
    if (isImporting) return;
    
    if (!confirm('This will clear existing data and load approved games from the pipeline. Continue?')) {
        return;
    }
    
    const button = document.getElementById('load-pipeline');
    const progress = document.getElementById('progress');
    
    try {
        isImporting = true;
        button.disabled = true;
        progress.style.display = 'block';
        
        // Reset progress element to have the text div
        progress.innerHTML = '<div id="progress-text">Loading pipeline data...</div>';
        
        const result = await pipelineLoader.loadDefaultData((status) => {
            const progressElement = document.getElementById('progress-text');
            if (progressElement) {
                progressElement.textContent = `Loading ${status.game}... (${status.current}/${status.total})`;
            }
        });
        
        showSuccess(`Pipeline data loaded! ${result.successful} approved games loaded.`);
        console.log('📊 Pipeline load results:', result);
        
        // Refresh the map
        await loadGamesFromDatabase();
        await updateStats();
        
    } catch (error) {
        console.error('Pipeline loading failed:', error);
        showError('Pipeline loading failed: ' + error.message);
    } finally {
        isImporting = false;
        button.disabled = false;
        progress.style.display = 'none';
    }
}


// Auto-load pipeline data on first visit
async function autoLoadPipelineData() {
    try {
        const stats = await database.getStats();
        
        // If no games in database, auto-load pipeline data
        if (stats.games === 0) {
            console.log('🔄 Auto-loading pipeline data on first visit...');
            const result = await pipelineLoader.loadDefaultData();
            console.log('📊 Auto-load completed:', result);
        }
    } catch (error) {
        console.error('Auto-load failed:', error);
    }
}

// Initialize everything when page loads
document.addEventListener('DOMContentLoaded', async function() {
    initMap();
    await initSystems();
    await autoLoadPipelineData();
    await loadGamesFromDatabase();
});
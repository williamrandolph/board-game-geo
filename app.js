// Board game data with locations
const boardGames = [
    {
        name: "Carcassonne",
        location: "Carcassonne, France",
        description: "Medieval fortress city tile-laying game"
    },
    {
        name: "Ticket to Ride",
        location: "United States",
        description: "Cross-country train adventure"
    },
    {
        name: "Santorini",
        location: "Santorini, Greece", 
        description: "Greek island building strategy game"
    },
    {
        name: "Pandemic",
        location: "Atlanta, Georgia, USA",
        description: "Global disease outbreak cooperative game"
    },
    {
        name: "King of Tokyo",
        location: "Tokyo, Japan",
        description: "Monster battle dice game"
    },
    {
        name: "Splendor",
        location: "Renaissance Europe",
        description: "Gem trading in the Renaissance"
    },
    {
        name: "Azul",
        location: "Portugal",
        description: "Portuguese tile-laying art game"
    }
];

// Initialize map
let map;
let markers = [];

// Geocoding function using Nominatim
async function geocodeLocation(location) {
    try {
        const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(location)}&limit=1`);
        const data = await response.json();
        
        if (data && data.length > 0) {
            return {
                lat: parseFloat(data[0].lat),
                lng: parseFloat(data[0].lon)
            };
        }
        return null;
    } catch (error) {
        console.error('Geocoding error:', error);
        return null;
    }
}

// Add delay to respect Nominatim rate limits
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Initialize the map
function initMap() {
    map = L.map('map').setView([45.0, 10.0], 4);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
}

// Add marker to map
function addMarker(game, coordinates) {
    const marker = L.marker([coordinates.lat, coordinates.lng]).addTo(map);
    
    const popupContent = `
        <div class="popup-content">
            <h3>${game.name}</h3>
            <p><strong>Location:</strong> ${game.location}</p>
            <p>${game.description}</p>
        </div>
    `;
    
    marker.bindPopup(popupContent);
    markers.push(marker);
}

// Load all game locations
async function loadGameLocations() {
    const loading = document.getElementById('loading');
    
    for (let i = 0; i < boardGames.length; i++) {
        const game = boardGames[i];
        loading.textContent = `Loading ${game.name}... (${i + 1}/${boardGames.length})`;
        
        const coordinates = await geocodeLocation(game.location);
        
        if (coordinates) {
            addMarker(game, coordinates);
        } else {
            console.warn(`Could not geocode location for ${game.name}: ${game.location}`);
        }
        
        // Rate limiting: wait 1 second between requests
        if (i < boardGames.length - 1) {
            await delay(1000);
        }
    }
    
    // Hide loading indicator
    loading.style.display = 'none';
    
    // Fit map to show all markers
    if (markers.length > 0) {
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

// Initialize everything when page loads
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    loadGameLocations();
});
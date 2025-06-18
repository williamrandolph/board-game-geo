# Board Game Geography

An interactive map showing the real-world locations associated with board games. Explore where your favorite games are set!

## Features

- Interactive world map using Leaflet.js and OpenStreetMap
- Automatic geocoding of game locations using Nominatim
- Clickable markers with game information
- Responsive design for desktop and mobile

## Getting Started

1. Clone the repository
2. Open `index.html` in your web browser
3. Wait for locations to load (respects rate limits)
4. Click markers to see game details

## Current Games

- Carcassonne → Carcassonne, France
- Ticket to Ride → United States
- Santorini → Santorini, Greece
- Pandemic → Atlanta, Georgia, USA
- King of Tokyo → Tokyo, Japan
- Splendor → Renaissance Europe
- Azul → Portugal

## Todo List

### Phase 1: Core Features
- [x] Basic map with Leaflet.js integration
- [x] Sample board game data
- [x] Nominatim geocoding implementation
- [x] Interactive map markers
- [x] Responsive styling

### Phase 2: Data Integration
- [ ] BoardGameGeek API integration
- [ ] Automated game data scraping
- [ ] Game location research and validation
- [ ] Database setup for game storage
- [ ] Bulk geocoding with caching

### Phase 3: Enhanced Features
- [ ] Search functionality for games
- [ ] Filter by game mechanics/genres
- [ ] Game detail pages with BGG links
- [ ] User favorites and collections
- [ ] Mobile app development

### Phase 4: Advanced Features
- [ ] Historical game location accuracy
- [ ] Multiple locations per game support
- [ ] Game route visualization (e.g., Ticket to Ride routes)
- [ ] Community contributions for locations
- [ ] Location photos and descriptions

### Phase 5: Scaling
- [ ] Performance optimization for large datasets
- [ ] CDN integration for global access
- [ ] Offline map support
- [ ] Analytics and usage tracking
- [ ] Internationalization support

## Tech Stack

- **Frontend**: HTML, CSS, JavaScript
- **Maps**: Leaflet.js with OpenStreetMap tiles
- **Geocoding**: Nominatim API (free)
- **Data Source**: BoardGameGeek API
- **Hosting**: Static site (Netlify/Vercel/GitHub Pages)

## Contributing

Feel free to suggest games, report location inaccuracies, or contribute code improvements!

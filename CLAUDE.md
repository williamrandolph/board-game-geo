# Board Game Geography - Project Instructions

## Project Overview
This is an interactive map application that displays real-world locations associated with board games. Users can explore where their favorite games are set by clicking on map markers.

## Current Architecture
- **Frontend**: Vanilla HTML, CSS, JavaScript
- **Map Library**: Leaflet.js with OpenStreetMap tiles
- **Geocoding**: Nominatim API (free, 1 req/sec limit)
- **Data**: Static JSON array in app.js
- **Hosting**: Static files (can be served from any web server)

## Key Files
- `index.html` - Main application page with Leaflet integration
- `app.js` - Core application logic, game data, and geocoding
- `README.md` - Project documentation and roadmap

## Development Guidelines

### Code Style
- Use vanilla JavaScript (no frameworks currently)
- Maintain rate limiting for Nominatim API (1 second between requests)
- Keep responsive design principles
- Use semantic HTML and accessible design

### Adding New Games
When adding games to the `boardGames` array in `app.js`:
1. Use specific, geocodable location names
2. Provide descriptive game information
3. Test geocoding accuracy manually
4. Consider historical accuracy of locations

### API Rate Limits
- Nominatim: 1 request per second maximum
- Always include proper attribution for OpenStreetMap
- Consider caching geocoded results for production

### Future Development Priorities
1. **Phase 2**: BoardGameGeek API integration
2. **Phase 3**: Search and filtering capabilities  
3. **Phase 4**: Multiple locations per game
4. **Phase 5**: Performance optimization and scaling

## Testing
- Test in multiple browsers (Chrome, Firefox, Safari)
- Verify mobile responsiveness
- Check geocoding accuracy for new locations
- Ensure rate limiting is respected

## Deployment
- Static site hosting (Netlify, Vercel, GitHub Pages)
- No backend required for current version
- CDN recommended for production (Phase 5)

## Known Limitations
- Rate limited by Nominatim (7 games take ~7 seconds to load)
- No offline support currently
- Limited to publicly geocodable locations
- No user data persistence

## Contributing
- Follow existing code patterns
- Test geocoding before submitting new games
- Update README.md todo list when completing features
- Consider performance impact of new features
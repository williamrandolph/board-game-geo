class BGGApi {
    constructor() {
        this.baseUrl = 'https://boardgamegeek.com/xmlapi2';
        this.rateLimitDelay = 500; // 500ms between requests (2 req/sec)
        this.lastRequestTime = 0;
    }

    async enforceRateLimit() {
        const now = Date.now();
        const timeSinceLastRequest = now - this.lastRequestTime;
        
        if (timeSinceLastRequest < this.rateLimitDelay) {
            const waitTime = this.rateLimitDelay - timeSinceLastRequest;
            await new Promise(resolve => setTimeout(resolve, waitTime));
        }
        
        this.lastRequestTime = Date.now();
    }

    async fetchXML(url) {
        await this.enforceRateLimit();
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const xmlText = await response.text();
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
            
            // Check for BGG API errors
            const errors = xmlDoc.querySelectorAll('error');
            if (errors.length > 0) {
                throw new Error(`BGG API Error: ${errors[0].getAttribute('message')}`);
            }
            
            return xmlDoc;
        } catch (error) {
            console.error('BGG API request failed:', error);
            throw error;
        }
    }

    async searchGames(query, exact = false) {
        const searchType = exact ? 'boardgame' : 'boardgame,boardgameexpansion';
        const url = `${this.baseUrl}/search?query=${encodeURIComponent(query)}&type=${searchType}`;
        
        const xmlDoc = await this.fetchXML(url);
        const items = xmlDoc.querySelectorAll('item');
        
        return Array.from(items).map(item => ({
            id: parseInt(item.getAttribute('id')),
            name: item.querySelector('name').getAttribute('value'),
            yearPublished: item.querySelector('yearpublished')?.getAttribute('value') || null
        }));
    }

    async getGameDetails(gameId) {
        const url = `${this.baseUrl}/thing?id=${gameId}&stats=1`;
        
        const xmlDoc = await this.fetchXML(url);
        const item = xmlDoc.querySelector('item');
        
        if (!item) {
            throw new Error(`Game with ID ${gameId} not found`);
        }

        return {
            id: parseInt(item.getAttribute('id')),
            name: this.getPrimaryName(item),
            yearPublished: item.querySelector('yearpublished')?.getAttribute('value') || null,
            description: item.querySelector('description')?.textContent || '',
            minPlayers: parseInt(item.querySelector('minplayers')?.getAttribute('value')) || null,
            maxPlayers: parseInt(item.querySelector('maxplayers')?.getAttribute('value')) || null,
            playingTime: parseInt(item.querySelector('playingtime')?.getAttribute('value')) || null,
            families: this.extractFamilies(item),
            categories: this.extractCategories(item),
            mechanics: this.extractMechanics(item),
            rating: this.extractRating(item)
        };
    }

    getPrimaryName(item) {
        const names = item.querySelectorAll('name');
        const primaryName = Array.from(names).find(name => 
            name.getAttribute('type') === 'primary'
        );
        return primaryName ? primaryName.getAttribute('value') : names[0]?.getAttribute('value');
    }

    extractFamilies(item) {
        const familyLinks = item.querySelectorAll('link[type="boardgamefamily"]');
        return Array.from(familyLinks).map(link => ({
            id: parseInt(link.getAttribute('id')),
            name: link.getAttribute('value')
        }));
    }

    extractCategories(item) {
        const categoryLinks = item.querySelectorAll('link[type="boardgamecategory"]');
        return Array.from(categoryLinks).map(link => ({
            id: parseInt(link.getAttribute('id')),
            name: link.getAttribute('value')
        }));
    }

    extractMechanics(item) {
        const mechanicLinks = item.querySelectorAll('link[type="boardgamemechanic"]');
        return Array.from(mechanicLinks).map(link => ({
            id: parseInt(link.getAttribute('id')),
            name: link.getAttribute('value')
        }));
    }

    extractRating(item) {
        const statistics = item.querySelector('statistics ratings');
        if (!statistics) return null;

        return {
            average: parseFloat(statistics.querySelector('average')?.getAttribute('value')) || null,
            usersRated: parseInt(statistics.querySelector('usersrated')?.getAttribute('value')) || null,
            rank: parseInt(statistics.querySelector('rank[name="boardgame"]')?.getAttribute('value')) || null
        };
    }

    extractLocationFamilies(families) {
        const locationPatterns = [
            /^Cities:\s*(.+)$/i,
            /^Country:\s*(.+)$/i,
            /^Regions:\s*(.+)$/i,
            /^States:\s*(.+)$/i,
            /^Provinces:\s*(.+)$/i
        ];

        const locations = [];

        families.forEach(family => {
            locationPatterns.forEach(pattern => {
                const match = family.name.match(pattern);
                if (match) {
                    const locationString = match[1].trim();
                    
                    // Parse location string (e.g., "Bordeaux (France)" -> {city: "Bordeaux", country: "France"})
                    const parsedLocation = this.parseLocationString(locationString);
                    
                    locations.push({
                        familyId: family.id,
                        familyName: family.name,
                        type: this.getLocationTypeFromPattern(pattern),
                        locationString: locationString,
                        parsed: parsedLocation
                    });
                }
            });
        });

        return locations;
    }

    parseLocationString(locationString) {
        // Handle formats like "Bordeaux (France)", "Brazil", "New York (United States)"
        const parenthesesMatch = locationString.match(/^(.+?)\s*\((.+?)\)$/);
        
        if (parenthesesMatch) {
            return {
                primary: parenthesesMatch[1].trim(),
                secondary: parenthesesMatch[2].trim()
            };
        }
        
        return {
            primary: locationString.trim(),
            secondary: null
        };
    }

    getLocationTypeFromPattern(pattern) {
        const patternString = pattern.toString();
        if (patternString.includes('Cities')) return 'city';
        if (patternString.includes('Country')) return 'country';
        if (patternString.includes('Regions')) return 'region';
        if (patternString.includes('States')) return 'state';
        if (patternString.includes('Provinces')) return 'province';
        return 'unknown';
    }

    async getGameWithLocations(gameId) {
        const gameDetails = await this.getGameDetails(gameId);
        const locations = this.extractLocationFamilies(gameDetails.families);
        
        return {
            ...gameDetails,
            locations: locations
        };
    }
}
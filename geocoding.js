class GeocodingPipeline {
    constructor() {
        this.nominatimUrl = 'https://nominatim.openstreetmap.org';
        this.rateLimitDelay = 1000; // 1 second between requests for Nominatim
        this.lastRequestTime = 0;
        this.cache = new Map(); // In-memory cache for geocoded locations
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

    generateCacheKey(locationString, type) {
        return `${type}:${locationString.toLowerCase()}`;
    }

    async geocodeLocation(locationString, type = 'unknown') {
        const cacheKey = this.generateCacheKey(locationString, type);
        
        // Check cache first
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }

        await this.enforceRateLimit();

        try {
            const query = this.buildSearchQuery(locationString, type);
            const url = `${this.nominatimUrl}/search?format=json&q=${encodeURIComponent(query)}&limit=3&addressdetails=1`;
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Nominatim HTTP ${response.status}: ${response.statusText}`);
            }
            
            const results = await response.json();
            
            if (results.length === 0) {
                const result = { success: false, error: 'No results found', query: query };
                this.cache.set(cacheKey, result);
                return result;
            }

            // Score and select best result
            const bestResult = this.selectBestResult(results, locationString, type);
            const geocodedResult = {
                success: true,
                lat: parseFloat(bestResult.lat),
                lng: parseFloat(bestResult.lon),
                displayName: bestResult.display_name,
                type: bestResult.type,
                importance: parseFloat(bestResult.importance || 0),
                boundingBox: bestResult.boundingbox ? {
                    south: parseFloat(bestResult.boundingbox[0]),
                    north: parseFloat(bestResult.boundingbox[1]),
                    west: parseFloat(bestResult.boundingbox[2]),
                    east: parseFloat(bestResult.boundingbox[3])
                } : null,
                address: bestResult.address || {},
                query: query,
                confidence: this.calculateConfidence(bestResult, locationString, type)
            };

            this.cache.set(cacheKey, geocodedResult);
            return geocodedResult;

        } catch (error) {
            console.error(`Geocoding failed for "${locationString}":`, error);
            const result = { success: false, error: error.message, query: locationString };
            this.cache.set(cacheKey, result);
            return result;
        }
    }

    async geocodeStructured(city, country, state = null, type = 'unknown') {
        const cacheKey = this.generateCacheKey(`${city}|${country}|${state}`, `structured-${type}`);
        
        // Check cache first
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }

        await this.enforceRateLimit();

        try {
            // Build structured query parameters
            const params = new URLSearchParams({
                format: 'json',
                addressdetails: '1',
                limit: '3'
            });

            if (city) params.append('city', city);
            if (country) params.append('country', country);
            if (state) params.append('state', state);

            const url = `${this.nominatimUrl}/search?${params.toString()}`;
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Nominatim HTTP ${response.status}: ${response.statusText}`);
            }
            
            const results = await response.json();
            
            if (results.length === 0) {
                const result = { 
                    success: false, 
                    error: 'No results found', 
                    query: `city=${city}, country=${country}${state ? `, state=${state}` : ''}` 
                };
                this.cache.set(cacheKey, result);
                return result;
            }

            // For structured queries, first result is usually best
            const bestResult = results[0];
            const geocodedResult = {
                success: true,
                lat: parseFloat(bestResult.lat),
                lng: parseFloat(bestResult.lon),
                displayName: bestResult.display_name,
                type: bestResult.type,
                importance: parseFloat(bestResult.importance || 0),
                boundingBox: bestResult.boundingbox ? {
                    south: parseFloat(bestResult.boundingbox[0]),
                    north: parseFloat(bestResult.boundingbox[1]),
                    west: parseFloat(bestResult.boundingbox[2]),
                    east: parseFloat(bestResult.boundingbox[3])
                } : null,
                address: bestResult.address || {},
                query: `structured: city=${city}, country=${country}${state ? `, state=${state}` : ''}`,
                confidence: 0.9 // Structured queries are generally more reliable
            };

            this.cache.set(cacheKey, geocodedResult);
            return geocodedResult;

        } catch (error) {
            console.error(`Structured geocoding failed for city=${city}, country=${country}:`, error);
            const result = { 
                success: false, 
                error: error.message, 
                query: `structured: city=${city}, country=${country}` 
            };
            this.cache.set(cacheKey, result);
            return result;
        }
    }

    buildSearchQuery(locationString, type) {
        // Enhance search query based on location type
        switch (type) {
            case 'city':
                return `${locationString} city`;
            case 'country':
                return `${locationString} country`;
            case 'region':
                return `${locationString} region`;
            case 'state':
                return `${locationString} state`;
            case 'province':
                return `${locationString} province`;
            default:
                return locationString;
        }
    }

    selectBestResult(results, originalLocation, type) {
        // First filter out obviously wrong results
        const filteredResults = results.filter(result => {
            return this.isReasonableMatch(result, originalLocation, type);
        });
        
        // If no reasonable matches, fall back to all results
        const resultsToScore = filteredResults.length > 0 ? filteredResults : results;
        
        // Score results based on type matching and importance
        const scoredResults = resultsToScore.map(result => {
            let score = parseFloat(result.importance || 0);
            
            // Boost score for type matching
            if (this.typeMatches(result, type)) {
                score += 0.3;
            }
            
            // Boost score for exact name matching
            if (this.nameMatches(result, originalLocation)) {
                score += 0.2;
            }
            
            // Boost score for country/region consistency in compound queries
            if (this.hasLocationConsistency(result, originalLocation)) {
                score += 0.4;
            }
            
            return { ...result, score };
        });

        // Sort by score descending
        scoredResults.sort((a, b) => b.score - a.score);
        
        return scoredResults[0];
    }

    typeMatches(result, expectedType) {
        const resultType = result.type?.toLowerCase() || '';
        const addressType = result.address ? Object.keys(result.address) : [];
        
        switch (expectedType) {
            case 'city':
                return resultType.includes('city') || 
                       resultType.includes('town') || 
                       addressType.includes('city') ||
                       addressType.includes('town');
            case 'country':
                return resultType.includes('country') || 
                       addressType.includes('country');
            case 'region':
                return resultType.includes('region') || 
                       resultType.includes('state') ||
                       addressType.includes('state') ||
                       addressType.includes('region');
            case 'state':
                return resultType.includes('state') || 
                       addressType.includes('state');
            case 'province':
                return resultType.includes('province') || 
                       addressType.includes('province');
            default:
                return true;
        }
    }

    nameMatches(result, originalLocation) {
        const resultName = result.display_name.toLowerCase();
        const originalLower = originalLocation.toLowerCase();
        
        // Check if original location appears in the display name
        return resultName.includes(originalLower) || 
               originalLower.includes(result.name?.toLowerCase() || '');
    }

    isReasonableMatch(result, originalLocation, type) {
        // For compound queries like "Tokyo, Japan", validate both parts
        if (originalLocation.includes(',')) {
            const parts = originalLocation.split(',').map(p => p.trim().toLowerCase());
            const displayName = result.display_name.toLowerCase();
            
            // Each part of the query should appear in the result
            const allPartsFound = parts.every(part => {
                return displayName.includes(part) || 
                       this.isLocationSynonym(part, displayName);
            });
            
            if (!allPartsFound) {
                return false;
            }
        }
        
        // Check for obvious mismatches (e.g., looking for Tokyo but getting Bangladesh)
        if (this.hasGeographicMismatch(result, originalLocation)) {
            return false;
        }
        
        return true;
    }

    hasLocationConsistency(result, originalLocation) {
        // For compound queries, boost results where all parts are found
        if (originalLocation.includes(',')) {
            const parts = originalLocation.split(',').map(p => p.trim().toLowerCase());
            const displayName = result.display_name.toLowerCase();
            const address = result.address || {};
            
            // Check if major parts are consistent
            for (const part of parts) {
                const foundInDisplay = displayName.includes(part);
                const foundInAddress = Object.values(address).some(value => 
                    value.toLowerCase().includes(part)
                );
                
                if (foundInDisplay || foundInAddress) {
                    return true;
                }
            }
        }
        
        return false;
    }

    isLocationSynonym(queryPart, displayName) {
        // Handle common synonyms and variations
        const synonyms = {
            'usa': ['united states', 'america'],
            'uk': ['united kingdom', 'britain'],
            'uae': ['united arab emirates'],
            'japan': ['nippon', 'nihon'],
            'germany': ['deutschland'],
            'netherlands': ['holland']
        };
        
        for (const [key, values] of Object.entries(synonyms)) {
            if (queryPart === key && values.some(syn => displayName.includes(syn))) {
                return true;
            }
            if (values.includes(queryPart) && displayName.includes(key)) {
                return true;
            }
        }
        
        return false;
    }

    hasGeographicMismatch(result, originalLocation) {
        // Detect major geographic mismatches
        const displayName = result.display_name.toLowerCase();
        const address = result.address || {};
        
        // If searching for "Tokyo, Japan" but result is in Bangladesh
        if (originalLocation.toLowerCase().includes('japan')) {
            if (displayName.includes('bangladesh') || 
                address.country?.toLowerCase().includes('bangladesh')) {
                return true;
            }
        }
        
        // Add more geographic consistency checks as needed
        const queryCountryHints = this.extractCountryHints(originalLocation);
        const resultCountry = address.country?.toLowerCase() || '';
        
        if (queryCountryHints.length > 0 && resultCountry) {
            const hasCountryMatch = queryCountryHints.some(hint => 
                resultCountry.includes(hint) || 
                this.isLocationSynonym(hint, resultCountry)
            );
            
            if (!hasCountryMatch) {
                return true; // Geographic mismatch
            }
        }
        
        return false;
    }

    extractCountryHints(locationString) {
        const hints = [];
        const lowerLocation = locationString.toLowerCase();
        
        // Common country names that might appear in queries
        const countries = [
            'japan', 'france', 'italy', 'germany', 'spain', 'usa', 'uk', 
            'china', 'india', 'brazil', 'canada', 'australia', 'russia',
            'united states', 'united kingdom', 'netherlands', 'belgium'
        ];
        
        for (const country of countries) {
            if (lowerLocation.includes(country)) {
                hints.push(country);
            }
        }
        
        return hints;
    }

    calculateConfidence(result, originalLocation, type) {
        let confidence = parseFloat(result.importance || 0.5);
        
        // Adjust confidence based on type matching
        if (this.typeMatches(result, type)) {
            confidence += 0.2;
        }
        
        // Adjust confidence based on name matching
        if (this.nameMatches(result, originalLocation)) {
            confidence += 0.2;
        }
        
        // Normalize to 0-1 range
        return Math.min(1.0, Math.max(0.0, confidence));
    }

    async geocodeBGGLocation(bggLocation) {
        const { type, parsed } = bggLocation;
        let result;

        // Strategy 1: Structured query (most accurate for city/country pairs)
        // For "Tokyo (Japan)" -> structured query with city=Tokyo, country=Japan
        if (parsed.secondary && type === 'city') {
            result = await this.geocodeStructured(
                parsed.primary, 
                parsed.secondary, 
                parsed.region, // Use region if available
                type
            );
            
            // Log structured query for debugging
            console.log(`Structured query: city=${parsed.primary}, country=${parsed.secondary}${parsed.region ? `, state=${parsed.region}` : ''}`);
        }

        // Strategy 2: Simple text query (primary + country)
        // Fallback if structured query failed or not applicable
        if (!result || !result.success) {
            if (parsed.secondary) {
                const simpleLocation = `${parsed.primary}, ${parsed.secondary}`;
                result = await this.geocodeLocation(simpleLocation, type);
            }
        }

        // Strategy 3: Just use primary if we don't have a result yet or it failed
        if (!result || !result.success) {
            result = await this.geocodeLocation(parsed.primary, type);
        }
        
        // Strategy 4: Try the full secondary content as fallback
        // For "Venice (Veneto, Italy)" this tries "Venice, Veneto, Italy"
        if (!result.success && parsed.fullSecondary && parsed.fullSecondary !== parsed.secondary) {
            const fullLocation = `${parsed.primary}, ${parsed.fullSecondary}`;
            result = await this.geocodeLocation(fullLocation, type);
        }
        
        // Strategy 5: Try just the secondary location (country only)
        if (!result.success && parsed.secondary) {
            result = await this.geocodeLocation(parsed.secondary, type);
        }

        return {
            ...bggLocation,
            geocoded: result,
            geocodedAt: new Date().toISOString()
        };
    }

    async geocodeGameLocations(gameWithLocations) {
        const geocodedLocations = [];
        
        for (const location of gameWithLocations.locations) {
            try {
                const geocodedLocation = await this.geocodeBGGLocation(location);
                geocodedLocations.push(geocodedLocation);
                
                // Log progress
                if (geocodedLocation.geocoded.success) {
                    console.log(`✓ Geocoded: ${location.locationString} → ${geocodedLocation.geocoded.displayName}`);
                } else {
                    console.warn(`✗ Failed to geocode: ${location.locationString} (${geocodedLocation.geocoded.error})`);
                }
            } catch (error) {
                console.error(`Error geocoding location ${location.locationString}:`, error);
                geocodedLocations.push({
                    ...location,
                    geocoded: { success: false, error: error.message },
                    geocodedAt: new Date().toISOString()
                });
            }
        }

        return {
            ...gameWithLocations,
            locations: geocodedLocations,
            geocodingStats: {
                total: geocodedLocations.length,
                successful: geocodedLocations.filter(loc => loc.geocoded.success).length,
                failed: geocodedLocations.filter(loc => !loc.geocoded.success).length
            }
        };
    }

    getCacheStats() {
        return {
            size: this.cache.size,
            keys: Array.from(this.cache.keys())
        };
    }

    clearCache() {
        this.cache.clear();
    }
}
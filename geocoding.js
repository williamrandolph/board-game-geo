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
        // Score results based on type matching and importance
        const scoredResults = results.map(result => {
            let score = parseFloat(result.importance || 0);
            
            // Boost score for type matching
            if (this.typeMatches(result, type)) {
                score += 0.3;
            }
            
            // Boost score for exact name matching
            if (this.nameMatches(result, originalLocation)) {
                score += 0.2;
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
        const { type, locationString, parsed } = bggLocation;
        
        // Try to geocode the primary location first
        let result = await this.geocodeLocation(parsed.primary, type);
        
        // If that fails and we have secondary info, try the full string
        if (!result.success && parsed.secondary) {
            const fullLocation = `${parsed.primary}, ${parsed.secondary}`;
            result = await this.geocodeLocation(fullLocation, type);
        }
        
        // If still failing, try just the secondary location
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
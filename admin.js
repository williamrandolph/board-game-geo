class AdminTools {
    constructor() {
        this.database = new GameDatabase();
        this.importSystem = new BulkImportSystem();
    }

    async init() {
        await this.database.init();
        await this.importSystem.init();
    }

    async validateLocations(options = {}) {
        const minConfidence = options.minConfidence || 0.5;
        const maxDistance = options.maxDistance || 100; // km from expected location
        
        console.log('🔍 Validating geocoded locations...');
        
        const allGames = await this.database.getAllGamesWithLocations();
        const issues = [];
        
        for (const game of allGames) {
            for (const location of game.locations) {
                const issue = this.validateLocation(game, location, { minConfidence, maxDistance });
                if (issue) {
                    issues.push(issue);
                }
            }
        }
        
        return this.generateValidationReport(issues);
    }

    validateLocation(game, location, options) {
        const issues = [];
        
        // Check confidence score
        if (location.confidence < options.minConfidence) {
            issues.push(`Low confidence geocoding (${location.confidence.toFixed(2)})`);
        }
        
        // Check for obvious mismatches
        if (this.isObviousMismatch(location)) {
            issues.push('Possible location mismatch');
        }
        
        // Check for missing coordinates
        if (!location.lat || !location.lng) {
            issues.push('Missing coordinates');
        }
        
        // Check for suspicious coordinates (0,0 or invalid ranges)
        if (this.hasSuspiciousCoordinates(location)) {
            issues.push('Suspicious coordinates');
        }
        
        if (issues.length > 0) {
            return {
                gameId: game.id,
                gameName: game.name,
                locationString: location.locationString,
                type: location.type,
                confidence: location.confidence,
                coordinates: { lat: location.lat, lng: location.lng },
                displayName: location.displayName,
                issues: issues,
                severity: this.calculateSeverity(issues)
            };
        }
        
        return null;
    }

    isObviousMismatch(location) {
        const locationLower = location.locationString.toLowerCase();
        const displayLower = location.displayName.toLowerCase();
        
        // Check if the original location appears anywhere in the display name
        const words = locationLower.split(/[,\s\(\)]+/).filter(word => word.length > 2);
        const hasMatch = words.some(word => displayLower.includes(word));
        
        return !hasMatch;
    }

    hasSuspiciousCoordinates(location) {
        const { lat, lng } = location;
        
        // Check for null island (0,0)
        if (lat === 0 && lng === 0) return true;
        
        // Check for invalid ranges
        if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return true;
        
        // Check for suspiciously round numbers (might indicate placeholder data)
        if (Number.isInteger(lat) && Number.isInteger(lng) && 
            Math.abs(lat) % 10 === 0 && Math.abs(lng) % 10 === 0) {
            return true;
        }
        
        return false;
    }

    calculateSeverity(issues) {
        if (issues.some(issue => issue.includes('Missing coordinates') || issue.includes('Suspicious coordinates'))) {
            return 'high';
        }
        if (issues.some(issue => issue.includes('mismatch'))) {
            return 'medium';
        }
        return 'low';
    }

    generateValidationReport(issues) {
        const report = {
            timestamp: new Date().toISOString(),
            summary: {
                total: issues.length,
                high: issues.filter(i => i.severity === 'high').length,
                medium: issues.filter(i => i.severity === 'medium').length,
                low: issues.filter(i => i.severity === 'low').length
            },
            issues: issues.sort((a, b) => {
                const severityOrder = { high: 3, medium: 2, low: 1 };
                return severityOrder[b.severity] - severityOrder[a.severity];
            })
        };
        
        console.log(`✅ Validation complete: ${report.summary.total} issues found`);
        console.log(`   High: ${report.summary.high}, Medium: ${report.summary.medium}, Low: ${report.summary.low}`);
        
        return report;
    }

    async exportData(format = 'json') {
        const games = await this.database.getAllGamesWithLocations();
        const stats = await this.database.getStats();
        
        const exportData = {
            metadata: {
                exportedAt: new Date().toISOString(),
                version: '1.0',
                stats: stats
            },
            games: games
        };
        
        switch (format) {
            case 'json':
                return JSON.stringify(exportData, null, 2);
            case 'csv':
                return this.convertToCSV(games);
            case 'geojson':
                return this.convertToGeoJSON(games);
            default:
                throw new Error(`Unsupported export format: ${format}`);
        }
    }

    convertToCSV(games) {
        const rows = [];
        rows.push(['Game ID', 'Game Name', 'Year', 'Location String', 'Location Type', 'Latitude', 'Longitude', 'Confidence', 'Display Name']);
        
        games.forEach(game => {
            game.locations.forEach(location => {
                rows.push([
                    game.id,
                    game.name,
                    game.yearPublished || '',
                    location.locationString,
                    location.type,
                    location.lat,
                    location.lng,
                    location.confidence,
                    location.displayName
                ]);
            });
        });
        
        return rows.map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
    }

    convertToGeoJSON(games) {
        const features = [];
        
        games.forEach(game => {
            game.locations.forEach(location => {
                features.push({
                    type: 'Feature',
                    geometry: {
                        type: 'Point',
                        coordinates: [location.lng, location.lat]
                    },
                    properties: {
                        gameId: game.id,
                        gameName: game.name,
                        yearPublished: game.yearPublished,
                        locationString: location.locationString,
                        locationType: location.type,
                        confidence: location.confidence,
                        displayName: location.displayName,
                        rating: game.rating?.average || null
                    }
                });
            });
        });
        
        return JSON.stringify({
            type: 'FeatureCollection',
            features: features
        }, null, 2);
    }

    async importData(jsonData) {
        const data = typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;
        
        if (!data.games || !Array.isArray(data.games)) {
            throw new Error('Invalid import data format');
        }
        
        let imported = 0;
        let errors = 0;
        
        for (const gameData of data.games) {
            try {
                await this.database.saveGameWithLocations(gameData);
                imported++;
            } catch (error) {
                console.error(`Error importing game ${gameData.id}:`, error);
                errors++;
            }
        }
        
        return {
            imported: imported,
            errors: errors,
            total: data.games.length
        };
    }

    async getSystemStats() {
        const dbStats = await this.database.getStats();
        const importStats = await this.importSystem.getImportStats();
        
        return {
            database: dbStats,
            import: importStats,
            validation: {
                lastRun: null // Would track last validation run
            },
            system: {
                userAgent: navigator.userAgent,
                timestamp: new Date().toISOString()
            }
        };
    }

    async runDiagnostics() {
        console.log('🔧 Running system diagnostics...');
        
        const diagnostics = {
            timestamp: new Date().toISOString(),
            database: await this.testDatabase(),
            api: await this.testAPIs(),
            geocoding: await this.testGeocoding()
        };
        
        console.log('✅ Diagnostics complete');
        return diagnostics;
    }

    async testDatabase() {
        try {
            const stats = await this.database.getStats();
            return {
                status: 'ok',
                stats: stats
            };
        } catch (error) {
            return {
                status: 'error',
                error: error.message
            };
        }
    }

    async testAPIs() {
        try {
            const bggApi = new BGGApi();
            const testGame = await bggApi.getGameDetails(13); // Catan
            return {
                bgg: {
                    status: 'ok',
                    testGame: testGame.name,
                    responseTime: Date.now() // Would measure actual response time
                }
            };
        } catch (error) {
            return {
                bgg: {
                    status: 'error',
                    error: error.message
                }
            };
        }
    }

    async testGeocoding() {
        try {
            const geocoder = new GeocodingPipeline();
            const testResult = await geocoder.geocodeLocation('London', 'city');
            return {
                nominatim: {
                    status: testResult.success ? 'ok' : 'error',
                    testLocation: 'London',
                    result: testResult.success ? testResult.displayName : testResult.error
                }
            };
        } catch (error) {
            return {
                nominatim: {
                    status: 'error',
                    error: error.message
                }
            };
        }
    }

    async clearCache() {
        const geocoder = new GeocodingPipeline();
        geocoder.clearCache();
        console.log('✅ Geocoding cache cleared');
    }

    async resetDatabase() {
        await this.database.clearAllData();
        console.log('⚠️ Database reset complete - all data cleared');
    }
}
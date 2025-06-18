class BulkImportSystem {
    constructor() {
        this.bggApi = new BGGApi();
        this.geocoder = new GeocodingPipeline();
        this.database = new GameDatabase();
        this.isRunning = false;
        this.currentJob = null;
    }

    async init() {
        await this.database.init();
    }

    async importGamesByIds(gameIds, options = {}) {
        if (this.isRunning) {
            throw new Error('Import job already running');
        }

        const jobOptions = {
            batchSize: options.batchSize || 10,
            delayBetweenBatches: options.delayBetweenBatches || 5000, // 5 seconds
            skipExisting: options.skipExisting !== false, // default true
            onProgress: options.onProgress || (() => {}),
            onError: options.onError || ((error) => console.error(error))
        };

        this.currentJob = {
            id: Date.now(),
            type: 'gameIds',
            status: 'running',
            total: gameIds.length,
            processed: 0,
            successful: 0,
            failed: 0,
            errors: [],
            startTime: new Date(),
            gameIds: gameIds,
            options: jobOptions
        };

        this.isRunning = true;

        try {
            await this.processGameIdsBatch(gameIds, jobOptions);
            
            this.currentJob.status = 'completed';
            this.currentJob.endTime = new Date();
            
        } catch (error) {
            this.currentJob.status = 'failed';
            this.currentJob.endTime = new Date();
            this.currentJob.errors.push({
                type: 'fatal',
                message: error.message,
                timestamp: new Date()
            });
            throw error;
        } finally {
            this.isRunning = false;
        }

        return this.currentJob;
    }

    async processGameIdsBatch(gameIds, options) {
        const batches = this.createBatches(gameIds, options.batchSize);
        
        for (let i = 0; i < batches.length; i++) {
            const batch = batches[i];
            
            console.log(`Processing batch ${i + 1}/${batches.length} (${batch.length} games)`);
            
            // Process games in batch sequentially to respect rate limits
            for (const gameId of batch) {
                try {
                    await this.processGame(gameId, options);
                    this.currentJob.processed++;
                    this.currentJob.successful++;
                    
                    options.onProgress({
                        jobId: this.currentJob.id,
                        processed: this.currentJob.processed,
                        total: this.currentJob.total,
                        successful: this.currentJob.successful,
                        failed: this.currentJob.failed,
                        currentGameId: gameId
                    });
                    
                } catch (error) {
                    this.currentJob.processed++;
                    this.currentJob.failed++;
                    this.currentJob.errors.push({
                        type: 'game',
                        gameId: gameId,
                        message: error.message,
                        timestamp: new Date()
                    });
                    
                    options.onError({
                        gameId: gameId,
                        error: error.message
                    });
                }
            }
            
            // Delay between batches
            if (i < batches.length - 1) {
                console.log(`Waiting ${options.delayBetweenBatches}ms before next batch...`);
                await this.delay(options.delayBetweenBatches);
            }
        }
    }

    async processGame(gameId, options) {
        // Check if game already exists and skip if requested
        if (options.skipExisting) {
            const existingGame = await this.database.getGame(gameId);
            if (existingGame) {
                console.log(`Skipping existing game ${gameId}: ${existingGame.name}`);
                return;
            }
        }

        // Fetch game details from BGG
        console.log(`Fetching game ${gameId} from BGG...`);
        const gameWithLocations = await this.bggApi.getGameWithLocations(gameId);
        
        if (gameWithLocations.locations.length === 0) {
            console.log(`Game ${gameId} (${gameWithLocations.name}) has no location data`);
            return;
        }

        // Geocode all locations
        console.log(`Geocoding ${gameWithLocations.locations.length} locations for ${gameWithLocations.name}...`);
        const geocodedGame = await this.geocoder.geocodeGameLocations(gameWithLocations);
        
        // Save to database
        const savedResult = await this.database.saveGameWithLocations(geocodedGame);
        
        console.log(`✓ Saved game ${gameId}: ${gameWithLocations.name} (${savedResult.locations.length} locations)`);
        
        return savedResult;
    }

    async importTopGames(count = 100, options = {}) {
        // This would require scraping BGG's top games list or using a predefined list
        // For now, we'll use a sample of popular games with known location families
        const popularGameIds = [
            174430, // Gloomhaven
            161936, // Pandemic Legacy: Season 1
            167791, // Terraforming Mars
            120677, // Terra Mystica
            84876,  // Le Havre
            31260,  // Agricola
            13,     // Catan
            30549,  // Pandemic
            68448,  // 7 Wonders
            36218,  // Dominion
            70323,  // King of Tokyo
            124361, // Codenames
            148228, // Splendor
            110327, // Lords of Waterdeep
            102794, // Tzolk'in: The Mayan Calendar
            39856,  // Dixit
            131357, // Coup
            28720,  // Brass
            25613,  // Carcassonne
            171623  // The Castles of Burgundy
        ];

        const gameIdsToImport = popularGameIds.slice(0, Math.min(count, popularGameIds.length));
        return this.importGamesByIds(gameIdsToImport, options);
    }

    async searchAndImportGames(searchQuery, maxResults = 50, options = {}) {
        console.log(`Searching BGG for "${searchQuery}"...`);
        const searchResults = await this.bggApi.searchGames(searchQuery);
        
        if (searchResults.length === 0) {
            throw new Error(`No games found for query: ${searchQuery}`);
        }

        const gameIds = searchResults
            .slice(0, maxResults)
            .map(game => game.id);
        
        console.log(`Found ${searchResults.length} games, importing top ${gameIds.length}...`);
        
        return this.importGamesByIds(gameIds, {
            ...options,
            searchQuery: searchQuery,
            searchResults: searchResults.length
        });
    }

    createBatches(array, batchSize) {
        const batches = [];
        for (let i = 0; i < array.length; i += batchSize) {
            batches.push(array.slice(i, i + batchSize));
        }
        return batches;
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    getCurrentJobStatus() {
        return this.currentJob;
    }

    async getImportStats() {
        const dbStats = await this.database.getStats();
        return {
            database: dbStats,
            currentJob: this.currentJob,
            isRunning: this.isRunning
        };
    }

    cancel() {
        if (this.currentJob && this.isRunning) {
            this.currentJob.status = 'cancelled';
            this.currentJob.endTime = new Date();
            this.isRunning = false;
        }
    }
}

// Sample import configurations
const ImportPresets = {
    quick: {
        batchSize: 5,
        delayBetweenBatches: 3000,
        skipExisting: true
    },
    
    thorough: {
        batchSize: 3,
        delayBetweenBatches: 5000,
        skipExisting: false
    },
    
    fast: {
        batchSize: 10,
        delayBetweenBatches: 2000,
        skipExisting: true
    }
};
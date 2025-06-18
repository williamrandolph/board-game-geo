// Unit tests for BGG location parsing
// Run in browser console or Node.js

class BGGParsingTests {
    constructor() {
        this.testCases = [
            // Simple cases
            {
                input: "Bordeaux (France)",
                expected: {
                    primary: "Bordeaux",
                    secondary: "France",
                    fullSecondary: "France"
                },
                description: "Simple city-country format"
            },
            {
                input: "Brazil",
                expected: {
                    primary: "Brazil",
                    secondary: null
                },
                description: "Country only"
            },
            
            // Complex cases with regions
            {
                input: "Venice (Veneto, Italy)",
                expected: {
                    primary: "Venice",
                    secondary: "Italy",
                    fullSecondary: "Veneto, Italy",
                    region: "Veneto"
                },
                description: "City with region and country"
            },
            {
                input: "New York (New York, United States)",
                expected: {
                    primary: "New York",
                    secondary: "United States",
                    fullSecondary: "New York, United States",
                    region: "New York"
                },
                description: "City with state and country (same name)"
            },
            {
                input: "San Francisco (California, United States)",
                expected: {
                    primary: "San Francisco",
                    secondary: "United States",
                    fullSecondary: "California, United States",
                    region: "California"
                },
                description: "City with state and country"
            },
            
            // Edge cases
            {
                input: "Paris (Île-de-France, France)",
                expected: {
                    primary: "Paris",
                    secondary: "France",
                    fullSecondary: "Île-de-France, France",
                    region: "Île-de-France"
                },
                description: "Region with hyphens and accents"
            },
            {
                input: "London (Greater London, England)",
                expected: {
                    primary: "London",
                    secondary: "England",
                    fullSecondary: "Greater London, England",
                    region: "Greater London"
                },
                description: "City with administrative region"
            },
            {
                input: "Tokyo (Kantō, Japan)",
                expected: {
                    primary: "Tokyo",
                    secondary: "Japan",
                    fullSecondary: "Kantō, Japan",
                    region: "Kantō"
                },
                description: "City with Japanese region"
            },
            
            // Multi-level regions
            {
                input: "Barcelona (Catalonia, Cataluña, Spain)",
                expected: {
                    primary: "Barcelona",
                    secondary: "Spain",
                    fullSecondary: "Catalonia, Cataluña, Spain",
                    region: "Catalonia"
                },
                description: "City with multiple regional identifiers"
            },
            
            // Unusual formats
            {
                input: "Ancient Rome (Latium, Roman Empire)",
                expected: {
                    primary: "Ancient Rome",
                    secondary: "Roman Empire",
                    fullSecondary: "Latium, Roman Empire",
                    region: "Latium"
                },
                description: "Historical location with ancient region"
            },
            {
                input: "The Thames (London, England)",
                expected: {
                    primary: "The Thames",
                    secondary: "England",
                    fullSecondary: "London, England",
                    region: "London"
                },
                description: "Geographic feature with city context"
            },
            
            // No parentheses
            {
                input: "Antarctica",
                expected: {
                    primary: "Antarctica",
                    secondary: null
                },
                description: "Single location without parentheses"
            },
            {
                input: "United States",
                expected: {
                    primary: "United States",
                    secondary: null
                },
                description: "Multi-word country"
            }
        ];
        
        this.geocodingTestCases = [
            {
                parsed: {
                    primary: "Venice",
                    secondary: "Italy",
                    fullSecondary: "Veneto, Italy"
                },
                expectedQueries: [
                    "Venice, Italy",      // Strategy 1: primary + secondary
                    "Venice",             // Strategy 2: primary only  
                    "Venice, Veneto, Italy", // Strategy 3: full location
                    "Italy"               // Strategy 4: country only
                ],
                description: "Venice geocoding strategy"
            },
            {
                parsed: {
                    primary: "Bordeaux",
                    secondary: "France",
                    fullSecondary: "France"
                },
                expectedQueries: [
                    "Bordeaux, France",   // Strategy 1: primary + secondary
                    "Bordeaux",           // Strategy 2: primary only
                    "France"              // Strategy 4: country only (skip 3, same as 1)
                ],
                description: "Simple location geocoding strategy"
            }
        ];
    }

    runParsingTests() {
        console.log("🧪 Running BGG Location Parsing Tests...\n");
        
        let passed = 0;
        let failed = 0;
        
        // Create a BGGApi instance for testing
        const bggApi = new BGGApi();
        
        this.testCases.forEach((testCase, index) => {
            console.log(`Test ${index + 1}: ${testCase.description}`);
            console.log(`Input: "${testCase.input}"`);
            
            const result = bggApi.parseLocationString(testCase.input);
            const success = this.compareObjects(result, testCase.expected);
            
            if (success) {
                console.log("✅ PASSED");
                passed++;
            } else {
                console.log("❌ FAILED");
                console.log("Expected:", testCase.expected);
                console.log("Got:", result);
                failed++;
            }
            
            console.log("");
        });
        
        console.log(`📊 Results: ${passed} passed, ${failed} failed`);
        return { passed, failed };
    }
    
    runGeocodingStrategyTests() {
        console.log("🗺️ Running Geocoding Strategy Tests...\n");
        
        this.geocodingTestCases.forEach((testCase, index) => {
            console.log(`Strategy Test ${index + 1}: ${testCase.description}`);
            console.log("Parsed data:", testCase.parsed);
            console.log("Expected query sequence:");
            testCase.expectedQueries.forEach((query, i) => {
                console.log(`  ${i + 1}. "${query}"`);
            });
            console.log("");
        });
    }
    
    compareObjects(obj1, obj2) {
        const keys1 = Object.keys(obj1);
        const keys2 = Object.keys(obj2);
        
        // Check if all expected keys are present
        for (const key of keys2) {
            if (!(key in obj1)) {
                return false;
            }
            if (obj1[key] !== obj2[key]) {
                return false;
            }
        }
        
        return true;
    }
    
    // Test specific edge cases
    testEdgeCases() {
        console.log("🔍 Testing Edge Cases...\n");
        
        const bggApi = new BGGApi();
        const edgeCases = [
            "London (London, England)",  // Same name for city and region
            "New York (New York, New York, United States)", // Multiple same names
            "São Paulo (São Paulo, Brazil)", // Accented characters
            "Mexico City (Mexico City, Mexico)", // City name includes "City"
            "St. Petersburg (Florida, United States)", // Abbreviated title
            "Las Vegas (Clark County, Nevada, United States)", // County level
        ];
        
        edgeCases.forEach(location => {
            const result = bggApi.parseLocationString(location);
            console.log(`"${location}"`);
            console.log("→", result);
            console.log("");
        });
    }
}

// Helper function to run all tests
function runAllBGGTests() {
    const tester = new BGGParsingTests();
    
    console.log("=" .repeat(60));
    console.log("BGG LOCATION PARSING TEST SUITE");
    console.log("=" .repeat(60));
    
    const results = tester.runParsingTests();
    tester.runGeocodingStrategyTests();
    tester.testEdgeCases();
    
    console.log("=" .repeat(60));
    console.log(`FINAL RESULTS: ${results.passed} passed, ${results.failed} failed`);
    
    if (results.failed === 0) {
        console.log("🎉 All tests passed!");
    } else {
        console.log("⚠️ Some tests failed. Check the output above.");
    }
    
    return results;
}

// Auto-run tests if BGGApi is available
if (typeof BGGApi !== 'undefined') {
    // Uncomment to auto-run tests:
    // runAllBGGTests();
} else {
    console.log("BGGApi not found. Load bgg-api.js first, then run: runAllBGGTests()");
}
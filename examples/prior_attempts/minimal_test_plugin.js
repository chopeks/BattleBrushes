/*
 * Minimal test plugin to debug Tiled JavaScript API
 */

// Test 1: Check if tiled object exists
if (typeof tiled === 'undefined') {
    console.log("ERROR: tiled object not available");
} else {
    console.log("SUCCESS: tiled object available");
    
    // Test 2: Check available methods
    if (tiled.log) {
        tiled.log("Minimal test plugin loaded");
        tiled.log("Testing basic functionality");
    }
    
    // Test 3: Try to register a simple format
    var testFormat = {
        name: "Test Format",
        extension: "test",
        supportsFile: function(fileName) { return false; },
        read: function(fileName) { return null; }
    };
    
    try {
        if (tiled.registerTilesetFormat) {
            tiled.registerTilesetFormat("test", testFormat);
            if (tiled.log) tiled.log("SUCCESS: registerTilesetFormat works");
        } else if (tiled.registerFormat) {
            tiled.registerFormat("test", testFormat);
            if (tiled.log) tiled.log("SUCCESS: registerFormat works");
        } else {
            if (tiled.log) tiled.log("ERROR: No registration method found");
        }
    } catch (e) {
        if (tiled.log) tiled.log("ERROR registering format: " + e.toString());
    }
}

// Always log to console as fallback
console.log("Minimal test plugin execution complete");
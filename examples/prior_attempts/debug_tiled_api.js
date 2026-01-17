/*
 * Debug script to understand Tiled 1.8.0 JavaScript API
 */

function debugLog(message) {
    if (typeof tiled !== 'undefined' && tiled.log) {
        tiled.log("[DEBUG] " + message);
    }
}

debugLog("=== Tiled JavaScript API Debug ===");

if (typeof tiled !== 'undefined') {
    debugLog("Tiled object is available");
    debugLog("Available tiled methods/properties:");
    for (var key in tiled) {
        debugLog("  " + key + ": " + typeof tiled[key]);
    }
} else {
    debugLog("ERROR: Tiled object is not available!");
}

if (typeof Tileset !== 'undefined') {
    debugLog("Tileset constructor is available");
} else {
    debugLog("Tileset constructor is not available");
}

if (typeof BinaryFile !== 'undefined') {
    debugLog("BinaryFile is available");
} else {
    debugLog("BinaryFile is not available");
}

debugLog("=== End Debug ===");
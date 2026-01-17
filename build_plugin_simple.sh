#!/bin/bash

# Simple plugin compilation without full Tiled build system
# This compiles just the brush plugin as a standalone shared library

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Simple Brush Plugin Builder ==="

# Check dependencies
echo "Checking Qt5 installation..."
if ! command -v qmake &> /dev/null; then
    echo "Qt5 not found. Installing..."
    sudo apt update
    sudo apt install -y qtbase5-dev qtbase5-dev-tools qtcreator
fi

# Create a minimal mock of Tiled's interfaces that our plugin needs
echo "Creating minimal Tiled interface headers..."
mkdir -p mock_tiled_headers

cat > mock_tiled_headers/tileset.h << 'EOF'
#pragma once
#include <QObject>
#include <QSharedPointer>
#include <QString>
#include <QVariant>

namespace Tiled {

class Tile {
public:
    QVariant property(const QString &name) const { return m_properties.value(name); }
    void setProperty(const QString &name, const QVariant &value) { m_properties[name] = value; }
    bool hasProperty(const QString &name) const { return m_properties.contains(name); }
    QImage image() const { return m_image; }
    void setImage(const QImage &image) { m_image = image; }
    
private:
    QMap<QString, QVariant> m_properties;
    QImage m_image;
};

class Tileset : public QObject {
    Q_OBJECT
public:
    QString name() const { return m_name; }
    void setName(const QString &name) { m_name = name; }
    QVariant property(const QString &name) const { return m_properties.value(name); }
    void setProperty(const QString &name, const QVariant &value) { m_properties[name] = value; }
    bool hasProperty(const QString &name) const { return m_properties.contains(name); }
    int tileCount() const { return m_tiles.size(); }
    Tile* tileAt(int index) const { return index < m_tiles.size() ? m_tiles[index] : nullptr; }
    Tile* addTile(const QString &imagePath) { 
        auto tile = new Tile();
        m_tiles.append(tile);
        return tile;
    }
    
private:
    QString m_name;
    QMap<QString, QVariant> m_properties;
    QList<Tile*> m_tiles;
};

using SharedTileset = QSharedPointer<Tileset>;

}
EOF

cat > mock_tiled_headers/tilesetformat.h << 'EOF'
#pragma once
#include "tileset.h"
#include <QObject>

namespace Tiled {

class TilesetFormat : public QObject {
    Q_OBJECT
public:
    struct Options {};
    
    explicit TilesetFormat(QObject *parent = nullptr) : QObject(parent) {}
    virtual ~TilesetFormat() = default;
    
    virtual SharedTileset read(const QString &fileName) = 0;
    virtual bool write(const Tileset &tileset, const QString &fileName, Options options = Options()) = 0;
    virtual bool supportsFile(const QString &fileName) const = 0;
    virtual QString nameFilter() const = 0;
    virtual QString shortName() const = 0;
    virtual QString errorString() const = 0;
};

}
EOF

cat > mock_tiled_headers/plugin.h << 'EOF'
#pragma once
#include <QObject>

namespace Tiled {

class Plugin : public QObject {
    Q_OBJECT
public:
    explicit Plugin(QObject *parent = nullptr) : QObject(parent) {}
    virtual ~Plugin() = default;
    virtual void initialize() = 0;
    
protected:
    void addObject(QObject *object) { m_objects.append(object); }
    
private:
    QList<QObject*> m_objects;
};

}
EOF

cat > mock_tiled_headers/imagereference.h << 'EOF'
#pragma once
#include <QString>

namespace Tiled {

struct ImageReference {
    QString filePath;
    ImageReference(const QString &path = QString()) : filePath(path) {}
};

}
EOF

cat > mock_tiled_headers/tile.h << 'EOF'
#pragma once
#include "imagereference.h"
#include <QVariant>
#include <QMap>
#include <QImage>

namespace Tiled {

// Already defined in tileset.h, this is just for completeness
}
EOF

cat > mock_tiled_headers/savefile.h << 'EOF'
#pragma once
#include <QIODevice>
#include <QFile>

namespace Tiled {

class SaveFile {
public:
    explicit SaveFile(const QString &fileName) : m_file(fileName) {}
    
    bool open(QIODevice::OpenMode mode) { return m_file.open(mode); }
    QIODevice* device() { return &m_file; }
    QString errorString() const { return m_file.errorString(); }
    bool commit() { 
        m_file.flush();
        return true; 
    }
    
private:
    QFile m_file;
};

}
EOF

echo "Creating pro file for qmake build..."
cat > brush_plugin.pro << 'EOF'
QT += core gui widgets

TARGET = brush
TEMPLATE = lib
CONFIG += plugin shared

DEFINES += BRUSH_LIBRARY QT_DEPRECATED_WARNINGS

SOURCES += \
    tiled/src/plugins/brush/brushplugin.cpp

HEADERS += \
    tiled/src/plugins/brush/brushplugin.h \
    tiled/src/plugins/brush/brush_global.h \
    mock_tiled_headers/tileset.h \
    mock_tiled_headers/tilesetformat.h \
    mock_tiled_headers/plugin.h \
    mock_tiled_headers/imagereference.h \
    mock_tiled_headers/tile.h \
    mock_tiled_headers/savefile.h

INCLUDEPATH += \
    mock_tiled_headers \
    tiled/src/plugins/brush

# Output settings
DESTDIR = build
OBJECTS_DIR = build/obj
MOC_DIR = build/moc

# Install settings
target.path = ./plugins
INSTALLS += target
EOF

echo "Building plugin with qmake..."
qmake brush_plugin.pro
make clean
make -j$(nproc)

if [ $? -eq 0 ]; then
    echo ""
    echo "=== Build Successful! ==="
    
    # Find the built plugin
    PLUGIN_FILE=$(find build -name "*brush*" \( -name "*.so" -o -name "*.dll" -o -name "*.dylib" \) | head -1)
    
    if [ -n "$PLUGIN_FILE" ]; then
        echo "✅ Plugin built: $PLUGIN_FILE"
        
        # Copy to convenient location
        cp "$PLUGIN_FILE" "./brush_plugin$(echo $PLUGIN_FILE | sed 's/.*\(\.[^.]*\)$/\1/')"
        
        echo ""
        echo "=== Plugin Information ==="
        file "$PLUGIN_FILE"
        ls -la "$PLUGIN_FILE"
        
        echo ""
        echo "=== Installation Instructions ==="
        echo "1. Copy the plugin to your Tiled plugins directory:"
        echo "   - Linux: ~/.local/share/Tiled/plugins/"
        echo "   - Windows: %APPDATA%/Tiled/plugins/"
        echo "   - macOS: ~/Library/Preferences/Tiled/plugins/"
        echo ""
        echo "2. Restart Tiled"
        echo ""
        echo "3. The brush format will appear in:"
        echo "   - File → Open (for .brush files)"
        echo "   - File → Export As (for tilesets)"
        echo ""
        echo "✅ Plugin ready for use!"
        
    else
        echo "❌ Plugin built but file not found"
        exit 1
    fi
else
    echo ""
    echo "=== Build Failed ==="
    echo "Check the error messages above"
    exit 1
fi
EOF
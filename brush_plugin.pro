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

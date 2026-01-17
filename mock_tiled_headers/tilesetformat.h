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

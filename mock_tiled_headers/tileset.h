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

#include <QCoreApplication>
#include <QDebug>
#include <QDir>
#include <QFileInfo>
#include <QDataStream>
#include <QFile>

struct TestSpriteRecord {
    QString id;
    QByteArray blob;
    QRect rect;
    QPoint offset;
    quint16 flags;
    quint32 averageColor;
    QString srcPath;
    float pivot1, pivot2;
};

bool parseBrushFile(const QString &fileName) {
    QFile file(fileName);
    if (!file.open(QIODevice::ReadOnly)) {
        qDebug() << "Could not open file:" << file.errorString();
        return false;
    }
    
    QByteArray data = file.readAll();
    if (data.size() < 16) {
        qDebug() << "File too small";
        return false;
    }
    
    QDataStream stream(data);
    stream.setByteOrder(QDataStream::LittleEndian);
    
    int offset = 0;
    
    // Read magic
    quint32 magic;
    stream >> magic;
    offset += 4;
    
    qDebug() << "Magic:" << Qt::hex << magic;
    
    if (magic != 0xBAADFAAD) {
        qDebug() << "Invalid magic";
        return false;
    }
    
    // Read version
    quint16 version;
    stream >> version;
    offset += 2;
    
    qDebug() << "Version:" << version;
    
    // Read sheet path
    quint16 sheetPathLen;
    stream >> sheetPathLen;
    offset += 2;
    
    if (offset + sheetPathLen + 1 > data.size()) {
        qDebug() << "Invalid sheet path length";
        return false;
    }
    
    QString sheetPath = QString::fromLatin1(data.mid(offset, sheetPathLen));
    offset += sheetPathLen + 1; // +1 for null terminator
    
    qDebug() << "Sheet path:" << sheetPath;
    qDebug() << "Header bytes processed:" << offset;
    
    // Read a few more bytes to see the pattern
    if (offset + 12 <= data.size()) {
        stream.device()->seek(offset);
        quint8 b1, b6, b9, b11;
        quint32 i0;
        stream >> b1 >> b6 >> b9 >> b11 >> i0;
        qDebug() << "Category flags:" << b1 << b6 << b9 << b11 << i0;
        offset += 12;
    }
    
    qDebug() << "Starting sprite parsing at offset:" << offset;
    
    // Parse first few sprite records
    int spriteCount = 0;
    while (offset < data.size() && spriteCount < 5) {
        qDebug() << "Parsing sprite at offset:" << offset;
        
        // Read sprite ID
        if (offset + 2 > data.size()) break;
        
        stream.device()->seek(offset);
        quint16 idLen;
        stream >> idLen;
        offset += 2;
        
        qDebug() << "ID length:" << idLen;
        
        if (offset + idLen > data.size()) {
            qDebug() << "Invalid ID length";
            break;
        }
        
        QString id = QString::fromLatin1(data.mid(offset, idLen));
        offset += idLen;
        
        qDebug() << "Sprite ID:" << id;
        
        // Skip the rest for now
        if (offset + 8 + 22 > data.size()) break;
        offset += 8; // blob
        
        // Read rect data
        stream.device()->seek(offset);
        qint16 width, height, offsetX, offsetY;
        quint16 flags;
        quint32 ic;
        stream >> width >> height >> offsetX >> offsetY >> flags >> ic;
        
        qDebug() << "  Size:" << width << "x" << height;
        qDebug() << "  Offset:" << offsetX << offsetY;
        qDebug() << "  Flags:" << Qt::hex << flags;
        qDebug() << "  IC:" << Qt::hex << ic;
        
        offset += 22;
        
        // Find source path
        int srcPathStart = offset;
        while (offset < data.size() && data[offset] != 0) {
            offset++;
        }
        
        if (offset >= data.size()) break;
        
        QString srcPath = QString::fromLatin1(data.mid(srcPathStart, offset - srcPathStart));
        offset += 1; // null terminator
        
        qDebug() << "  Source path:" << srcPath;
        
        // Skip floats
        offset += 8;
        
        spriteCount++;
        qDebug() << "---";
    }
    
    qDebug() << "Parsed" << spriteCount << "sprites successfully";
    return true;
}

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);
    
    QString testFile = "../examples/original_packed_brush_example/brushes/terrain.brush";
    
    qDebug() << "Testing brush parser with:" << testFile;
    
    if (QFile::exists(testFile)) {
        parseBrushFile(testFile);
    } else {
        qDebug() << "Test file not found:" << testFile;
    }
    
    return 0;
}
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

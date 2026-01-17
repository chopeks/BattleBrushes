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

#pragma once
#include <QString>

namespace Tiled {

struct ImageReference {
    QString filePath;
    ImageReference(const QString &path = QString()) : filePath(path) {}
};

}

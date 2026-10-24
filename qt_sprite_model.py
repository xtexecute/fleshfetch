"""Stable QML sprite delegates; motion changes data instead of rebuilding items."""

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


class SpriteModel(QAbstractListModel):
    SpriteRole = int(Qt.ItemDataRole.UserRole) + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sprites = []

    def roleNames(self):
        return {self.SpriteRole: b"spriteData"}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._sprites)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == self.SpriteRole and index.isValid() and 0 <= index.row() < len(self._sprites):
            return self._sprites[index.row()]
        return None

    def sync(self, sprites):
        if [s["id"] for s in sprites] != [s["id"] for s in self._sprites]:
            self.beginResetModel()
            self._sprites = sprites
            self.endResetModel()
            return
        for row, sprite in enumerate(sprites):
            if sprite != self._sprites[row]:
                self._sprites[row] = sprite
                index = self.index(row)
                self.dataChanged.emit(index, index, [self.SpriteRole])

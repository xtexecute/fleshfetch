import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: page
    required property var theme
    property var saves: game.catalog.saves || []
    spacing: 12
    SectionTitle { theme: page.theme; text: "Saves" }
    RowLayout {
        Layout.fillWidth: true
        PixelField {
            id: newName
            theme: page.theme
            Layout.fillWidth: true
            placeholderText: "New save name"
            Accessible.name: "New save name"
            maximumLength: 120
            onAccepted: page.createSave()
        }
        PixelButton { theme: page.theme; text: "Create"; enabled: newName.text.trim().length > 0; onClicked: page.createSave() }
    }
    Flow {
        Layout.fillWidth: true
        Layout.preferredHeight: childrenRect.height
        spacing: 6
        PixelButton { theme: page.theme; text: "Save now"; enabled: !!game.live.saveId; onClicked: game.manualSave() }
        PixelButton { theme: page.theme; text: "Import"; onClicked: game.importSave() }
    }
    ListView {
        id: list
        Layout.fillWidth: true
        Layout.fillHeight: true
        model: page.saves
        clip: true
        spacing: 10
        ScrollBar.vertical: ScrollBar {}
        delegate: PixelFrame {
            id: save
            required property var modelData
            theme: page.theme
            width: list.width - 12
            height: content.implicitHeight + 28
            ColumnLayout {
                id: content
                width: parent.width
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: save.modelData.name; color: page.theme.text; font.pixelSize: 16; font.bold: true; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Text { text: save.modelData.active ? "ACTIVE" : ""; color: page.theme.dark ? page.theme.accentHover : page.theme.focus; font.family: page.theme.mono; font.pixelSize: 12 }
                }
                Text { text: (save.modelData.kind || "Save") + "  \u00b7  " + (save.modelData.updated || ""); color: page.theme.muted; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                Text {
                    text: "Required mods: " + (save.modelData.requiredMods || []).join(", ")
                    visible: (save.modelData.requiredMods || []).length > 0
                    color: page.theme.warning
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }
                RowLayout {
                    Layout.fillWidth: true
                    PixelField {
                        id: rename
                        theme: page.theme
                        Layout.fillWidth: true
                        text: save.modelData.name
                        Accessible.name: "Rename " + save.modelData.name
                        maximumLength: 120
                        onAccepted: if (text.trim()) game.renameSave(save.modelData.id, text.trim())
                    }
                    PixelButton { theme: page.theme; text: "Rename"; enabled: rename.text.trim().length > 0 && rename.text.trim() !== save.modelData.name; onClicked: game.renameSave(save.modelData.id, rename.text.trim()) }
                }
                Flow {
                    Layout.fillWidth: true
                    Layout.preferredHeight: childrenRect.height
                    spacing: 6
                    PixelButton { theme: page.theme; text: "Load"; enabled: !save.modelData.active; onClicked: game.loadSave(save.modelData.id) }
                    PixelButton { theme: page.theme; text: "Duplicate"; onClicked: game.duplicateSave(save.modelData.id) }
                    PixelButton { theme: page.theme; text: "Backup"; onClicked: game.backupSave(save.modelData.id) }
                    PixelButton { theme: page.theme; text: "Restore"; onClicked: game.restoreSave(save.modelData.id) }
                    PixelButton { theme: page.theme; text: "Export"; onClicked: game.exportSave(save.modelData.id) }
                    PixelButton { theme: page.theme; text: "Delete"; destructive: true; onClicked: game.deleteSave(save.modelData.id) }
                }
            }
        }
        Text { anchors.centerIn: parent; text: "No saves yet"; visible: list.count === 0; color: page.theme.muted; font.pixelSize: 14 }
    }
    function createSave() {
        const name = newName.text.trim()
        if (!name) return
        game.createSave(name)
        newName.clear()
    }
}

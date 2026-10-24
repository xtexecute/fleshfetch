import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: page
    required property var theme
    spacing: 12
    SectionTitle { theme: page.theme; text: "Achievements" }
    ListView {
        id: list
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        spacing: 8
        model: game.live.achievements || []
        ScrollBar.vertical: ScrollBar {}
        delegate: PixelFrame {
            required property var modelData
            theme: page.theme
            width: list.width - 12
            height: content.implicitHeight + 28
            ColumnLayout {
                id: content
                width: parent.width
                spacing: 6
                Text { text: modelData.name; color: page.theme.text; font.pixelSize: 15; font.bold: true; wrapMode: Text.Wrap; Layout.fillWidth: true }
                Text { text: modelData.desc || ""; color: page.theme.muted; font.pixelSize: 14; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
        }
        Text { anchors.centerIn: parent; width: parent.width - 24; text: "No achievements unlocked yet"; visible: list.count === 0; color: page.theme.muted; font.pixelSize: 14; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter }
    }
}

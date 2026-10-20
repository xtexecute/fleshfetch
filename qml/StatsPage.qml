import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: page
    required property var theme
    spacing: 12
    SectionTitle { theme: page.theme; text: "Statistics" }
    ScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        contentWidth: availableWidth
        clip: true
        TextArea {
            text: game.live.statsText || "No statistics yet"
            readOnly: true
            selectByMouse: true
            textFormat: TextEdit.PlainText
            wrapMode: TextEdit.Wrap
            font.family: page.theme.mono
            font.pixelSize: 14
            color: page.theme.text
            selectionColor: page.theme.accent
            selectedTextColor: "#202020"
            background: null
        }
    }
}

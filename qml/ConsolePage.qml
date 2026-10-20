import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: page
    required property var theme
    property var history: []
    property int historyIndex: 0
    property string draft: ""
    spacing: 10
    RowLayout {
        Layout.fillWidth: true
        SectionTitle { theme: page.theme; text: "Console"; Layout.fillWidth: true }
        PixelButton { theme: page.theme; text: "Clear"; onClicked: game.clearConsole() }
    }
    ScrollView {
        id: outputScroll
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        contentWidth: availableWidth
        TextArea {
            id: output
            text: game.consoleHtml
            readOnly: true
            selectByMouse: true
            textFormat: TextEdit.RichText
            wrapMode: TextEdit.Wrap
            color: page.theme.text
            font.family: page.theme.mono
            font.pixelSize: 13
            selectionColor: page.theme.accent
            selectedTextColor: "#202020"
            background: Rectangle { color: page.theme.surface; border.color: page.theme.line }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        PixelField {
            id: command
            theme: page.theme
            Layout.fillWidth: true
            placeholderText: "Command"
            Accessible.name: "Console command"
            font.family: page.theme.mono
            onAccepted: page.execute()
            Keys.onUpPressed: {
                if (page.historyIndex === page.history.length) page.draft = text
                if (page.historyIndex > 0) text = page.history[--page.historyIndex]
            }
            Keys.onDownPressed: {
                if (page.historyIndex < page.history.length) {
                    page.historyIndex++
                    text = page.historyIndex === page.history.length ? page.draft : page.history[page.historyIndex]
                }
            }
        }
        PixelButton { theme: page.theme; text: "\u21b5"; tooltip: "Execute command"; Accessible.name: "Execute command"; enabled: command.text.trim().length > 0; onClicked: page.execute() }
    }
    function execute() {
        const text = command.text.trim()
        if (!text) return
        history = history.concat([text]).slice(-100)
        historyIndex = history.length
        draft = ""
        game.executeCommand(text)
        command.clear()
        command.forceActiveFocus()
        Qt.callLater(function() { outputScroll.contentItem.contentY = Math.max(0, outputScroll.contentItem.contentHeight - outputScroll.availableHeight) })
    }
}

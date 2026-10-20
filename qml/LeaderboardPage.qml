import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: page
    required property var theme
    readonly property var scoresState: game.leaderboard.state
    spacing: 12
    Component.onCompleted: game.leaderboard.refresh()
    RowLayout {
        Layout.fillWidth: true
        SectionTitle { theme: page.theme; text: "Leaderboard"; Layout.fillWidth: true }
        BusyIndicator { running: page.scoresState.busy; visible: running; implicitWidth: 28; implicitHeight: 28 }
        PixelButton { theme: page.theme; text: "\u21bb"; tooltip: "Refresh leaderboard"; enabled: !page.scoresState.busy; onClicked: game.leaderboard.refresh() }
    }
    RowLayout {
        Layout.fillWidth: true
        PixelField { id: username; theme: page.theme; text: page.scoresState.username || ""; placeholderText: "Player name"; maximumLength: 64; Layout.fillWidth: true }
        PixelButton { theme: page.theme; text: "Submit score"; enabled: !page.scoresState.busy && page.scoresState.configured; onClicked: game.leaderboard.submit(username.text) }
    }
    Text { text: page.scoresState.message || ""; visible: text.length > 0; color: page.theme.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
    RowLayout {
        Layout.fillWidth: true
        Text { text: "Player"; color: page.theme.muted; Layout.fillWidth: true }
        Text { text: "Flesh"; color: page.theme.muted; Layout.preferredWidth: 130; horizontalAlignment: Text.AlignRight }
    }
    ListView {
        id: scores
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        model: page.scoresState.rows || []
        ScrollBar.vertical: ScrollBar {}
        delegate: Rectangle {
            required property var modelData
            required property int index
            width: scores.width
            height: 56
            color: index % 2 ? page.theme.surface : page.theme.canvas
            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text { text: modelData.username || "?"; textFormat: Text.PlainText; color: page.theme.text; Layout.fillWidth: true; elide: Text.ElideRight }
                    Text { text: modelData.last_update || modelData.created_at || ""; textFormat: Text.PlainText; color: page.theme.muted; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                }
                Text { text: Number(modelData.flesh_amount === undefined ? modelData.flesh || 0 : modelData.flesh_amount).toLocaleString(Qt.locale(), 'f', 0); color: page.theme.text; Layout.preferredWidth: 130; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight }
            }
        }
        Text { anchors.centerIn: parent; text: "No entries yet"; visible: !page.scoresState.busy && page.scoresState.configured && scores.count === 0; color: page.theme.muted }
    }
}

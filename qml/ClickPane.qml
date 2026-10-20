import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: pane
    required property var theme
    property var live: game.live
    spacing: 12
    SectionTitle { theme: pane.theme; text: pane.live.title || "Fleshfetch"; Layout.fillWidth: true; font.pixelSize: 22 }
    Text { text: pane.live.saveName || "No active save"; color: pane.theme.muted; font.pixelSize: 14; Layout.fillWidth: true; elide: Text.ElideRight }
    ScrollView {
        id: currencyScroll
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(currencyRows.implicitHeight, pane.height * 0.34)
        contentWidth: availableWidth
        clip: true
        Grid {
            id: currencyRows
            objectName: "currencyTiles"
            width: currencyScroll.availableWidth
            columns: Math.max(1, Math.floor((width + 8) / 132))
            columnSpacing: 8
            rowSpacing: 8
            Repeater {
                model: pane.live.currencies || []
                delegate: PixelFrame {
                    required property var modelData
                    theme: pane.theme
                    width: (currencyRows.width - (currencyRows.columns - 1) * currencyRows.columnSpacing) / currencyRows.columns
                    height: 128
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 2
                        Text { text: modelData.name || modelData.id; color: pane.theme.muted; font.pixelSize: 14; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight; Layout.fillWidth: true }
                        Text { text: pane.amount(modelData.amount); color: pane.theme.text; font.family: pane.theme.mono; font.pixelSize: 22; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                        Text { text: pane.amount(modelData.cpc) + " / click\n" + pane.amount(modelData.cps) + " / sec"; color: pane.theme.muted; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.Wrap; maximumLineCount: 4; elide: Text.ElideRight }
                    }
                }
            }
        }
    }
    PixelFrame {
        theme: pane.theme
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 120
        inset: 8
        Item {
            id: stage
            anchors.fill: parent
            clip: true
            AbstractButton {
                id: clickTarget
                objectName: "clickTarget"
                anchors.fill: parent
                hoverEnabled: true
                focusPolicy: Qt.StrongFocus
                Accessible.name: "Fetch flesh"
                onClicked: game.click()
                background: Rectangle {
                    color: "transparent"
                    border.width: clickTarget.activeFocus ? 2 : 0
                    border.color: pane.theme.accent
                }
                contentItem: Image {
                    source: pane.live.imageUrl || "../flesh.png"
                    fillMode: Image.PreserveAspectFit
                    smooth: false
                    mipmap: false
                    scale: clickTarget.down ? 0.93 : clickTarget.hovered ? 1.025 : 1
                    Behavior on scale { NumberAnimation { duration: Number(game.preferences.squish_ms || 100); easing.type: Easing.OutQuad } }
                }
            }
        }
    }
    Text {
        text: pane.amount(pane.live.totalClicks) + " total clicks"
        color: pane.theme.muted
        font.pixelSize: 13
        horizontalAlignment: Text.AlignHCenter
        Layout.fillWidth: true
        elide: Text.ElideRight
    }
    function amount(value) {
        const n = Number(value || 0)
        return isFinite(n) ? n.toLocaleString(Qt.locale(), 'f', n % 1 === 0 ? 0 : 1) : String(value)
    }
}

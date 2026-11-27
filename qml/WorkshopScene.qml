import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "CurrencyFormat.js" as CurrencyFormat

Item {
    id: scene
    objectName: "workshopScene"
    required property var theme
    property var state: game.live.workshop || ({})
    property var items: game.catalog.shopItems || []
    readonly property bool animate: visible && Qt.application.state === Qt.ApplicationActive
    implicitHeight: 196
    clip: true

    ColumnLayout {
        anchors.fill: parent
        spacing: 6
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: scene.state.title || "One very ordinary click"
                color: scene.theme.text
                font.pixelSize: 15
                font.bold: true
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Text {
                text: (scene.state.delivered || 0) + " / " + (scene.state.total || 7) + " upgrades"
                color: scene.theme.muted
                font.pixelSize: 12
            }
        }
        ListView {
            id: bench
            objectName: "workshopBench"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 112
            orientation: ListView.Horizontal
            boundsBehavior: Flickable.StopAtBounds
            clip: true
            spacing: 4
            model: scene.items
            ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }
            Rectangle {
                width: Math.max(bench.width, bench.contentWidth)
                height: 4
                y: bench.height - 47
                color: scene.theme.line
                z: -1
            }
            delegate: Item {
                id: machine
                required property var modelData
                required property int index
                readonly property int owned: ((game.live.upgradeInfo || {})[modelData.id] || {}).owned || 0
                width: 106
                height: bench.height
                objectName: "workshop:" + modelData.id
                Image {
                    id: art
                    objectName: "equipment:" + machine.modelData.id
                    source: "image://skins/equipment/" + machine.modelData.art
                    width: 64
                    height: 64
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: bench.height - 111
                    opacity: machine.owned > 0 ? 1 : 0.25
                    smooth: false
                    mipmap: false
                    fillMode: Image.PreserveAspectFit
                    SequentialAnimation on y {
                        running: scene.animate && machine.owned > 0 && machine.modelData.art !== 3
                        loops: Animation.Infinite
                        NumberAnimation { to: bench.height - 114; duration: 420 + machine.index * 55; easing.type: Easing.InOutSine }
                        NumberAnimation { to: bench.height - 111; duration: 420 + machine.index * 55; easing.type: Easing.InOutSine }
                    }
                    SequentialAnimation {
                        id: delivered
                        NumberAnimation { target: art; property: "scale"; from: 0.7; to: 1.18; duration: 180; easing.type: Easing.OutCubic }
                        NumberAnimation { target: art; property: "scale"; to: 1; duration: 170; easing.type: Easing.OutBack }
                    }
                }
                Text {
                    text: machine.owned > 0 ? "x" + machine.owned : "--"
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: bench.height - 44
                    color: machine.owned > 0 ? scene.theme.accent : scene.theme.muted
                    font.pixelSize: 12
                    font.bold: true
                }
                Text {
                    text: machine.modelData.name
                    x: 2
                    y: bench.height - 26
                    width: parent.width - 4
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                    color: machine.owned > 0 ? scene.theme.text : scene.theme.muted
                    font.pixelSize: 11
                }
                HoverHandler { id: hover }
                ToolTip.visible: hover.hovered
                ToolTip.text: machine.modelData.name + ": " + machine.owned + " owned"
                Connections {
                    target: game
                    function onUpgradePurchased(uid) {
                        if (uid === machine.modelData.id) delivered.restart()
                    }
                    function onClicked() {
                        if (machine.modelData.art === 0 && machine.owned > 0) delivered.restart()
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: scene.state.complete ? "Business is booming." : "Next upgrade: " + ((scene.state.goal || {}).name || "Spring Glove")
                color: scene.state.complete ? (scene.theme.dark ? "#55b8a5" : "#26786a") : scene.theme.muted
                font.pixelSize: 12
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            PixelButton {
                theme: scene.theme
                visible: !scene.state.complete
                text: "Buy " + CurrencyFormat.format(Math.ceil((scene.state.goal || {}).cost || 10), game.preferences.show_full_numbers) + " " + ((scene.state.goal || {}).currency || "Flesh")
                implicitHeight: 30
                enabled: (scene.state.goal || {}).available === true && (scene.state.goal || {}).progress >= 1
                tooltip: "Buy " + ((scene.state.goal || {}).name || "equipment") + " with " + ((scene.state.goal || {}).currency || "Flesh")
                onClicked: game.buy(scene.state.goal.id)
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 3
            color: scene.theme.line
            Rectangle {
                height: parent.height
                width: parent.width * (scene.state.complete ? 1 : ((scene.state.goal || {}).progress || 0))
                color: scene.state.complete ? "#55b8a5" : scene.theme.accent
                Behavior on width { NumberAnimation { duration: 120 } }
            }
        }
    }
    Connections {
        target: game
        function onUpgradePurchased(uid) {
            for (let i = 0; i < scene.items.length; ++i) {
                if (scene.items[i].id === uid) {
                    bench.positionViewAtIndex(i, ListView.Contain)
                    break
                }
            }
        }
    }
}

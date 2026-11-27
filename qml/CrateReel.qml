import QtQuick

Item {
    id: reel
    objectName: "crateReel"
    required property var theme
    signal settled()
    property var entries: []
    property real offset: 0
    property real targetOffset: 0
    property int winnerIndex: -1
    property int previousIndex: -1
    property bool running: false
    readonly property int cardWidth: 108
    readonly property int stride: 116
    readonly property int centerIndex: Math.max(0, Math.min(entries.length - 1, Math.floor((offset + width / 2) / stride)))
    readonly property var currentItem: entries[centerIndex] || ({})
    implicitHeight: 154

    function weightedItem(pool) {
        let total = 0
        for (const item of pool) total += Number(item.weight || 1)
        let roll = Math.random() * total
        for (const item of pool) {
            roll -= Number(item.weight || 1)
            if (roll <= 0) return item
        }
        return pool[pool.length - 1]
    }

    function start(pool, winner) {
        cancel()
        const source = pool && pool.length ? pool : [winner]
        const sequence = []
        winnerIndex = 33 + Math.floor(Math.random() * 6)
        for (let i = 0; i < winnerIndex + 7; ++i) sequence.push(weightedItem(source))
        sequence[winnerIndex] = winner
        entries = sequence
        offset = stride
        previousIndex = centerIndex
        targetOffset = winnerIndex * stride + cardWidth / 2 - width / 2 + (Math.random() - 0.5) * cardWidth * 0.38
        running = true
        spin.start()
    }

    function finish() {
        if (!running) return
        spin.stop()
        offset = targetOffset
        running = false
        settled()
    }

    function cancel() {
        running = false
        spin.stop()
    }

    onCenterIndexChanged: {
        if (running && centerIndex !== previousIndex) game.playEffectSound("roll")
        previousIndex = centerIndex
    }
    onWidthChanged: {
        if (!running && winnerIndex >= 0)
            offset = winnerIndex * stride + cardWidth / 2 - width / 2
    }

    Rectangle { anchors.fill: parent; color: reel.theme.canvas; border.width: 2; border.color: reel.theme.line }
    Item {
        anchors.fill: parent
        anchors.margins: 5
        clip: true
        Row {
            x: -reel.offset - 5
            y: 10
            spacing: 8
            Repeater {
                model: reel.entries
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    width: reel.cardWidth
                    height: 124
                    color: !reel.running && index === reel.winnerIndex ? reel.theme.hover : reel.theme.surface
                    border.width: !reel.running && index === reel.winnerIndex ? 2 : 1
                    border.color: modelData.color || reel.theme.line
                    Image {
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 8
                        width: 62
                        height: 62
                        sourceSize: Qt.size(72, 72)
                        source: modelData.icon || "image://skins/loot/crate/Common"
                        fillMode: Image.PreserveAspectFit
                        smooth: false
                    }
                    Text {
                        x: 6
                        y: 76
                        width: parent.width - 12
                        height: 32
                        text: modelData.name + (modelData.count > 1 ? " x" + modelData.count : "")
                        color: reel.theme.text
                        font.pixelSize: 12
                        font.bold: true
                        wrapMode: Text.Wrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    Rectangle { x: 1; y: parent.height - 5; width: parent.width - 2; height: 4; color: modelData.color || reel.theme.line }
                }
            }
        }
    }
    Rectangle { x: Math.round((parent.width - 3) / 2); width: 3; height: 13; color: reel.theme.accent }
    Rectangle { x: Math.round((parent.width - 3) / 2); y: parent.height - height; width: 3; height: 13; color: reel.theme.accent }
    NumberAnimation {
        id: spin
        target: reel
        property: "offset"
        to: reel.targetOffset
        duration: 4300
        easing.type: Easing.OutQuint
        onFinished: reel.finish()
    }
}

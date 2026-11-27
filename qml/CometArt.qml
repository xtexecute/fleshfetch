import QtQuick

Item {
    id: art
    property real fleshLeft: 0
    property real fleshTop: 0
    property real fleshWidth: 0
    property real fleshHeight: 0
    property real kickX: 0
    property real kickY: 0
    property real ambientY: 0
    property real tailWhip: 0
    property real glowLevel: 0
    property bool fastTail: false
    property int tailFrame: 0
    property int fragmentCursor: 0
    property int moteCursor: 0
    property int burstCursor: 0
    readonly property int pixelSize: Math.max(2, Math.round(fleshWidth * 0.72 / 40))

    function react() {
        settle.stop()
        kickX = (Math.random() - 0.5) * 12
        kickY = (Math.random() - 0.5) * 10
        tailWhip = Math.max(-4, Math.min(4, -kickY / pixelSize + (Math.random() - 0.5) * 3))
        glowDecay.stop()
        glowLevel = Math.min(1, glowLevel + 0.35)
        glowDecay.start()
        fastTail = true
        fastTailTimer.restart()
        settle.start()
        for (let i = 0; i < 16; ++i) {
            const fragment = fragments.itemAt(fragmentCursor)
            fragmentCursor = (fragmentCursor + 1) % fragments.count
            if (fragment) fragment.launch()
        }
        for (let i = 0; i < 14; ++i) {
            const spark = burst.itemAt(burstCursor)
            burstCursor = (burstCursor + 1) % burst.count
            if (spark) spark.launch()
        }
    }

    onVisibleChanged: {
        if (visible) return
        settle.stop()
        glowDecay.stop()
        fastTailTimer.stop()
        kickX = 0
        kickY = 0
        ambientY = 0
        tailWhip = 0
        glowLevel = 0
        fastTail = false
        tailFrame = 0
        for (let i = 0; i < fragments.count; ++i) {
            const fragment = fragments.itemAt(i)
            if (fragment) fragment.clear()
        }
        for (let i = 0; i < motes.count; ++i) {
            const mote = motes.itemAt(i)
            if (mote) mote.clear()
        }
        for (let i = 0; i < burst.count; ++i) {
            const spark = burst.itemAt(i)
            if (spark) spark.clear()
        }
    }

    ParallelAnimation {
        id: settle
        NumberAnimation { target: art; property: "kickX"; to: 0; duration: 280; easing.type: Easing.OutCubic }
        NumberAnimation { target: art; property: "kickY"; to: 0; duration: 280; easing.type: Easing.OutCubic }
        NumberAnimation { target: art; property: "tailWhip"; to: 0; duration: 350; easing.type: Easing.OutBack }
    }

    NumberAnimation {
        id: glowDecay
        target: art
        property: "glowLevel"
        to: 0
        duration: 950
        easing.type: Easing.OutQuad
    }

    Timer {
        id: fastTailTimer
        interval: 850
        onTriggered: art.fastTail = false
    }

    Timer {
        interval: art.fastTail ? 83 : 250
        repeat: true
        running: art.visible
        onTriggered: {
            art.tailFrame = (art.tailFrame + 1) % 8
            trailCanvas.requestPaint()
        }
    }

    SequentialAnimation on ambientY {
        running: art.visible
        loops: Animation.Infinite
        NumberAnimation { from: -2; to: 2; duration: 1600; easing.type: Easing.InOutSine }
        NumberAnimation { from: 2; to: -2; duration: 1600; easing.type: Easing.InOutSine }
    }

    Item {
        id: tail
        opacity: 0.80 + art.glowLevel * 0.20
        x: Math.round(art.fleshLeft + art.fleshWidth * 0.14 - width)
        y: Math.round(art.fleshTop + art.fleshHeight * 0.24)
        width: 40 * art.pixelSize
        height: 30 * art.pixelSize
        Canvas {
            id: trailCanvas
            anchors.fill: parent
            onPaint: {
                const ctx = getContext("2d")
                ctx.reset()
                ctx.scale(art.pixelSize, art.pixelSize)
                function pixel(x, y, color) {
                    if (x < 0 || x >= 40 || y < 0 || y >= 30) return
                    ctx.fillStyle = color
                    ctx.fillRect(x, y, 1, 1)
                }
                for (let x = 2; x < 40; ++x) {
                    const bend = Math.round(art.tailWhip * (1 - x / 40))
                    const center = 15 - Math.floor(x / 15) + bend
                    const radius = 2 + Math.floor(x / 6)
                    for (let y = center - radius; y <= center + radius; ++y) {
                        const distance = Math.abs(y - center)
                        if (x < 29 && distance > 2
                                && (x + art.tailFrame * 2 + distance * 3) % 9 < 3) continue
                        pixel(x, y, distance === radius ? "#8061b7"
                            : distance <= 2 && x > 7
                                ? (x + art.tailFrame * 4) % 17 < 5 ? "#ffffff" : "#f0e3ff"
                                : "#c8a9ed")
                    }
                }
                for (let x = 4; x < 37; ++x) {
                    const bend = Math.round(art.tailWhip * (1 - x / 40))
                    const upper = 2 + Math.floor(x / 5) + bend
                    if ((x + art.tailFrame * 2) % 8 !== 0) pixel(x, upper, "#e0d4fa")
                    if (x > 12 && x % 7 < 6) pixel(x, upper + 1, "#a987d7")
                }
                for (let x = 1; x < 36; ++x) {
                    const bend = Math.round(art.tailWhip * (1 - x / 40))
                    const lower = 28 - Math.floor(x / 5) + bend
                    if ((x + art.tailFrame * 2) % 7 !== 0) pixel(x, lower, "#b596e2")
                    if (x > 11 && x % 6 < 5) pixel(x, lower - 1, "#e0d4fa")
                }
                pixel(1, 14, "#f5efff")
                pixel(6, 23, "#b9a5db")
                pixel(9, 4, "#d6c9f0")
            }
        }
    }

    Timer {
        interval: 90
        repeat: true
        running: art.visible
        onTriggered: {
            const mote = motes.itemAt(art.moteCursor)
            art.moteCursor = (art.moteCursor + 1) % motes.count
            if (mote) mote.launch()
        }
    }

    Repeater {
        id: motes
        model: 32
        delegate: Rectangle {
            id: mote
            property real life: 1
            property real startX: 0
            property real startY: 0
            property real dx: 0
            property real dy: 0
            width: art.pixelSize * (index % 4 === 0 ? 2 : 1)
            height: width
            x: Math.round(startX + dx * life)
            y: Math.round(startY + dy * life)
            visible: life < 1
            opacity: (1 - life) * 0.8
            color: index % 3 === 0 ? "#f5efff" : index % 3 === 1 ? "#c8baf0" : "#8d78bd"
            function launch() {
                drift.stop()
                const lane = index % 3
                startX = tail.x + tail.width * (0.62 + Math.random() * 0.30)
                startY = tail.y + tail.height * (lane === 0 ? 0.28 : lane === 1 ? 0.52 : 0.76)
                dx = -art.fleshWidth * (0.28 + Math.random() * 0.28)
                dy = (lane - 1) * (5 + Math.random() * 7) * art.pixelSize
                life = 0
                drift.start()
            }
            function clear() { drift.stop(); life = 1 }
            NumberAnimation { id: drift; target: mote; property: "life"; from: 0; to: 1; duration: 1100 }
        }
    }

    Repeater {
        id: fragments
        model: 112
        delegate: Rectangle {
            id: fragment
            property real life: 1
            property real startX: 0
            property real startY: 0
            property real dx: 0
            property real dy: 0
            width: art.pixelSize * (index % 5 === 0 ? 3 : index % 3 === 0 ? 2 : 1)
            height: art.pixelSize
            x: Math.round(startX + dx * life)
            y: Math.round(startY + dy * life)
            opacity: life < 0.65 ? 1 : (1 - life) / 0.35
            visible: life < 1
            color: index % 4 === 0 ? "#ffffff" : index % 4 === 1 ? "#d8c8f2"
                : index % 4 === 2 ? "#ad9aca" : "#f0eaff"
            function launch() {
                flight.stop()
                startX = tail.x + tail.width * (0.36 + Math.random() * 0.54)
                startY = tail.y + tail.height * (0.22 + Math.random() * 0.56)
                dx = -art.fleshWidth * (0.22 + Math.random() * 0.48)
                dy = (Math.random() - 0.5) * art.fleshHeight * 0.44
                life = 0
                flight.start()
            }
            function clear() { flight.stop(); life = 1 }
            NumberAnimation { id: flight; target: fragment; property: "life"; from: 0; to: 1; duration: 620 + index * 5 }
        }
    }

    Repeater {
        id: burst
        model: 72
        delegate: Item {
            id: spark
            property real life: 1
            property real startX: 0
            property real startY: 0
            property real dx: 0
            property real dy: 0
            width: 3 * art.pixelSize
            height: width
            x: Math.round(startX + dx * life)
            y: Math.round(startY + dy * life)
            visible: life < 1
            opacity: life < 0.36 ? 1 : (1 - life) / 0.64
            Rectangle {
                width: spark.width
                height: art.pixelSize
                anchors.verticalCenter: parent.verticalCenter
                color: index % 3 === 0 ? "#ffffff" : "#dac8ff"
            }
            Rectangle {
                visible: index % 4 === 0
                width: art.pixelSize
                height: spark.height
                anchors.horizontalCenter: parent.horizontalCenter
                color: "#f5efff"
            }
            function launch() {
                flare.stop()
                const angle = Math.random() * Math.PI * 2
                startX = art.fleshLeft + art.fleshWidth * (0.51 + Math.cos(angle) * 0.44) - width / 2
                startY = art.fleshTop + art.fleshHeight * (0.50 + Math.sin(angle) * 0.42) - height / 2
                dx = Math.cos(angle) * (18 + Math.random() * 23) * art.pixelSize
                dy = Math.sin(angle) * (13 + Math.random() * 19) * art.pixelSize
                life = 0
                flare.start()
            }
            function clear() { flare.stop(); life = 1 }
            NumberAnimation { id: flare; target: spark; property: "life"; from: 0; to: 1; duration: 440 }
        }
    }
}

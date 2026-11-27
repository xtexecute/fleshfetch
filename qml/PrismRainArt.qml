import QtQuick

Item {
    id: art
    objectName: "prismRainArt"
    required property Item frontLayer
    readonly property real extent: Math.max(1, Math.min(width, height))
    readonly property int pixelSize: Math.max(1, Math.floor(extent / 210))
    readonly property vector2d emitter: Qt.vector2d(prism.x + 26 * pixelSize,
                                                   prism.y + 30 * pixelSize)
    readonly property vector2d viewport: Qt.vector2d(width, height)
    property int cursor: 0
    property real energy: 0
    property real sweep: 1
    property real floatOffset: 0
    readonly property var colors: ["#ea7284", "#f4a566", "#f2d583", "#8cd2a5",
                                   "#7bcfdd", "#84a4e9", "#ba91dd"]

    function drop(x, y, shower) {
        for (let i = 0; i < drops.count; ++i) {
            const shard = drops.itemAt(cursor)
            cursor = (cursor + 1) % drops.count
            if (!shard || shard.alive) continue
            shard.launch(x, y, shower)
            return
        }
    }

    function strike(x, y) {
        if (!visible) return
        fade.stop()
        energy = Math.min(1, energy + 0.44)
        fade.start()
        travel.restart()
        for (let i = 0; i < 6; ++i) drop(x, y, true)
    }

    onVisibleChanged: {
        if (visible) return
        fade.stop()
        travel.stop()
        energy = 0
        sweep = 1
        cursor = 0
        for (let i = 0; i < drops.count; ++i) drops.itemAt(i)?.clear()
    }
    NumberAnimation {
        id: fade
        target: art
        property: "energy"
        to: 0
        duration: 1350
        easing.type: Easing.OutQuad
    }
    NumberAnimation {
        id: travel
        target: art
        property: "sweep"
        from: 0; to: 1
        duration: 780
    }
    SequentialAnimation on floatOffset {
        running: art.visible
        loops: Animation.Infinite
        NumberAnimation { from: -1; to: 1; duration: 1900; easing.type: Easing.InOutSine }
        NumberAnimation { from: 1; to: -1; duration: 1900; easing.type: Easing.InOutSine }
    }
    Timer {
        interval: 330
        repeat: true
        running: art.visible
        onTriggered: art.drop(art.width * (0.07 + Math.random() * 0.86), -15, false)
    }

    ShaderEffect {
        anchors.fill: parent
        fragmentShader: "shaders/prism-rain.frag.qsb"
        property vector2d viewport: art.viewport
        property vector2d emitter: art.emitter
        property real extent: art.extent
        property real energy: art.energy
        property real sweep: art.sweep
        property real pixelSize: art.pixelSize
    }

    Item {
        parent: art.frontLayer
        visible: art.visible
        anchors.fill: parent
        Image {
            id: prism
            objectName: "rainPrism"
            x: Math.round((art.width - width) / 2)
            y: Math.round((art.height - art.extent) / 2 + art.extent * 0.015 + art.floatOffset)
            width: 52 * art.pixelSize
            height: 38 * art.pixelSize
            source: "../assets/skins/prism-rain-prism.png"
            smooth: false
            mipmap: false
            Image {
                x: 17 * art.pixelSize
                y: 2 * art.pixelSize
                width: 9 * art.pixelSize
                height: width
                smooth: false
                source: "../assets/skins/prism-rain-glint.png"
                opacity: 0.24 + art.energy * 0.76
            }
        }

        Repeater {
            id: drops
            model: 96
            delegate: Item {
                id: shard
                objectName: "prismRainDrop"
                property real age: 1
                property real startX: 0
                property real startY: 0
                property real vx: 0
                property real vy: 0
                property real flightTime: 1
                property int hue: 0
                property bool shower: false
                readonly property bool alive: flight.running
                readonly property real seconds: age * flight.duration / 1000
                readonly property real flightSeconds: Math.min(seconds, flightTime)
                readonly property real gravity: art.extent * 1.65
                readonly property real landing: Math.max(0, (seconds - flightTime) / 0.38)
                x: Math.round(startX + vx * flightSeconds)
                y: Math.round(startY + vy * flightSeconds + 0.5 * gravity * flightSeconds * flightSeconds)
                width: 9 * art.pixelSize
                height: 14 * art.pixelSize
                visible: alive

                function launch(x, y, burst) {
                    shower = burst
                    startX = x - width / 2
                    startY = y - height / 2
                    hue = Math.floor(Math.random() * 7)
                    vx = (Math.random() - 0.5) * art.extent * (burst ? 0.72 : 0.13)
                    vy = burst ? -art.extent * (0.16 + Math.random() * 0.34) : art.extent * 0.24
                    const distance = Math.max(1, art.height - 9 * art.pixelSize - startY)
                    flightTime = (Math.sqrt(vy * vy + 2 * gravity * distance) - vy) / gravity
                    flight.duration = Math.round((flightTime + 0.38) * 1000)
                    age = 0
                    flight.start()
                }
                function clear() {
                    flight.stop()
                    age = 1
                }
                NumberAnimation {
                    id: flight
                    target: shard
                    property: "age"
                    from: 0; to: 1
                }
                Rectangle {
                    visible: shard.landing === 0
                    x: 4 * art.pixelSize
                    y: -height + 4 * art.pixelSize
                    width: art.pixelSize
                    height: (shard.shower ? 13 : 7) * art.pixelSize
                    color: art.colors[shard.hue]
                    opacity: shard.shower ? 0.24 : 0.11
                }
                Image {
                    source: "../assets/skins/prism-rain-drops.png"
                    sourceClipRect: Qt.rect(9 * (Math.floor(shard.seconds * 5) % 3), shard.hue * 14, 9, 14)
                    width: parent.width
                    height: parent.height
                    smooth: false
                    visible: shard.landing === 0
                    opacity: shard.shower ? 0.95 : 0.55
                }
                Repeater {
                    model: 3
                    delegate: Rectangle {
                        required property int index
                        visible: shard.landing > 0
                        width: art.pixelSize * (index === 1 ? 2 : 1)
                        height: width
                        x: Math.round(shard.width / 2 + (index - 1) * 15 * art.pixelSize * shard.landing)
                        y: Math.round(-Math.sin(shard.landing * Math.PI) * (index === 1 ? 12 : 7) * art.pixelSize)
                        color: index === 1 ? "#eef4e9" : art.colors[shard.hue]
                        opacity: 1 - shard.landing
                    }
                }
            }
        }
    }
}

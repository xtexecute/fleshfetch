import QtQuick

Item {
    id: jar
    objectName: "fireflyJarArt"
    required property Item frontLayer
    property int pixelSize: 1
    width: 112 * pixelSize
    height: 136 * pixelSize
    property real excitement: 0
    property real time: 0
    property real lastTick: 0
    property vector2d gathering: Qt.vector2d(56, 77)
    readonly property vector3d lamp0: lamp(0)
    readonly property vector3d lamp1: lamp(1)
    readonly property vector3d lamp2: lamp(2)
    readonly property vector3d lamp3: lamp(3)
    readonly property vector3d lamp4: lamp(4)
    readonly property vector3d lamp5: lamp(5)
    readonly property vector3d lamp6: lamp(6)
    readonly property vector3d lamp7: lamp(7)

    function lamp(i) {
        const clock = time
        const bug = flies.itemAt(i)
        return bug ? Qt.vector3d(bug.px, bug.py, bug.brightness) : Qt.vector3d(56, 77, 0)
    }
    function stir(x, y) {
        if (!visible) return
        gathering = Qt.vector2d(Math.max(29, Math.min(83, x / pixelSize)),
                                Math.max(45, Math.min(105, y / pixelSize)))
        decay.stop()
        excitement = Math.min(1, excitement + 0.56)
        decay.start()
        for (let i = 0; i < flies.count; ++i) {
            const fly = flies.itemAt(i)
            if (fly) fly.angle += (Math.random() - 0.5) * 1.8
        }
    }
    function reset() {
        decay.stop()
        excitement = 0
        time = 0
        lastTick = 0
        gathering = Qt.vector2d(56, 77)
        for (let i = 0; i < flies.count; ++i) flies.itemAt(i)?.reset()
    }
    onVisibleChanged: reset()
    Component.onCompleted: reset()
    NumberAnimation {
        id: decay
        target: jar
        property: "excitement"
        to: 0
        duration: 2350
        easing.type: Easing.OutQuad
    }
    Timer {
        interval: 32
        repeat: true
        running: jar.visible
        onTriggered: {
            const now = Date.now()
            const dt = jar.lastTick ? Math.min(0.065, (now - jar.lastTick) / 1000) : 0.032
            jar.lastTick = now
            jar.time += dt
            for (let i = 0; i < flies.count; ++i) flies.itemAt(i)?.step(dt)
        }
    }
    Image {
        anchors.fill: parent
        source: "../assets/skins/firefly-jar-back.png"
        smooth: false
        mipmap: false
    }
    Item {
        id: backgroundFlies
        anchors.fill: parent
    }
    Repeater {
        id: flies
        model: 16
        delegate: Item {
            id: bug
            required property int index
            objectName: "jarFirefly"
            property real px: 56
            property real py: 70
            property real vx: 0
            property real vy: 0
            property real targetX: 56
            property real targetY: 70
            property real angle: index * 2.399963
            property real nextTurn: 0
            readonly property real blink: Math.pow(0.5 + 0.5 * Math.sin(jar.time * (1.3 + index * 0.047) + index * 2.4), 2)
            readonly property real brightness: 0.24 + 0.55 * blink + jar.excitement * 0.52
            x: Math.round(px * jar.pixelSize - width / 2)
            y: Math.round(py * jar.pixelSize - height / 2)
            width: 7 * jar.pixelSize
            height: width

            function reset() {
                px = 25 + ((index * 37 + 11) % 63)
                py = 42 + ((index * 23 + 17) % 67)
                vx = 0
                vy = 0
                nextTurn = 0
                angle = index * 2.399963
            }
            function step(dt) {
                if (jar.time >= nextTurn) {
                    targetX = 22 + Math.random() * 68
                    targetY = 40 + Math.random() * 73
                    nextTurn = jar.time + 1.4 + Math.random() * 2.2
                }
                angle += dt * (0.45 + jar.excitement * 2.8) * (index % 2 ? 1 : -1)
                const ring = 11 + index % 4 * 4
                const gatherX = Math.max(21, Math.min(91, jar.gathering.x + Math.cos(angle) * ring))
                const gatherY = Math.max(39, Math.min(113, jar.gathering.y + Math.sin(angle) * ring * 0.68))
                const pull = Math.min(1, jar.excitement * 1.65)
                const goalX = targetX * (1 - pull) + gatherX * pull
                const goalY = targetY * (1 - pull) + gatherY * pull
                const rate = 1.3 + jar.excitement * 3.8
                vx += ((goalX - px) * rate - vx * 2.1 + Math.sin(jar.time * 2 + index) * 3) * dt
                vy += ((goalY - py) * rate - vy * 2.1 + Math.cos(jar.time * 1.7 + index) * 3) * dt
                const cap = 19 + jar.excitement * 32
                const speed = Math.hypot(vx, vy)
                if (speed > cap) { vx *= cap / speed; vy *= cap / speed }
                px = Math.max(20, Math.min(92, px + vx * dt))
                py = Math.max(38, Math.min(114, py + vy * dt))
            }
            Item {
                parent: bug.index % 3 === 0 ? backgroundFlies : foreground
                x: bug.x
                y: bug.y
                width: bug.width
                height: bug.height
                visible: jar.visible
                Image {
                    x: -11 * jar.pixelSize
                    y: -9 * jar.pixelSize
                    width: 29 * jar.pixelSize
                    height: width
                    source: "../assets/skins/firefly-jar-glow.png"
                    smooth: true
                    opacity: bug.brightness
                }
                Repeater {
                    model: 3
                    delegate: Rectangle {
                        required property int index
                        x: Math.round((3 - bug.vx * 0.018 * (index + 1)) * jar.pixelSize)
                        y: Math.round((5 - bug.vy * 0.018 * (index + 1)) * jar.pixelSize)
                        width: jar.pixelSize
                        height: width
                        color: "#eed889"
                        opacity: jar.excitement * (0.25 - index * 0.065)
                    }
                }
                Image {
                    anchors.fill: parent
                    source: "../assets/skins/firefly-jar-bug.png"
                    sourceClipRect: Qt.rect(7 * (Math.floor(jar.time * 8 + bug.index) % 3), 0, 7, 7)
                    smooth: false
                    mipmap: false
                    opacity: 0.70 + bug.brightness * 0.24
                    mirror: bug.vx < 0
                }
            }
        }
    }
    Item {
        id: foreground
        parent: jar.frontLayer
        x: jar.x
        y: jar.y
        width: jar.width
        height: jar.height
        visible: jar.visible
    }
    Image {
        parent: jar.frontLayer
        x: jar.x
        y: jar.y
        width: jar.width
        height: jar.height
        visible: jar.visible
        source: "../assets/skins/firefly-jar-front.png"
        smooth: false
        mipmap: false
    }
}

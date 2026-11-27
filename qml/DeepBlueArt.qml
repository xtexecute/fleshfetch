import QtQuick

Item {
    id: ocean
    objectName: "deepBlueArt"
    required property Item frontLayer
    property real fill: 0
    property real time: 0
    property real flow: 0
    property real energy: 0
    property real lastTick: 0
    property int cursor: 0
    property int bubbleCursor: 0
    readonly property real floatOffset: Math.sin(time * 0.72) * Math.min(3, height * 0.012)
    readonly property vector3d ripple0: first.localValue
    readonly property vector3d ripple1: second.localValue
    readonly property vector3d ripple2: third.localValue
    readonly property vector3d ripple3: fourth.localValue
    readonly property vector3d wake0: first.worldValue
    readonly property vector3d wake1: second.worldValue
    readonly property vector3d wake2: third.worldValue
    readonly property vector3d wake3: fourth.worldValue
    property alias caustics: lightMap
    property alias normals: normalMap

    function strike(u, v, x, y) {
        if (!visible) return
        const waves = [first, second, third, fourth]
        waves[cursor].light(u, v, x / Math.max(1, width), y / Math.max(1, height))
        cursor = (cursor + 1) % waves.length
        fade.stop()
        energy = Math.min(1, energy + 0.32)
        fade.start()
        let count = 0
        for (let i = 0; i < bubbles.count && count < 3; ++i) {
            const bubble = bubbles.itemAt(bubbleCursor)
            bubbleCursor = (bubbleCursor + 1) % bubbles.count
            if (!bubble || bubble.alive) continue
            bubble.launch(x, y)
            ++count
        }
    }
    onVisibleChanged: {
        if (visible) return
        fade.stop()
        energy = 0
        time = 0
        flow = 0
        lastTick = 0
        cursor = 0
        bubbleCursor = 0
        for (const wave of [first, second, third, fourth]) wave.clear()
        for (let i = 0; i < bubbles.count; ++i) bubbles.itemAt(i)?.clear()
    }
    NumberAnimation {
        id: fade
        target: ocean
        property: "energy"
        to: 0
        duration: 2600
        easing.type: Easing.OutQuad
    }
    Timer {
        interval: 32
        repeat: true
        running: ocean.visible
        onTriggered: {
            const now = Date.now()
            const dt = ocean.lastTick ? Math.min(0.065, (now - ocean.lastTick) / 1000) : 0.032
            ocean.lastTick = now
            ocean.time += dt
            ocean.flow += dt * (0.28 + ocean.energy * 0.55)
        }
    }
    component Wave: QtObject {
        id: wave
        property real u: 0.5
        property real v: 0.5
        property real x: 0.5
        property real y: 0.5
        property real age: 1
        readonly property vector3d localValue: Qt.vector3d(u, v, age)
        readonly property vector3d worldValue: Qt.vector3d(x, y, age)
        property NumberAnimation travel: NumberAnimation {
            target: wave
            property: "age"
            from: 0; to: 1
            duration: 1800
        }
        function light(a, b, c, d) { travel.stop(); u = a; v = b; x = c; y = d; travel.start() }
        function clear() { travel.stop(); age = 1 }
    }
    Wave { id: first }
    Wave { id: second }
    Wave { id: third }
    Wave { id: fourth }
    Image { id: lightMap; visible: false; smooth: true; source: ocean.visible ? "../assets/skins/deep-blue-caustics.png" : "" }
    Image { id: normalMap; visible: false; smooth: true; source: ocean.visible ? "../assets/skins/deep-blue-normals.png" : "" }
    ShaderEffect {
        objectName: "deepBlueWater"
        anchors.fill: parent
        fragmentShader: "shaders/deep-blue-water.frag.qsb"
        property var caustics: ocean.caustics
        property vector2d viewport: Qt.vector2d(width, height)
        property real time: ocean.time
        property real flow: ocean.flow
        property real energy: ocean.energy
        property real fill: ocean.fill
        property vector3d wake0: ocean.wake0
        property vector3d wake1: ocean.wake1
        property vector3d wake2: ocean.wake2
        property vector3d wake3: ocean.wake3
        Behavior on fill { NumberAnimation { duration: 340; easing.type: Easing.OutQuad } }
    }
    Item {
        parent: ocean.frontLayer
        anchors.fill: parent
        visible: ocean.visible
        Repeater {
            id: bubbles
            model: 72
            delegate: Image {
                id: bubble
                objectName: "deepBlueBubble"
                property real age: 1
                property real startX: 0
                property real startY: 0
                property real drift: 0
                property real rise: 0
                property real phase: 0
                property int variant: 0
                readonly property bool alive: motion.running
                source: "../assets/skins/deep-blue-bubbles.png"
                sourceClipRect: Qt.rect(variant * 7, 0, 7, 7)
                width: 7
                height: 7
                smooth: false
                visible: alive
                x: Math.round(startX + drift * age + Math.sin(age * 6.0 + phase) * 5 * age)
                y: Math.round(startY - rise * age)
                opacity: Math.min(1, age * 12) * Math.min(1, (1 - age) * 4) * 0.85
                function launch(x, y) {
                    startX = x - width / 2 + (Math.random() - 0.5) * 20
                    startY = y - height / 2 + Math.random() * 8
                    drift = (Math.random() - 0.5) * 32
                    rise = 55 + Math.random() * 55
                    phase = Math.random() * 6.2831853
                    variant = Math.floor(Math.random() * 3)
                    motion.duration = Math.round(1800 + Math.random() * 1100)
                    age = 0
                    motion.start()
                }
                function clear() { motion.stop(); age = 1 }
                NumberAnimation { id: motion; target: bubble; property: "age"; from: 0; to: 1 }
            }
        }
    }
}

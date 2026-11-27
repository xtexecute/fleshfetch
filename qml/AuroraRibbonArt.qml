import QtQuick

Item {
    id: aurora
    objectName: "auroraRibbonArt"
    required property Item flesh
    required property Item frontLayer
    required property Item poolLayer
    property real fill: 0
    property real time: 0
    property real flow: 0
    property real energy: 0
    property real lastTick: 0
    property int cursor: 0
    readonly property real extent: Math.max(1, Math.min(width, height) * 0.82)
    readonly property real floatOffset: Math.sin(time * 0.82) * Math.min(4, extent * 0.015)
    readonly property vector2d center: Qt.vector2d(flesh.x + flesh.width / 2, flesh.y + flesh.height / 2)
    readonly property vector3d stroke0: first.value
    readonly property vector3d stroke1: second.value
    readonly property vector3d stroke2: third.value
    readonly property vector3d stroke3: fourth.value

    function strike(x, y) {
        if (!visible) return
        const waves = [first, second, third, fourth]
        waves[cursor].light((x - center.x) / extent, (y - center.y) / extent)
        cursor = (cursor + 1) % waves.length
        fade.stop()
        energy = Math.min(1, energy + 0.34)
        fade.start()
    }
    onVisibleChanged: {
        if (visible) return
        fade.stop()
        energy = 0
        time = 0
        flow = 0
        lastTick = 0
        cursor = 0
        for (const wave of [first, second, third, fourth]) wave.clear()
    }
    NumberAnimation {
        id: fade
        target: aurora
        property: "energy"
        to: 0
        duration: 3200
        easing.type: Easing.OutQuad
    }
    Timer {
        interval: 32
        repeat: true
        running: aurora.visible
        onTriggered: {
            const now = Date.now()
            const dt = aurora.lastTick ? Math.min(0.065, (now - aurora.lastTick) / 1000) : 0.032
            aurora.lastTick = now
            aurora.time += dt
            aurora.flow += dt * (0.22 + aurora.energy * 0.82)
        }
    }
    component Wave: QtObject {
        id: wave
        property real u: 0
        property real v: 0
        property real age: 1
        readonly property vector3d value: Qt.vector3d(u, v, age)
        property NumberAnimation travel: NumberAnimation {
            target: wave
            property: "age"
            from: 0; to: 1
            duration: 1700
        }
        function light(x, y) { travel.stop(); u = x; v = y; travel.start() }
        function clear() { travel.stop(); age = 1 }
    }
    Wave { id: first }
    Wave { id: second }
    Wave { id: third }
    Wave { id: fourth }

    component Curtain: ShaderEffect {
        fragmentShader: "shaders/aurora-ribbon.frag.qsb"
        property vector2d viewport: Qt.vector2d(width, height)
        property vector2d center: aurora.center
        property real extent: aurora.extent
        property real time: aurora.time
        property real flow: aurora.flow
        property real energy: aurora.energy
        property real front: 0
        property vector3d stroke0: aurora.stroke0
        property vector3d stroke1: aurora.stroke1
        property vector3d stroke2: aurora.stroke2
        property vector3d stroke3: aurora.stroke3
    }
    Curtain { anchors.fill: parent }
    Curtain {
        parent: aurora.frontLayer
        anchors.fill: parent
        visible: aurora.visible
        front: 1
    }
    ShaderEffect {
        parent: aurora.poolLayer
        anchors.fill: parent
        visible: aurora.visible && aurora.fill > 0
        fragmentShader: "shaders/aurora-streak.frag.qsb"
        property vector2d viewport: Qt.vector2d(width, height)
        property real fill: aurora.fill
        property real time: aurora.time
        property real flow: aurora.flow
        property real energy: aurora.energy
        Behavior on fill { NumberAnimation { duration: 340; easing.type: Easing.OutQuad } }
    }
}

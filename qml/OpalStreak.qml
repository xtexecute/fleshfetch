import QtQuick

ShaderEffect {
    id: liquid
    objectName: "opalStreak"
    property real fill: 0
    property real phase: 0
    property int cursor: 0
    readonly property real rise: height * 0.84 * Math.max(0, Math.min(1, fill / 100))
    property vector2d viewport: Qt.vector2d(Math.max(1, width), Math.max(1, height))
    readonly property vector3d ripple0: first.value
    readonly property vector3d ripple1: second.value
    readonly property vector3d ripple2: third.value
    readonly property vector3d ripple3: fourth.value
    readonly property vector3d ripple4: fifth.value
    readonly property vector3d ripple5: sixth.value
    opacity: 0.93
    fragmentShader: "shaders/opal-streak.frag.qsb"

    Behavior on fill {
        enabled: liquid.visible
        NumberAnimation { duration: 340; easing.type: Easing.OutQuad }
    }
    NumberAnimation on phase {
        running: liquid.visible && liquid.fill > 0
        from: 0; to: 6.2831853
        duration: 22000
        loops: Animation.Infinite
    }
    function splash(u) {
        if (!visible || fill <= 0) return
        const waves = [first, second, third, fourth, fifth, sixth]
        waves[cursor].splash(Math.max(0, Math.min(1, u)))
        cursor = (cursor + 1) % waves.length
    }
    onVisibleChanged: {
        if (visible) return
        for (const wave of [first, second, third, fourth, fifth, sixth]) wave.clear()
        cursor = 0
        phase = 0
    }
    component Ripple: QtObject {
        id: wave
        property real u: 0.5
        property real age: 1
        readonly property vector3d value: Qt.vector3d(u, age, 1)
        property NumberAnimation motion: NumberAnimation {
            target: wave
            property: "age"
            from: 0; to: 1
            duration: 1100
        }
        function splash(x) { motion.stop(); u = x; motion.start() }
        function clear() { motion.stop(); age = 1 }
    }
    Ripple { id: first }
    Ripple { id: second }
    Ripple { id: third }
    Ripple { id: fourth }
    Ripple { id: fifth }
    Ripple { id: sixth }
}

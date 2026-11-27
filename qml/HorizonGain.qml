import QtQuick

Item {
    id: bit
    objectName: "horizonGain"
    required property vector2d center
    required property vector2d bounds
    required property real horizonRadius
    required property string fontFamily
    property alias text: gainLabel.text
    property color tint: "#ffffff"
    property real age: 1
    property real startRadius: 0
    property real startAngle: 0
    property real turn: 0
    readonly property bool alive: fall.running
    readonly property real progress: smooth(0.14, 1, age)
    readonly property real approach: smooth(0.26, 0.98, age)
    readonly property real radius: horizonRadius * 1.015
        + Math.max(0, startRadius - horizonRadius * 1.015) * Math.pow(1 - progress, 1.65)
    readonly property real angle: startAngle + turn * progress
    readonly property real normalX: Math.cos(angle)
    readonly property real normalY: Math.sin(angle)
    readonly property real radialScale: 1 + approach * 0.95
    readonly property real tangentScale: 1 - approach * 0.70
    readonly property real xx: tangentScale + (radialScale - tangentScale) * normalX * normalX
    readonly property real xy: (radialScale - tangentScale) * normalX * normalY
    readonly property real yy: tangentScale + (radialScale - tangentScale) * normalY * normalY
    width: gainLabel.implicitWidth
    height: gainLabel.implicitHeight
    x: center.x + normalX * radius - width / 2
    y: center.y + normalY * radius - height / 2
    opacity: Math.pow(1 - smooth(0.42, 1, age), 0.8)
    visible: alive
    transform: Matrix4x4 {
        // Stretch along the pull direction while compressing perpendicular to it.
        matrix: Qt.matrix4x4(bit.xx, bit.xy, 0, bit.width / 2 - bit.xx * bit.width / 2 - bit.xy * bit.height / 2,
                             bit.xy, bit.yy, 0, bit.height / 2 - bit.xy * bit.width / 2 - bit.yy * bit.height / 2,
                             0, 0, 1, 0,
                             0, 0, 0, 1)
    }

    function smooth(a, b, v) {
        const t = Math.max(0, Math.min(1, (v - a) / (b - a)))
        return t * t * (3 - 2 * t)
    }
    function launch(atX, atY, label, color, large) {
        fall.stop()
        text = label
        tint = color
        gainLabel.font.pixelSize = large ? 27 : 24
        let x = atX
        let y = atY + height / 2
        let dx = x - center.x, dy = y - center.y
        const distance = Math.hypot(dx, dy)
        const minimum = horizonRadius + gainLabel.font.pixelSize * 0.78
        if (distance < minimum) {
            const angle = distance > 1 ? Math.atan2(dy, dx) : -Math.PI / 2
            x = center.x + Math.cos(angle) * minimum
            y = center.y + Math.sin(angle) * minimum
        }
        x = Math.max(width / 2 + 3, Math.min(bounds.x - width / 2 - 3, x))
        y = Math.max(height / 2 + 3, Math.min(bounds.y - height / 2 - 3, y))
        dx = x - center.x
        dy = y - center.y
        startRadius = Math.hypot(dx, dy)
        startAngle = Math.atan2(dy, dx)
        turn = 0.38 + Math.random() * 0.45
        age = 0
        fall.duration = 1500 + Math.round(Math.random() * 180)
        fall.start()
    }
    function clear() { fall.stop(); age = 1 }
    NumberAnimation {
        id: fall
        target: bit
        property: "age"
        from: 0; to: 1
    }
    Text {
        id: gainLabel
        text: ""
        color: bit.tint
        font.family: bit.fontFamily
        font.bold: true
        font.pixelSize: 24
        style: Text.Outline
        styleColor: "#271217"
        layer.enabled: bit.alive
        layer.effect: ShaderEffect {
            fragmentShader: "shaders/horizon-gain.frag.qsb"
            property var source
            property real age: bit.age
            property vector2d size: Qt.vector2d(bit.width, bit.height)
            property vector2d position: Qt.vector2d(bit.x + bit.width / 2, bit.y + bit.height / 2)
            property vector2d center: bit.center
            property real radius: bit.horizonRadius
            property vector3d deformation: Qt.vector3d(bit.xx, bit.xy, bit.yy)
        }
    }
}

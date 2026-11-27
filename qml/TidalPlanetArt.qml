import QtQuick

Item {
    id: planet
    objectName: "tidalPlanetArt"
    property real fill: 0
    property real time: 0
    property real spin: 0
    property real energy: 0
    property real lastTick: 0
    property int cursor: 0
    readonly property real radius: Math.max(1, Math.min(width, height) * 0.345)
    readonly property vector2d center: Qt.vector2d(width / 2, height / 2)
    readonly property real moonAngle: -0.48 + time * 0.24
    readonly property vector2d moon: Qt.vector2d(Math.cos(moonAngle) * radius * 1.23,
                                                Math.sin(moonAngle) * radius * 0.53)
    readonly property real tideAngle: Math.atan2(moon.y, moon.x)
    readonly property real tide: 0.014 + energy * 0.018
    readonly property vector4d stroke0: first.value
    readonly property vector4d stroke1: second.value
    readonly property vector4d stroke2: third.value
    readonly property vector4d stroke3: fourth.value

    function surfacePoint(x, y) {
        let px = (Math.floor(x) + 0.5 - center.x) / radius
        let py = (Math.floor(y) + 0.5 - center.y) / radius
        const c = Math.cos(tideAngle), s = Math.sin(tideAngle)
        const along = (c * px + s * py) / (1 + tide)
        const across = (-s * px + c * py) / (1 - tide * 0.5)
        px = c * along - s * across
        py = s * along + c * across
        return Qt.vector3d(px, py, Math.sqrt(Math.max(0, 1 - px * px - py * py)))
    }
    function hitTest(x, y) {
        if (!visible) return false
        const mx = Math.floor(x) + 0.5 - center.x - moon.x
        const my = Math.floor(y) + 0.5 - center.y - moon.y
        if (Math.sin(moonAngle) > 0 && mx * mx + my * my <= Math.pow(radius * 0.105, 2)) return false
        const point = surfacePoint(x, y)
        return point.x * point.x + point.y * point.y <= 1
    }
    function strike(x, y) {
        if (!hitTest(x, y)) return
        const n = surfacePoint(x, y)
        const c = Math.cos(spin), s = Math.sin(spin)
        const waves = [first, second, third, fourth]
        waves[cursor].light(c * n.x + s * n.z, n.y, -s * n.x + c * n.z)
        cursor = (cursor + 1) % waves.length
        fade.stop()
        energy = Math.min(1, energy + 0.34)
        fade.start()
    }
    onVisibleChanged: {
        if (visible) return
        fade.stop()
        time = 0
        spin = 0
        energy = 0
        lastTick = 0
        cursor = 0
        for (const wave of [first, second, third, fourth]) wave.clear()
    }
    NumberAnimation {
        id: fade
        target: planet
        property: "energy"
        to: 0
        duration: 2800
        easing.type: Easing.OutQuad
    }
    Timer {
        interval: 32
        repeat: true
        running: planet.visible
        onTriggered: {
            const now = Date.now()
            const dt = planet.lastTick ? Math.min(0.065, (now - planet.lastTick) / 1000) : 0.032
            planet.lastTick = now
            planet.time += dt
            planet.spin += dt * (0.035 + planet.energy * 0.055)
        }
    }
    component Wave: QtObject {
        id: wave
        property vector3d normal: Qt.vector3d(0, 0, 1)
        property real age: 1
        readonly property vector4d value: Qt.vector4d(normal.x, normal.y, normal.z, age)
        property NumberAnimation travel: NumberAnimation {
            target: wave
            property: "age"
            from: 0; to: 1
            duration: 2100
        }
        function light(x, y, z) { travel.stop(); normal = Qt.vector3d(x, y, z); travel.start() }
        function clear() { travel.stop(); age = 1 }
    }
    Wave { id: first }
    Wave { id: second }
    Wave { id: third }
    Wave { id: fourth }
    Image { id: terrainImage; visible: false; smooth: true; source: planet.visible ? "../assets/skins/tidal-planet-surface.png" : "" }
    Image { id: weatherImage; visible: false; smooth: true; source: planet.visible ? "../assets/skins/tidal-planet-weather.png" : "" }
    ShaderEffect {
        objectName: "tidalPlanetRenderer"
        anchors.fill: parent
        fragmentShader: "shaders/tidal-planet.frag.qsb"
        property var surface: terrainImage
        property var weather: weatherImage
        property vector2d viewport: Qt.vector2d(width, height)
        property real radius: planet.radius
        property real time: planet.time
        property real spin: planet.spin
        property real energy: planet.energy
        property real moonAngle: planet.moonAngle
        property real tideAngle: planet.tideAngle
        property real tide: planet.tide
        property real fill: planet.fill
        property vector4d stroke0: planet.stroke0
        property vector4d stroke1: planet.stroke1
        property vector4d stroke2: planet.stroke2
        property vector4d stroke3: planet.stroke3
        Behavior on fill { NumberAnimation { duration: 340; easing.type: Easing.OutQuad } }
    }
}

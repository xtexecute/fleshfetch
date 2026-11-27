import QtQuick
import QtQuick.Window

Item {
    id: scene
    objectName: "eventHorizonArt"
    required property string source
    required property string fontFamily
    property real fill: 0
    property real time: 0
    property real lastTick: 0
    property real energy: 0
    property int impulseCursor: 0
    property int particleCursor: 0
    property int gainCursor: 0
    readonly property real halfSize: Math.max(1, Math.min(width, height) * 0.5)
    readonly property real lensScale: 1 + energy * 0.065
    readonly property real shadow: 2.603435 / 10 * halfSize * lensScale
    readonly property vector2d fleshCenter: Qt.vector2d(-3.4 + Math.sin(time * 0.18) * 0.46,
                                                       2.2 + Math.sin(time * 0.15) * 0.32)

    function hitTest(x, y) {
        const origin = mapToItem(null, 0, 0)
        return visible && game.isEventHorizonHit(x, y, width, height, lensScale,
                                                fleshCenter.x, fleshCenter.y, Screen.devicePixelRatio,
                                                origin.x, origin.y)
    }
    function emitAt(x, y) {
        for (let i = 0; i < matter.count; ++i) {
            const bit = matter.itemAt(particleCursor)
            particleCursor = (particleCursor + 1) % matter.count
            if (!bit || bit.alive) continue
            bit.launch(x, y)
            return
        }
    }
    function strike(x, y) {
        if (!visible) return
        decay.stop()
        energy = Math.min(1, energy + 0.34)
        decay.start()
        const waves = [first, second, third, fourth]
        waves[impulseCursor].start(Math.atan2(height / 2 - y, x - width / 2))
        impulseCursor = (impulseCursor + 1) % waves.length
        for (let i = 0; i < 4; ++i) emitAt(x, y)
    }
    function showGain(x, y, label, tint, large) {
        if (!visible) return
        for (let i = 0; i < gains.count; ++i) {
            const number = gains.itemAt(gainCursor)
            gainCursor = (gainCursor + 1) % gains.count
            if (!number || number.alive) continue
            number.launch(x, y, label, tint, large)
            return
        }
    }
    onVisibleChanged: {
        if (visible) return
        decay.stop()
        time = 0
        lastTick = 0
        energy = 0
        impulseCursor = 0
        particleCursor = 0
        gainCursor = 0
        for (const wave of [first, second, third, fourth]) wave.clear()
        for (let i = 0; i < matter.count; ++i) matter.itemAt(i)?.clear()
        for (let i = 0; i < gains.count; ++i) gains.itemAt(i)?.clear()
    }
    Behavior on fill { enabled: scene.visible; NumberAnimation { duration: 340; easing.type: Easing.OutQuad } }
    NumberAnimation {
        id: decay
        target: scene
        property: "energy"
        to: 0
        duration: 1600
        easing.type: Easing.OutQuad
    }
    Timer {
        interval: 16
        repeat: true
        running: scene.visible
        onTriggered: {
            const now = Date.now()
            const elapsed = scene.lastTick ? Math.min(0.065, (now - scene.lastTick) / 1000) : 0.016
            scene.lastTick = now
            scene.time += elapsed
        }
    }
    Timer {
        interval: 570
        repeat: true
        running: scene.visible && scene.fill > 0
        onTriggered: scene.emitAt(scene.width * (0.12 + Math.random() * 0.76), scene.height - 4)
    }
    component Impulse: QtObject {
        id: wave
        property real angle: 0
        property real age: 1
        readonly property vector3d value: Qt.vector3d(angle, age, 1)
        property NumberAnimation travel: NumberAnimation {
            target: wave
            property: "age"
            from: 0; to: 1
            duration: 1300
        }
        function start(phi) { travel.stop(); angle = phi; travel.start() }
        function clear() { travel.stop(); age = 1 }
    }
    Impulse { id: first }
    Impulse { id: second }
    Impulse { id: third }
    Impulse { id: fourth }

    Image { id: body; source: scene.visible ? scene.source : ""; visible: false; smooth: true }
    Image { id: paths; source: scene.visible ? "../assets/skins/event-horizon-rays.png" : ""; visible: false; smooth: true }
    Image { id: bodyPaths; source: scene.visible ? "../assets/skins/event-horizon-body-rays.png" : ""; visible: false; smooth: true }
    Image { id: nearDisc; source: scene.visible ? "../assets/skins/event-horizon-disc-0.png" : ""; visible: false; smooth: true }
    Image { id: farDisc; source: scene.visible ? "../assets/skins/event-horizon-disc-1.png" : ""; visible: false; smooth: true }
    Image { id: stars; source: scene.visible ? "../assets/skins/event-horizon-sky.png" : ""; visible: false; smooth: false }
    Image { id: bloom; source: scene.visible ? "../assets/skins/event-horizon-glow.png" : ""; visible: false; smooth: true }
    Image { id: grain; source: scene.visible ? "../assets/skins/event-horizon-turbulence.png" : ""; visible: false; smooth: true }
    ShaderEffect {
        objectName: "eventHorizonRenderer"
        anchors.fill: parent
        visible: body.status === Image.Ready && paths.status === Image.Ready
            && bodyPaths.status === Image.Ready && nearDisc.status === Image.Ready
            && farDisc.status === Image.Ready && stars.status === Image.Ready
            && bloom.status === Image.Ready && grain.status === Image.Ready
        fragmentShader: "shaders/event-horizon.frag.qsb"
        property var flesh: body
        property var rays: paths
        property var bodyRays: bodyPaths
        property var disc0: nearDisc
        property var disc1: farDisc
        property var sky: stars
        property var glow: bloom
        property var turbulence: grain
        property vector2d viewport: Qt.vector2d(Math.max(1, width), Math.max(1, height))
        property real time: scene.time
        property real energy: scene.energy
        property real lensScale: scene.lensScale
        property real fill: scene.fill
        property vector2d fleshCenter: scene.fleshCenter
        property vector3d impulse0: first.value
        property vector3d impulse1: second.value
        property vector3d impulse2: third.value
        property vector3d impulse3: fourth.value
    }
    Repeater {
        id: matter
        model: 64
        delegate: Rectangle {
            id: bit
            required property int index
            objectName: "horizonMatter"
            property real age: 1
            property real startRadius: 0
            property real startAngle: 0
            property real turn: 0
            readonly property bool alive: motion.running
            readonly property real radius: scene.shadow * 0.80
                + Math.max(0, startRadius * scene.halfSize - scene.shadow * 0.80) * Math.pow(1 - age, 1.75)
            readonly property real angle: startAngle + age * (2.1 + age * 8.0) + turn * age
            readonly property real px: Math.cos(angle) * radius
            readonly property real py: Math.sin(angle) * radius * (1 - age * 0.73)
            x: Math.round(scene.width / 2 + px - width / 2)
            y: Math.round(scene.height / 2 + py - height / 2)
            width: index % 5 === 0 ? 3 : 2
            height: index % 3 === 0 ? 1 : 2
            color: ["#c77853", "#e8bc80", "#d9d9c2", "#b5d5dc"][index % 4]
            visible: alive && Math.hypot(px, py) > scene.shadow * 0.94
            opacity: Math.min(1, age * 18) * (1 - age * 0.45)
            function launch(x, y) {
                const dx = x - scene.width / 2, dy = y - scene.height / 2
                startRadius = Math.hypot(dx, dy) / scene.halfSize
                startAngle = Math.atan2(dy, dx) + (Math.random() - 0.5) * 0.17
                if (startRadius * scene.halfSize < scene.shadow * 1.25) {
                    startRadius = (scene.shadow / scene.halfSize) * (1.7 + Math.random() * 0.65)
                    startAngle = Math.random() * 6.2831853
                }
                turn = Math.random() * 1.8
                age = 0
                motion.duration = 1250 + Math.round(Math.random() * 220)
                motion.start()
            }
            function clear() { motion.stop(); age = 1 }
            NumberAnimation { id: motion; target: bit; property: "age"; from: 0; to: 1 }
        }
    }
    Repeater {
        id: gains
        model: 24
        delegate: HorizonGain {
            center: Qt.vector2d(scene.width / 2, scene.height / 2)
            bounds: Qt.vector2d(scene.width, scene.height)
            horizonRadius: scene.shadow
            fontFamily: scene.fontFamily
            z: 2
        }
    }
}

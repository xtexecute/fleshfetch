import QtQuick

Item {
    id: sun
    objectName: "sunlightArt"
    property real aimX: 0.52
    property real aimY: 0.54
    property real intensity: 0
    property real sweep: 1
    property real charge: 0
    property real breakAge: 1
    property vector2d breakCenter: Qt.vector2d(0.5, 0.5)
    readonly property real sunbreak: Math.min(1, breakAge * 12) * Math.pow(1 - breakAge, 1.5)
    readonly property vector2d aim: Qt.vector2d(aimX, aimY)
    readonly property real aspect: height / Math.max(1, width)
    property int sparkCursor: 0
    required property Item sparkLayer

    function strike(u, v) {
        if (!visible) return
        aimX = Math.max(0.18, Math.min(0.88, 0.11 + 0.78 * u))
        aimY = Math.max(0.18, Math.min(0.88, 0.11 + 0.78 * v))
        settle.restart()
        fade.stop()
        intensity = Math.min(1, intensity + 0.51)
        fade.start()
        pass.restart()
        const x = u * width, y = v * height
        discharge.stop()
        charge = Math.min(1, charge + 0.18)
        chargeWait.restart()
        const breaking = charge >= 1 && breakAge >= 0.72
        if (breaking) {
            charge = 0
            breakCenter = Qt.vector2d(0.5 + (u - 0.5) * 0.38, 0.5 + (v - 0.5) * 0.38)
            eruption.restart()
        }
        const count = breaking ? 18 : 5
        for (let i = 0; i < count; ++i) {
            sparks.itemAt(sparkCursor)?.light(x, y, i, count, breaking)
            sparkCursor = (sparkCursor + 1) % sparks.count
        }
    }

    onVisibleChanged: {
        if (visible) return
        settle.stop()
        fade.stop()
        pass.stop()
        chargeWait.stop()
        discharge.stop()
        eruption.stop()
        intensity = 0
        sweep = 1
        charge = 0
        breakAge = 1
        aimX = 0.52
        aimY = 0.54
        sparkCursor = 0
        for (let i = 0; i < sparks.count; ++i) sparks.itemAt(i)?.clear()
    }

    Behavior on aimX { enabled: sun.visible; NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
    Behavior on aimY { enabled: sun.visible; NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
    Timer {
        id: settle
        interval: 890
        onTriggered: { sun.aimX = 0.52; sun.aimY = 0.54 }
    }
    NumberAnimation {
        id: fade
        target: sun
        property: "intensity"
        to: 0
        duration: 970
        easing.type: Easing.OutQuad
    }
    NumberAnimation {
        id: pass
        target: sun
        property: "sweep"
        from: 0
        to: 1
        duration: 690
    }
    Timer {
        id: chargeWait
        interval: 590
        onTriggered: discharge.start()
    }
    NumberAnimation {
        id: discharge
        target: sun
        property: "charge"
        to: 0
        duration: 740
    }
    NumberAnimation {
        id: eruption
        target: sun
        property: "breakAge"
        from: 0; to: 1
        duration: 1280
    }

    ShaderEffect {
        anchors.fill: parent
        fragmentShader: "shaders/sunlight-shafts.frag.qsb"
        property vector2d aim: sun.aim
        property real aspect: sun.aspect
        property real flash: sun.intensity
        property real sweep: sun.sweep
        property real sunbreak: sun.sunbreak
        property real breakAge: sun.breakAge
        property vector2d breakCenter: sun.breakCenter
    }

    Repeater {
        model: 11
        delegate: Rectangle {
            id: dust
            required property int index
            property real travel: 0
            readonly property real slide: (travel + index * 0.381966) % 1
            readonly property real lane: (index % 3 - 1) * (0.04 + slide * 0.11)
            width: index % 4 === 0 ? 3 : 2
            height: width
            x: sun.width * (-0.14 + (sun.aimX + 0.14) * (0.19 + slide * 1.52) + lane)
            y: sun.height * (-0.085 + (sun.aimY + 0.085) * (0.19 + slide * 1.52)
                + Math.sin(slide * 7 + index) * 0.023)
            color: "#fff0be"
            opacity: Math.sin(slide * Math.PI) * (0.32 + sun.intensity * 0.27)
            NumberAnimation on travel {
                running: sun.visible
                loops: Animation.Infinite
                from: 0
                to: 1
                duration: 3700 + dust.index * 390
            }
        }
    }

    Item {
        parent: sun.sparkLayer
        anchors.fill: parent
        visible: sun.visible
        Repeater {
            id: sparks
            model: 42
            delegate: Rectangle {
                id: mote
                required property int index
                objectName: "sunlightGlint"
                property real life: 1
                property real originX: 0
                property real originY: 0
                property real dx: 0
                property real dy: 0
                property bool flare: false
                width: flare ? (index % 4 === 0 ? 6 : 3) : (index % 4 === 0 ? 4 : 2)
                height: flare && index % 3 === 0 ? 2 : width
                visible: life < 1
                x: Math.round(originX + dx * life)
                y: Math.round(originY + dy * life)
                opacity: Math.min(1, (1 - life) * 1.56)
                color: index % 3 === 0 ? "#fff9dc" : "#ffcf81"
                function light(x, y, i, count, breaking) {
                    drift.stop()
                    originX = x
                    originY = y
                    flare = breaking
                    const angle = ((i + Math.random() * 0.8) / count) * Math.PI * 2
                    const distance = breaking ? 29 + Math.random() * 66 : 12 + Math.random() * 33
                    dx = Math.cos(angle) * distance
                    dy = Math.sin(angle) * distance - 6
                    life = 0
                    drift.duration = breaking ? 660 + Math.round(Math.random() * 220) : 430
                    drift.start()
                }
                function clear() { drift.stop(); life = 1 }
                NumberAnimation {
                    id: drift
                    target: mote
                    property: "life"
                    from: 0; to: 1
                    duration: 430
                    easing.type: Easing.OutQuad
                }
            }
        }
    }
}

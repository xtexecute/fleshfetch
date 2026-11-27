import QtQuick

Item {
    id: opal
    objectName: "opalArt"
    required property Item frontLayer
    property real viewX: 0
    property real viewY: 0
    property int cursor: 0
    property int glintCursor: 0
    readonly property vector2d view: Qt.vector2d(viewX, viewY)
    readonly property vector3d stroke0: first.value
    readonly property vector3d stroke1: second.value
    readonly property vector3d stroke2: third.value
    readonly property vector3d stroke3: fourth.value
    property alias normals: normalMap
    property alias fire: fireMap

    function strike(u, v, x, y) {
        if (!visible) return
        const strokes = [first, second, third, fourth]
        strokes[cursor].flash(u, v)
        cursor = (cursor + 1) % strokes.length
        viewX = Math.max(-0.5, Math.min(0.5, viewX + (Math.random() - 0.5) * 0.62))
        viewY = Math.max(-0.4, Math.min(0.4, viewY + (Math.random() - 0.5) * 0.44))
        let emitted = 0
        for (let i = 0; i < glints.count && emitted < 4; ++i) {
            const bit = glints.itemAt(glintCursor)
            glintCursor = (glintCursor + 1) % glints.count
            if (!bit || bit.alive) continue
            bit.launch(x, y)
            ++emitted
        }
    }
    onVisibleChanged: {
        if (visible) return
        viewX = 0
        viewY = 0
        cursor = 0
        glintCursor = 0
        for (const bit of [first, second, third, fourth]) bit.clear()
        for (let i = 0; i < glints.count; ++i) glints.itemAt(i)?.clear()
    }
    Behavior on viewX { enabled: opal.visible; NumberAnimation { duration: 320; easing.type: Easing.OutCubic } }
    Behavior on viewY { enabled: opal.visible; NumberAnimation { duration: 320; easing.type: Easing.OutCubic } }
    component Flash: QtObject {
        id: bit
        property real u: 0.5
        property real v: 0.5
        property real age: 1
        readonly property vector3d value: Qt.vector3d(u, v, age)
        property NumberAnimation motion: NumberAnimation {
            target: bit
            property: "age"
            from: 0; to: 1
            duration: 1200
        }
        function flash(x, y) {
            motion.stop()
            u = x
            v = y
            motion.start()
        }
        function clear() { motion.stop(); age = 1 }
    }
    Flash { id: first }
    Flash { id: second }
    Flash { id: third }
    Flash { id: fourth }
    Image {
        id: normalMap
        source: opal.visible ? "../assets/skins/opal-normals.png" : ""
        visible: false
        smooth: true
    }
    Image {
        id: fireMap
        source: opal.visible ? "../assets/skins/opal-fire.png" : ""
        visible: false
        smooth: true
    }
    Item {
        parent: opal.frontLayer
        anchors.fill: parent
        visible: opal.visible
        Repeater {
            id: glints
            model: 32
            delegate: Image {
                id: bit
                objectName: "opalGlint"
                property real age: 1
                property real startX: 0
                property real startY: 0
                property real dx: 0
                property real dy: 0
                property int tint: 0
                readonly property bool alive: motion.running
                source: "../assets/skins/opal-glints.png"
                sourceClipRect: Qt.rect(tint * 5, 0, 5, 5)
                width: 5
                height: 5
                smooth: false
                mipmap: false
                visible: alive
                x: Math.round(startX + dx * age)
                y: Math.round(startY + dy * age + 12 * age * age)
                opacity: (1 - age) * Math.min(1, age * 14)
                function launch(x, y) {
                    startX = x - width / 2
                    startY = y - height / 2
                    const angle = Math.random() * 6.2831853
                    const speed = 18 + Math.random() * 30
                    dx = Math.cos(angle) * speed
                    dy = Math.sin(angle) * speed - 12
                    tint = Math.floor(Math.random() * 4)
                    motion.duration = Math.round(650 + Math.random() * 150)
                    age = 0
                    motion.start()
                }
                function clear() { motion.stop(); age = 1 }
                NumberAnimation {
                    id: motion
                    target: bit
                    property: "age"
                    from: 0; to: 1
                    easing.type: Easing.OutQuad
                }
            }
        }
    }
}

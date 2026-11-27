import QtQuick

Item {
    id: art
    objectName: "stainedGlassArt"
    required property Item flesh
    required property real bodyAngle
    required property vector2d bodySquish
    property int cursor: 0
    readonly property vector3d pulse0: first.value
    readonly property vector3d pulse1: second.value
    readonly property vector3d pulse2: third.value
    property alias paneMap: cells

    function strike(u, v) {
        if (!visible) return
        const pulse = [first, second, third][cursor]
        pulse.fire(u, v)
        cursor = (cursor + 1) % 3
    }

    onVisibleChanged: {
        if (visible) return
        for (const pulse of [first, second, third]) pulse.clear()
        cursor = 0
    }

    component Pulse: QtObject {
        id: bit
        property real u: 0.5
        property real v: 0.5
        property real age: 1
        readonly property vector3d value: Qt.vector3d(u, v, age)
        property NumberAnimation travel: NumberAnimation {
            target: bit
            property: "age"
            from: 0
            to: 1
            duration: 950
        }
        function fire(x, y) {
            travel.stop()
            u = x
            v = y
            age = 0
            travel.start()
        }
        function clear() {
            travel.stop()
            age = 1
        }
    }

    Pulse { id: first }
    Pulse { id: second }
    Pulse { id: third }
    Image {
        id: cells
        source: art.visible ? "../assets/skins/stained-glass-panes.png" : ""
        visible: false
        smooth: false
    }
    Image {
        id: coloredGlass
        source: art.visible ? art.flesh.source : ""
        visible: false
        smooth: true
    }
    Image {
        id: rayRoutes
        source: art.visible ? "../assets/skins/stained-glass-rays.png" : ""
        visible: false
        smooth: false
    }
    ShaderEffect {
        anchors.fill: parent
        visible: rayRoutes.status === Image.Ready && coloredGlass.status === Image.Ready && cells.status === Image.Ready
        fragmentShader: "shaders/stained-glass-cast.frag.qsb"
        property var glass: coloredGlass
        property var panes: cells
        property var routes: rayRoutes
        property vector3d pulse0: art.pulse0
        property vector3d pulse1: art.pulse1
        property vector3d pulse2: art.pulse2
        property vector2d bodyOrigin: Qt.vector2d(art.flesh.x / Math.max(1, width), art.flesh.y / Math.max(1, height))
        property vector2d bodySize: Qt.vector2d(art.flesh.width / Math.max(1, width), art.flesh.height / Math.max(1, height))
        property vector2d bodySquish: art.bodySquish
        property real bodyAngle: art.bodyAngle
    }
}

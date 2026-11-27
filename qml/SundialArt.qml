import QtQuick

Item {
    id: art
    objectName: "sundialArt"
    required property Item flesh
    required property real bodyAngle
    required property vector2d bodySquish

    property real hour: 2
    property int nextHour: 2
    readonly property real day: (hour % 12) / 12
    // The return below the horizon takes less time than the daylight sweep.
    readonly property real sunAngle: Math.PI * (day < 0.85
        ? day / 0.85 : 1 + (day - 0.85) / 0.15)

    function advance() {
        if (nextHour - hour > 3) return
        sweep.stop()
        sweep.to = ++nextHour
        sweep.restart()
    }

    onVisibleChanged: {
        if (visible) return
        sweep.stop()
        nextHour = 2
        hour = nextHour
    }

    NumberAnimation {
        id: sweep
        target: art
        property: "hour"
        duration: 460
        easing.type: Easing.OutCubic
        onFinished: {
            if (art.nextHour < 24) return
            art.nextHour %= 12
            art.hour = art.nextHour
        }
    }

    Image {
        id: caster
        visible: false
        smooth: true
        source: art.visible ? art.flesh.source : ""
    }
    ShaderEffect {
        anchors.fill: parent
        visible: caster.status === Image.Ready
        fragmentShader: "shaders/sundial.frag.qsb"
        property var silhouette: caster
        property real sunAngle: art.sunAngle
        property real bodyAngle: art.bodyAngle
        property vector2d bodySquish: art.bodySquish
        property real pixelGrid: Math.max(1, Math.round(width))
        property vector2d bodySize: Qt.vector2d(art.flesh.paintedWidth / Math.max(1, width),
                                              art.flesh.paintedHeight / Math.max(1, height))
    }
}

import QtQuick

Item {
    id: box
    objectName: "lightboxArt"
    required property Item flesh
    required property Item frontLayer
    required property real bodyAngle
    required property vector2d bodySquish
    property int pixelSize: 1
    width: 116 * pixelSize
    height: 132 * pixelSize
    property real exposure: 0
    property real scan: 1
    property vector2d hit: Qt.vector2d(0.5, 0.5)
    readonly property vector2d panelOrigin: Qt.vector2d(x + 12 * pixelSize, y + 14 * pixelSize)
    readonly property vector2d panelSize: Qt.vector2d(92 * pixelSize, 90 * pixelSize)

    function expose(u, v) {
        if (!visible) return
        hit = Qt.vector2d(u, v)
        decay.stop()
        exposure = Math.min(1, exposure + 0.58)
        decay.start()
        // Keep an active scan moving when clicks arrive faster than its travel.
        if (!pass.running) pass.restart()
    }
    onVisibleChanged: {
        if (visible) return
        decay.stop()
        pass.stop()
        exposure = 0
        scan = 1
        hit = Qt.vector2d(0.5, 0.5)
    }
    NumberAnimation {
        id: decay
        target: box
        property: "exposure"
        to: 0
        duration: 1800
        easing.type: Easing.OutQuad
    }
    NumberAnimation {
        id: pass
        target: box
        property: "scan"
        from: 0; to: 1
        duration: 620
    }
    ShaderEffect {
        x: -14 * box.pixelSize
        y: -14 * box.pixelSize
        width: box.width + 28 * box.pixelSize
        height: box.height + 28 * box.pixelSize
        fragmentShader: "shaders/lightbox-glow.frag.qsb"
        property real exposure: box.exposure
        property vector2d size: Qt.vector2d(width / box.pixelSize, height / box.pixelSize)
    }
    Image {
        anchors.fill: parent
        source: "../assets/skins/lightbox-case.png"
        smooth: false
        mipmap: false
    }
    Image {
        id: caster
        visible: false
        source: box.visible ? box.flesh.source : ""
        smooth: true
    }
    ShaderEffect {
        objectName: "lightboxPanel"
        x: 12 * box.pixelSize
        y: 14 * box.pixelSize
        width: 92 * box.pixelSize
        height: 90 * box.pixelSize
        visible: caster.status === Image.Ready
        fragmentShader: "shaders/lightbox-panel.frag.qsb"
        property var silhouette: caster
        property real exposure: box.exposure
        property real scan: box.scan
        property vector2d bodyOrigin: Qt.vector2d(box.flesh.x - box.x - x, box.flesh.y - box.y - y)
        property vector2d bodySize: Qt.vector2d(box.flesh.width, box.flesh.height)
        property vector2d bodySquish: box.bodySquish
        property real bodyAngle: box.bodyAngle
        property real pixelSize: box.pixelSize
    }
    Repeater {
        model: 8
        delegate: Image {
            required property int index
            readonly property bool powered: box.exposure > index / 8
            x: (34 + index * 6) * box.pixelSize
            y: 111 * box.pixelSize
            width: 4 * box.pixelSize
            height: 3 * box.pixelSize
            source: "../assets/skins/lightbox-meter.png"
            sourceClipRect: Qt.rect(index < 2 ? 0 : index < 6 ? 4 : 8,
                                    powered || index === 0 ? 3 : 0, 4, 3)
            smooth: false
            mipmap: false
            opacity: powered ? 1 : index === 0 ? 0.70 : 0.45
        }
    }
    Repeater {
        model: 11
        delegate: Rectangle {
            required property int index
            x: 7 * box.pixelSize
            y: (18 + index * 8) * box.pixelSize
            width: 2 * box.pixelSize
            height: 3 * box.pixelSize
            color: "#e3f1d0"
            opacity: box.scan < 0.99
                ? Math.max(0.08, 1 - Math.abs(box.scan - index / 10) * 4) * box.exposure : 0.08
        }
    }
    Item {
        parent: box.frontLayer
        x: box.x
        y: box.y
        width: box.width
        height: box.height
        visible: box.visible
        Image {
            anchors.fill: parent
            source: "../assets/skins/lightbox-clips.png"
            smooth: false
            mipmap: false
        }
    }
}

import QtQuick

Item {
    id: art
    property int pixelScale: 1
    property real fleshLeft: 0
    property real fleshTop: 0
    property real fleshWidth: 0
    property real fleshHeight: 0
    property real pulse: 1

    function react() { scanPulse.restart() }

    onVisibleChanged: {
        if (!visible) {
            scanPulse.stop()
            pulse = 1
        }
    }

    NumberAnimation {
        id: scanPulse
        target: art
        property: "pulse"
        from: 0
        to: 1
        duration: 410
        easing.type: Easing.OutCubic
    }

    Canvas {
        id: beam
        width: art.fleshWidth * 0.84
        height: art.fleshHeight * 1.03
        x: Math.round(art.fleshLeft + (art.fleshWidth - width) / 2)
        y: Math.round(art.fleshTop + art.fleshHeight * 0.16)
        opacity: 0.55 + (1 - art.pulse) * 0.3
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.fillStyle = "rgba(95, 211, 199, 0.24)"
            ctx.beginPath()
            ctx.moveTo(width * 0.12, 0)
            ctx.lineTo(width * 0.88, 0)
            ctx.lineTo(width * 0.62, height)
            ctx.lineTo(width * 0.38, height)
            ctx.closePath()
            ctx.fill()
        }
    }

    Image {
        source: "../assets/skins/holo-projector.png"
        width: 96 * art.pixelScale
        height: 28 * art.pixelScale
        x: Math.round(art.fleshLeft + (art.fleshWidth - width) / 2)
        y: Math.round(Math.min(art.height - height - 2 * art.pixelScale,
                              art.fleshTop + art.fleshHeight + 2 * art.pixelScale))
        smooth: false
        mipmap: false
    }
}

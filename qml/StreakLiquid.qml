import QtQuick

Canvas {
    id: liquid
    property real fill: 0
    property real phase: 0
    property bool mercury: false
    opacity: 0.86
    Behavior on fill { NumberAnimation { duration: 340; easing.type: Easing.OutQuad } }
    onFillChanged: requestPaint()
    onMercuryChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Timer {
        interval: 60
        repeat: true
        running: liquid.visible && liquid.fill > 0
        onTriggered: { liquid.phase += 0.12; liquid.requestPaint() }
    }
    onPaint: {
        const ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        if (fill <= 0 || width <= 0 || height <= 0) return
        const level = Math.max(0, Math.min(1, fill / 100))
        const top = height * (1 - 0.84 * level)
        function surface(x) {
            if (mercury)
                return top + 2.6 * Math.sin(x * 0.028 + phase) + 1.3 * Math.sin(x * 0.064 - phase)
            return Math.round((top + 3 * Math.sin(x * 0.037 + phase)
                + 2 * Math.sin(x * 0.071 - phase * 0.7)) / 2) * 2
        }
        ctx.beginPath()
        ctx.moveTo(0, height)
        ctx.lineTo(0, surface(0))
        for (let x = 6; x <= width + 6; x += 6) ctx.lineTo(x, surface(x))
        ctx.lineTo(width, height)
        ctx.closePath()
        if (mercury) {
            const sheen = ctx.createLinearGradient(0, top, 0, height)
            sheen.addColorStop(0, "#c0d5df")
            sheen.addColorStop(0.065, "#667884")
            sheen.addColorStop(0.20, "#293540")
            sheen.addColorStop(0.43, "#586c79")
            sheen.addColorStop(0.53, "#a2b7c1")
            sheen.addColorStop(0.68, "#687d89")
            sheen.addColorStop(1, "#31414d")
            ctx.fillStyle = sheen
        } else {
            ctx.fillStyle = "#6d1c31"
        }
        ctx.fill()

        ctx.beginPath()
        ctx.moveTo(0, surface(0))
        for (let x = 6; x <= width + 6; x += 6) ctx.lineTo(x, surface(x))
        ctx.strokeStyle = mercury ? "#e2f2f7" : level > 0.92 ? "#ffacbb" : "#d95670"
        ctx.lineWidth = level > 0.92 ? 3 : 2
        ctx.stroke()

        ctx.fillStyle = mercury ? "#94bac5" : "#ad3a54"
        for (let i = 0; i < 8; ++i) {
            const x = (i * 73 + 29) % Math.max(1, width)
            const y = top + 14 + ((i * 97 + phase * 11) % Math.max(1, height - top - 18))
            if (y < height - 4) ctx.fillRect(Math.round(x), Math.round(y),
                mercury ? 5 + i % 4 : i % 3 === 0 ? 4 : 2, mercury ? 1 : 2)
        }
    }
}

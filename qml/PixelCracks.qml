import QtQuick

Item {
    id: cracks
    property real screenX: 0
    property real screenY: 0
    property real screenWidth: 0
    property real screenHeight: 0
    property int pixelSize: 4
    property int baseRayLength: 4
    property color crackColor: "#dceee8"
    property color edgeColor: "#91b1ab"
    property int frameBranchDistance: -1
    property var screenPixels: []
    property var escapedPixels: []
    property bool escaped: false
    opacity: 0

    function strike(hitX, hitY) {
        const size = pixelSize
        const columns = Math.max(1, Math.floor(screenWidth / size))
        const rows = Math.max(1, Math.floor(screenHeight / size))
        const startX = Math.max(0, Math.min(columns - 1, Math.round((hitX - screenX) / size)))
        const startY = Math.max(0, Math.min(rows - 1, Math.round((hitY - screenY) / size)))
        const pixels = [[startX, startY]]

        for (let ray = 0; ray < 6; ++ray) {
            const angle = ray * Math.PI / 3 + (Math.random() - 0.5) * 0.34
            const length = baseRayLength + Math.floor(Math.random() * 5)
            const bend = (Math.random() - 0.5) * 1.4
            for (let step = 1; step <= length; ++step) {
                const side = step > length / 2 ? bend : 0
                const x = startX + Math.round(Math.cos(angle) * step - Math.sin(angle) * side)
                const y = startY + Math.round(Math.sin(angle) * step + Math.cos(angle) * side)
                pixels.push([x, y])
                if (step === 4 && ray % 3 === 0) {
                    const fork = angle + (ray === 0 ? 0.72 : -0.72)
                    for (let branch = 1; branch <= 2; ++branch)
                        pixels.push([x + Math.round(Math.cos(fork) * branch),
                                     y + Math.round(Math.sin(fork) * branch)])
                }
            }
        }

        const escapedPath = []
        const edge = [startX, columns - 1 - startX, startY, rows - 1 - startY]
        let nearest = 0
        for (let i = 1; i < edge.length; ++i)
            if (edge[i] < edge[nearest]) nearest = i
        escaped = Math.random() < 0.18 && (frameBranchDistance < 0 || edge[nearest] <= frameBranchDistance)
        if (escaped) {
            const endX = nearest === 0 ? -2 : nearest === 1 ? columns + 1 : startX
            const endY = nearest === 2 ? -2 : nearest === 3 ? rows + 1 : startY
            const steps = Math.max(Math.abs(endX - startX), Math.abs(endY - startY))
            for (let step = 0; step <= steps; ++step) {
                const sideStep = step > 2 && step < steps - 2 && step % 6 >= 3 ? 1 : 0
                const x = startX + Math.round((endX - startX) * step / steps)
                    + (nearest >= 2 ? sideStep : 0)
                const y = startY + Math.round((endY - startY) * step / steps)
                    + (nearest < 2 ? sideStep : 0)
                escapedPath.push([x, y])
            }
        }

        screenPixels = pixels
        escapedPixels = escapedPath
        drawing.requestPaint()
        fade.restart()
    }

    onVisibleChanged: {
        if (visible) return
        fade.stop()
        opacity = 0
        screenPixels = []
        escapedPixels = []
        escaped = false
        drawing.requestPaint()
    }

    Canvas {
        id: drawing
        anchors.fill: parent
        onPaint: {
            const ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            const size = cracks.pixelSize
            function drawPixels(pixels) {
                for (let i = 0; i < pixels.length; ++i) {
                    const point = pixels[i]
                    ctx.fillStyle = i % 5 === 0 ? cracks.edgeColor : cracks.crackColor
                    ctx.fillRect(Math.round(cracks.screenX + point[0] * size),
                                 Math.round(cracks.screenY + point[1] * size), size, size)
                }
            }
            ctx.save()
            ctx.beginPath()
            ctx.rect(cracks.screenX, cracks.screenY, cracks.screenWidth, cracks.screenHeight)
            ctx.clip()
            drawPixels(cracks.screenPixels)
            ctx.restore()
            drawPixels(cracks.escapedPixels)
        }
    }

    SequentialAnimation {
        id: fade
        NumberAnimation { target: cracks; property: "opacity"; from: 0; to: 1; duration: 30 }
        PauseAnimation { duration: 600 }
        NumberAnimation { target: cracks; property: "opacity"; to: 0; duration: 1250; easing.type: Easing.OutQuad }
    }
}

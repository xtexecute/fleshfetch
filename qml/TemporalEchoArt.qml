import QtQuick

Item {
    id: echo
    objectName: "temporalEchoArt"
    required property url source
    required property Item flesh
    required property Item flashLayer
    required property real liveAngle
    required property real liveScale
    required property real liveScaleX
    required property real liveScaleY
    required property int clickMotionMs
    property string saveId: ""
    readonly property int delayMs: 500
    property var poses: []
    property var hits: []
    property double firstHit: 0
    property double lastHit: 0
    property real echoAngle: 0
    property real echoScale: 1
    property real echoScaleX: 1
    property real echoScaleY: 1
    property real echoAlpha: 0
    property real separation: 0
    property int flashCursor: 0

    function sample(now) {
        const pose = [now, liveAngle, liveScale, liveScaleX, liveScaleY]
        if (poses.length && poses[poses.length - 1][0] >= now)
            poses[poses.length - 1] = pose
        else
            poses.push(pose)
    }

    function recordHit(u, v) {
        if (!visible) return
        const now = Date.now()
        if (!clock.running) firstHit = now
        lastHit = now
        sample(now)
        hits.push([now, u, v])
        clock.start()
    }

    function replay() {
        const now = Date.now()
        const playhead = now - delayMs
        sample(now)
        if (playhead < firstHit) return

        // Keep the two samples around the playhead and discard older poses.
        while (poses.length > 2 && poses[1][0] <= playhead) poses.shift()
        const a = poses[0], b = poses[1] || a
        const fraction = Math.max(0, Math.min(1, (playhead - a[0]) / Math.max(1, b[0] - a[0])))
        echoAngle = a[1] + (b[1] - a[1]) * fraction
        echoScale = a[2] + (b[2] - a[2]) * fraction
        echoScaleX = a[3] + (b[3] - a[3]) * fraction
        echoScaleY = a[4] + (b[4] - a[4]) * fraction

        const age = playhead - lastHit
        const tail = Math.max(320, clickMotionMs + 35)
        const fade = Math.max(0, Math.min(1, 1 - (age - tail) / 160))
        const emerge = Math.min(1, (playhead - firstHit + 16) / 85)
        echoAlpha = 0.69 * fade * emerge
        separation = fade * Math.min(1, (playhead - firstHit + 40) / 90)

        while (hits.length && hits[0][0] <= playhead) {
            const hit = hits.shift()
            const point = ghost.mapToItem(flashLayer, hit[1] * ghost.width, hit[2] * ghost.height)
            flashes.itemAt(flashCursor)?.light(point.x, point.y)
            flashCursor = (flashCursor + 1) % flashes.count
        }
        if (fade === 0 && !hits.length) stopReplay()
    }

    function stopReplay() {
        clock.stop()
        poses = []
        hits = []
        echoAlpha = 0
        separation = 0
    }

    function reset() {
        stopReplay()
        for (let i = 0; i < flashes.count; ++i) flashes.itemAt(i)?.clear()
        flashCursor = 0
    }

    onSaveIdChanged: reset()
    onVisibleChanged: if (!visible) reset()

    Timer {
        id: clock
        interval: 16
        repeat: true
        onTriggered: echo.replay()
    }

    Item {
        width: echo.width
        height: echo.height
        x: echo.flesh.width * 0.18 * echo.separation
        y: -echo.flesh.height * (echo.height < 180 ? 0.025 : 0.105) * echo.separation
        rotation: echo.echoAngle
        scale: echo.echoScale
        opacity: echo.echoAlpha
        visible: opacity > 0
        transform: Scale {
            origin.x: echo.width / 2
            origin.y: echo.height / 2
            xScale: echo.echoScaleX
            yScale: echo.echoScaleY
        }
        Image {
            id: ghost
            objectName: "temporalEchoGhost"
            x: echo.flesh.x
            y: echo.flesh.y
            width: echo.flesh.width
            height: echo.flesh.height
            source: echo.visible ? echo.source : ""
            fillMode: Image.PreserveAspectFit
            smooth: true
        }
    }

    Item {
        parent: echo.flashLayer
        anchors.fill: parent
        visible: echo.visible
        Repeater {
            id: flashes
            model: 8
            delegate: Item {
                id: tick
                objectName: "temporalEchoFlash"
                property real life: 1
                readonly property real spread: 4 + Math.round(11 * life)
                width: 0
                height: 0
                visible: life < 1
                opacity: (1 - life) * (1 - life)

                function light(atX, atY) {
                    fade.stop()
                    x = Math.round(atX)
                    y = Math.round(atY)
                    life = 0
                    fade.start()
                }
                function clear() { fade.stop(); life = 1 }

                Repeater {
                    model: 4
                    delegate: Rectangle {
                        required property int index
                        width: index % 2 ? 5 : 2
                        height: index % 2 ? 2 : 5
                        x: (index === 1 ? tick.spread : index === 3 ? -tick.spread : 0) - width / 2
                        y: (index === 2 ? tick.spread : index === 0 ? -tick.spread : 0) - height / 2
                        color: "#e3fff6"
                    }
                }
                Rectangle {
                    x: -2; y: -2; width: 4; height: 4
                    visible: tick.life < 0.28
                    color: "#c3fff1"
                }
                NumberAnimation { id: fade; target: tick; property: "life"; from: 0; to: 1; duration: 330 }
            }
        }
    }
}

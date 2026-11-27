import QtQuick

Item {
    id: art
    signal impact()
    property int pixelScale: 2
    property real strikeProgress: 0
    readonly property real handleBaseX: 4 * pixelScale
    readonly property real handleBaseY: 68 * pixelScale
    readonly property real impactX: handleBaseX + 66 * pixelScale * Math.sin(35 * Math.PI / 180)
    readonly property real impactY: handleBaseY - 66 * pixelScale * Math.cos(35 * Math.PI / 180)
    property int sparkCursor: 0

    function hitTest(x, y) {
        const px = x / (2 * pixelScale)
        const py = y / (2 * pixelScale)
        function box(x0, y0, x1, y1) {
            return px >= x0 && px < x1 && py >= y0 && py < y1
        }
        return box(14, 25, 58, 36) || box(7, 31, 22, 36)
            || box(2, 33, 20, 38) || box(20, 35, 54, 42)
            || box(23, 40, 50, 52) || box(14, 50, 55, 56)
            || box(9, 54, 57, 61)
    }

    function strike() {
        const count = 6 + Math.floor(Math.random() * 3)
        for (let i = 0; i < count; ++i) {
            const spark = sparks.itemAt(sparkCursor)
            sparkCursor = (sparkCursor + 1) % sparks.count
            if (spark) spark.launch(impactX + 15 * pixelScale, impactY + 10 * pixelScale)
        }
        impact()
        game.playEffectSound("blacksmith")
    }

    function react() {
        if (!hammerStrike.running) {
            hammerStrike.start()
        }
    }

    onVisibleChanged: {
        if (visible) return
        hammerStrike.stop()
        strikeProgress = 0
        for (let i = 0; i < sparks.count; ++i) {
            const spark = sparks.itemAt(i)
            if (spark) spark.clear()
        }
    }

    Canvas {
        id: anvil
        anchors.fill: parent
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            ctx.scale(art.pixelScale * 2, art.pixelScale * 2)
            function block(x, y, w, h, color) {
                ctx.fillStyle = color
                ctx.fillRect(x, y, w, h)
            }
            block(14, 25, 44, 11, "#141b1e")
            block(7, 31, 15, 6, "#141b1e")
            block(2, 33, 18, 5, "#141b1e")
            block(20, 35, 34, 7, "#141b1e")
            block(23, 40, 27, 12, "#141b1e")
            block(14, 50, 41, 6, "#141b1e")
            block(9, 54, 48, 7, "#141b1e")

            block(15, 26, 42, 5, "#89999c")
            block(16, 26, 40, 1, "#bec9c8")
            block(15, 31, 42, 3, "#526167")
            block(8, 32, 14, 3, "#63747a")
            block(3, 34, 15, 2, "#798b8e")
            block(3, 34, 13, 1, "#aab9b8")
            block(21, 36, 32, 4, "#4d5d63")
            block(22, 36, 29, 1, "#68797e")
            block(24, 41, 25, 10, "#405056")
            block(24, 41, 2, 10, "#68797c")
            block(47, 41, 2, 10, "#303d42")
            block(15, 51, 39, 4, "#526167")
            block(16, 51, 37, 1, "#7d8d90")
            block(10, 55, 46, 5, "#445358")
            block(11, 55, 44, 1, "#728286")
        }
    }

    Item {
        id: hammer
        width: 58 * art.pixelScale
        height: 82 * art.pixelScale
        readonly property real angle: 20 + 15 * art.strikeProgress
        readonly property real pivotX: 28 * art.pixelScale
        readonly property real pivotY: 80 * art.pixelScale
        x: art.handleBaseX - pivotX
        y: art.handleBaseY - pivotY
        transform: Rotation {
            origin.x: hammer.pivotX
            origin.y: hammer.pivotY
            angle: hammer.angle
        }
        Canvas {
            anchors.fill: parent
            onPaint: {
                const ctx = getContext("2d")
                ctx.reset()
                ctx.scale(art.pixelScale * 2, art.pixelScale * 2)
                function block(x, y, w, h, color) {
                    ctx.fillStyle = color
                    ctx.fillRect(x, y, w, h)
                }
                block(12, 9, 4, 31, "#171d21")
                block(13, 10, 2, 29, "#7d5d4b")
                block(13, 11, 1, 27, "#a77d5e")
                block(5, 3, 18, 9, "#141b1f")
                block(6, 4, 16, 7, "#4c5b60")
                block(7, 4, 14, 1, "#aab8b8")
                block(6, 5, 2, 5, "#78898c")
                block(20, 5, 2, 5, "#889a9b")
                block(7, 10, 14, 1, "#303d42")
            }
        }
    }

    SequentialAnimation {
        id: hammerStrike
        NumberAnimation { target: art; property: "strikeProgress"; from: 0; to: 1; duration: 95; easing.type: Easing.OutCubic }
        ScriptAction { script: art.strike() }
        NumberAnimation { target: art; property: "strikeProgress"; to: 0; duration: 230; easing.type: Easing.OutBack }
    }

    Repeater {
        id: sparks
        model: 32
        delegate: Rectangle {
            id: spark
            z: 10
            property real life: 1
            property real startX: 0
            property real startY: 0
            property real vx: 0
            property real vy: 0
            width: (index % 3 === 0 ? 4 : 2) * art.pixelScale
            height: width
            x: startX + vx * life - width / 2
            y: startY + vy * life + 42 * art.pixelScale * life * life - height / 2
            visible: life < 1
            opacity: Math.min(1, (1 - life) * 1.2)
            color: index % 3 === 0 ? "#ffd35e" : index % 3 === 1 ? "#ff9f35" : "#fff5cf"
            function launch(x, y) {
                flight.stop()
                const angle = -Math.PI + Math.random() * Math.PI
                const speed = (75 + Math.random() * 50) * art.pixelScale
                startX = x + Math.cos(angle) * 6 * art.pixelScale
                startY = y + Math.sin(angle) * 6 * art.pixelScale
                vx = Math.cos(angle) * speed
                vy = Math.sin(angle) * speed - 20 * art.pixelScale
                life = 0
                flight.start()
            }
            function clear() { flight.stop(); life = 1 }
            NumberAnimation { id: flight; target: spark; property: "life"; from: 0; to: 1; duration: 520 }
        }
    }
}

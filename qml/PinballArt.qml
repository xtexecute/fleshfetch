import QtQuick

Item {
    id: art
    property int pixelScale: 1
    property real fleshLeft: 0
    property real fleshTop: 0
    property real fleshWidth: 0
    property real fleshHeight: 0
    property real leftBump: 1
    property real rightBump: 1
    property real leftAngle: -20
    property real rightAngle: 20
    property int ballCursor: 0
    property int sparkCursor: 0
    property int lastRoute: -1

    function react(x, y) {
        const ball = balls.itemAt(ballCursor)
        ballCursor = (ballCursor + 1) % balls.count
        if (ball) ball.launch(x, y)
    }

    function sparksAt(x, y, colorIndex) {
        for (let i = 0; i < 6; ++i) {
            const spark = sparks.itemAt(sparkCursor)
            sparkCursor = (sparkCursor + 1) % sparks.count
            const angle = (i / 6) * Math.PI * 2 + Math.random() * 0.3
            if (spark) spark.launch(x, y, Math.cos(angle) * 18 * pixelScale,
                                    Math.sin(angle) * 18 * pixelScale, colorIndex)
        }
    }

    function hitLeft() {
        leftFlash.restart()
        sparksAt(leftBumper.x + leftBumper.width / 2,
                 leftBumper.y + leftBumper.height / 2, 0)
    }
    function hitRight() {
        rightFlash.restart()
        sparksAt(rightBumper.x + rightBumper.width / 2,
                 rightBumper.y + rightBumper.height / 2, 1)
    }
    function hitRail(x, y) {
        sparksAt(x, y, 1)
    }
    function hitFlipper(left) {
        if (left) leftFlip.restart()
        else rightFlip.restart()
        sparksAt(railArt.x + railArt.width * (left ? 0.46 : 0.54),
                 railArt.y + railArt.height * 0.79, 0)
    }

    onVisibleChanged: {
        if (visible) return
        leftFlash.stop()
        rightFlash.stop()
        leftFlip.stop()
        rightFlip.stop()
        leftBump = 1
        rightBump = 1
        leftAngle = -20
        rightAngle = 20
        lastRoute = -1
        for (let i = 0; i < balls.count; ++i) {
            const ball = balls.itemAt(i)
            if (ball) ball.clear()
        }
        for (let i = 0; i < sparks.count; ++i) {
            const spark = sparks.itemAt(i)
            if (spark) spark.clear()
        }
    }

    SequentialAnimation {
        id: leftFlash
        NumberAnimation { target: art; property: "leftBump"; from: 1; to: 1.18; duration: 65; easing.type: Easing.OutQuad }
        NumberAnimation { target: art; property: "leftBump"; to: 1; duration: 170; easing.type: Easing.OutBack }
    }
    SequentialAnimation {
        id: rightFlash
        NumberAnimation { target: art; property: "rightBump"; from: 1; to: 1.18; duration: 65; easing.type: Easing.OutQuad }
        NumberAnimation { target: art; property: "rightBump"; to: 1; duration: 170; easing.type: Easing.OutBack }
    }
    SequentialAnimation {
        id: leftFlip
        NumberAnimation { target: art; property: "leftAngle"; from: -20; to: -42; duration: 75; easing.type: Easing.OutCubic }
        NumberAnimation { target: art; property: "leftAngle"; to: -20; duration: 180; easing.type: Easing.OutQuad }
    }
    SequentialAnimation {
        id: rightFlip
        NumberAnimation { target: art; property: "rightAngle"; from: 20; to: 42; duration: 75; easing.type: Easing.OutCubic }
        NumberAnimation { target: art; property: "rightAngle"; to: 20; duration: 180; easing.type: Easing.OutQuad }
    }

    Image {
        id: railArt
        source: "../assets/skins/pinball-rails.png"
        width: 120 * art.pixelScale
        height: width
        x: Math.round(art.fleshLeft + (art.fleshWidth - width) / 2)
        y: Math.round(art.fleshTop + (art.fleshHeight - height) / 2)
        smooth: false
        mipmap: false
    }
    Image {
        id: leftBumper
        objectName: "pinballLeftBumper"
        source: "../assets/skins/pinball-bumper-red.png"
        width: 22 * art.pixelScale
        height: width
        x: railArt.x + 11 * art.pixelScale
        y: railArt.y + 37 * art.pixelScale
        scale: art.leftBump
        smooth: false
        mipmap: false
    }
    Image {
        id: rightBumper
        objectName: "pinballRightBumper"
        source: "../assets/skins/pinball-bumper-teal.png"
        width: 22 * art.pixelScale
        height: width
        x: railArt.x + 87 * art.pixelScale
        y: railArt.y + 47 * art.pixelScale
        scale: art.rightBump
        smooth: false
        mipmap: false
    }
    Image {
        source: "../assets/skins/pinball-flipper.png"
        width: 32 * art.pixelScale
        height: 12 * art.pixelScale
        x: railArt.x + 27 * art.pixelScale
        y: railArt.y + 97 * art.pixelScale
        transform: Rotation {
            origin.x: 4 * art.pixelScale
            origin.y: 6 * art.pixelScale
            angle: art.leftAngle
        }
        smooth: false
        mipmap: false
    }
    Image {
        source: "../assets/skins/pinball-flipper.png"
        width: 32 * art.pixelScale
        height: 12 * art.pixelScale
        x: railArt.x + 61 * art.pixelScale
        y: railArt.y + 97 * art.pixelScale
        mirror: true
        transform: Rotation {
            origin.x: 28 * art.pixelScale
            origin.y: 6 * art.pixelScale
            angle: art.rightAngle
        }
        smooth: false
        mipmap: false
    }
    Repeater {
        id: balls
        model: 24
        delegate: Image {
            id: ball
            objectName: "pinballBall"
            property real startX: 0
            property real startY: 0
            property real leftX: 0
            property real leftY: 0
            property real rightX: 0
            property real rightY: 0
            property real firstX: 0
            property real firstY: 0
            property real secondX: 0
            property real secondY: 0
            property real thirdX: 0
            property real thirdY: 0
            property real bottomX: 0
            property real bottomY: 0
            property real exitX: 0
            property real exitY: 0
            property bool firstLeft: true
            property bool flipperLeft: true
            property int route: 0
            property int secondKind: 0
            property int thirdKind: 0
            property int firstDuration: 160
            property int secondDuration: 0
            property int thirdDuration: 0
            property int dropDuration: 260
            property int reboundDuration: 300
            source: "../assets/skins/pinball-ball.png"
            width: 10 * art.pixelScale
            height: width
            opacity: 0
            smooth: false
            mipmap: false
            function clear() {
                travel.stop()
                opacity = 0
            }
            function hitSecond() {
                if (secondKind === 1) art.hitLeft()
                else if (secondKind === 2) art.hitRight()
                else if (secondKind === 3) art.hitRail(secondX + width / 2, secondY + height / 2)
            }
            function hitThird() {
                if (thirdKind === 1) art.hitLeft()
                else if (thirdKind === 2) art.hitRight()
            }
            function launch(x, y) {
                travel.stop()
                startX = x - width / 2
                startY = y - height / 2
                leftX = leftBumper.x + (leftBumper.width - width) / 2
                leftY = leftBumper.y + (leftBumper.height - height) / 2
                rightX = rightBumper.x + (rightBumper.width - width) / 2
                rightY = rightBumper.y + (rightBumper.height - height) / 2
                route = (art.lastRoute + 1 + Math.floor(Math.random() * 3)) % 4
                art.lastRoute = route
                firstLeft = Math.random() < 0.5
                flipperLeft = Math.random() < 0.5
                firstX = (firstLeft ? leftX : rightX) + (Math.random() - 0.5) * 5 * art.pixelScale
                firstY = (firstLeft ? leftY : rightY) + (Math.random() - 0.5) * 5 * art.pixelScale
                secondKind = 0
                thirdKind = 0
                secondX = firstX
                secondY = firstY
                thirdX = secondX
                thirdY = secondY
                firstDuration = 130 + Math.floor(Math.random() * 100)
                secondDuration = 0
                thirdDuration = 0
                if (route === 0 || route === 2) {
                    secondKind = firstLeft ? 2 : 1
                    secondX = firstLeft ? rightX : leftX
                    secondY = firstLeft ? rightY : leftY
                    secondDuration = 150 + Math.floor(Math.random() * 100)
                } else if (route === 1) {
                    secondKind = 3
                    secondX = railArt.x + railArt.width * (firstLeft ? 0.91 : 0.09) - width / 2
                    secondY = railArt.y + railArt.height * (0.28 + Math.random() * 0.22) - height / 2
                    secondDuration = 160 + Math.floor(Math.random() * 90)
                }
                thirdX = secondX
                thirdY = secondY
                if (route === 1 || route === 2) {
                    thirdKind = route === 2 ? (firstLeft ? 1 : 2) : (firstLeft ? 2 : 1)
                    thirdX = route === 2 ? firstX : (firstLeft ? rightX : leftX)
                    thirdY = route === 2 ? firstY : (firstLeft ? rightY : leftY)
                    thirdDuration = 130 + Math.floor(Math.random() * 90)
                }
                bottomX = railArt.x + railArt.width * (flipperLeft ? 0.46 : 0.54) - width / 2
                bottomY = railArt.y + railArt.height * 0.79 - height / 2
                dropDuration = 190 + Math.floor(Math.random() * 120)
                exitX = railArt.x + railArt.width * (flipperLeft ? 0.66 : 0.34)
                    + (Math.random() - 0.5) * railArt.width * 0.18 - width / 2
                exitY = railArt.y + railArt.height * (0.18 + Math.random() * 0.18) - height / 2
                reboundDuration = 260 + Math.floor(Math.random() * 130)
                travel.start()
            }
            SequentialAnimation {
                id: travel
                ParallelAnimation {
                    NumberAnimation { target: ball; property: "x"; from: ball.startX; to: ball.firstX; duration: ball.firstDuration; easing.type: Easing.OutQuad }
                    NumberAnimation { target: ball; property: "y"; from: ball.startY; to: ball.firstY; duration: ball.firstDuration; easing.type: Easing.OutQuad }
                    NumberAnimation { target: ball; property: "opacity"; from: 1; to: 1; duration: ball.firstDuration }
                }
                ScriptAction { script: ball.firstLeft ? art.hitLeft() : art.hitRight() }
                ParallelAnimation {
                    NumberAnimation { target: ball; property: "x"; to: ball.secondX; duration: ball.secondDuration; easing.type: Easing.InOutQuad }
                    NumberAnimation { target: ball; property: "y"; to: ball.secondY; duration: ball.secondDuration; easing.type: Easing.InOutQuad }
                }
                ScriptAction { script: ball.hitSecond() }
                ParallelAnimation {
                    NumberAnimation { target: ball; property: "x"; to: ball.thirdX; duration: ball.thirdDuration; easing.type: Easing.InOutQuad }
                    NumberAnimation { target: ball; property: "y"; to: ball.thirdY; duration: ball.thirdDuration; easing.type: Easing.InOutQuad }
                }
                ScriptAction { script: ball.hitThird() }
                ParallelAnimation {
                    NumberAnimation { target: ball; property: "x"; to: ball.bottomX; duration: ball.dropDuration; easing.type: Easing.InQuad }
                    NumberAnimation { target: ball; property: "y"; to: ball.bottomY; duration: ball.dropDuration; easing.type: Easing.InQuad }
                }
                ScriptAction { script: art.hitFlipper(ball.flipperLeft) }
                ParallelAnimation {
                    NumberAnimation { target: ball; property: "x"; to: ball.exitX; duration: ball.reboundDuration; easing.type: Easing.OutQuad }
                    NumberAnimation { target: ball; property: "y"; to: ball.exitY; duration: ball.reboundDuration; easing.type: Easing.OutQuad }
                    SequentialAnimation {
                        NumberAnimation { target: ball; property: "opacity"; from: 1; to: 1; duration: ball.reboundDuration / 2 }
                        NumberAnimation { target: ball; property: "opacity"; to: 0; duration: ball.reboundDuration / 2 }
                    }
                }
            }
        }
    }
    Repeater {
        id: sparks
        model: 24
        delegate: Rectangle {
            id: spark
            objectName: "pinballSpark"
            property real startX: 0
            property real startY: 0
            property real dx: 0
            property real dy: 0
            property int palette: 0
            width: 2 * art.pixelScale
            height: width
            color: palette === 0 ? (index % 2 === 0 ? "#e5c278" : "#f18d8e")
                : (index % 2 === 0 ? "#9dc6bd" : "#e0e4d7")
            opacity: 0
            function clear() {
                fly.stop()
                opacity = 0
            }
            function launch(x, y, vx, vy, colorIndex) {
                fly.stop()
                startX = x - width / 2
                startY = y - height / 2
                dx = vx
                dy = vy
                palette = colorIndex
                fly.start()
            }
            ParallelAnimation {
                id: fly
                NumberAnimation { target: spark; property: "x"; from: spark.startX; to: spark.startX + spark.dx; duration: 340; easing.type: Easing.OutQuad }
                NumberAnimation { target: spark; property: "y"; from: spark.startY; to: spark.startY + spark.dy; duration: 340; easing.type: Easing.OutQuad }
                NumberAnimation { target: spark; property: "opacity"; from: 1; to: 0; duration: 340 }
            }
        }
    }
}

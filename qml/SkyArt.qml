import QtQuick

Item {
    id: art
    property int pixelScale: 1
    property real fleshLeft: 0
    property real fleshTop: 0
    property real fleshWidth: 0
    property real fleshHeight: 0
    property real backShift: 0
    property real frontShift: 0
    property real cloudSquash: 1
    property int wispCursor: 0

    function react() {
        cloudBounce.restart()
        for (let i = 0; i < 4; ++i) {
            const wisp = wisps.itemAt(wispCursor)
            wispCursor = (wispCursor + 1) % wisps.count
            if (wisp) wisp.launch(i % 2 === 0 ? -1 : 1)
        }
    }

    onVisibleChanged: {
        if (visible) return
        cloudBounce.stop()
        cloudSquash = 1
        for (let i = 0; i < wisps.count; ++i) {
            const wisp = wisps.itemAt(i)
            if (wisp) wisp.clear()
        }
    }

    SequentialAnimation on backShift {
        running: art.visible
        loops: Animation.Infinite
        NumberAnimation { from: -5 * art.pixelScale; to: 5 * art.pixelScale; duration: 3400; easing.type: Easing.InOutSine }
        NumberAnimation { to: -5 * art.pixelScale; duration: 3400; easing.type: Easing.InOutSine }
    }
    SequentialAnimation on frontShift {
        running: art.visible
        loops: Animation.Infinite
        NumberAnimation { from: 3 * art.pixelScale; to: -3 * art.pixelScale; duration: 2700; easing.type: Easing.InOutSine }
        NumberAnimation { to: 3 * art.pixelScale; duration: 2700; easing.type: Easing.InOutSine }
    }
    SequentialAnimation {
        id: cloudBounce
        NumberAnimation { target: art; property: "cloudSquash"; to: 0.86; duration: 90; easing.type: Easing.OutCubic }
        NumberAnimation { target: art; property: "cloudSquash"; to: 1; duration: 420; easing.type: Easing.OutBack }
    }

    Image {
        source: "../assets/skins/sky-cloud-back.png"
        width: 76 * art.pixelScale
        height: 30 * art.pixelScale
        x: Math.round(art.fleshLeft - 12 * art.pixelScale + art.backShift)
        y: Math.round(art.fleshTop + art.fleshHeight * 0.52)
        opacity: 0.82
        smooth: false
        mipmap: false
    }
    Image {
        source: "../assets/skins/sky-cloud-back.png"
        width: 76 * art.pixelScale
        height: 30 * art.pixelScale
        x: Math.round(art.fleshLeft + art.fleshWidth * 0.49 - art.backShift)
        y: Math.round(art.fleshTop + art.fleshHeight * 0.45)
        mirror: true
        opacity: 0.7
        smooth: false
        mipmap: false
    }
    Image {
        id: frontCloud
        source: "../assets/skins/sky-cloud-front.png"
        width: 110 * art.pixelScale
        height: 42 * art.pixelScale
        x: Math.round(art.fleshLeft + (art.fleshWidth - width) / 2 + art.frontShift)
        y: Math.round(art.fleshTop + art.fleshHeight * 0.72)
        transform: Scale {
            origin.x: frontCloud.width / 2
            origin.y: frontCloud.height * 0.65
            xScale: 1 + (1 - art.cloudSquash) * 0.1
            yScale: art.cloudSquash
        }
        smooth: false
        mipmap: false
    }
    Repeater {
        id: wisps
        model: 48
        delegate: Image {
            id: wisp
            objectName: "skyWisp"
            property real life: 1
            property real startX: 0
            property real startY: 0
            property real drift: 0
            property real rise: 0
            source: "../assets/skins/sky-wisp.png"
            width: 18 * art.pixelScale
            height: 10 * art.pixelScale
            x: Math.round(startX + drift * life)
            y: Math.round(startY - rise * life)
            opacity: life < 0.45 ? 1 : (1 - life) / 0.55
            smooth: false
            mipmap: false
            function clear() {
                floatAway.stop()
                life = 1
            }
            function launch(side) {
                floatAway.stop()
                startX = frontCloud.x + frontCloud.width * (side < 0 ? 0.04 : 0.96) - width / 2
                startY = frontCloud.y + frontCloud.height * (0.38 + Math.random() * 0.22) - height / 2
                drift = side * (15 + Math.random() * 13) * art.pixelScale
                rise = (4 + Math.random() * 6) * art.pixelScale
                life = 0
                floatAway.start()
            }
            NumberAnimation {
                id: floatAway
                target: wisp
                property: "life"
                from: 0
                to: 1
                duration: 1200
                easing.type: Easing.OutQuad
            }
        }
    }
}

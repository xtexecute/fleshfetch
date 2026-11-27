import QtQuick

Item {
    id: art
    property int pixelScale: 1
    property real fleshLeft: 0
    property real fleshTop: 0
    property real fleshWidth: 0
    property real fleshHeight: 0
    property real cloudJolt: 0
    property real cloudDrift: 0
    property int boltCursor: 0

    function react() {
        cloudBounce.restart()
        const bolt = bolts.itemAt(boltCursor)
        boltCursor = (boltCursor + 1) % bolts.count
        if (bolt) bolt.strike()
    }

    onVisibleChanged: {
        if (visible) return
        cloudBounce.stop()
        cloudJolt = 0
        for (let i = 0; i < bolts.count; ++i) {
            const bolt = bolts.itemAt(i)
            if (bolt) bolt.clear()
        }
    }

    SequentialAnimation {
        id: cloudBounce
        NumberAnimation { target: art; property: "cloudJolt"; to: -3 * art.pixelScale; duration: 60; easing.type: Easing.OutCubic }
        NumberAnimation { target: art; property: "cloudJolt"; to: 0; duration: 350; easing.type: Easing.OutBack }
    }

    SequentialAnimation on cloudDrift {
        running: art.visible
        loops: Animation.Infinite
        NumberAnimation { from: -2 * art.pixelScale; to: 2 * art.pixelScale; duration: 2600; easing.type: Easing.InOutSine }
        NumberAnimation { to: -2 * art.pixelScale; duration: 2600; easing.type: Easing.InOutSine }
    }

    Image {
        source: "../assets/skins/thunder-cloud.png"
        width: 112 * art.pixelScale
        height: 46 * art.pixelScale
        x: Math.round(art.fleshLeft + (art.fleshWidth - width) / 2 + art.cloudDrift)
        y: Math.round(art.fleshTop - 12 * art.pixelScale + art.cloudJolt)
        smooth: false
        mipmap: false
    }

    Repeater {
        id: bolts
        model: 8
        delegate: Image {
            id: bolt
            objectName: "thunderBolt"
            property real life: 1
            property real lane: 0.5
            source: "../assets/skins/thunder-bolt.png"
            width: 28 * art.pixelScale
            height: 70 * art.pixelScale
            x: Math.round(art.fleshLeft + art.fleshWidth * lane - width / 2)
            y: Math.round(art.fleshTop + 9 * art.pixelScale + art.cloudJolt)
            opacity: life < 0.16 ? 1 : Math.max(0, (1 - life) / 0.84)
            smooth: false
            mipmap: false
            function clear() {
                strikeFade.stop()
                life = 1
            }
            function strike() {
                strikeFade.stop()
                lane = 0.28 + Math.random() * 0.44
                life = 0
                strikeFade.start()
            }
            NumberAnimation {
                id: strikeFade
                target: bolt
                property: "life"
                from: 0
                to: 1
                duration: 380
                easing.type: Easing.OutQuad
            }
        }
    }
}

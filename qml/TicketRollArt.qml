import QtQuick

Item {
    id: art
    property int pixelScale: 1
    property real fleshLeft: 0
    property real fleshTop: 0
    property real fleshWidth: 0
    property real fleshHeight: 0
    property real spoolAngle: 0
    property real spoolTarget: 0
    property real feedOffset: 0
    property int ticketCursor: 0

    function react() {
        rollSpin.stop()
        if (spoolTarget >= 3600) {
            spoolAngle -= 3600
            spoolTarget -= 3600
        }
        spoolTarget += 90
        rollSpin.from = spoolAngle
        rollSpin.to = spoolTarget
        rollSpin.start()
        feed.restart()

        const ticket = looseTickets.itemAt(ticketCursor)
        ticketCursor = (ticketCursor + 1) % looseTickets.count
        if (ticket) ticket.launch(housing.x + housing.width * 0.5,
                                  housing.y + housing.height * 0.85)
    }

    onVisibleChanged: {
        if (visible) return
        rollSpin.stop()
        feed.stop()
        spoolAngle = 0
        spoolTarget = 0
        feedOffset = 0
        for (let i = 0; i < looseTickets.count; ++i) {
            const ticket = looseTickets.itemAt(i)
            if (ticket) ticket.clear()
        }
    }

    NumberAnimation {
        id: rollSpin
        target: art
        property: "spoolAngle"
        duration: 300
        easing.type: Easing.OutCubic
    }
    SequentialAnimation {
        id: feed
        NumberAnimation { target: art; property: "feedOffset"; from: 0; to: 7 * art.pixelScale; duration: 130; easing.type: Easing.OutCubic }
        NumberAnimation { target: art; property: "feedOffset"; to: 0; duration: 260; easing.type: Easing.OutBack }
    }

    Image {
        id: strip
        source: "../assets/skins/ticket-stub.png"
        width: 18 * art.pixelScale
        height: 30 * art.pixelScale
        x: housing.x + (housing.width - width) / 2
        y: housing.y + 31 * art.pixelScale + art.feedOffset
        smooth: false
        mipmap: false
    }
    Image {
        id: housing
        source: "../assets/skins/ticket-roll-housing.png"
        width: 44 * art.pixelScale
        height: width
        x: Math.round(art.fleshLeft + art.fleshWidth * 0.84 - width / 2)
        y: Math.round(art.fleshTop + art.fleshHeight * 0.48 - height / 2)
        smooth: false
        mipmap: false
    }
    Image {
        objectName: "ticketRollSpool"
        source: "../assets/skins/ticket-roll-spool.png"
        width: 30 * art.pixelScale
        height: width
        x: housing.x + 7 * art.pixelScale
        y: housing.y + 8 * art.pixelScale
        rotation: art.spoolAngle
        smooth: false
        mipmap: false
    }
    Repeater {
        id: looseTickets
        model: 12
        delegate: Image {
            id: ticket
            objectName: "looseTicket"
            property real startX: 0
            property real startY: 0
            property real drift: 0
            property real drop: 0
            property real turn: 0
            source: "../assets/skins/ticket-stub.png"
            width: 18 * art.pixelScale
            height: 30 * art.pixelScale
            opacity: 0
            smooth: false
            mipmap: false
            function clear() {
                motion.stop()
                opacity = 0
            }
            function launch(x, y) {
                motion.stop()
                startX = x - width / 2
                startY = y
                drift = (Math.random() - 0.5) * 18 * art.pixelScale
                drop = (34 + Math.random() * 10) * art.pixelScale
                turn = (Math.random() - 0.5) * 22
                motion.start()
            }
            ParallelAnimation {
                id: motion
                NumberAnimation { target: ticket; property: "x"; from: ticket.startX; to: ticket.startX + ticket.drift; duration: 900; easing.type: Easing.OutQuad }
                NumberAnimation { target: ticket; property: "y"; from: ticket.startY; to: ticket.startY + ticket.drop; duration: 900; easing.type: Easing.InQuad }
                NumberAnimation { target: ticket; property: "rotation"; from: 0; to: ticket.turn; duration: 900; easing.type: Easing.OutQuad }
                SequentialAnimation {
                    NumberAnimation { target: ticket; property: "opacity"; from: 1; to: 1; duration: 420 }
                    NumberAnimation { target: ticket; property: "opacity"; to: 0; duration: 480 }
                }
            }
        }
    }
}

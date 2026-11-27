import QtQuick

Image {
    id: crate
    signal landed(int dropId, real atX, real atY)
    property int dropId: -1
    property string tier: "Common"
    property real launchY: 0
    property real floorY: 0
    property real endX: 0
    width: 38
    height: 38
    opacity: 0
    visible: opacity > 0
    source: ((game.catalog.progression || {}).crateTiers || []).find(function(item) { return item.id === crate.tier })?.icon || "image://skins/loot/crate/Common"
    smooth: false
    fillMode: Image.PreserveAspectFit
    transformOrigin: Item.Center

    function launch(id, name, startX, startY, bottomY) {
        if (dropId >= 0) game.collectCrateDrop(dropId)
        flight.stop()
        dropId = id
        tier = name
        x = startX - width / 2
        y = startY - height / 2
        launchY = y
        floorY = Math.max(0, bottomY - height)
        endX = Math.max(0, Math.min(parent.width - width, x + (Math.random() - 0.5) * 45))
        rotation = 0
        scale = 0.28
        opacity = 1
        flight.start()
    }
    SequentialAnimation {
        id: flight
        ParallelAnimation {
            NumberAnimation { target: crate; property: "y"; from: crate.launchY; to: crate.launchY - 28; duration: 190; easing.type: Easing.OutCubic }
            NumberAnimation { target: crate; property: "scale"; from: 0.28; to: 1; duration: 190; easing.type: Easing.OutBack }
        }
        ParallelAnimation {
            NumberAnimation { target: crate; property: "y"; to: crate.floorY; duration: 750; easing.type: Easing.InQuad }
            NumberAnimation { target: crate; property: "x"; to: crate.endX; duration: 750; easing.type: Easing.OutQuad }
            NumberAnimation { target: crate; property: "rotation"; to: 22; duration: 750; easing.type: Easing.OutQuad }
        }
        onFinished: {
            const id = crate.dropId
            crate.dropId = -1
            crate.opacity = 0
            if (id >= 0) crate.landed(id, crate.x + crate.width / 2, crate.floorY + crate.height / 2)
        }
    }
}

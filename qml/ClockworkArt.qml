import QtQuick

Item {
    id: art
    property real turn: 450
    readonly property real pixel: width / 160

    function advance() { turn += 45 }

    Behavior on turn {
        NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
    }

    Image {
        anchors.fill: parent
        source: "image://skins/clockwork/01-chassis"
        smooth: false
        mipmap: false
    }
    Image {
        anchors.fill: parent
        source: "image://skins/clockwork/02-housings"
        smooth: false
        mipmap: false
    }
    Repeater {
        id: gears
        model: [
            { name: "left", cx: 25, cy: 80, size: 40, ratio: 1 },
            { name: "left-pinion", cx: 49, cy: 80, size: 24, ratio: -2 },
            { name: "idler-1", cx: 63, cy: 72, size: 24, ratio: 2 },
            { name: "idler-2", cx: 77, cy: 80, size: 24, ratio: -2 },
            { name: "idler-3", cx: 91, cy: 72, size: 24, ratio: 2 },
            { name: "idler-4", cx: 105, cy: 80, size: 24, ratio: -2 },
            { name: "upper-right", cx: 119, cy: 72, size: 24, ratio: 2 },
            { name: "lower-right", cx: 113, cy: 95, size: 40, ratio: -1 }
        ]
        delegate: Image {
            required property var modelData
            objectName: "clockworkGear_" + modelData.name
            source: "image://skins/clockwork/gear-" + modelData.name
            width: modelData.size * art.pixel
            height: width
            x: (modelData.cx - modelData.size / 2) * art.pixel
            y: (modelData.cy - modelData.size / 2) * art.pixel
            rotation: art.turn * modelData.ratio
            smooth: false
            mipmap: false
        }
    }
    Image {
        anchors.fill: parent
        source: "image://skins/clockwork/04-front-brackets"
        smooth: false
        mipmap: false
    }
    Image {
        anchors.fill: parent
        source: "image://skins/clockwork/05-clock-face"
        smooth: false
        mipmap: false
    }
    Image {
        source: "image://skins/clockwork/clock-hour-hand"
        width: 64 * art.pixel
        height: width
        x: (69 - 32) * art.pixel
        y: (77 - 32) * art.pixel
        rotation: art.turn / 90
        smooth: false
        mipmap: false
    }
    Image {
        source: "image://skins/clockwork/clock-minute-hand"
        width: 64 * art.pixel
        height: width
        x: (69 - 32) * art.pixel
        y: (77 - 32) * art.pixel
        rotation: art.turn * 2 / 15
        smooth: false
        mipmap: false
    }
    Image {
        source: "image://skins/clockwork/clock-pivot"
        width: 5 * art.pixel
        height: width
        x: (69 - 2) * art.pixel
        y: (77 - 2) * art.pixel
        smooth: false
        mipmap: false
    }
}

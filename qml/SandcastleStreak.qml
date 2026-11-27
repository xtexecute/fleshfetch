import QtQuick

Item {
    id: dune
    objectName: "sandcastleStreak"
    property real fill: 0
    readonly property int unit: width < 180 || height < 180 ? 1 : 2
    property real rise: fill > 0 ? Math.min(height * 0.84, Math.max(5 * unit, height * 0.84 * fill / 100)) : 0

    Behavior on rise {
        enabled: dune.visible
        NumberAnimation { duration: 155; easing.type: Easing.OutQuad }
    }

    Image {
        source: "../assets/skins/streak-sand.png"
        visible: dune.rise > 0
        y: Math.round((dune.height - dune.rise) / dune.unit) * dune.unit
        width: Math.ceil(dune.width / dune.unit)
        height: sourceSize.height
        scale: dune.unit
        transformOrigin: Item.TopLeft
        horizontalAlignment: Image.AlignLeft
        fillMode: Image.TileHorizontally
        smooth: false
    }
}

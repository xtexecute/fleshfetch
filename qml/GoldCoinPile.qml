import QtQuick

Item {
    id: pile
    required property Item flightLayer
    property real fill: 0
    property string saveId: ""
    property real settledFill: 0
    property int inFlight: 0
    property int cursor: 0
    readonly property int unit: width < 180 || height < 180 ? 1 : 2
    readonly property real targetHeight: pileHeight(settledFill)
    property real rise: targetHeight

    signal coinLanded()
    objectName: "goldCoinPile"

    function pileHeight(level) {
        if (level <= 0) return 0
        const maxHeight = height * 0.84
        const firstCoins = Math.min(maxHeight, 6 * unit)
        return firstCoins + (maxHeight - firstCoins) * Math.min(1, level / 100)
    }

    function launch(x, y, afterClickFill) {
        if (!visible) return
        const sprite = drops.itemAt(cursor)
        cursor = (cursor + 1) % drops.count
        const drift = (Math.random() - 0.5) * 40
        const floorX = Math.max(8, Math.min(width - 8, x + drift))
        const floorY = Math.min(height - 3 * unit, height - pileHeight(afterClickFill) + 6 * unit)
        if (!sprite.active) ++inFlight
        sprite.launch(x, y, floorX, floorY, afterClickFill)
    }

    function settle(level) {
        --inFlight
        // A flight may finish before the next live snapshot reaches QML.
        settledFill = Math.max(settledFill, level, inFlight ? 0 : fill)
        coinLanded()
    }

    function reset() {
        for (let i = 0; i < drops.count; ++i) drops.itemAt(i)?.cancel()
        inFlight = 0
        cursor = 0
        settledFill = fill
    }

    onVisibleChanged: reset()
    onSaveIdChanged: reset()
    onFillChanged: {
        settledFill = inFlight ? Math.min(settledFill, fill) : fill
    }

    Behavior on rise {
        enabled: pile.visible
        NumberAnimation { duration: 105; easing.type: Easing.OutQuad }
    }

    Image {
        objectName: "goldHeapSprite"
        source: "../assets/skins/gold-coin-heap.png"
        visible: pile.rise > 0
        width: Math.ceil(pile.width / pile.unit)
        height: sourceSize.height
        y: Math.round((pile.height - pile.rise) / pile.unit) * pile.unit
        scale: pile.unit
        transformOrigin: Item.TopLeft
        horizontalAlignment: Image.AlignLeft
        fillMode: Image.TileHorizontally
        smooth: false
    }

    Item {
        parent: pile.flightLayer
        anchors.fill: parent
        visible: pile.visible
        Repeater {
            id: drops
            model: 16
            delegate: Item {
                id: coin
                objectName: "goldCoinDrop"
                property bool active: false
                property real life: 0
                property real startX: 0
                property real startY: 0
                property real endX: 0
                property real endY: 0
                property real level: 0
                readonly property int pixel: pile.unit
                readonly property int step: Math.floor(life * 10) % 4
                width: 13 * pixel
                height: width
                visible: active
                clip: true
                x: Math.round((startX + (endX - startX) * life) / pixel) * pixel - 6 * pixel
                y: Math.round((startY + (endY - startY) * life * life
                    - 20 * Math.sin(life * Math.PI)) / pixel) * pixel - 6 * pixel
                function launch(x, y, targetX, targetY, afterClickFill) {
                    fall.stop()
                    startX = x
                    startY = y
                    endX = targetX
                    endY = targetY
                    level = afterClickFill
                    life = 0
                    active = true
                    fall.duration = Math.min(590, 280 + Math.round(20 * Math.sqrt(Math.abs(y - targetY))))
                    fall.start()
                }
                function cancel() {
                    fall.stop()
                    active = false
                }
                Image {
                    source: "../assets/skins/gold-coin-flip.png"
                    smooth: false
                    width: coin.width * 3
                    height: coin.height
                    x: -(coin.step === 3 ? 1 : coin.step) * coin.width
                }
                NumberAnimation {
                    id: fall
                    target: coin
                    property: "life"
                    from: 0
                    to: 1
                    onFinished: {
                        coin.active = false
                        pile.settle(coin.level)
                    }
                }
            }
        }
    }
}

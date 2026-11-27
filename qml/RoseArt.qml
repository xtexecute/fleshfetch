import QtQuick

Item {
    id: art
    required property int pixelSize
    required property Item particleLayer
    readonly property var buds: [[104, 20, 0, 1], [19, 52, 1, 0], [101, 80, 1, 0]]
    property int nextBud: 0
    property int petalCursor: 0
    objectName: "roseArt"

    function react() {
        if (!visible) return
        blossoms.itemAt(nextBud)?.bloom()
        nextBud = (nextBud + 1) % blossoms.count
    }

    function release(bud) {
        const origin = bud.mapToItem(particleLayer, bud.width / 2, bud.height * 0.48)
        for (let i = 0; i < 3; ++i) {
            petals.itemAt(petalCursor)?.scatter(origin.x, origin.y, i)
            petalCursor = (petalCursor + 1) % petals.count
        }
    }

    onVisibleChanged: {
        if (visible) return
        nextBud = 0
        petalCursor = 0
        for (let i = 0; i < blossoms.count; ++i) blossoms.itemAt(i)?.clear()
        for (let i = 0; i < petals.count; ++i) petals.itemAt(i)?.clear()
    }

    Image {
        anchors.fill: parent
        source: "../assets/skins/rose-vine-front.png"
        smooth: false
    }
    Repeater {
        id: blossoms
        model: art.buds
        delegate: Item {
            id: flower
            required property var modelData
            readonly property int idleFrame: modelData[3]
            property int frame: idleFrame
            width: 21 * art.pixelSize
            height: width
            x: (modelData[0] - 10) * art.pixelSize
            y: (modelData[1] - 17) * art.pixelSize
            clip: true
            objectName: "roseBlossom"

            function bloom() {
                opening.restart()
            }
            function clear() {
                opening.stop()
                frame = idleFrame
            }

            Image {
                source: "../assets/skins/rose-blooms.png"
                width: 3 * flower.width
                height: 2 * flower.height
                x: -flower.frame * flower.width
                y: -flower.modelData[2] * flower.height
                smooth: false
            }
            SequentialAnimation {
                id: opening
                ScriptAction { script: flower.frame = Math.max(1, flower.frame) }
                PauseAnimation { duration: 85 }
                ScriptAction { script: { flower.frame = 2; art.release(flower) } }
                PauseAnimation { duration: 1750 }
                ScriptAction { script: flower.frame = 1 }
                PauseAnimation { duration: 140 }
                ScriptAction { script: flower.frame = flower.idleFrame }
            }
        }
    }
    Item {
        parent: art.particleLayer
        anchors.fill: parent
        visible: art.visible
        Repeater {
            id: petals
            model: 36
            delegate: Item {
                id: petal
                objectName: "roseLoosePetal"
                property real life: 1
                property real startX: 0
                property real startY: 0
                property real drift: 0
                property real lift: 0
                property real fall: 0
                property real phase: 0
                readonly property int pixel: art.pixelSize
                readonly property int flip: Math.floor(life * 12 + phase) % 3
                width: 7 * pixel
                height: width
                clip: true
                visible: life < 1
                opacity: Math.min(1, (1 - life) * 3.2)
                x: Math.round((startX + drift * life + Math.sin(life * 8 + phase)
                    * 4 * pixel * life) / pixel) * pixel - 3 * pixel
                y: Math.round((startY - lift * Math.sin(life * Math.PI) + fall * life * life)
                    / pixel) * pixel - 3 * pixel

                function scatter(x, y, side) {
                    falling.stop()
                    startX = x + (side - 1) * 2 * pixel
                    startY = y
                    phase = Math.random() * 6
                    drift = (side - 1 + (Math.random() - 0.5) * 0.8) * 19 * pixel
                    lift = (8 + Math.random() * 9) * pixel
                    fall = (34 + Math.random() * 26) * pixel
                    life = 0
                    falling.duration = 1450 + Math.round(Math.random() * 600)
                    falling.start()
                }
                function clear() {
                    falling.stop()
                    life = 1
                }

                Image {
                    source: "../assets/skins/rose-petals.png"
                    width: 3 * petal.width
                    height: petal.height
                    x: -petal.flip * petal.width
                    smooth: false
                }
                NumberAnimation { id: falling; target: petal; property: "life"; from: 0; to: 1 }
            }
        }
    }
}

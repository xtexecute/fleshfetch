import QtQuick

Item {
    id: art
    objectName: "sandcastleArt"
    required property int pixelSize
    readonly property var breaksAt: [[67, 89, 98, 108], [18, 59, 72, 91], [111, 55, 67, 88]]
    property var damage: [0, 0, 0]
    property int debrisCursor: 0

    function crumble(u) {
        if (!visible) return
        rebuild.stop()
        idle.restart()
        const preferred = u < 0.42 ? 1 : u > 0.58 ? 2 : 0
        let section = preferred
        if (damage[section] === 3) {
            const others = preferred === 0 ? (u < 0.50 ? [1, 2] : [2, 1]) : [0, 3 - preferred]
            section = others.find(i => damage[i] < 3) ?? preferred
        }
        const before = damage[section]
        if (before < 3) {
            const stages = damage.slice()
            stages[section]++
            damage = stages
        }
        const point = breaksAt[section]
        const count = before < 3 ? 8 : 3
        for (let i = 0; i < count; ++i) {
            debris.itemAt(debrisCursor)?.scatter(point[0] * pixelSize,
                point[1 + before] * pixelSize, i)
            debrisCursor = (debrisCursor + 1) % debris.count
        }
    }

    onVisibleChanged: {
        if (visible) return
        idle.stop()
        rebuild.stop()
        damage = [0, 0, 0]
        debrisCursor = 0
        for (let i = 0; i < debris.count; ++i) debris.itemAt(i)?.clear()
    }

    Timer {
        id: idle
        interval: 950
        onTriggered: rebuild.start()
    }
    Timer {
        id: rebuild
        interval: 145
        repeat: true
        onTriggered: {
            const stages = art.damage.slice()
            const section = stages.indexOf(Math.max(...stages))
            if (stages[section] > 0) {
                stages[section]--
                art.damage = stages
            }
            if (stages.every(level => level === 0)) stop()
        }
    }

    Repeater {
        model: 3
        delegate: Item {
            id: section
            required property int index
            anchors.fill: parent
            clip: true
            Image {
                source: "../assets/skins/sandcastle-parts.png"
                width: section.width * 4
                height: section.height * 3
                x: -art.damage[section.index] * section.width
                y: -section.index * section.height
                smooth: false
            }
        }
    }
    Repeater {
        id: debris
        model: 42
        delegate: Item {
            id: piece
            objectName: "sandcastleDebris"
            property real life: 1
            property real originX: 0
            property real originY: 0
            property real travelX: 0
            property real heightAtApex: 0
            property real landedY: 0
            property int shape: 0
            readonly property int unit: art.pixelSize
            width: 7 * unit
            height: width
            clip: true
            visible: life < 1
            opacity: Math.min(1, (1 - life) * 3)
            x: Math.round((originX + travelX * life) / unit) * unit - 3 * unit
            y: Math.round((originY + (landedY - originY) * life * life
                - 4 * heightAtApex * life * (1 - life)) / unit) * unit - 3 * unit

            function scatter(x, y, i) {
                tumble.stop()
                shape = i % 3
                originX = x + (Math.random() - 0.5) * 15 * unit
                originY = y + Math.random() * 4 * unit
                travelX = (Math.random() - 0.5) * 36 * unit
                heightAtApex = (3 + Math.random() * 9) * unit
                landedY = Math.min(art.height - 4 * unit, originY + (13 + Math.random() * 30) * unit)
                life = 0
                tumble.duration = 370 + Math.round(Math.random() * 300)
                tumble.start()
            }
            function clear() {
                tumble.stop()
                life = 1
            }
            Image {
                source: "../assets/skins/sandcastle-chunks.png"
                width: piece.width * 3
                height: piece.height
                x: -piece.shape * piece.width
                smooth: false
            }
            NumberAnimation { id: tumble; target: piece; property: "life"; from: 0; to: 1 }
        }
    }
}

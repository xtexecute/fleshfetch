import QtQuick

Item {
    id: chamber
    objectName: "zeroGravityMotion"
    required property real bodySize
    readonly property real topMargin: Math.min(22, height * 0.18)
    readonly property real centerY: (height + topMargin) / 2
    readonly property real maxSpeed: Math.max(95, bodySize * 1.5)
    property real offsetX: 0
    property real offsetY: 0
    property real velocityX: 0
    property real velocityY: 0
    property real angle: 0
    property real angularVelocity: 0
    property real lastTick: 0
    property int dustCursor: 0

    function reset() {
        offsetX = 0
        offsetY = 0
        velocityX = visible ? 17 : 0
        velocityY = visible ? -12 : 0
        angle = 0
        angularVelocity = 0
        lastTick = 0
        dustCursor = 0
        for (let i = 0; i < motes.count; ++i) motes.itemAt(i)?.clear()
    }

    function limit(value, max) {
        return Math.max(-max, Math.min(max, value))
    }

    function kick(u, v, hitX, hitY) {
        if (!visible) return
        const radians = angle * Math.PI / 180
        const localX = u - 0.5, localY = v - 0.5
        let dx = localX * Math.cos(radians) - localY * Math.sin(radians)
        let dy = localX * Math.sin(radians) + localY * Math.cos(radians)
        let distance = Math.hypot(dx, dy)
        if (distance < 0.06) {
            const heading = Math.random() * 2 * Math.PI
            dx = Math.cos(heading) * 0.06
            dy = Math.sin(heading) * 0.06
            distance = 0.06
        }
        const bias = (Math.random() - 0.5) * 0.52
        const pushX = (-dx * Math.cos(bias) + dy * Math.sin(bias)) / distance
        const pushY = (-dx * Math.sin(bias) - dy * Math.cos(bias)) / distance
        const impulse = Math.max(54, bodySize * 0.53)
        velocityX += pushX * impulse
        velocityY += pushY * impulse
        const speed = Math.hypot(velocityX, velocityY)
        if (speed > maxSpeed) {
            velocityX *= maxSpeed / speed
            velocityY *= maxSpeed / speed
        }
        angularVelocity = limit(angularVelocity + (dx * pushY - dy * pushX) * 680, 92)
        scatter(hitX, hitY, 5, -pushX * 20, -pushY * 20, false)
    }

    function step() {
        const now = Date.now()
        const dt = lastTick ? Math.max(0, Math.min(0.038, (now - lastTick) / 1000)) : 0
        lastTick = now
        if (!dt) return

        angle += angularVelocity * dt
        if (Math.abs(angle) > 32) {
            angle = limit(angle, 32)
            angularVelocity *= -0.42
        }
        angularVelocity *= Math.exp(-1.0 * dt)
        const theta = Math.abs(angle) * Math.PI / 180
        const c = Math.cos(theta), s = Math.sin(theta)
        const xRadius = bodySize * (0.424 * c + 0.397 * s)
        const yRadius = bodySize * (0.397 * c + 0.424 * s)
        const maxX = Math.max(0, width / 2 - xRadius - 3)
        const maxY = Math.max(0, (height - topMargin) / 2 - yRadius - 3)
        offsetX += velocityX * dt
        offsetY += velocityY * dt

        if (Math.abs(offsetX) > maxX) {
            const edge = Math.sign(offsetX)
            offsetX = limit(offsetX, maxX)
            if (velocityX * edge > 0) {
                if (Math.abs(velocityX) > 32)
                    scatter(edge > 0 ? width - 4 : 4, centerY + offsetY, 6, -edge * 20, 0, true)
                velocityX *= -0.87
                angularVelocity = limit(angularVelocity - edge * velocityY * 0.24, 92)
            }
        }
        if (Math.abs(offsetY) > maxY) {
            const edge = Math.sign(offsetY)
            offsetY = limit(offsetY, maxY)
            if (velocityY * edge > 0) {
                if (Math.abs(velocityY) > 32)
                    scatter(width / 2 + offsetX, edge > 0 ? height - 4 : topMargin + 3, 6, 0, -edge * 20, true)
                velocityY *= -0.87
                angularVelocity = limit(angularVelocity + edge * velocityX * 0.24, 92)
            }
        }
        const coast = Math.exp(-0.14 * dt)
        velocityX *= coast
        velocityY *= coast
    }

    function scatter(x, y, count, pushX, pushY, impact) {
        for (let i = 0; i < count; ++i) {
            motes.itemAt(dustCursor)?.release(x, y, pushX, pushY, impact)
            dustCursor = (dustCursor + 1) % motes.count
        }
    }

    onVisibleChanged: reset()
    Timer {
        interval: 16
        repeat: true
        running: chamber.visible
        onTriggered: chamber.step()
    }

    Repeater {
        model: 4
        delegate: Item {
            required property int index
            readonly property bool onRight: index % 2 === 1
            readonly property bool onBottom: index >= 2
            width: 16
            height: 16
            x: onRight ? chamber.width - width - 4 : 4
            y: onBottom ? chamber.height - height - 4 : chamber.topMargin + 4
            opacity: 0.64
            Rectangle {
                width: 14; height: 2
                x: parent.onRight ? 2 : 0
                y: parent.onBottom ? 14 : 0
                color: "#87acbb"
            }
            Rectangle {
                width: 2; height: 14
                x: parent.onRight ? 14 : 0
                y: parent.onBottom ? 2 : 0
                color: "#87acbb"
            }
            Rectangle {
                width: 3; height: 3
                x: parent.onRight ? 9 : 4
                y: parent.onBottom ? 9 : 4
                color: "#e3d398"
            }
        }
    }

    Repeater {
        id: motes
        model: 36
        delegate: Rectangle {
            id: mote
            required property int index
            property real life: 1
            property real originX: 0
            property real originY: 0
            property real driftX: 0
            property real driftY: 0
            property bool wall: false
            objectName: "zeroGravityMote"
            width: wall ? (index % 2 === 0 ? 5 : 3) : (index % 3 === 0 ? 5 : 3)
            height: wall ? 2 : width
            visible: life < 1
            opacity: wall ? (1 - life) * 0.96 : Math.min(1, (1 - life) * 2.1)
            x: Math.round(originX + driftX * life - width / 2)
            y: Math.round(originY + driftY * life - height / 2)
            color: wall ? "#d9f4ff" : ["#d96a76", "#a3c6d3", "#f9e3ae"][index % 3]

            function release(x, y, pushX, pushY, impact) {
                drift.stop()
                originX = x
                originY = y
                const heading = Math.random() * Math.PI * 2
                const travel = (impact ? 6 : 17) + Math.random() * (impact ? 12 : 29)
                driftX = pushX + Math.cos(heading) * travel
                driftY = pushY + Math.sin(heading) * travel
                wall = impact
                life = 0
                drift.duration = impact ? 240 : 1120 + Math.round(Math.random() * 620)
                drift.start()
            }
            function clear() {
                drift.stop()
                life = 1
            }
            NumberAnimation { id: drift; target: mote; property: "life"; from: 0; to: 1 }
        }
    }
}

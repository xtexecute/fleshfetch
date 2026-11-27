import QtQuick

Item {
    id: motion
    property real bowlWidth: 0
    property real bowlHeight: 0
    property real offsetX: 0
    property real offsetY: 0
    property real velocityX: 0
    property real velocityY: 0
    property real floatAngle: 0
    property real angularVelocity: 0
    property real surfaceTilt: 0
    property real surfaceVelocity: 0
    property real currentX: 0
    property real currentY: 0
    property real targetCurrentX: 0
    property real targetCurrentY: 0
    property real currentTime: 0
    property real lastTick: 0

    function reset() {
        offsetX = 0
        offsetY = 0
        velocityX = 0
        velocityY = 0
        floatAngle = 0
        angularVelocity = 0
        surfaceTilt = 0
        surfaceVelocity = 0
        currentX = 0
        currentY = 0
        targetCurrentX = 0
        targetCurrentY = 0
        currentTime = 0
        lastTick = 0
    }

    function kick(normalizedX, normalizedY) {
        const side = normalizedX < 0.45 ? 1
            : normalizedX > 0.55 ? -1 : (Math.random() < 0.5 ? -1 : 1)
        const depth = Math.max(0, Math.min(1, normalizedY))
        velocityX = Math.max(-130, Math.min(130, velocityX + side * (62 + depth * 18)))
        velocityY = Math.max(-100, velocityY - 32)
        angularVelocity = Math.max(-90, Math.min(90, angularVelocity + side * 54))
        surfaceVelocity = Math.max(-100, Math.min(100, surfaceVelocity + side * 65))
    }

    function step() {
        const now = Date.now()
        if (!lastTick) {
            lastTick = now
            return
        }
        const dt = Math.min(0.034, (now - lastTick) / 1000)
        lastTick = now
        if (dt <= 0) return
        currentTime -= dt
        if (currentTime <= 0) {
            targetCurrentX = (Math.random() < 0.5 ? -1 : 1) * (16 + Math.random() * 16)
            targetCurrentY = (Math.random() < 0.5 ? -1 : 1) * (24 + Math.random() * 30)
            currentTime = 1.2 + Math.random() * 1.4
        }
        const blend = 1 - Math.exp(-1.5 * dt)
        currentX += (targetCurrentX - currentX) * blend
        currentY += (targetCurrentY - currentY) * blend

        velocityX += (currentX - 10 * offsetX - 2.5 * velocityX) * dt
        velocityY += (currentY - 16 * offsetY - 3 * velocityY) * dt
        offsetX += velocityX * dt
        offsetY += velocityY * dt

        const maxX = Math.min(24, bowlWidth * 0.095)
        const maxY = Math.min(14, bowlHeight * 0.06)
        if (Math.abs(offsetX) > maxX) {
            offsetX = Math.sign(offsetX) * maxX
            velocityX *= -0.38
        }
        if (Math.abs(offsetY) > maxY) {
            offsetY = Math.sign(offsetY) * maxY
            velocityY *= -0.32
        }

        angularVelocity += (-18 * floatAngle - 4 * angularVelocity + 0.025 * velocityX) * dt
        floatAngle += angularVelocity * dt
        if (Math.abs(floatAngle) > 12) {
            floatAngle = Math.sign(floatAngle) * 12
            angularVelocity *= -0.3
        }

        surfaceVelocity += (-30 * surfaceTilt - 5 * surfaceVelocity + 0.16 * velocityX) * dt
        surfaceTilt = Math.max(-10, Math.min(10, surfaceTilt + surfaceVelocity * dt))
    }

    onVisibleChanged: reset()
    Timer {
        interval: 16
        repeat: true
        running: motion.visible
        onTriggered: motion.step()
    }
}

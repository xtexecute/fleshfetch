import QtQuick

Item {
    id: art
    objectName: "shadowTwinArt"
    required property url source
    required property real fleshLeft
    required property real fleshTop
    required property real fleshWidth
    required property real fleshHeight
    readonly property real size: Math.min(fleshWidth, fleshHeight)
    readonly property point nearRest: Qt.point(-size * 0.105, -size * 0.060)
    readonly property var exposureTimes: [0, 0.075, 0.17]
    property real travel: 1
    property point start: Qt.point(0, 0)
    property point end: Qt.point(0, 0)
    readonly property point shift: positionAt(travel)
    property int exposure: exposureTimes.length
    property int trailCursor: 0
    property int strikes: 0

    function clamp(value, low, high) {
        return Math.max(low, Math.min(high, value))
    }

    function positionAt(t) {
        if (t < 0.24) {
            const k = 1 - Math.pow(1 - t / 0.24, 2.3)
            return Qt.point(start.x + (end.x - start.x) * k,
                            start.y + (end.y - start.y) * k)
        }
        const k = Math.pow((1 - t) / 0.76, 1.9)
        return Qt.point(end.x * k, end.y * k)
    }

    function react(u, v) {
        if (!visible || size <= 0) return
        start = shift
        lunge.stop()
        let dx = 0.5 - u
        let dy = 0.5 - v
        if (dx * dx + dy * dy < 0.025) {
            dx = strikes % 2 ? 0.45 : -0.45
            dy = strikes % 2 ? -0.8 : 0.8
        }
        const length = Math.hypot(dx, dy)
        const x = clamp(nearRest.x + size * 0.245 * dx / length,
                        -fleshLeft - size * 0.06, width - fleshLeft - fleshWidth + size * 0.06)
        const y = clamp(nearRest.y + size * 0.30 * dy / length,
                        -fleshTop - size * 0.015, height - fleshTop - fleshHeight + size * 0.06)
        end = Qt.point(x - nearRest.x, y - nearRest.y)
        ++strikes
        exposure = 0
        travel = 0
        capture()
        lunge.start()
    }

    function capture() {
        while (exposure < exposureTimes.length && travel >= exposureTimes[exposure]) {
            const t = exposureTimes[exposure]
            const at = positionAt(t)
            const image = traces.itemAt(trailCursor)
            if (image) image.imprint(fleshLeft + nearRest.x + at.x,
                                     fleshTop + nearRest.y + at.y,
                                     t / 0.24 * end.x / Math.max(1, size) * 36,
                                     0.42 + 0.10 * exposure)
            trailCursor = (trailCursor + 1) % traces.count
            ++exposure
        }
    }

    onTravelChanged: capture()
    onVisibleChanged: {
        if (visible) return
        lunge.stop()
        exposure = exposureTimes.length
        travel = 1
        trailCursor = 0
        strikes = 0
        for (let i = 0; i < traces.count; ++i) traces.itemAt(i)?.clear()
    }

    NumberAnimation {
        id: lunge
        target: art
        property: "travel"
        from: 0
        to: 1
        duration: 530
    }

    Repeater {
        id: traces
        model: 18
        delegate: Image {
            id: trace
            objectName: "shadowTwinTrace"
            source: art.visible ? art.source : ""
            width: art.fleshWidth
            height: art.fleshHeight
            fillMode: Image.PreserveAspectFit
            smooth: true
            visible: opacity > 0
            opacity: 0

            function imprint(left, top, tilt, strength) {
                fade.stop()
                x = left
                y = top
                rotation = tilt
                opacity = strength
                fade.start()
            }
            function clear() {
                fade.stop()
                opacity = 0
            }
            NumberAnimation {
                id: fade
                target: trace
                property: "opacity"
                to: 0
                duration: 680
                easing.type: Easing.InQuad
            }
        }
    }

    Image {
        objectName: "shadowTwinNear"
        source: art.visible ? art.source : ""
        x: art.fleshLeft + art.nearRest.x + art.shift.x
        y: art.fleshTop + art.nearRest.y + art.shift.y
        width: art.fleshWidth
        height: art.fleshHeight
        fillMode: Image.PreserveAspectFit
        smooth: true
        rotation: art.shift.x / Math.max(1, art.size) * 36
        opacity: 0.91
    }
}

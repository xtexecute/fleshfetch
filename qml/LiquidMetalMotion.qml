import QtQuick

Item {
    id: motion
    objectName: "liquidMetalMotion"
    readonly property vector3d ripple0: first.sample
    readonly property vector3d ripple1: second.sample
    readonly property vector3d ripple2: third.sample
    property int next: 0

    function strike(u, v) {
        if (!visible) return
        const wave = [first, second, third][next]
        wave.start(u, v)
        next = (next + 1) % 3
    }

    onVisibleChanged: {
        if (visible) return
        first.clear()
        second.clear()
        third.clear()
        next = 0
    }

    component Wave: QtObject {
        id: wave
        property real u: 0.5
        property real v: 0.5
        property real age: 1
        readonly property vector3d sample: Qt.vector3d(u, v, age)
        property NumberAnimation travel: NumberAnimation {
            target: wave
            property: "age"
            from: 0
            to: 1
            duration: 970
        }
        function start(x, y) {
            travel.stop()
            u = x
            v = y
            travel.start()
        }
        function clear() {
            travel.stop()
            age = 1
        }
    }

    Wave { id: first }
    Wave { id: second }
    Wave { id: third }
}

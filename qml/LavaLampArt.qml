import QtQuick

Item {
    id: lamp
    objectName: "lavaLampArt"
    required property string source
    property int pixelSize: 1
    width: 76 * pixelSize
    height: 132 * pixelSize
    property real time: 0
    property real energy: 0
    property real lastTick: 0
    readonly property vector2d clickPoint: Qt.vector2d(38 * pixelSize, 63 * pixelSize)
    readonly property vector4d blob0: first.value
    readonly property vector4d blob1: second.value
    readonly property vector4d blob2: third.value
    readonly property vector4d blob3: fourth.value
    readonly property vector4d blob4: fifth.value
    function hitTest(x, y) {
        return visible && game.isCosmeticPropHit("lava_lamp", x, y, width, height);
    }
    function strike(x, y) {
        if (!visible)
            return;
        fade.stop();
        energy = Math.min(1, energy + .34);
        fade.start();
        for (const b of [first, second, third, fourth, fifth]) {
            const depth = Math.max(0, Math.min(1, (b.py - 38) / 55));
            b.heat = Math.min(1, b.heat + .12 * depth);
            b.vy = Math.max(-22, b.vy - 3 * depth);
            b.vx = Math.max(-16, Math.min(16, b.vx + (b.px - x / pixelSize) * .16));
        }
    }
    onVisibleChanged: {
        fade.stop();
        energy = 0;
        time = 0;
        lastTick = 0;
        for (const b of [first, second, third, fourth, fifth])
            b.reset();
    }
    NumberAnimation {
        id: fade
        target: lamp
        property: "energy"
        to: 0
        duration: 2500
        easing.type: Easing.OutQuad
    }
    Timer {
        interval: 32
        repeat: true
        running: lamp.visible
        onTriggered: {
            const now = Date.now(), dt = lamp.lastTick ? Math.min(.04, (now - lamp.lastTick) / 1000) : .032;
            lamp.lastTick = now;
            lamp.time += dt;
            for (const b of [first, second, third, fourth, fifth])
                b.step(dt);
        }
    }
    component Blob: QtObject {
        required property int index
        property real px: 38
        property real py: 65
        property real vx: 0
        property real vy: 0
        property real heat: .5
        readonly property real radius: [15, 8, 10, 7, 9][index]
        readonly property vector4d value: Qt.vector4d(px, py, radius, heat)
        function reset() {
            px = [36, 32, 46, 29, 44][index];
            py = [66, 32, 82, 88, 47][index];
            heat = [.65, .25, .75, .8, .45][index];
            vx = 0;
            vy = 0;
        }
        Component.onCompleted: reset()
        function step(dt) {
            const target = Math.max(0, Math.min(1, (py - 24) / 66));
            heat += (target - heat) * dt * (py < 45 ? 1.5 : .45);
            vx += (Math.sin(lamp.time * .4 + index * 2.4) * 1.8 - vx * .7) * dt;
            vy += ((.52 - heat) * 24 - vy * .55) * dt;
            vx = Math.max(-16, Math.min(16, vx));
            vy = Math.max(-22, Math.min(22, vy));
            px += vx * dt;
            py += vy * dt;
            const upper = 22 + radius * .6, lower = 98 - radius * .55;
            if (py < upper) {
                py = upper;
                vy = Math.abs(vy) * .3;
            }
            if (py > lower) {
                py = lower;
                vy = -Math.abs(vy) * .3;
            }
            const edge = 25 - (py - 17) * 12 / 80 + radius * .65;
            if (px < edge) {
                px = edge;
                vx = Math.abs(vx) * .35;
            }
            if (px > 76 - edge) {
                px = 76 - edge;
                vx = -Math.abs(vx) * .35;
            }
        }
    }
    Blob {
        id: first
        index: 0
    }
    Blob {
        id: second
        index: 1
    }
    Blob {
        id: third
        index: 2
    }
    Blob {
        id: fourth
        index: 3
    }
    Blob {
        id: fifth
        index: 4
    }
    Item {
        width: 76
        height: 132
        scale: lamp.pixelSize
        transformOrigin: Item.TopLeft
        Image {
            anchors.fill: parent
            source: "../assets/skins/lava-lamp-back.png"
            smooth: false
        }
        ShaderEffect {
            anchors.fill: parent
            fragmentShader: "shaders/lava-lamp.frag.qsb"
            property real time: lamp.time
            property real energy: lamp.energy
            property vector4d blob0: lamp.blob0
            property vector4d blob1: lamp.blob1
            property vector4d blob2: lamp.blob2
            property vector4d blob3: lamp.blob3
            property vector4d blob4: lamp.blob4
        }
        Image {
            x: first.px - 17
            y: first.py - 17
            width: 34
            height: 34
            source: lamp.visible ? lamp.source : ""
            fillMode: Image.PreserveAspectFit
            smooth: true
            layer.enabled: lamp.visible
            layer.effect: ShaderEffect {
                property var source
                property real time: lamp.time
                property real energy: lamp.energy
                property vector2d bodyOrigin: Qt.vector2d(first.px - 17, first.py - 17)
                fragmentShader: "shaders/lava-flesh.frag.qsb"
            }
        }
        Image {
            anchors.fill: parent
            source: "../assets/skins/lava-lamp-front.png"
            smooth: false
        }
    }
}

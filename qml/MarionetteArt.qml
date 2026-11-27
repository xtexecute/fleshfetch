import QtQuick

Item {
    id: puppet
    objectName: "marionetteArt"
    required property string source
    property int pixelSize: 1
    width: 128 * pixelSize
    height: 136 * pixelSize
    property real energy: 0
    property bool moving: false
    property real lastTick: 0
    readonly property vector2d p0: Qt.vector2d(20 + first.dx, 24 + first.dy)
    readonly property vector2d p1: Qt.vector2d(108 + second.dx, 24 + second.dy)
    readonly property vector2d p2: Qt.vector2d(20 + third.dx, 112 + third.dy)
    readonly property vector2d p3: Qt.vector2d(108 + fourth.dx, 112 + fourth.dy)
    readonly property vector2d clickPoint: Qt.vector2d((p0.x + p1.x + p2.x + p3.x) * .25 * pixelSize, (p0.y + p1.y + p2.y + p3.y) * .25 * pixelSize)
    function mapNative(u, v) {
        return Qt.point((1 - u) * (1 - v) * p0.x + u * (1 - v) * p1.x + (1 - u) * v * p2.x + u * v * p3.x, (1 - u) * (1 - v) * p0.y + u * (1 - v) * p1.y + (1 - u) * v * p2.y + u * v * p3.y);
    }
    function texturePoint(x, y) {
        const px = x / pixelSize, py = y / pixelSize;
        const ax = p1.x - p0.x, ay = p1.y - p0.y, bx = p2.x - p0.x, by = p2.y - p0.y;
        const cx = p0.x - p1.x - p2.x + p3.x, cy = p0.y - p1.y - p2.y + p3.y;
        let u = (px - 20) / 88, v = (py - 24) / 88;
        for (let i = 0; i < 6; ++i) {
            const ex = p0.x + ax * u + bx * v + cx * u * v - px, ey = p0.y + ay * u + by * v + cy * u * v - py;
            const ux = ax + cx * v, uy = ay + cy * v, vx = bx + cx * u, vy = by + cy * u, det = ux * vy - uy * vx;
            if (Math.abs(det) < 1)
                return Qt.point(-1, -1);
            u -= (ex * vy - ey * vx) / det;
            v -= (ux * ey - uy * ex) / det;
        }
        return Qt.point(u, v);
    }
    function hitTest(x, y) {
        if (!visible)
            return false;
        const px = x / pixelSize, py = y / pixelSize;
        if (px <= 15 || px >= 113 || py <= 24 || py >= 119)
            return false;
        const uv = texturePoint(x, y);
        return uv.x >= 0 && uv.x < 1 && uv.y >= 0 && uv.y < 1 && game.isFleshHit(uv.x * 100, uv.y * 100, 100, 100);
    }
    function strike(u, v) {
        if (!visible)
            return;
        fade.stop();
        energy = Math.min(1, energy + .4);
        fade.start();
        const direction = u < .4 ? -1 : u > .6 ? 1 : Math.random() < .5 ? -1 : 1;
        const joints = [first, second, third, fourth];
        for (let i = 0; i < joints.length; ++i) {
            const j = joints[i], weight = .55 + 1 / (1 + Math.hypot(u - i % 2, v - Math.floor(i / 2)) * 3);
            j.vx = Math.max(-70, Math.min(70, j.vx + ((i % 2 ? 1 : -1) * 24 + direction * 12) * weight));
            j.vy = Math.max(-80, Math.min(80, j.vy + (i < 2 ? -28 : 34) * weight));
        }
        lastTick = 0;
        moving = true;
    }
    onVisibleChanged: {
        fade.stop();
        energy = 0;
        moving = false;
        lastTick = 0;
        for (const j of [first, second, third, fourth])
            j.clear();
        Qt.callLater(function () {
            ropes.requestPaint();
        });
    }
    NumberAnimation {
        id: fade
        target: puppet
        property: "energy"
        to: 0
        duration: 1400
        easing.type: Easing.OutQuad
    }
    component Joint: QtObject {
        property real dx: 0
        property real dy: 0
        property real vx: 0
        property real vy: 0
        function clear() {
            dx = 0;
            dy = 0;
            vx = 0;
            vy = 0;
        }
        function step(dt) {
            vx += (-65 * dx - 10 * vx) * dt;
            vy += (-65 * dy - 10 * vy) * dt;
            dx += vx * dt;
            dy += vy * dt;
            if (Math.abs(dx) > 8) {
                dx = Math.sign(dx) * 8;
                vx *= -.25;
            }
            if (Math.abs(dy) > 10) {
                dy = Math.sign(dy) * 10;
                vy *= -.25;
            }
            if (Math.abs(dx) + Math.abs(dy) + Math.abs(vx) + Math.abs(vy) < .04)
                clear();
        }
    }
    Joint {
        id: first
        objectName: "puppetJoint0"
    }
    Joint {
        id: second
        objectName: "puppetJoint1"
    }
    Joint {
        id: third
        objectName: "puppetJoint2"
    }
    Joint {
        id: fourth
        objectName: "puppetJoint3"
    }
    Timer {
        interval: 16
        repeat: true
        running: puppet.visible && puppet.moving
        onTriggered: {
            const now = Date.now(), dt = puppet.lastTick ? Math.min(.025, (now - puppet.lastTick) / 1000) : .016;
            puppet.lastTick = now;
            let motion = 0;
            for (const j of [first, second, third, fourth]) {
                j.step(dt);
                motion += Math.abs(j.dx) + Math.abs(j.dy) + Math.abs(j.vx) + Math.abs(j.vy);
            }
            ropes.requestPaint();
            if (motion === 0)
                puppet.moving = false;
        }
    }
    Item {
        width: 128
        height: 136
        scale: puppet.pixelSize
        transformOrigin: Item.TopLeft
        Image {
            id: body
            visible: false
            source: puppet.visible ? puppet.source : ""
            smooth: true
        }
        ShaderEffect {
            anchors.fill: parent
            fragmentShader: "shaders/marionette-flesh.frag.qsb"
            property var flesh: body
            property vector2d p0: puppet.p0
            property vector2d p1: puppet.p1
            property vector2d p2: puppet.p2
            property vector2d p3: puppet.p3
        }
        Canvas {
            id: ropes
            anchors.fill: parent
            onPaint: {
                const ctx = getContext('2d');
                ctx.clearRect(0, 0, width, height);
                const anchors = [[.16, .45, 28], [.8, .25, 100], [.18, .76, 38], [.65, .8, 90]];
                function thread(x0, y0, x1, y1, color) {
                    x0 = Math.round(x0);
                    y0 = Math.round(y0);
                    x1 = Math.round(x1);
                    y1 = Math.round(y1);
                    const dx = Math.abs(x1 - x0), sx = x0 < x1 ? 1 : -1, dy = -Math.abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
                    let error = dx + dy;
                    ctx.fillStyle = color;
                    for (let step = 0; step < 180; ++step) {
                        ctx.fillRect(x0, y0, 1, 1);
                        if (x0 === x1 && y0 === y1)
                            break;
                        const twice = 2 * error;
                        if (twice >= dy) {
                            error += dy;
                            x0 += sx;
                        }
                        if (twice <= dx) {
                            error += dx;
                            y0 += sy;
                        }
                    }
                }
                for (const a of anchors) {
                    const p = puppet.mapNative(a[0], a[1]);
                    thread(a[2] + 1, 22, p.x + 1, p.y, '#403b34');
                    thread(a[2], 22, p.x, p.y, '#b4a991');
                }
            }
            Component.onCompleted: requestPaint()
        }
        Repeater {
            model: [[.16, .45], [.8, .25], [.18, .76], [.65, .8]]
            delegate: Rectangle {
                required property var modelData
                x: Math.round(puppet.mapNative(modelData[0], modelData[1]).x) - 1
                y: Math.round(puppet.mapNative(modelData[0], modelData[1]).y) - 1
                width: 3
                height: 3
                color: '#79634a'
                Rectangle {
                    x: 1
                    y: 0
                    width: 1
                    height: 1
                    color: '#ead2a2'
                }
            }
        }
        Image {
            anchors.fill: parent
            source: "../assets/skins/marionette-frame.png"
            smooth: false
        }
    }
}

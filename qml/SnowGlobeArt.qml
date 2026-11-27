import QtQuick

Item {
    id: globe
    objectName: "snowGlobeArt"
    required property string source
    property int pixelSize: 1
    width: 112 * pixelSize
    height: 132 * pixelSize
    property real time: 0
    property real energy: 0
    property real fill: 0
    property real lastTick: 0
    readonly property vector2d clickPoint: Qt.vector2d(56 * pixelSize, 54 * pixelSize)
    function hitTest(x, y) {
        return visible && game.isCosmeticPropHit("snow_globe", x, y, width, height);
    }
    function strike(x, y) {
        if (!visible)
            return;
        fade.stop();
        energy = Math.min(1, energy + .36);
        fade.start();
        const u = x / pixelSize, v = y / pixelSize;
        const direction = u < 52 ? 1 : u > 60 ? -1 : Math.random() < .5 ? -1 : 1;
        for (let i = 0; i < flakes.count; ++i) {
            const flake = flakes.itemAt(i);
            flake.vx = Math.max(-65, Math.min(65, flake.vx - (flake.py - 54) * direction * .65 + (flake.px - u) * .16));
            flake.vy = Math.max(-65, Math.min(65, flake.vy + (flake.px - 56) * direction * .55 - 16 - Math.random() * 12));
        }
    }
    onVisibleChanged: {
        fade.stop();
        energy = 0;
        time = 0;
        lastTick = 0;
        for (let i = 0; i < flakes.count; ++i)
            flakes.itemAt(i)?.reset();
    }
    NumberAnimation {
        id: fade
        target: globe
        property: "energy"
        to: 0
        duration: 2300
        easing.type: Easing.OutQuad
    }
    Timer {
        interval: 32
        repeat: true
        running: globe.visible
        onTriggered: {
            const now = Date.now(), dt = globe.lastTick ? Math.min(.04, (now - globe.lastTick) / 1000) : .032;
            globe.lastTick = now;
            globe.time += dt;
            for (let i = 0; i < flakes.count; ++i)
                flakes.itemAt(i).step(dt);
        }
    }
    Item {
        width: 112
        height: 132
        scale: globe.pixelSize
        transformOrigin: Item.TopLeft
        Image {
            anchors.fill: parent
            source: "../assets/skins/snow-globe-back.png"
            smooth: false
        }
        Item {
            id: rear
            anchors.fill: parent
        }
        Image {
            x: 21
            y: 23
            width: 70
            height: 70
            source: globe.visible ? globe.source : ""
            fillMode: Image.PreserveAspectFit
            smooth: true
        }
        Item {
            id: front
            anchors.fill: parent
        }
        Repeater {
            id: flakes
            model: 72
            delegate: Item {
                id: flake
                objectName: "globeSnowflake"
                required property int index
                property real px: 56
                property real py: 54
                property real vx: 0
                property real vy: 0
                readonly property real phase: index * 2.399963
                width: index % 5 === 0 ? 2 : 1
                height: width
                x: Math.round(px - width / 2)
                y: Math.round(py - height / 2)
                Rectangle {
                    parent: flake.index % 3 === 0 ? rear : front
                    x: flake.x
                    y: flake.y
                    width: flake.width
                    height: flake.height
                    color: flake.index % 3 === 0 ? "#9ebbc8" : "#e7efeb"
                    opacity: flake.index % 3 === 0 ? .6 : .85
                }
                function reset() {
                    const a = Math.random() * 6.2831853, r = Math.sqrt(Math.random()) * .90;
                    px = 56 + Math.cos(a) * 44 * r;
                    py = 54 + Math.sin(a) * 43 * r;
                    vx = 0;
                    vy = 2 + Math.random() * 5;
                }
                Component.onCompleted: reset()
                function step(dt) {
                    vx += (Math.sin(globe.time * .7 + phase) * 1.2 - vx * .75) * dt;
                    vy += (7 - vy * .5) * dt;
                    px += vx * dt;
                    py += vy * dt;
                    const u = (px - 56) / 45, v = (py - 54) / 44, r = Math.hypot(u, v);
                    if (r > 1) {
                        px = 56 + u / r * 44.7;
                        py = 54 + v / r * 43.7;
                        const nx = u / r, ny = v / r, dot = vx * nx + vy * ny;
                        if (dot > 0) {
                            vx -= 1.3 * dot * nx;
                            vy -= 1.3 * dot * ny;
                        }
                    }
                }
            }
        }
        MaterialStreak {
            objectName: "globeStreakSnow"
            x: 9
            y: 6
            width: 94
            height: 94
            material: 1
            roundClip: 1
            fill: globe.fill
            time: globe.time
            energy: globe.energy
        }
        Image {
            anchors.fill: parent
            source: "../assets/skins/snow-globe-front.png"
            smooth: false
        }
    }
}

import QtQuick

Item {
    id: neon
    objectName: "neonOutlineArt"
    required property Item flesh
    property real time: 0
    property real energy: 0
    property real lastTick: 0
    property real pulse: 1
    property real origin: 0
    function strike(u, v) {
        if (!visible)
            return;
        origin = (Math.atan2(v - .5, u - .5) / (Math.PI * 2) + 1) % 1;
        travel.restart();
        fade.stop();
        energy = Math.min(1, energy + .45);
        fade.start();
    }
    onVisibleChanged: {
        if (visible)
            return;
        fade.stop();
        travel.stop();
        energy = 0;
        time = 0;
        pulse = 1;
        lastTick = 0;
    }
    NumberAnimation {
        id: fade
        target: neon
        property: "energy"
        to: 0
        duration: 1200
        easing.type: Easing.OutQuad
    }
    NumberAnimation {
        id: travel
        target: neon
        property: "pulse"
        from: 0
        to: 1
        duration: 1000
    }
    Timer {
        interval: 32
        repeat: true
        running: neon.visible
        onTriggered: {
            const now = Date.now();
            neon.time += neon.lastTick ? Math.min(.065, (now - neon.lastTick) / 1000) : .032;
            neon.lastTick = now;
        }
    }
    Image {
        id: distanceMap
        visible: false
        source: neon.visible ? "../assets/skins/neon-outline-field.png" : ""
        smooth: true
    }
    ShaderEffect {
        x: neon.flesh.x - neon.flesh.width * .125
        y: neon.flesh.y - neon.flesh.height * .125
        width: neon.flesh.width * 1.25
        height: neon.flesh.height * 1.25
        fragmentShader: "shaders/neon-outline.frag.qsb"
        property var field: distanceMap
        property real bodyWidth: neon.flesh.width
        property real time: neon.time
        property real energy: neon.energy
        property real pulse: neon.pulse
        property real origin: neon.origin
    }
}

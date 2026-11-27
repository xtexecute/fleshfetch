import QtQuick

Item {
    id: chart
    objectName: "starMapArt"
    property real time: 0
    property real lastTick: 0
    property real glow: 0
    property int cursor: 0
    property real fill: 0
    readonly property vector3d stroke0: first.value
    readonly property vector3d stroke1: second.value
    readonly property vector3d stroke2: third.value
    readonly property vector3d stroke3: fourth.value
    property alias stars: starsImage
    property alias halo: haloImage
    property alias traits: traitsImage

    function strike(u,v) {
        if (!visible) return
        const flashes=[first,second,third,fourth]
        flashes[cursor].light(u,v)
        cursor=(cursor+1)%flashes.length
        settle.stop()
        glow=Math.min(1,glow+.45)
        settle.start()
    }
    onVisibleChanged: {
        if (visible) return
        settle.stop()
        glow=0
        cursor=0
        time=0
        lastTick=0
        for (const flash of [first,second,third,fourth]) flash.clear()
    }
    NumberAnimation {
        id: settle
        target: chart
        property: "glow"
        to: 0
        duration: 2100
        easing.type: Easing.OutQuad
    }
    Timer {
        interval: 32
        repeat: true
        running: chart.visible
        onTriggered: {
            const now=Date.now()
            const dt=chart.lastTick ? Math.min(.065,(now-chart.lastTick)/1000) : .032
            chart.lastTick=now
            chart.time+=dt
        }
    }
    component Flash: QtObject {
        id: flash
        property real u: .5
        property real v: .5
        property real age: 1
        readonly property vector3d value: Qt.vector3d(u,v,age)
        property NumberAnimation travel: NumberAnimation {
            target: flash
            property: "age"
            from: 0; to: 1
            duration: 1600
        }
        function light(x,y) { travel.stop(); u=x; v=y; travel.start() }
        function clear() { travel.stop(); age=1 }
    }
    Flash { id: first }
    Flash { id: second }
    Flash { id: third }
    Flash { id: fourth }
    Image { id: starsImage; visible: false; source: chart.visible ? "../assets/skins/star-map.png" : ""; smooth: true }
    Image { id: haloImage; visible: false; source: chart.visible ? "../assets/skins/star-map-glow.png" : ""; smooth: true }
    Image { id: traitsImage; visible: false; source: chart.visible ? "../assets/skins/star-map-traits.png" : ""; smooth: false }
    ShaderEffect {
        anchors.fill: parent
        visible: chart.fill>0
        fragmentShader: "shaders/star-map-streak.frag.qsb"
        property real fill: chart.fill
        property real time: chart.time
        property real glow: chart.glow
        property vector2d viewport: Qt.vector2d(width,height)
        Behavior on fill { NumberAnimation { duration: 340; easing.type: Easing.OutQuad } }
    }
}

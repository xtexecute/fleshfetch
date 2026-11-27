import QtQuick

Item {
    id: art
    property string cosmetic: ""
    property int pixelScale: 1
    property real fleshLeft: 0
    property real fleshTop: 0
    property real fleshWidth: 0
    property real fleshHeight: 0
    property real keyAngle: 0
    property real hatLift: 0
    property real hatTilt: 0
    property int confettiCursor: 0
    property real glassesDrop: 0
    property real toyWidth: 1
    property real toyHeight: 1
    property int flagFrame: 0

    function react() {
        if (cosmetic === "wind_up_key") {
            keyWind.stop()
            if (keyAngle > 3600) keyAngle -= 3600
            keyWind.from = keyAngle
            keyWind.to = keyAngle + 90
            keyWind.start()
        } else if (cosmetic === "party_hat") {
            hatBounce.restart()
            const tip = partyHatArt.mapToItem(art, partyHatArt.width * 0.5, partyHatArt.height * 0.12)
            for (let i = 0; i < 6 && hatConfetti.count > 0; ++i) {
                const piece = hatConfetti.itemAt(confettiCursor)
                confettiCursor = (confettiCursor + 1) % hatConfetti.count
                if (piece) piece.launch(tip.x, tip.y, i)
            }
        } else if (cosmetic === "sunglasses") {
            glassesNudge.restart()
        } else if (cosmetic === "squeaky_toy") {
            toySqueeze.restart()
            game.playEffectSound("squeak")
        } else if (cosmetic === "tiny_flag") {
            flagFlutter.restart()
        }
    }

    onCosmeticChanged: {
        keyWind.stop()
        hatBounce.stop()
        glassesNudge.stop()
        toySqueeze.stop()
        flagFlutter.stop()
        keyAngle = 0
        hatLift = 0
        hatTilt = 0
        confettiCursor = 0
        for (let i = 0; i < hatConfetti.count; ++i) {
            const piece = hatConfetti.itemAt(i)
            if (piece) piece.clear()
        }
        glassesDrop = 0
        toyWidth = 1
        toyHeight = 1
        flagFrame = 0
    }

    NumberAnimation {
        id: keyWind
        target: art
        property: "keyAngle"
        duration: 320
        easing.type: Easing.OutCubic
    }
    SequentialAnimation {
        id: hatBounce
        ParallelAnimation {
            NumberAnimation { target: art; property: "hatLift"; from: 0; to: -8; duration: 85; easing.type: Easing.OutCubic }
            NumberAnimation { target: art; property: "hatTilt"; from: 0; to: 9; duration: 85; easing.type: Easing.OutCubic }
        }
        ParallelAnimation {
            NumberAnimation { target: art; property: "hatLift"; to: 0; duration: 310; easing.type: Easing.OutBounce }
            NumberAnimation { target: art; property: "hatTilt"; to: 0; duration: 310; easing.type: Easing.OutBack }
        }
    }
    SequentialAnimation {
        id: glassesNudge
        NumberAnimation { target: art; property: "glassesDrop"; from: 0; to: 7; duration: 65; easing.type: Easing.OutQuad }
        NumberAnimation { target: art; property: "glassesDrop"; to: 0; duration: 280; easing.type: Easing.OutBack }
    }
    SequentialAnimation {
        id: toySqueeze
        ParallelAnimation {
            NumberAnimation { target: art; property: "toyWidth"; from: 1; to: 1.14; duration: 75; easing.type: Easing.OutQuad }
            NumberAnimation { target: art; property: "toyHeight"; from: 1; to: 0.82; duration: 75; easing.type: Easing.OutQuad }
        }
        ParallelAnimation {
            NumberAnimation { target: art; property: "toyWidth"; to: 1; duration: 290; easing.type: Easing.OutBack }
            NumberAnimation { target: art; property: "toyHeight"; to: 1; duration: 290; easing.type: Easing.OutBack }
        }
    }
    SequentialAnimation {
        id: flagFlutter
        ScriptAction { script: art.flagFrame = 1 }
        PauseAnimation { duration: 90 }
        ScriptAction { script: art.flagFrame = 2 }
        PauseAnimation { duration: 90 }
        ScriptAction { script: art.flagFrame = 0 }
        PauseAnimation { duration: 90 }
        ScriptAction { script: art.flagFrame = 1 }
        PauseAnimation { duration: 90 }
        ScriptAction { script: art.flagFrame = 0 }
    }

    Image {
        id: keySocket
        visible: art.cosmetic === "wind_up_key"
        source: "../assets/skins/wind-up-socket.png"
        width: 44 * art.pixelScale
        height: 44 * art.pixelScale
        x: Math.round(art.fleshLeft + art.fleshWidth * 0.75 - width / 2)
        y: Math.round(art.fleshTop + art.fleshHeight * 0.38 - height / 2)
        smooth: false
        mipmap: false
    }
    Image {
        objectName: "windUpKeyArt"
        visible: keySocket.visible
        source: "../assets/skins/wind-up-key.png"
        width: keySocket.width
        height: keySocket.height
        x: keySocket.x
        y: keySocket.y
        rotation: art.keyAngle
        smooth: false
        mipmap: false
    }
    Image {
        id: partyHatArt
        objectName: "partyHatArt"
        visible: art.cosmetic === "party_hat"
        source: "../assets/skins/party-hat.png"
        width: 40 * art.pixelScale
        height: 44 * art.pixelScale
        x: Math.round(art.fleshLeft + art.fleshWidth * 0.52 - width / 2)
        y: Math.round(Math.max(3, art.fleshTop + art.fleshHeight * 0.16 - height + art.hatLift))
        transform: Rotation {
            origin.x: 20 * art.pixelScale
            origin.y: 40 * art.pixelScale
            angle: art.hatTilt
        }
        smooth: false
        mipmap: false
    }
    Repeater {
        id: hatConfetti
        model: 96
        delegate: Rectangle {
            id: piece
            objectName: "partyHatParticle"
            property real startX: 0
            property real startY: 0
            property real drift: 0
            property real rise: 0
            property real fall: 0
            visible: art.cosmetic === "party_hat"
            width: (index % 3 === 0 ? 3 : 2) * art.pixelScale
            height: (index % 3 === 0 ? 2 : 3) * art.pixelScale
            color: ["#ce5466", "#5b9292", "#e0b448", "#c86a37", "#893949", "#2d5b61"][index % 6]
            opacity: 0
            function clear() {
                motion.stop()
                opacity = 0
            }
            function launch(x, y, slot) {
                motion.stop()
                startX = x - width / 2
                startY = y - height / 2
                drift = (slot - 2.5) * (8 + Math.random() * 3) * art.pixelScale
                rise = (2 + Math.random() * 2) * art.pixelScale
                fall = (28 + Math.random() * 14) * art.pixelScale
                motion.start()
            }
            ParallelAnimation {
                id: motion
                NumberAnimation {
                    target: piece; property: "x"
                    from: piece.startX; to: piece.startX + piece.drift
                    duration: 1600; easing.type: Easing.OutQuad
                }
                SequentialAnimation {
                    NumberAnimation {
                        target: piece; property: "y"
                        from: piece.startY; to: piece.startY - piece.rise
                        duration: 220; easing.type: Easing.OutQuad
                    }
                    NumberAnimation {
                        target: piece; property: "y"
                        to: piece.startY + piece.fall
                        duration: 1380; easing.type: Easing.OutQuad
                    }
                }
                SequentialAnimation {
                    NumberAnimation { target: piece; property: "opacity"; from: 1; to: 1; duration: 850 }
                    NumberAnimation { target: piece; property: "opacity"; to: 0; duration: 750 }
                }
            }
        }
    }
    Image {
        objectName: "sunglassesArt"
        visible: art.cosmetic === "sunglasses"
        source: "../assets/skins/sunglasses.png"
        width: 64 * art.pixelScale
        height: 26 * art.pixelScale
        x: Math.round(art.fleshLeft + art.fleshWidth * 0.52 - width / 2)
        y: Math.round(art.fleshTop + art.fleshHeight * 0.30 + art.glassesDrop)
        smooth: false
        mipmap: false
    }
    Image {
        objectName: "squeakyToyArt"
        visible: art.cosmetic === "squeaky_toy"
        source: "../assets/skins/squeaky-toy.png"
        width: 46 * art.pixelScale
        height: 36 * art.pixelScale
        x: Math.round(art.fleshLeft + art.fleshWidth * 0.28 - width / 2)
        y: Math.round(art.fleshTop + art.fleshHeight * 0.49 - height / 2)
        transform: Scale {
            origin.x: 23 * art.pixelScale
            origin.y: 35 * art.pixelScale
            xScale: art.toyWidth
            yScale: art.toyHeight
        }
        smooth: false
        mipmap: false
    }
    Image {
        objectName: "tinyFlagArt"
        visible: art.cosmetic === "tiny_flag"
        source: "../assets/skins/tiny-flag-" + art.flagFrame + ".png"
        width: 38 * art.pixelScale
        height: 52 * art.pixelScale
        x: Math.round(art.fleshLeft + art.fleshWidth * 0.71 - width / 2)
        y: Math.round(Math.max(3, art.fleshTop + art.fleshHeight * 0.25 - height))
        smooth: false
        mipmap: false
    }
}

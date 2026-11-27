import QtQuick
import QtQuick.Window

Window {
    id: splash
    objectName: "startupSplash"
    width: 420
    height: 430
    x: (Screen.width - width) / 2
    y: (Screen.height - height) / 2
    visible: true
    flags: Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    title: "fleshfetch"
    color: "#181818"

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.width: 2
        border.color: "#d45b65"
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 115
        text: "fleshfetch"
        color: "#f4f4f4"
        font.family: Qt.platform.os === "windows" ? "Consolas" : "monospace"
        font.pixelSize: 35
        font.bold: true
    }

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 170
        width: 64
        height: 3
        color: "#d45b65"
    }

    AnimatedSprite {
        id: logo
        objectName: "startupLogo"
        anchors.horizontalCenter: parent.horizontalCenter
        y: 184
        width: 156
        height: 156
        source: splashLogoUrl
        frameWidth: 144
        frameHeight: 144
        frameCount: 120
        frameRate: 30
        interpolate: false
        smooth: true
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 345
        text: "xtexecute"
        color: "#bcbcbc"
        font.family: Qt.platform.os === "windows" ? "Consolas" : "monospace"
        font.pixelSize: 14
    }

    Text {
        id: loadingText
        anchors.horizontalCenter: parent.horizontalCenter
        y: 394
        property int dots: 0
        text: "Loading" + ".".repeat(dots)
        color: "#d45b65"
        font.family: Qt.platform.os === "windows" ? "Consolas" : "monospace"
        font.pixelSize: 12
        Timer {
            interval: 350
            running: true
            repeat: true
            onTriggered: loadingText.dots = (loadingText.dots + 1) % 4
        }
    }
}

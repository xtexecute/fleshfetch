import QtQuick

ShaderEffect {
    property real fill: 0
    property real time: 0
    property real energy: 0
    property real material: 0
    property real roundClip: 0
    property vector2d viewport: Qt.vector2d(width, height)
    visible: fill > 0
    fragmentShader: "shaders/material-streak.frag.qsb"
    Behavior on fill {
        NumberAnimation {
            duration: 340
            easing.type: Easing.OutQuad
        }
    }
}

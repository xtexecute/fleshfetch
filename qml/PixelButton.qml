import QtQuick
import QtQuick.Controls

AbstractButton {
    id: control
    required property var theme
    property string tooltip: ""
    property bool selected: false
    property bool destructive: false
    property bool tabStyle: false
    property var sprites: ({})
    property var spriteBorder: ({left: 8, top: 8, right: 8, bottom: 8})
    readonly property string spriteSource: (!enabled && sprites.disabled ? sprites.disabled
        : down && sprites.pressed ? sprites.pressed
        : hovered && sprites.hover ? sprites.hover : sprites.normal) || ""
    readonly property real visualOffset: tabStyle
        ? (selected || (enabled && hovered && !down) ? 0 : 6)
        : (enabled && down ? 2 : enabled && hovered ? -1 : 0)
    property real animatedOffset: visualOffset
    Behavior on animatedOffset { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    padding: 12
    topPadding: 10
    bottomPadding: 10
    implicitWidth: Math.max(40, contentItem.implicitWidth + leftPadding + rightPadding)
    implicitHeight: 42
    Accessible.name: text
    font.family: theme.family
    font.pixelSize: 14
    contentItem: Text {
        transform: Translate { y: control.animatedOffset }
        text: control.text
        font: control.font
        color: !control.enabled ? control.theme.muted
              : control.destructive ? control.theme.danger : control.theme.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Item {
        transform: Translate { y: control.animatedOffset }
        BorderImage {
            id: spriteImage
            anchors.fill: parent
            source: control.spriteSource
            border.left: control.spriteBorder.left
            border.top: control.spriteBorder.top
            border.right: control.spriteBorder.right
            border.bottom: control.spriteBorder.bottom
            smooth: false
        }
        PixelFrame {
        anchors.fill: parent
        visible: spriteImage.status !== Image.Ready
        theme: control.theme
        inset: 0
        opacity: control.enabled ? 1 : 0.45
        fillColor: control.down ? theme.pressed
                   : control.hovered || control.selected ? theme.hover : theme.raised
        Behavior on fillColor { ColorAnimation { duration: 140 } }
        Rectangle {
            anchors.fill: parent
            anchors.margins: 8
            color: "transparent"
            border.width: control.activeFocus ? 2 : control.selected ? 1 : 0
            border.color: control.theme.accent
        }
        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 9 }
            height: 2
            visible: control.hovered && control.enabled
            color: control.theme.accentHover
        }
    }
    }
    ToolTip.visible: hovered && tooltip.length > 0
    ToolTip.text: tooltip
    ToolTip.delay: 600
}

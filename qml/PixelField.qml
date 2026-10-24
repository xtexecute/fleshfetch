import QtQuick
import QtQuick.Controls

TextField {
    id: field
    required property var theme
    font.family: theme.family
    font.pixelSize: 14
    color: theme.text
    placeholderTextColor: theme.muted
    selectionColor: theme.accent
    selectedTextColor: "#202020"
    implicitHeight: 40
    leftPadding: 12
    rightPadding: 12
    selectByMouse: true
    background: Rectangle {
        color: field.theme.surface
        border.width: field.activeFocus ? 2 : 1
        border.color: field.activeFocus ? field.theme.focus : field.theme.line
    }
}

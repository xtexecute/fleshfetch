import QtQuick

Text {
    required property var theme
    color: theme.text
    font.family: theme.mono
    font.pixelSize: 18
    font.bold: true
    wrapMode: Text.Wrap
}

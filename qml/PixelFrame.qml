import QtQuick

Item {
    id: frame
    required property var theme
    property color fillColor: theme.surface
    property int inset: 14
    default property alias contentData: contents.data
    implicitWidth: 180
    implicitHeight: 48

    Rectangle {
        anchors.fill: parent
        anchors.margins: 4
        color: frame.fillColor
    }
    BorderImage {
        anchors.fill: parent
        source: frame.theme.frameSource
        border { left: 8; top: 8; right: 8; bottom: 8 }
        horizontalTileMode: BorderImage.Stretch
        verticalTileMode: BorderImage.Stretch
        smooth: false
    }
    Item {
        id: contents
        anchors.fill: parent
        anchors.margins: frame.inset
    }
}

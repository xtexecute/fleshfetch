import QtQuick
import QtQuick.Window

Item {
    id: handles
    required property var window
    enabled: window.visibility !== Window.Maximized && window.visibility !== Window.FullScreen
    Repeater {
        model: [Qt.LeftEdge | Qt.TopEdge, Qt.RightEdge | Qt.TopEdge,
                Qt.LeftEdge | Qt.BottomEdge, Qt.RightEdge | Qt.BottomEdge,
                Qt.LeftEdge, Qt.RightEdge, Qt.TopEdge, Qt.BottomEdge]
        delegate: MouseArea {
            required property int modelData
            readonly property bool leftEdge: (modelData & Qt.LeftEdge) !== 0
            readonly property bool rightEdge: (modelData & Qt.RightEdge) !== 0
            readonly property bool topEdge: (modelData & Qt.TopEdge) !== 0
            readonly property bool bottomEdge: (modelData & Qt.BottomEdge) !== 0
            readonly property bool corner: (leftEdge || rightEdge) && (topEdge || bottomEdge)
            x: rightEdge ? handles.width - width : leftEdge ? 0 : 10
            y: bottomEdge ? handles.height - height : topEdge ? 0 : 10
            width: corner ? 10 : leftEdge || rightEdge ? 5 : handles.width - 20
            height: corner ? 10 : topEdge || bottomEdge ? 5 : handles.height - 20
            cursorShape: corner ? (leftEdge === topEdge ? Qt.SizeFDiagCursor : Qt.SizeBDiagCursor)
                                : leftEdge || rightEdge ? Qt.SizeHorCursor : Qt.SizeVerCursor
            onPressed: handles.window.startSystemResize(modelData)
        }
    }
}

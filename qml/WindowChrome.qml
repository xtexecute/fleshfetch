import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Item {
    id: chrome
    required property var theme
    required property var window
    property string title: "Fleshfetch"
    implicitHeight: 46
    Rectangle { anchors.fill: parent; color: chrome.theme.surface }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: chrome.theme.line }
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 5
        spacing: 3
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10
                Rectangle { width: 8; height: 8; anchors.verticalCenter: parent.verticalCenter; color: chrome.theme.accent }
                Text { text: chrome.title; color: chrome.theme.text; font.family: chrome.theme.mono; font.pixelSize: 15; font.bold: true; width: Math.max(0, parent.parent.width - 30); elide: Text.ElideRight }
            }
            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                onPressed: chrome.window.startSystemMove()
                onDoubleClicked: chrome.toggleMaximize()
            }
        }
        PixelButton { theme: chrome.theme; text: "\u2212"; tooltip: "Minimize"; implicitWidth: 40; onClicked: chrome.window.showMinimized() }
        PixelButton { theme: chrome.theme; text: chrome.window.visibility === Window.Maximized ? "\u2750" : "\u25a1"; tooltip: "Maximize / Restore"; implicitWidth: 40; onClicked: chrome.toggleMaximize() }
        PixelButton { theme: chrome.theme; text: "\u00d7"; tooltip: "Close"; implicitWidth: 40; destructive: true; onClicked: chrome.window.close() }
    }
    function toggleMaximize() {
        if (window.visibility === Window.Maximized) window.showNormal()
        else window.showMaximized()
    }
}

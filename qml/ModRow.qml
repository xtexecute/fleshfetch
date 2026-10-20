import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: row
    required property var theme
    required property var mod
    property bool expanded: false
    readonly property bool severe: Number(mod.level) >= 2 || mod.blocked === true
    readonly property bool warning: Number(mod.level) > 0 || mod.blocked === true
    spacing: 6
    RowLayout {
        Layout.fillWidth: true
        AbstractButton {
            id: disclosure
            Layout.fillWidth: true
            implicitHeight: 48
            hoverEnabled: true
            focusPolicy: Qt.StrongFocus
            Accessible.name: row.mod.name + (row.expanded ? ", collapse details" : ", expand details")
            Accessible.role: Accessible.Button
            onClicked: row.expanded = !row.expanded
            background: Rectangle { color: disclosure.hovered ? row.theme.hover : "transparent"; border.width: disclosure.activeFocus ? 2 : 0; border.color: row.theme.focus }
            contentItem: RowLayout {
                spacing: 8
                Text { text: row.expanded ? "\u25be" : "\u25b8"; color: row.theme.accentHover; font.pixelSize: 16; Layout.preferredWidth: 16 }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text { text: row.mod.name; color: row.theme.text; font.bold: true; font.pixelSize: 14; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Text { text: row.mod.blocked ? "Blocked" : row.mod.enabled ? "Enabled" : "Disabled"; color: row.warning ? (row.severe ? row.theme.danger : row.theme.warning) : row.theme.muted; font.pixelSize: 12 }
                }
            }
        }
        Switch {
            checked: row.mod.enabled === true
            Accessible.name: "Enable " + row.mod.name
            enabled: !row.mod.blocked || row.mod.enabled === true
            onClicked: game.toggleMod(row.mod.key)
        }
    }
    ColumnLayout {
        visible: row.expanded
        Layout.fillWidth: true
        Layout.leftMargin: 24
        Layout.rightMargin: 6
        spacing: 9
        Text { text: (row.mod.author || "Unknown author") + "  \u00b7  " + (row.mod.version || "Unversioned"); color: row.theme.muted; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
        Text { text: row.mod.description || ""; color: row.theme.text; font.pixelSize: 14; wrapMode: Text.Wrap; Layout.fillWidth: true; visible: text.length > 0 }
        Rectangle {
            visible: row.warning
            Layout.fillWidth: true
            implicitHeight: warningContent.implicitHeight + 20
            color: row.theme.surface
            border.color: row.severe ? row.theme.danger : row.theme.warning
            ColumnLayout {
                id: warningContent
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                spacing: 6
                Text { text: row.severe ? "Security / dependency warning" : "Mod warning"; color: row.severe ? row.theme.danger : row.theme.warning; font.bold: true; font.pixelSize: 14; wrapMode: Text.Wrap; Layout.fillWidth: true }
                Text { text: (row.mod.reasons || []).join("\n"); color: row.theme.text; font.pixelSize: 13; wrapMode: Text.Wrap; textFormat: Text.PlainText; Layout.fillWidth: true; visible: text.length > 0 }
                PixelButton { theme: row.theme; text: "Dismiss warning"; destructive: row.severe; visible: Number(row.mod.level) > 0; onClicked: game.dismissModWarning(row.mod.key) }
            }
        }
        Text { text: "Legacy API"; visible: row.mod.legacy === true; color: row.theme.warning; font.pixelSize: 12 }
        CheckBox {
            text: "Use title: " + (row.mod.gameTitle || "")
            visible: !!row.mod.gameTitle
            enabled: row.mod.enabled === true && !row.mod.blocked
            checked: row.mod.titleSelected === true
            Layout.fillWidth: true
            contentItem: Text { text: parent.text; font.pixelSize: 14; color: row.theme.text; wrapMode: Text.Wrap; leftPadding: parent.indicator.width + parent.spacing; verticalAlignment: Text.AlignVCenter }
            onClicked: game.selectModTitle(row.mod.key, checked)
        }
    }
    Rectangle { Layout.fillWidth: true; Layout.topMargin: 6; height: 1; color: row.theme.line }
}

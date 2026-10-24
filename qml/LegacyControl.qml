import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Fleshfetch.Legacy 1.0

Item {
    id: control
    required property var node
    required property var theme
    readonly property var d: node ? node.data : ({})
    visible: d.visible !== false
    enabled: d.sensitive !== false
    implicitHeight: visible && view.item ? view.item.implicitHeight + (d.marginTop || 0) + (d.marginBottom || 0) : 0
    Loader {
    id: view
    anchors.fill: parent
    anchors.topMargin: control.d.marginTop || 0
    anchors.bottomMargin: control.d.marginBottom || 0
    anchors.leftMargin: control.d.marginLeft || 0
    anchors.rightMargin: control.d.marginRight || 0
    sourceComponent: {
        switch (d.kind) {
        case "label": return labelControl
        case "button": return buttonControl
        case "entry": return entryControl
        case "text": return textControl
        case "combo": return comboControl
        case "switch": case "check": return switchControl
        case "spin": return spinControl
        case "scale": return scaleControl
        case "separator": return separatorControl
        case "drawing": return drawingControl
        case "fixed": return fixedControl
        default: return containerControl
        }
    }
    }
    Component {
        id: drawingControl
        LegacyPaintItem {
            node: control.node
            implicitHeight: control.d.height > 0 ? control.d.height : 160
            opacity: control.d.opacity === undefined ? 1 : control.d.opacity
        }
    }
    Component {
        id: fixedControl
        Item {
            Repeater {
                model: control.d.children || []
                delegate: Loader {
                    required property var modelData
                    readonly property var childData: modelData ? modelData.data : ({})
                    x: childData.x || 0
                    y: childData.y || 0
                    width: childData.width > 0 ? childData.width : parent.width
                    height: childData.height > 0 ? childData.height : parent.height
                    visible: childData.visible !== false
                    Component.onCompleted: setSource(Qt.resolvedUrl("LegacyControl.qml"), {node: modelData, theme: control.theme})
                }
            }
        }
    }
    Component {
        id: labelControl
        Text {
            text: control.d.text || ""
            textFormat: Text.PlainText
            color: control.theme.text
            wrapMode: control.d.wrap ? Text.Wrap : Text.NoWrap
            font.pixelSize: 14
        }
    }
    Component {
        id: buttonControl
        PixelButton {
            theme: control.theme
            text: control.d.text || ""
            tooltip: control.d.tooltip || ""
            onClicked: control.node.action("click", null)
        }
    }
    Component {
        id: entryControl
        TextField {
            text: control.d.text || ""
            maximumLength: control.d.maxLength || 32767
            placeholderText: control.d.placeholder || ""
            readOnly: control.d.editable === false
            onTextEdited: control.node.action("text", text)
            onAccepted: control.node.action("activate", null)
        }
    }
    Component {
        id: textControl
        TextArea {
            text: control.d.text || ""
            readOnly: control.d.editable === false
            wrapMode: control.d.wrap ? TextEdit.Wrap : TextEdit.NoWrap
            font.family: control.d.monospace ? control.theme.mono : control.theme.family
            implicitHeight: control.d.height > 0 ? control.d.height : Math.max(90, contentHeight + 16)
            onTextChanged: if (activeFocus && text !== control.d.text) control.node.action("text", text)
        }
    }
    Component {
        id: comboControl
        ComboBox {
            model: control.d.choices || []
            textRole: "text"
            currentIndex: control.d.index === undefined ? -1 : control.d.index
            onActivated: function(index) { control.node.action("index", index) }
        }
    }
    Component {
        id: switchControl
        Switch {
            text: control.d.text || ""
            checked: !!control.d.active
            onToggled: control.node.action("active", checked)
        }
    }
    Component {
        id: spinControl
        TextField {
            text: String(control.d.value || 0)
            validator: DoubleValidator { bottom: control.d.minimum; top: control.d.maximum }
            inputMethodHints: Qt.ImhFormattedNumbersOnly
            onEditingFinished: if (acceptableInput) control.node.action("value", Number(text))
            Keys.onUpPressed: control.node.action("value", Number(text) + control.d.step)
            Keys.onDownPressed: control.node.action("value", Number(text) - control.d.step)
        }
    }
    Component {
        id: scaleControl
        Slider {
            from: control.d.minimum
            to: control.d.maximum
            stepSize: control.d.step
            value: control.d.value
            onMoved: control.node.action("value", value)
        }
    }
    Component {
        id: separatorControl
        Rectangle { implicitHeight: 1; color: control.theme.line }
    }
    Component {
        id: containerControl
        ColumnLayout {
            spacing: control.d.spacing || 0
            Button {
                visible: control.d.kind === "expander"
                text: (control.d.expanded ? "- " : "+ ") + (control.d.text || "")
                Layout.fillWidth: true
                onClicked: control.node.action("expanded", !control.d.expanded)
            }
            GridLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                visible: control.d.kind !== "expander" || !!control.d.expanded
                columns: control.d.kind === "grid" ? Math.max(1, control.d.columns || 1)
                    : control.d.orientation === 0 ? Math.max(1, (control.d.children || []).length) : 1
                columnSpacing: control.d.spacing || 6
                rowSpacing: control.d.spacing || 6
                Repeater {
                    model: control.d.children || []
                    delegate: Loader {
                        required property var modelData
                        readonly property var childData: modelData ? modelData.data : ({})
                        visible: childData.visible !== false
                        Layout.fillWidth: childData.width === undefined || childData.width <= 0 || !!childData.hexpand
                        Layout.minimumWidth: 0
                        Layout.maximumWidth: childData.width > 0 && !childData.hexpand ? childData.width : Infinity
                        Layout.preferredWidth: childData.width > 0 ? childData.width : -1
                        Layout.preferredHeight: childData.height > 0 ? childData.height : -1
                        Layout.row: control.d.kind === "grid" ? childData.row : -1
                        Layout.column: control.d.kind === "grid" ? childData.column : -1
                        Layout.columnSpan: childData.columnSpan || 1
                        Layout.rowSpan: childData.rowSpan || 1
                        Component.onCompleted: setSource(Qt.resolvedUrl("LegacyControl.qml"), {node: modelData, theme: control.theme})
                    }
                }
            }
        }
    }
}

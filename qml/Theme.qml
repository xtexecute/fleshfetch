import QtQuick

QtObject {
    property bool dark: true
    property var overrides: ({})
    readonly property string frameSource: "image://skins/frame/" + String(accent).slice(1)
    readonly property color canvas: overrides.canvas !== undefined ? overrides.canvas : (dark ? "#181818" : "#fff1f3")
    readonly property color surface: overrides.surface !== undefined ? overrides.surface : (dark ? "#252525" : "#ffe6eb")
    readonly property color raised: overrides.raised !== undefined ? overrides.raised : (dark ? "#303030" : "#ffe6eb")
    readonly property color hover: overrides.hover !== undefined ? overrides.hover : (dark ? "#3a3031" : "#ffdae2")
    readonly property color pressed: overrides.pressed !== undefined ? overrides.pressed : (dark ? "#493336" : "#ffcbd6")
    readonly property color text: overrides.text !== undefined ? overrides.text : (dark ? "#f4f4f4" : "#232323")
    readonly property color muted: overrides.muted !== undefined ? overrides.muted : (dark ? "#bcbcbc" : "#626262")
    readonly property color line: overrides.line !== undefined ? overrides.line : (dark ? "#424242" : "#d8d8d8")
    readonly property color accent: overrides.accent !== undefined ? overrides.accent : ("#d45b65")
    readonly property color accentHover: overrides.accentHover !== undefined ? overrides.accentHover : ("#e67a80")
    readonly property color focus: overrides.focus !== undefined ? overrides.focus : (dark ? "#ffbbc0" : "#a52e42")
    readonly property color warning: overrides.warning !== undefined ? overrides.warning : (dark ? "#f4ce73" : "#805800")
    readonly property color danger: overrides.danger !== undefined ? overrides.danger : (dark ? "#ff9299" : "#b5233b")
    readonly property string family: Qt.application.font.family
    readonly property string mono: Qt.platform.os === "windows" ? "Consolas" : "monospace"
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: page
    required property var theme
    property string tabId: ""
    property var catalog: game.catalog
    readonly property var tab: (catalog.tabs || []).find(function(t) { return t.id === page.tabId }) || {}
    readonly property var entries: {
        if (tab.items) return tab.items
        let items = []
        for (const b of catalog.buttons || []) if (b.tabId === tabId) items.push({type: "button", id: b.id})
        for (const i of catalog.images || []) if (i.tabId === tabId) items.push({type: "image", id: i.id})
        return items
    }
    contentWidth: availableWidth
    clip: true
    ColumnLayout {
        width: page.availableWidth - 12
        spacing: 12
        SectionTitle { theme: page.theme; text: page.tab.label || page.tabId; Layout.fillWidth: true }
        Loader {
            Layout.fillWidth: true
            active: !!page.tab.legacyRoot
            sourceComponent: Component {
                LegacyControl { node: page.tab.legacyRoot; theme: page.theme }
            }
        }
        Repeater {
            model: page.entries
            delegate: Loader {
                id: entry
                required property var modelData
                readonly property var record: modelData.type === "button"
                    ? (page.catalog.buttons || []).find(function(b) { return b.id === entry.modelData.id }) || {}
                    : modelData.type === "image"
                    ? (page.catalog.images || []).find(function(i) { return i.id === entry.modelData.id }) || {}
                    : modelData
                Layout.fillWidth: true
                visible: record.visible !== false
                sourceComponent: modelData.type === "label" ? labelComponent : modelData.type === "button" ? buttonComponent : imageComponent
                Component {
                    id: labelComponent
                    Text { text: entry.record.text || ""; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: page.theme.text; font.pixelSize: 14 }
                }
                Component {
                    id: buttonComponent
                    PixelButton {
                        id: modButton
                        theme: page.theme
                        text: entry.record.label || ""
                        enabled: entry.record.enabled !== false
                        tooltip: entry.record.tooltip || ""
                        sprites: entry.record.sprites || ({})
                        spriteBorder: entry.record.spriteBorder || ({left: 8, top: 8, right: 8, bottom: 8})
                        onClicked: game.activateModButton(entry.record.id)
                    }
                }
                Component {
                    id: imageComponent
                    Item {
                        implicitHeight: Number(entry.record.height || 160)
                        Image {
                            anchors.fill: parent
                            source: entry.record.url || ""
                            sourceSize.width: Number(entry.record.width || 0)
                            fillMode: Image.PreserveAspectFit
                            opacity: entry.record.opacity === undefined ? 1 : Number(entry.record.opacity)
                            smooth: false
                        }
                    }
                }
            }
        }
    }
}

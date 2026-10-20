import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: extras
    required property var theme
    required property string tabId
    readonly property var tab: (game.catalog.extraTabs || []).find(function(t) { return t.id === extras.tabId }) || ({})
    readonly property bool hasContent: !!tab.legacyRoot || (tab.items || []).length > 0
    implicitHeight: hasContent ? Math.min(180, content.implicitHeight + 8) : 0
    visible: hasContent
    clip: true
    contentWidth: availableWidth
    ColumnLayout {
        id: content
        width: extras.availableWidth
        spacing: 6
        Loader {
            Layout.fillWidth: true
            active: !!extras.tab.legacyRoot
            sourceComponent: Component { LegacyControl { node: extras.tab.legacyRoot; theme: extras.theme } }
        }
        Repeater {
            model: extras.tab.items || []
            delegate: Loader {
                id: entry
                required property var modelData
                readonly property var record: modelData.type === "button"
                    ? (game.catalog.buttons || []).find(function(b) { return b.id === entry.modelData.id }) || ({})
                    : (game.catalog.images || []).find(function(i) { return i.id === entry.modelData.id }) || ({})
                Layout.fillWidth: true
                visible: record.visible !== false
                sourceComponent: modelData.type === "button" ? buttonComponent : imageComponent
                Component {
                    id: buttonComponent
                    PixelButton {
                        theme: extras.theme
                        text: entry.record.label || ""
                        enabled: entry.record.enabled !== false
                        sprites: entry.record.sprites || ({})
                        spriteBorder: entry.record.spriteBorder || ({left: 8, top: 8, right: 8, bottom: 8})
                        onClicked: game.activateModButton(entry.record.id)
                    }
                }
                Component {
                    id: imageComponent
                    Item {
                        implicitHeight: entry.record.height || 128
                        Image { anchors.fill: parent; source: entry.record.url || ""; fillMode: Image.PreserveAspectFit; smooth: false }
                    }
                }
            }
        }
    }
}

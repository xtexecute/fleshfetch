import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: page
    objectName: "modPage:" + tabId
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
                objectName: "modEntry:" + modelData.id
                required property var modelData
                readonly property var record: modelData.type === "button"
                    ? (page.catalog.buttons || []).find(function(b) { return b.id === entry.modelData.id }) || {}
                    : modelData.type === "image"
                    ? (page.catalog.images || []).find(function(i) { return i.id === entry.modelData.id }) || {}
                    : modelData.type === "surface"
                    ? (page.catalog.surfaces || []).find(function(s) { return s.id === entry.modelData.id }) || {}
                    : modelData
                Layout.fillWidth: true
                visible: record.visible !== false
                sourceComponent: modelData.type === "label" ? labelComponent : modelData.type === "button" ? buttonComponent : modelData.type === "surface" ? surfaceComponent : imageComponent
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
                Component {
                    id: surfaceComponent
                    Item {
                        id: surfaceView
                        objectName: "modSurface:" + entry.record.id
                        Layout.fillWidth: true
                        implicitHeight: Math.min(Number(entry.record.height || 200),
                                                 Math.max(1, width) * Number(entry.record.height || 200) / Number(entry.record.width || 320))
                        focus: false
                        activeFocusOnTab: true
                        clip: true
                        Image {
                            id: surfaceImage
                            anchors.fill: parent
                            fillMode: Image.Stretch
                            smooth: false
                            cache: false
                            source: {
                                let revision = game.surfaceRevision(entry.record.id)
                                return revision ? "image://surfaces/" + entry.record.id + "/" + revision : ""
                            }
                        }
                        Connections {
                            target: game
                            function onSurfaceFrameChanged(id, revision) {
                                if (id === entry.record.id)
                                    surfaceImage.source = "image://surfaces/" + id + "/" + revision
                            }
                        }
                        Keys.onPressed: function(event) {
                            game.surfaceKey(entry.record.id, event.key, true, event.modifiers)
                            event.accepted = true
                        }
                        Keys.onReleased: function(event) {
                            game.surfaceKey(entry.record.id, event.key, false, event.modifiers)
                            event.accepted = true
                        }
                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.AllButtons
                            hoverEnabled: true
                            onPressed: function(mouse) {
                                surfaceView.forceActiveFocus()
                                game.surfacePointer(entry.record.id, "press",
                                    mouse.x * Number(entry.record.width) / width,
                                    mouse.y * Number(entry.record.height) / height,
                                    mouse.button, mouse.buttons)
                            }
                            onReleased: function(mouse) {
                                game.surfacePointer(entry.record.id, "release",
                                    mouse.x * Number(entry.record.width) / width,
                                    mouse.y * Number(entry.record.height) / height,
                                    mouse.button, mouse.buttons)
                            }
                            onPositionChanged: function(mouse) {
                                game.surfacePointer(entry.record.id, "move",
                                    mouse.x * Number(entry.record.width) / width,
                                    mouse.y * Number(entry.record.height) / height,
                                    mouse.button, mouse.buttons)
                            }
                        }
                    }
                }
            }
        }
    }
}

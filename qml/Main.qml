import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "StableList.js" as StableList

Window {
    id: mainWindow
    objectName: "mainWindow"
    visible: true
    width: 1100
    height: 740
    minimumWidth: 760
    minimumHeight: 560
    flags: Qt.Window | Qt.FramelessWindowHint
    title: game.live.title || "fleshfetch"
    color: appTheme.canvas
    property string selectedTab: "upgrades"
    ListModel { id: tabEntries; dynamicRoles: true }
    readonly property var tabs: {
        let result = [{id: "upgrades", label: "Upgrades"}, {id: "saves", label: "Saves"},
            {id: "stats", label: "Statistics"}, {id: "achievements", label: "Achievements"},
            {id: "crates", label: "Crates"}, {id: "rebirth", label: "Rebirth"},
            {id: "settings", label: "Settings"}, {id: "console", label: "Console"},
            {id: "leaderboard", label: "Leaderboard"}].filter(function(t) {
                return (game.catalog.builtinTabs || {})[t.id] !== false
            })
        for (const t of game.catalog.tabs || []) {
            if (t.visible !== false && !result.some(function(r) { return r.id === t.id })) result.push(t)
        }
        return result
    }
    onTabsChanged: {
        StableList.sync(tabEntries, tabs.map(function(t) { return {id: t.id, label: t.label} }))
        if (!tabs.some(function(t) { return t.id === mainWindow.selectedTab })) selectedTab = tabs.length ? tabs[0].id : "saves"
    }
    onSelectedTabChanged: Qt.callLater(function() {
        for (let i = 0; i < tabButtons.count; ++i) {
            const button = tabButtons.itemAt(i)
            if (button && button.modelData.id === mainWindow.selectedTab)
                tabsBar.ensureVisible(button.x, button.width)
        }
    })
    onClosing: function(close) {
        const result = game.shutdown()
        if (result === false) close.accepted = false
    }
    Theme {
        id: appTheme
        dark: game.darkMode
        overrides: (game.catalog.tabThemes || {})[mainWindow.selectedTab] || ({})
    }
    Control {
        id: surface
        anchors.fill: parent
        font.family: appTheme.family
        font.pixelSize: 14
        palette.window: appTheme.canvas
        palette.windowText: appTheme.text
        palette.base: appTheme.surface
        palette.alternateBase: appTheme.canvas
        palette.text: appTheme.text
        palette.button: appTheme.raised
        palette.buttonText: appTheme.text
        palette.highlight: appTheme.accent
        palette.highlightedText: "#202020"
        palette.light: appTheme.hover
        palette.midlight: appTheme.raised
        palette.mid: appTheme.line
        palette.dark: appTheme.line
        palette.shadow: appTheme.line
        palette.toolTipBase: appTheme.surface
        palette.toolTipText: appTheme.text
        palette.placeholderText: appTheme.muted
        background: Rectangle { color: appTheme.canvas; border.width: 1; border.color: appTheme.accent }
        ColumnLayout {
            id: mainLayout
            anchors.fill: parent
            anchors.margins: 5
            spacing: 0
            WindowChrome { theme: appTheme; window: mainWindow; title: mainWindow.title; Layout.fillWidth: true }
            SplitView {
                id: gameArea
                objectName: "gameSplit"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: 14
                orientation: Qt.Horizontal
                handle: Rectangle {
                    id: splitterHandle
                    objectName: "paneDivider"
                    implicitWidth: 14
                    implicitHeight: 14
                    color: "transparent"
                    Rectangle {
                        anchors.centerIn: parent
                        width: 2
                        height: parent.height
                        color: splitterHandle.SplitHandle.hovered || splitterHandle.SplitHandle.pressed ? appTheme.accent : appTheme.line
                    }
                    HoverHandler { cursorShape: Qt.SplitHCursor }
                }
                ClickPane {
                    objectName: "clickPane"
                    visible: (game.live.vanilla || {}).clicker !== false
                    theme: appTheme
                    SplitView.preferredWidth: mainWindow.width < 900 ? 210 : 285
                    SplitView.minimumWidth: 180
                    SplitView.maximumWidth: gameArea.width - 354
                }
                ColumnLayout {
                    SplitView.fillWidth: true
                    SplitView.minimumWidth: 340
                    spacing: -6
                    RowLayout {
                        id: tabsNavigator
                        Layout.fillWidth: true
                        Layout.preferredHeight: 54
                        Layout.minimumHeight: 54
                        Layout.maximumHeight: 54
                        Layout.fillHeight: false
                        spacing: 4
                        readonly property bool overflowing: tabRow.width > width
                        PixelButton {
                            objectName: "scrollTabsLeft"
                            theme: appTheme
                            text: "\u2039"
                            tooltip: "Scroll tabs left"
                            Accessible.name: tooltip
                            focusPolicy: Qt.NoFocus
                            visible: tabsNavigator.overflowing
                            enabled: tabsBar.contentX > 0
                            Layout.preferredWidth: 26
                            padding: 0
                            onClicked: tabsBar.contentX = Math.max(0, tabsBar.contentX - tabsBar.width * 0.7)
                        }
                        Flickable {
                        id: tabsBar
                        objectName: "tabsBar"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        contentWidth: tabRow.width
                        contentHeight: height
                        flickableDirection: Flickable.HorizontalFlick
                        boundsBehavior: Flickable.StopAtBounds
                        clip: true
                        function ensureVisible(left, itemWidth) {
                            if (left < contentX) contentX = left
                            else if (left + itemWidth > contentX + width) contentX = left + itemWidth - width
                            contentX = Math.max(0, Math.min(contentX, Math.max(0, contentWidth - width)))
                        }
                        onWidthChanged: contentX = Math.max(0, Math.min(contentX, Math.max(0, contentWidth - width)))
                        WheelHandler {
                            onWheel: function(event) {
                                const delta = event.pixelDelta.x || event.pixelDelta.y
                                    || (event.angleDelta.x || event.angleDelta.y) * 0.5
                                tabsBar.contentX = Math.max(0, Math.min(tabsBar.contentX - delta,
                                    Math.max(0, tabsBar.contentWidth - tabsBar.width)))
                                event.accepted = true
                            }
                        }
                        Row {
                            id: tabRow
                            y: 2
                            spacing: 5
                            Repeater {
                                id: tabButtons
                                model: tabEntries
                                delegate: PixelButton {
                                    required property var model
                                    readonly property var modelData: model
                                    objectName: "tab:" + modelData.id
                                    theme: tabTheme
                                    Theme {
                                        id: tabTheme
                                        dark: game.darkMode
                                        overrides: (game.catalog.tabThemes || {})[modelData.id] || ({})
                                    }
                                    tabStyle: true
                                    text: modelData.label
                                    selected: mainWindow.selectedTab === modelData.id
                                    Accessible.role: Accessible.PageTab
                                    Accessible.name: text
                                    onClicked: mainWindow.selectedTab = modelData.id
                                    onVisualFocusChanged: if (visualFocus) tabsBar.ensureVisible(x, width)
                                }
                            }
                        }
                        ScrollBar.horizontal: ScrollBar { policy: tabsBar.contentWidth > tabsBar.width ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff; height: 4 }
                        }
                        PixelButton {
                            objectName: "scrollTabsRight"
                            theme: appTheme
                            text: "\u203a"
                            tooltip: "Scroll tabs right"
                            Accessible.name: tooltip
                            focusPolicy: Qt.NoFocus
                            visible: tabsNavigator.overflowing
                            enabled: tabsBar.contentX < tabsBar.contentWidth - tabsBar.width
                            Layout.preferredWidth: 26
                            padding: 0
                            onClicked: tabsBar.contentX = Math.min(tabsBar.contentWidth - tabsBar.width,
                                tabsBar.contentX + tabsBar.width * 0.7)
                        }
                    }
                    PixelFrame {
                        theme: appTheme
                        fillColor: appTheme.canvas
                        inset: 14
                        z: 1
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                    ColumnLayout {
                    anchors.fill: parent
                    spacing: 8
                    Loader {
                        id: workspace
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        sourceComponent: {
                            switch (mainWindow.selectedTab) {
                            case "upgrades": return upgradesComponent
                            case "saves": return savesComponent
                            case "stats": return statsComponent
                            case "achievements": return achievementsComponent
                            case "settings": return settingsComponent
                            case "console": return consoleComponent
                            case "leaderboard": return leaderboardComponent
                            case "crates": return cratesComponent
                            case "rebirth": return rebirthComponent
                            default: return modComponent
                            }
                        }
                    }
                    ModExtras {
                        theme: appTheme
                        tabId: mainWindow.selectedTab
                        Layout.fillWidth: true
                    }
                    }
                    }
                }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: appTheme.line }
            Text {
                text: game.status || "Ready"
                Layout.fillWidth: true
                Layout.preferredHeight: 30
                Layout.leftMargin: 14
                Layout.rightMargin: 14
                color: appTheme.muted
                font.pixelSize: 12
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                ToolTip.visible: statusHover.hovered && text.length > 0
                ToolTip.text: text
                HoverHandler { id: statusHover }
            }
        }
        Item {
            id: spriteLayer
            objectName: "spriteLayer"
            x: mainLayout.x + gameArea.x
            y: mainLayout.y + gameArea.y
            width: gameArea.width
            height: gameArea.height
            z: 20
            clip: true
            function syncViewport() {
                if (width > 0 && height > 0) {
                    game.setViewport(width, height)
                    game.setLegacyOrigin(x, y)
                }
            }
            LegacyControl { anchors.fill: parent; node: game.legacyOverlay; theme: appTheme }
            onWidthChanged: viewportTimer.restart()
            onHeightChanged: viewportTimer.restart()
            Component.onCompleted: viewportTimer.restart()
            Timer { id: viewportTimer; interval: 60; onTriggered: spriteLayer.syncViewport() }
            // Images have no input handlers; the overlay never intercepts game controls.
            Repeater {
                model: game.spriteModel
                delegate: Image {
                    id: spriteImage
                    required property var spriteData
                    objectName: "sprite:" + spriteData.id
                    source: spriteData.url || ""
                    x: Number(spriteData.x || 0)
                    y: Number(spriteData.y || 0)
                    width: Number(spriteData.width || implicitWidth)
                    height: Number(spriteData.height || implicitHeight)
                    rotation: Number(spriteData.rotation || 0)
                    opacity: spriteData.opacity === undefined ? 1 : Number(spriteData.opacity)
                    visible: spriteData.visible !== false
                    smooth: false
                    MouseArea {
                        id: spriteDrag
                        anchors.fill: parent
                        enabled: spriteImage.spriteData.draggable === true
                        hoverEnabled: enabled
                        cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                        property real grabX: 0
                        property real grabY: 0
                        property real lastX: 0
                        property real lastY: 0
                        property real speedX: 0
                        property real speedY: 0
                        property double lastTime: 0
                        onPressed: function(mouse) {
                            if (!game.spriteHit(spriteImage.spriteData.id, mouse.x, mouse.y)) {
                                mouse.accepted = false
                                return
                            }
                            grabX = mouse.x
                            grabY = mouse.y
                            const point = spriteImage.mapToItem(spriteLayer, mouse.x, mouse.y)
                            lastX = point.x
                            lastY = point.y
                            speedX = 0
                            speedY = 0
                            lastTime = Date.now()
                            game.grabSprite(spriteImage.spriteData.id)
                        }
                        onPositionChanged: function(mouse) {
                            if (!pressed) return
                            const point = spriteImage.mapToItem(spriteLayer, mouse.x, mouse.y)
                            const now = Date.now()
                            const elapsed = Math.max(1, now - lastTime)
                            speedX = Math.max(-650, Math.min(650, (point.x - lastX) * 1000 / elapsed))
                            speedY = Math.max(-650, Math.min(650, (point.y - lastY) * 1000 / elapsed))
                            lastX = point.x
                            lastY = point.y
                            lastTime = now
                            game.moveSprite(spriteImage.spriteData.id, point.x - grabX, point.y - grabY)
                        }
                        onReleased: {
                            if (Date.now() - lastTime > 100) { speedX = 0; speedY = 0 }
                            game.releaseSprite(spriteImage.spriteData.id, speedX, speedY)
                        }
                        onCanceled: game.releaseSprite(spriteImage.spriteData.id, 0, 0)
                    }
                }
            }
        }
        Dialog {
            id: confirmation
            parent: Overlay.overlay
            anchors.centerIn: parent
            width: Math.min(480, mainWindow.width - 60)
            modal: true
            focus: true
            closePolicy: Popup.CloseOnEscape
            property string message: ""
            property bool pending: false
            padding: 22
            title: "Confirm"
            background: PixelFrame { theme: appTheme }
            contentItem: Text {
                text: confirmation.message
                textFormat: Text.PlainText
                color: appTheme.text
                font.pixelSize: 14
                wrapMode: Text.Wrap
            }
            header: Text {
                text: confirmation.title
                color: appTheme.text
                font.family: appTheme.mono
                font.pixelSize: 18
                font.bold: true
                wrapMode: Text.Wrap
                padding: 22
                bottomPadding: 8
            }
            footer: RowLayout {
                spacing: 8
                Item { Layout.fillWidth: true }
                PixelButton { id: cancelButton; theme: appTheme; text: "Cancel"; Layout.bottomMargin: 18; onClicked: confirmation.reject() }
                PixelButton {
                    theme: appTheme
                    text: confirmation.title === "Dismiss security warning" ? "I don't care" : "Confirm"
                    destructive: true
                    Layout.rightMargin: 18
                    Layout.bottomMargin: 18
                    onClicked: confirmation.accept()
                }
            }
            onOpened: cancelButton.forceActiveFocus()
            onAccepted: { pending = false; game.confirmPending(true) }
            onRejected: { pending = false; game.confirmPending(false) }
            onClosed: if (pending) { pending = false; game.confirmPending(false) }
        }
    }
    Connections {
        target: game
        function onConfirmationRequested(title, message) {
            confirmation.title = title
            confirmation.message = message
            confirmation.pending = true
            confirmation.open()
        }
    }
    BorderImage {
        anchors.fill: parent
        source: appTheme.frameSource
        border { left: 8; top: 8; right: 8; bottom: 8 }
        smooth: false
        z: 90
    }
    ResizeHandles { anchors.fill: parent; window: mainWindow; z: 100 }
    Component { id: upgradesComponent; UpgradesPage { theme: appTheme } }
    Component { id: savesComponent; SavesPage { theme: appTheme } }
    Component { id: statsComponent; StatsPage { theme: appTheme } }
    Component { id: achievementsComponent; AchievementsPage { theme: appTheme } }
    Component { id: settingsComponent; SettingsPage { theme: appTheme } }
    Component { id: consoleComponent; ConsolePage { theme: appTheme } }
    Component { id: leaderboardComponent; LeaderboardPage { theme: appTheme } }
    Component { id: cratesComponent; CratesPage { theme: appTheme } }
    Component { id: rebirthComponent; RebirthPage { theme: appTheme } }
    Component { id: modComponent; ModPage { theme: appTheme; tabId: mainWindow.selectedTab } }
}

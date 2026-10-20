import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: mainWindow
    objectName: "mainWindow"
    visible: true
    width: 1100
    height: 740
    minimumWidth: 760
    minimumHeight: 560
    flags: Qt.Window | Qt.FramelessWindowHint
    title: game.live.title || "Fleshfetch"
    color: appTheme.canvas
    property string selectedTab: "upgrades"
    readonly property var tabs: {
        let result = [{id: "upgrades", label: "Upgrades"}, {id: "saves", label: "Saves"},
            {id: "stats", label: "Statistics"}, {id: "achievements", label: "Achievements"},
            {id: "settings", label: "Settings"}, {id: "console", label: "Console"},
            {id: "leaderboard", label: "Leaderboard"}]
        for (const t of game.catalog.tabs || []) {
            if (t.visible !== false && !result.some(function(r) { return r.id === t.id })) result.push(t)
        }
        return result
    }
    onTabsChanged: {
        if (!tabs.some(function(t) { return t.id === mainWindow.selectedTab })) selectedTab = "upgrades"
    }
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
                    theme: appTheme
                    SplitView.preferredWidth: mainWindow.width < 900 ? 210 : 285
                    SplitView.minimumWidth: 180
                    SplitView.maximumWidth: gameArea.width - 354
                }
                ColumnLayout {
                    SplitView.fillWidth: true
                    SplitView.minimumWidth: 340
                    spacing: -6
                    Flickable {
                        id: tabsBar
                        objectName: "tabsBar"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 48
                        contentWidth: tabRow.width
                        contentHeight: height
                        flickableDirection: Flickable.HorizontalFlick
                        boundsBehavior: Flickable.StopAtBounds
                        clip: true
                        Row {
                            id: tabRow
                            y: 2
                            spacing: 5
                            Repeater {
                                model: mainWindow.tabs
                                delegate: PixelButton {
                                    required property var modelData
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
                                    onActiveFocusChanged: if (activeFocus) tabsBar.contentX = Math.max(0, Math.min(x, tabsBar.contentWidth - tabsBar.width))
                                }
                            }
                        }
                        ScrollBar.horizontal: ScrollBar { policy: tabsBar.contentWidth > tabsBar.width ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff; height: 4 }
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
    Component { id: modComponent; ModPage { theme: appTheme; tabId: mainWindow.selectedTab } }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "CurrencyFormat.js" as CurrencyFormat
import "StableList.js" as StableList

ColumnLayout {
    id: page
    objectName: "upgradesPage"
    required property var theme
    property var live: game.live
    property var catalog: game.catalog
    property string category: "All"
    readonly property var categories: {
        let result = ["All"]
        for (const u of catalog.upgrades || []) {
            const c = u.category || "Other"
            if (result.indexOf(c) < 0) result.push(c)
        }
        return result
    }
    ListModel { id: upgradeEntries; dynamicRoles: true }
    function refreshEntries() {
        const query = search.text.trim().toLowerCase()
        const filtered = (catalog.upgrades || []).filter(function(u) {
            const info = (page.live.upgradeInfo || {})[u.id]
            return info && info.visible !== false && (page.category === "All" || (u.category || "Other") === page.category)
                && (!query || (u.name + " " + (u.desc || "")).toLowerCase().indexOf(query) >= 0)
        })
        StableList.sync(upgradeEntries, filtered)
    }
    onCategoryChanged: refreshEntries()
    Component.onCompleted: refreshEntries()
    Connections {
        target: game
        function onLiveChanged() { page.refreshEntries() }
        function onCatalogChanged() { page.refreshEntries() }
    }
    spacing: 12
    RowLayout {
        Layout.fillWidth: true
        SectionTitle { theme: page.theme; text: (page.live.workshop || {}).visible ? "Equipment shop" : "Upgrades"; Layout.fillWidth: true }
        ComboBox {
            id: categoryBox
            Layout.maximumWidth: 180
            Layout.preferredWidth: 145
            model: page.categories
            Accessible.name: "Upgrade category"
            onActivated: page.category = currentText
        }
    }
    WorkshopScene {
        theme: page.theme
        visible: (page.live.workshop || {}).visible === true
        Layout.fillWidth: true
        Layout.preferredHeight: page.height > 510 ? 196 : 184
    }
    PixelField {
        id: search
        theme: page.theme
        Layout.fillWidth: true
        placeholderText: "Search upgrades"
        Accessible.name: "Search upgrades"
        onTextChanged: page.refreshEntries()
    }
    ListView {
        id: list
        objectName: "upgradeList"
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        spacing: 8
        model: upgradeEntries
        ScrollBar.vertical: ScrollBar {}
        delegate: PixelFrame {
            id: upgrade
            objectName: "upgrade:" + modelData.id
            required property var model
            readonly property var modelData: model
            readonly property var info: (page.live.upgradeInfo || {})[modelData.id] || {}
            readonly property var shopItem: (page.catalog.shopItems || []).find(function(item) { return item.id === upgrade.modelData.id })
            property real purchaseFlash: 0
            theme: page.theme
            width: list.width - 12
            height: details.implicitHeight + 28
            RowLayout {
                id: details
                width: parent.width
                spacing: 12
                Image {
                    visible: upgrade.shopItem !== undefined
                    source: upgrade.shopItem ? "image://skins/equipment/" + upgrade.shopItem.art : ""
                    Layout.preferredWidth: list.width < 600 ? 32 : 64
                    Layout.preferredHeight: list.width < 600 ? 32 : 64
                    fillMode: Image.PreserveAspectFit
                    smooth: false
                    mipmap: false
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Text { text: upgrade.modelData.name; color: page.theme.text; font.pixelSize: 15; font.bold: true; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Text { text: upgrade.modelData.desc || ""; color: page.theme.muted; font.pixelSize: 14; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Text { text: "Owned " + (upgrade.info.owned || 0); color: page.theme.muted; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Text {
                        visible: (upgrade.info.milestone || {}).multiplier !== undefined
                        text: {
                            const m = upgrade.info.milestone || {}
                            return "Output x" + (m.multiplier || 1) + (m.nextCount ? "  /  x" + m.nextMultiplier + " at " + m.nextCount + " owned" : "  /  Fully tuned")
                        }
                        color: (upgrade.info.milestone || {}).multiplier > 1 ? (page.theme.dark ? "#55b8a5" : "#26786a") : page.theme.muted
                        font.pixelSize: 11
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
                PixelButton {
                    id: buyButton
                    objectName: "buy:" + upgrade.modelData.id
                    theme: page.theme
                    text: (upgrade.info.cost === undefined ? "--" : CurrencyFormat.format(Math.ceil(Number(upgrade.info.cost)), game.preferences.show_full_numbers)) + " " + upgrade.modelData.currency
                    implicitHeight: Math.max(42, priceLabel.implicitHeight + 20)
                    contentItem: Text {
                        id: priceLabel
                        text: buyButton.text
                        font: buyButton.font
                        color: buyButton.enabled ? page.theme.text : page.theme.muted
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.Wrap
                        transform: Translate { y: buyButton.animatedOffset }
                    }
                    Layout.preferredWidth: Math.min(150, Math.max(92, list.width * 0.24))
                    enabled: upgrade.info.canBuy === true
                    tooltip: "Buy " + upgrade.modelData.name + " for " + text
                    Accessible.name: tooltip
                    onClicked: game.buy(upgrade.modelData.id)
                }
            }
            Rectangle {
                anchors.fill: parent
                color: page.theme.accent
                opacity: upgrade.purchaseFlash
                z: -0.5
            }
            NumberAnimation { id: purchaseAnimation; target: upgrade; property: "purchaseFlash"; from: 0.3; to: 0; duration: 450 }
            Connections {
                target: game
                function onUpgradePurchased(uid) {
                    if (uid === upgrade.modelData.id) purchaseAnimation.restart()
                }
            }
        }
        Text { anchors.centerIn: parent; width: parent.width - 24; text: "No upgrades available"; visible: list.count === 0; color: page.theme.muted; font.pixelSize: 14; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
    }
}

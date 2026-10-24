import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: page
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
    readonly property var entries: (catalog.upgrades || []).filter(function(u) {
        const info = (page.live.upgradeInfo || {})[u.id]
        const query = search.text.trim().toLowerCase()
        return info && info.visible !== false && (page.category === "All" || (u.category || "Other") === page.category)
            && (!query || (u.name + " " + (u.desc || "")).toLowerCase().indexOf(query) >= 0)
    })
    spacing: 12
    RowLayout {
        Layout.fillWidth: true
        SectionTitle { theme: page.theme; text: "Upgrades"; Layout.fillWidth: true }
        ComboBox {
            id: categoryBox
            Layout.maximumWidth: 180
            Layout.preferredWidth: 145
            model: page.categories
            Accessible.name: "Upgrade category"
            onActivated: page.category = currentText
        }
    }
    PixelField {
        id: search
        theme: page.theme
        Layout.fillWidth: true
        placeholderText: "Search upgrades"
        Accessible.name: "Search upgrades"
    }
    ListView {
        id: list
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        spacing: 8
        model: page.entries
        ScrollBar.vertical: ScrollBar {}
        delegate: PixelFrame {
            id: upgrade
            required property var modelData
            readonly property var info: (page.live.upgradeInfo || {})[modelData.id] || {}
            theme: page.theme
            width: list.width - 12
            height: details.implicitHeight + 28
            RowLayout {
                id: details
                width: parent.width
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Text { text: upgrade.modelData.name; color: page.theme.text; font.pixelSize: 15; font.bold: true; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Text { text: upgrade.modelData.desc || ""; color: page.theme.muted; font.pixelSize: 14; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Text { text: "Owned " + (upgrade.info.owned || 0); color: page.theme.muted; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                }
                PixelButton {
                    id: buyButton
                    theme: page.theme
                    text: (upgrade.info.cost === undefined ? "--" : Math.ceil(Number(upgrade.info.cost)).toLocaleString(Qt.locale(), 'f', 0)) + " " + upgrade.modelData.currency
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
        }
        Text { anchors.centerIn: parent; width: parent.width - 24; text: "No upgrades available"; visible: list.count === 0; color: page.theme.muted; font.pixelSize: 14; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
    }
}

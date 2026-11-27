import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "CurrencyFormat.js" as CurrencyFormat

ColumnLayout {
    id: page
    objectName: "cratesPage"
    required property var theme
    property var progress: game.live.progression || ({})
    property var catalog: game.catalog.progression || ({})
    property string kind: "equipment"
    readonly property bool inventoryEnabled: page.kind === "equipment"
        ? !!catalog.equipmentEnabled : !!catalog.skinsEnabled
    spacing: 10

    function rarityColor(name) {
        const found = (catalog.rarities || []).find(function(item) { return item.id === name || item.name === name })
        return found ? found.color : theme.text
    }
    function rarityInfo(id) {
        return (catalog.rarities || []).find(function(item) { return item.id === id }) || ({name: id, rank: 0})
    }
    function crateInfo(id) {
        return (catalog.crateTiers || []).find(function(item) { return item.id === id }) || ({name: id})
    }
    function crateCount(tier) {
        return ((progress.crates || {})[kind] || {})[tier] || 0
    }
    function startOpen(crateKind, tier) {
        if (reveal.phase === "rolling") return
        const outcome = game.openCrate(crateKind, tier)
        if (!outcome.ok) return
        reveal.crateKind = crateKind
        reveal.tier = tier
        reveal.result = outcome.result
        reveal.rarity = outcome.rarity
        reveal.phase = "rolling"
        reveal.open()
        Qt.callLater(function() {
            if (reveal.phase === "rolling") itemReel.start(outcome.pool, outcome.reward)
        })
    }

    RowLayout {
        Layout.fillWidth: true
        SectionTitle { theme: page.theme; text: "Crates"; Layout.fillWidth: true }
        Text { visible: (game.live.currencies || []).some(function(c) { return c.id === "tokens" }); text: CurrencyFormat.format(page.progress.tokens, game.preferences.show_full_numbers) + " Flesh Tokens"; color: page.theme.text; font.pixelSize: 13 }
    }
    RowLayout {
        spacing: 6
        PixelButton { theme: page.theme; text: "Equipment"; selected: page.kind === "equipment"; onClicked: page.kind = "equipment" }
        PixelButton { theme: page.theme; text: "Cosmetics"; selected: page.kind === "cosmetic"; onClicked: page.kind = "cosmetic" }
    }
    Text {
        Layout.fillWidth: true
        visible: !!page.progress.lastReward && !reveal.visible
        text: page.progress.lastReward || ""
        color: page.rarityColor((page.progress.lastReward || "").split(":")[0])
        wrapMode: Text.Wrap
        font.pixelSize: 13
        font.bold: true
    }
    Flickable {
        id: scroll
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        contentWidth: width
        contentHeight: body.implicitHeight + 16
        ScrollBar.vertical: ScrollBar {}
        ColumnLayout {
            id: body
            width: scroll.width - 12
            spacing: 9
            Text { text: "Crates"; color: page.theme.text; font.family: page.theme.mono; font.bold: true; font.pixelSize: 15 }
            Repeater {
                model: (page.catalog.crateTiers || []).filter(function(item) { return item.kinds.includes(page.kind) })
                delegate: PixelFrame {
                    id: crateRow
                    required property var modelData
                    theme: page.theme
                    Layout.fillWidth: true
                    Layout.preferredHeight: 74
                    RowLayout {
                        anchors.fill: parent
                        spacing: 10
                        Image {
                            source: crateRow.modelData.icon
                            Layout.preferredWidth: 48
                            Layout.preferredHeight: 48
                            fillMode: Image.PreserveAspectFit
                            smooth: false
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text { text: crateRow.modelData.name; color: crateRow.modelData.color; font.bold: true; font.pixelSize: 14; wrapMode: Text.Wrap; Layout.fillWidth: true }
                            Text {
                                text: "Owned " + page.crateCount(crateRow.modelData.id)
                                    + (crateRow.modelData.pityAfter > 0
                                        ? "  |  Pity " + ((page.progress.pity || {})[crateRow.modelData.id] || 0)
                                            + "/" + crateRow.modelData.pityAfter : "")
                                color: page.theme.muted
                                font.pixelSize: 12
                            }
                        }
                        PixelButton {
                            theme: page.theme
                            text: "Buy " + CurrencyFormat.format(crateRow.modelData.cost, game.preferences.show_full_numbers) + " " + crateRow.modelData.currencyName
                            enabled: (((game.live.currencies || []).find(function(c) { return c.id === crateRow.modelData.currency }) || {}).amount || 0) >= crateRow.modelData.cost
                            onClicked: game.buyCrate(page.kind, crateRow.modelData.id)
                        }
                        PixelButton {
                            theme: page.theme
                            text: "Open"
                            enabled: page.crateCount(crateRow.modelData.id) > 0 && reveal.phase !== "rolling"
                            onClicked: page.startOpen(page.kind, crateRow.modelData.id)
                        }
                    }
                }
            }
            Text { visible: page.inventoryEnabled; text: page.kind === "equipment" ? "Equipment" : "Cosmetics"; color: page.theme.text; font.family: page.theme.mono; font.bold: true; font.pixelSize: 15; Layout.topMargin: 12 }
            Text {
                visible: page.inventoryEnabled && page.kind === "equipment" && (page.progress.gear || []).length === 0
                text: "No equipment yet."
                color: page.theme.muted
            }
            Text {
                visible: page.inventoryEnabled && page.kind === "cosmetic" && (page.progress.cosmetics || []).length === 0
                text: "No cosmetics yet."
                color: page.theme.muted
            }
            Repeater {
                model: !page.inventoryEnabled ? [] : page.kind === "equipment" ? (page.progress.gear || []) : (page.progress.cosmetics || [])
                delegate: PixelFrame {
                    id: itemRow
                    required property var modelData
                    theme: page.theme
                    Layout.fillWidth: true
                    Layout.preferredHeight: 68
                    RowLayout {
                        anchors.fill: parent
                        spacing: 10
                        Image {
                            visible: page.kind === "equipment"
                            source: itemRow.modelData.icon || "image://skins/loot/gear/" + (itemRow.modelData.id.includes(":") ? "wrist_wrap" : itemRow.modelData.id)
                            Layout.preferredWidth: 42
                            Layout.preferredHeight: 42
                            fillMode: Image.PreserveAspectFit
                            smooth: false
                        }
                        Rectangle {
                            readonly property bool nativeCommonArt: ["paper_crown", "price_tag", "sticky_note", "button_badge"].includes(itemRow.modelData.id)
                            visible: page.kind === "cosmetic"
                            Layout.preferredWidth: 42
                            Layout.preferredHeight: 42
                            color: itemRow.modelData.color || "transparent"
                            border.width: 2
                            border.color: page.rarityColor(itemRow.modelData.rarity)
                            Column {
                                anchors.fill: parent
                                anchors.margins: 2
                                visible: itemRow.modelData.id === "deep_blue"
                                Rectangle { width: parent.width; height: parent.height / 3; color: "#5ef1ee" }
                                Rectangle { width: parent.width; height: parent.height / 3; color: "#258bb7" }
                                Rectangle { width: parent.width; height: parent.height / 3; color: "#101e4e" }
                            }
                            Image {
                                anchors.fill: parent
                                visible: itemRow.modelData.id === "top_hat"
                                source: "image://skins/accessory/top_hat"
                                fillMode: Image.PreserveAspectFit
                                smooth: false
                            }
                            Image {
                                anchors.fill: parent
                                visible: itemRow.modelData.id === "magnet" || itemRow.modelData.id === "clockwork"
                                source: itemRow.modelData.id === "magnet" ? "../assets/skins/magnet.png" : "image://skins/clockwork/preview"
                                fillMode: Image.PreserveAspectFit
                                smooth: false
                            }
                            Image {
                                anchors.centerIn: parent
                                visible: parent.nativeCommonArt
                                source: visible ? (itemRow.modelData.icon || "image://skins/preview/" + itemRow.modelData.id) : ""
                                smooth: false
                                fillMode: Image.Pad
                            }
                            Image {
                                anchors.fill: parent
                                visible: !parent.nativeCommonArt && !["top_hat", "wobble", "deep_blue", "magnet", "clockwork"].includes(itemRow.modelData.id)
                                source: visible ? (itemRow.modelData.icon || "image://skins/preview/" + itemRow.modelData.id) : ""
                                fillMode: Image.PreserveAspectFit
                                smooth: itemRow.modelData.id === "gold"
                                mipmap: itemRow.modelData.id === "gold"
                            }
                            Text {
                                anchors.centerIn: parent
                                visible: itemRow.modelData.id === "wobble"
                                text: "~"
                                color: "#151515"
                                font.pixelSize: 27
                                font.bold: true
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text { text: itemRow.modelData.name + (itemRow.modelData.level > 1 ? "  Lv. " + itemRow.modelData.level : ""); color: page.rarityColor(itemRow.modelData.rarity); font.pixelSize: 14; font.bold: true }
                            Text {
                                text: page.kind === "equipment" ? Object.keys(itemRow.modelData.bonuses || {}).map(function(stat) { return "+" + itemRow.modelData.bonuses[stat] + "% " + stat }).join("  |  ")
                                    : page.rarityInfo(itemRow.modelData.rarity).name + (itemRow.modelData.feature ? "  |  " + itemRow.modelData.feature : "")
                                color: page.theme.muted
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }
                        }
                        PixelButton {
                            theme: page.theme
                            text: page.kind === "equipment"
                                ? (itemRow.modelData.equipped ? "Unequip" : "Equip")
                                : (page.progress.selectedCosmetic === itemRow.modelData.id ? "Selected" : "Use")
                            enabled: page.kind === "equipment" || page.progress.selectedCosmetic !== itemRow.modelData.id
                            onClicked: {
                                if (page.kind === "equipment") game.equipGear(itemRow.modelData.id)
                                else game.selectCosmetic(itemRow.modelData.id)
                            }
                        }
                    }
                }
            }
            PixelButton {
                visible: page.inventoryEnabled && page.kind === "cosmetic" && !!page.progress.selectedCosmetic
                theme: page.theme
                text: "Original flesh image"
                onClicked: game.selectCosmetic("")
            }
            Text { visible: page.inventoryEnabled && page.kind === "equipment"; text: "Equipped " + (page.progress.equipped || []).length + " / " + (page.progress.slots || 2); color: page.theme.muted; font.pixelSize: 12 }
            Text { visible: page.inventoryEnabled && page.kind === "equipment"; text: "Potions"; color: page.theme.text; font.family: page.theme.mono; font.bold: true; font.pixelSize: 15; Layout.topMargin: 12 }
            Repeater {
                model: page.inventoryEnabled && page.kind === "equipment" ? (page.progress.potions || []) : []
                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    Image {
                        source: modelData.icon
                        Layout.preferredWidth: 30
                        Layout.preferredHeight: 30
                        fillMode: Image.PreserveAspectFit
                        smooth: false
                    }
                    Text { text: modelData.name + " x" + modelData.count + "  " + modelData.desc; color: page.theme.text; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    PixelButton { theme: page.theme; text: "Use"; onClicked: game.usePotion(modelData.id) }
                }
            }
            Repeater {
                model: page.inventoryEnabled && page.kind === "equipment" ? (page.progress.boosts || []) : []
                delegate: Text { required property var modelData; text: modelData.name + "  " + modelData.seconds + "s"; color: page.theme.muted; font.pixelSize: 12 }
            }
            Text { visible: page.inventoryEnabled && page.kind === "equipment"; text: "This run"; color: page.theme.text; font.family: page.theme.mono; font.bold: true; font.pixelSize: 15; Layout.topMargin: 12 }
            Repeater {
                model: page.inventoryEnabled && page.kind === "equipment" ? (page.progress.runUpgrades || []) : []
                delegate: Text { required property var modelData; text: modelData.name + " x" + modelData.count; color: page.theme.muted; font.pixelSize: 12 }
            }
        }
    }
    Popup {
        id: reveal
        objectName: "crateReveal"
        parent: Overlay.overlay
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        width: Math.min(620, parent.width - 28)
        modal: true
        focus: true
        padding: 20
        closePolicy: Popup.CloseOnEscape
        property string phase: "idle"
        property string crateKind: "equipment"
        property string tier: "Common"
        property string rarity: "Common"
        property string result: ""
        background: PixelFrame { theme: page.theme; fillColor: page.theme.surface }
        onClosed: { itemReel.cancel(); phase = "idle" }
        function finish() {
            if (phase !== "rolling") return
            phase = "result"
            const rank = page.rarityInfo(rarity).rank
            game.playEffectSound(rank >= 4 ? "rare" : "open")
            revealPulse.restart()
        }
        contentItem: ColumnLayout {
            spacing: 14
            Text {
                text: (reveal.phase === "rolling" ? "Opening " : "") + page.crateInfo(reveal.tier).name + " crate"
                color: page.theme.text
                font.family: page.theme.mono
                font.pixelSize: 16
                font.bold: true
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
            }
            CrateReel {
                id: itemReel
                theme: page.theme
                Layout.fillWidth: true
                Layout.preferredHeight: 154
                onSettled: reveal.finish()
            }
            Text {
                id: rarityText
                text: reveal.phase === "result" ? page.rarityInfo(reveal.rarity).name : (itemReel.currentItem.rarityName || "")
                color: reveal.phase === "result" ? page.rarityColor(reveal.rarity) : (itemReel.currentItem.color || page.theme.text)
                font.family: page.theme.mono
                font.pixelSize: 25
                font.bold: true
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                Behavior on color { ColorAnimation { duration: 100 } }
            }
            SequentialAnimation {
                id: revealPulse
                NumberAnimation { target: rarityText; property: "scale"; from: 0.76; to: 1.12; duration: 140; easing.type: Easing.OutCubic }
                NumberAnimation { target: rarityText; property: "scale"; to: 1; duration: 200; easing.type: Easing.OutBack }
            }
            Text {
                text: reveal.result
                visible: reveal.phase === "result"
                color: page.theme.text
                font.pixelSize: 14
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                PixelButton {
                    theme: page.theme
                    text: reveal.phase === "rolling" ? "Skip" : "Close"
                    objectName: "skipCrateReveal"
                    onClicked: reveal.phase === "rolling" ? itemReel.finish() : reveal.close()
                }
                PixelButton {
                    visible: reveal.phase === "result" && page.crateCount(reveal.tier) > 0
                    theme: page.theme
                    text: "Open another"
                    onClicked: page.startOpen(reveal.crateKind, reveal.tier)
                }
                Item { Layout.fillWidth: true }
            }
        }
    }
}

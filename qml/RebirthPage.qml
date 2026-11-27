import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "CurrencyFormat.js" as CurrencyFormat

ColumnLayout {
    id: page
    required property var theme
    property var progress: game.live.progression || ({})
    readonly property bool vanillaRebirth: (game.live.vanilla || {}).rebirth !== false
    spacing: 10
    SectionTitle { theme: page.theme; text: "Rebirth" }
    RowLayout {
        visible: page.vanillaRebirth
        Layout.fillWidth: true
        Text { text: CurrencyFormat.format(page.progress.tokens, game.preferences.show_full_numbers) + " Flesh Tokens"; color: page.theme.text; font.pixelSize: 16; font.bold: true; Layout.fillWidth: true }
        Text { text: (page.progress.rebirths || 0) + " rebirths"; color: page.theme.muted; font.pixelSize: 12 }
    }
    Text {
        visible: page.vanillaRebirth
        Layout.fillWidth: true
        text: "Earned this run: " + CurrencyFormat.format(Math.floor(page.progress.runEarned || 0), game.preferences.show_full_numbers)
            + "     Next token at " + CurrencyFormat.format(Math.floor(page.progress.nextTokenAt || 0), game.preferences.show_full_numbers) + " flesh earned this run"
        color: page.theme.muted
        wrapMode: Text.Wrap
        font.pixelSize: 12
    }
    RowLayout {
        visible: page.vanillaRebirth
        Layout.fillWidth: true
        Text { text: "+" + (page.progress.unclaimed || 0) + " tokens available"; color: page.theme.text; Layout.fillWidth: true; font.pixelSize: 14 }
        PixelButton { theme: page.theme; text: "Rebirth"; enabled: page.progress.canRebirth === true; onClicked: game.requestRebirth() }
    }
    Text {
        visible: page.vanillaRebirth
        Layout.fillWidth: true
        text: page.progress.firstRebirthMultiplier === 2
            ? "First rebirth bonus: x2 click gains and production"
            : "First rebirth: permanently doubles click gains and production"
        color: page.theme.text
        wrapMode: Text.Wrap
        font.pixelSize: 12
    }
    Text {
        visible: page.vanillaRebirth
        Layout.fillWidth: true
        text: "Flesh and vanilla upgrades reset. Equipped items, cosmetics, unopened crates, and Flesh Tokens stay. Other items and active boosts are lost."
        wrapMode: Text.Wrap
        color: page.theme.muted
        font.pixelSize: 12
    }
    Rectangle { Layout.fillWidth: true; height: 1; color: page.theme.line }
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
            Text { visible: (page.progress.choices || []).length > 0; text: "Choose a permanent bonus"; color: page.theme.text; font.family: page.theme.mono; font.bold: true; font.pixelSize: 15 }
            Repeater {
                model: page.progress.choices || []
                delegate: PixelButton {
                    required property var modelData
                    theme: page.theme
                    text: modelData.name + "  " + modelData.desc
                    Layout.fillWidth: true
                    onClicked: game.chooseRebirthBonus(modelData.id)
                }
            }
            Text { visible: (page.progress.pendingChoices || 0) > 1; text: (page.progress.pendingChoices || 0) + " choices waiting"; color: page.theme.muted; font.pixelSize: 12 }
            Text { text: page.vanillaRebirth ? "Token upgrades" : "Permanent upgrades"; color: page.theme.text; font.family: page.theme.mono; font.bold: true; font.pixelSize: 15; Layout.topMargin: 8 }
            Repeater {
                model: page.progress.shop || []
                delegate: PixelFrame {
                    id: upgrade
                    required property var modelData
                    theme: page.theme
                    Layout.fillWidth: true
                    Layout.preferredHeight: 72
                    RowLayout {
                        anchors.fill: parent
                        spacing: 10
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text { text: upgrade.modelData.name + "  " + upgrade.modelData.level + "/" + upgrade.modelData.maxLevel; color: page.theme.text; font.pixelSize: 14; font.bold: true }
                            Text { text: upgrade.modelData.desc; color: page.theme.muted; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        }
                        PixelButton {
                            theme: page.theme
                            text: upgrade.modelData.level >= upgrade.modelData.maxLevel ? "Max" : CurrencyFormat.format(upgrade.modelData.cost, game.preferences.show_full_numbers) + " " + upgrade.modelData.currencyName
                            enabled: upgrade.modelData.level < upgrade.modelData.maxLevel && upgrade.modelData.canBuy === true
                            onClicked: game.buyRebirthUpgrade(upgrade.modelData.id)
                        }
                    }
                }
            }
        }
    }
}

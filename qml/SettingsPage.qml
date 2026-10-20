import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: page
    required property var theme
    property var preferences: game.preferences
    clip: true
    contentWidth: availableWidth
    ColumnLayout {
        width: page.availableWidth - 12
        spacing: 14
        SectionTitle { theme: page.theme; text: "Settings" }
        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 12
            rowSpacing: 12
            Text { text: "Appearance"; color: page.theme.text; font.pixelSize: 14; Layout.fillWidth: true }
            ComboBox {
                id: themeSelector
                objectName: "themeSelector"
                model: ["Light", "Dark", "System"]
                currentIndex: ["light", "dark", "system"].indexOf(page.preferences.theme || "system")
                Accessible.name: "Appearance"
                Layout.preferredWidth: 142
                onActivated: game.setPreference("theme", ["light", "dark", "system"][currentIndex])
            }
            Text { text: "Click sound"; color: page.theme.text; font.pixelSize: 14; Layout.fillWidth: true; wrapMode: Text.Wrap }
            Switch { checked: page.preferences.play_click_sound === true; Accessible.name: "Click sound"; onClicked: game.setPreference("play_click_sound", checked) }
            Text { text: "Volume"; color: page.theme.text; font.pixelSize: 14; Layout.fillWidth: true }
            RowLayout {
                Layout.preferredWidth: 180
                Slider { id: volume; Layout.fillWidth: true; from: 0; to: 100; stepSize: 1; value: Number(page.preferences.click_sound_volume || 0); Accessible.name: "Click sound volume"; onMoved: game.setPreference("click_sound_volume", Math.round(value)) }
                Text { text: Math.round(volume.value) + "%"; color: page.theme.muted; font.pixelSize: 12; Layout.preferredWidth: 36; horizontalAlignment: Text.AlignRight }
            }
            Text { text: "Squish duration (ms)"; color: page.theme.text; font.pixelSize: 14; Layout.fillWidth: true; wrapMode: Text.Wrap }
            SpinBox { from: 0; to: 2000; stepSize: 10; editable: true; value: Number(page.preferences.squish_ms || 0); Accessible.name: "Squish duration in milliseconds"; Layout.preferredWidth: 142; onValueModified: game.setPreference("squish_ms", value) }
            Text { text: "Discord presence"; color: page.theme.text; font.pixelSize: 14; Layout.fillWidth: true; wrapMode: Text.Wrap }
            Switch { checked: page.preferences.enable_rpc === true; Accessible.name: "Discord presence"; onClicked: game.setPreference("enable_rpc", checked) }
            Text { text: "Auto reload mod changes"; color: page.theme.text; font.pixelSize: 14; Layout.fillWidth: true; wrapMode: Text.Wrap }
            Switch { checked: page.preferences.auto_reload_mod_changes === true; Accessible.name: "Auto reload mod changes"; onClicked: game.setPreference("auto_reload_mod_changes", checked) }
        }
        Rectangle { Layout.fillWidth: true; Layout.topMargin: 6; height: 1; color: page.theme.line }
        RowLayout {
            Layout.fillWidth: true
            SectionTitle { theme: page.theme; text: "Installed mods"; Layout.fillWidth: true }
            PixelButton { theme: page.theme; text: "\u21bb"; tooltip: "Reload mods"; Accessible.name: "Reload mods"; onClicked: game.reloadMods() }
        }
        Repeater {
            model: game.catalog.mods || []
            delegate: ModRow { required property var modelData; Layout.fillWidth: true; theme: page.theme; mod: modelData }
        }
        Text { text: "No mods installed"; visible: (game.catalog.mods || []).length === 0; color: page.theme.muted; font.pixelSize: 14 }
        Item { Layout.preferredHeight: 12 }
    }
}

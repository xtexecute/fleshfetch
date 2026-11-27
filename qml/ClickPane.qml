import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "CurrencyFormat.js" as CurrencyFormat

ColumnLayout {
    id: pane
    required property var theme
    property var live: game.live
    property var preferences: game.preferences
    spacing: 12
    SectionTitle { theme: pane.theme; text: pane.live.title || "fleshfetch"; Layout.fillWidth: true; font.pixelSize: 22 }
    RowLayout {
        Layout.fillWidth: true
        Text { text: pane.live.saveName || "No active save"; color: pane.theme.muted; font.pixelSize: 14; Layout.fillWidth: true; elide: Text.ElideRight }
        Switch {
            text: "Full"
            checked: pane.preferences.show_full_numbers === true
            Accessible.name: "Show full currency amounts"
            ToolTip.visible: hovered
            ToolTip.text: checked ? "Show abbreviated amounts" : "Show full amounts"
            onClicked: game.setPreference("show_full_numbers", checked)
        }
    }
    ScrollView {
        id: currencyScroll
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(currencyRows.implicitHeight, pane.height * 0.34)
        contentWidth: availableWidth
        clip: true
        Grid {
            id: currencyRows
            objectName: "currencyTiles"
            width: currencyScroll.availableWidth
            columns: Math.max(1, Math.floor((width + 8) / 132))
            columnSpacing: 8
            rowSpacing: 8
            Repeater {
                model: pane.live.currencies || []
                delegate: PixelFrame {
                    required property var modelData
                    theme: pane.theme
                    width: (currencyRows.width - (currencyRows.columns - 1) * currencyRows.columnSpacing) / currencyRows.columns
                    height: 128
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 2
                        Text { text: modelData.name || modelData.id; color: pane.theme.muted; font.pixelSize: 14; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight; Layout.fillWidth: true }
                        Text {
                            text: pane.amount(modelData.amount)
                            color: pane.theme.text
                            font.family: pane.theme.mono
                            font.pixelSize: 22
                            font.bold: true
                            fontSizeMode: Text.HorizontalFit
                            minimumPixelSize: 12
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            HoverHandler { id: amountHover }
                            ToolTip.visible: amountHover.hovered
                            ToolTip.text: CurrencyFormat.format(modelData.amount, true)
                        }
                        Text { text: pane.amount(modelData.cpc) + " / click\n" + pane.amount(modelData.cps) + " / sec"; color: pane.theme.muted; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.Wrap; maximumLineCount: 4; elide: Text.ElideRight }
                    }
                }
            }
        }
    }
    PixelFrame {
        theme: pane.theme
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 120
        inset: 8
        Item {
            id: stage
            objectName: "clickStage"
            anchors.fill: parent
            clip: true
            property int particleCursor: 0
            property int dropletCursor: 0
            property int burstCursor: 0
            property int gainCursor: 0
            property int crateCursor: 0
            property int mintLeafCursor: 0
            property real lastClickX: width / 2
            property real lastClickY: height / 2
            property var streak: (pane.live.progression || {}).streak || ({fill: 0, multiplier: 1})
            readonly property string cosmetic: (pane.live.progression || {}).selectedCosmetic || ""
            readonly property string cosmeticRarity: (pane.live.progression || {}).cosmeticRarity || ""
            readonly property int cosmeticRank: Number((pane.live.progression || {}).cosmeticRank ?? -1)
            readonly property int commonPixelScale: Math.max(1, Math.round(fleshArt.paintedWidth / 150))
            readonly property int rosePixelScale: Math.max(1, Math.floor(Math.min(width, height) / 120))
            readonly property real maxTilt: cosmetic === "wobble" ? 55 : 12
            property real wobbleAngle: 0
            property real wobbleVelocity: 0
            property real magnetPull: 0
            property real magnetSwing: 0
            property real tagAngle: 24
            property real tagVelocity: 0
            property real mintShakeAngle: 0
            property real skyLift: 0
            property real confusionPhase: 0
            NumberAnimation on confusionPhase {
                running: stage.cosmetic === "violet"
                from: 0
                to: 6.2831853
                duration: 4200
                loops: Animation.Infinite
            }
            readonly property real clockworkSize: Math.min(width * 0.96, height * 0.9)
            onCosmeticChanged: Qt.callLater(function() {
                wobbleMotion.stop()
                magnetSnap.stop()
                tagMotion.stop()
                mintShake.stop()
                skyLiftAnim.stop()
                wobbleAngle = 0
                wobbleVelocity = 0
                magnetPull = 0
                magnetSwing = 0
                tagAngle = 24
                tagVelocity = 0
                mintShakeAngle = 0
                skyLift = 0
                compressionBounce.stop()
                compression.xScale = 1
                compression.yScale = 1
                fleshImpulse.rotation = 0
                clickTarget.fleshPressed = false
                fleshSpin.rotation = 0
                if (cosmetic !== "hologram") fleshArt.opacity = 1
            })
            function formatGain(amount) {
                const value = Number(amount || 0)
                if (value >= 1e12) return "+" + (value / 1e12).toFixed(1) + "T"
                if (value >= 1e9) return "+" + (value / 1e9).toFixed(1) + "B"
                if (value >= 1e6) return "+" + (value / 1e6).toFixed(1) + "M"
                if (value >= 1e3) return "+" + (value / 1e3).toFixed(1) + "K"
                const shown = Math.abs(value - Math.round(value)) < 0.01 ? Math.round(value) : value
                return "+" + shown.toLocaleString(Qt.locale(), 'f', shown % 1 === 0 ? 0 : 1)
            }
            function popup(x, y, label, color, large) {
                const item = gainTexts.itemAt(gainCursor)
                gainCursor = (gainCursor + 1) % gainTexts.count
                if (item) item.launch(x, y, label, color, large)
            }
            function spawnCrate(dropId, kind, tier) {
                const crate = fallingCrates.itemAt(crateCursor)
                crateCursor = (crateCursor + 1) % fallingCrates.count
                if (crate) crate.launch(dropId, tier, lastClickX, lastClickY, height)
                else game.collectCrateDrop(dropId)
            }
            function burst(x, y) {
                for (let i = 0; i < 12; ++i) {
                    const particle = whiteBurst.itemAt(burstCursor)
                    burstCursor = (burstCursor + 1) % whiteBurst.count
                    const angle = Math.random() * Math.PI * 2
                    if (particle) particle.launch(x, y, Math.cos(angle) * (20 + Math.random() * 48),
                                                   Math.sin(angle) * (18 + Math.random() * 35) - 15)
                }
            }
            function react(hitX, hitY, outcome) {
                if (cosmetic === "temporal_echo") {
                    const local = fleshArt.mapFromItem(stage, hitX, hitY)
                    temporalEcho.recordHit(local.x / fleshArt.width, local.y / fleshArt.height)
                }
                if (cosmetic !== "fishbowl" && cosmetic !== "blacksmith" && cosmetic !== "zero_gravity"
                        && cosmetic !== "event_horizon" && cosmetic !== "tidal_planet" && cosmetic !== "snow_globe"
                        && cosmetic !== "lava_lamp" && cosmetic !== "marionette")
                    compressionBounce.restart()
                if (cosmetic === "magnet") magnetSnap.restart()
                if (cosmetic === "ticket_roll") ticketRollArt.react()
                if (cosmetic === "sky") {
                    skyArt.react()
                    skyLiftAnim.restart()
                }
                if (cosmetic === "hologram") hologramArt.react()
                if (cosmetic === "thunderhead") thunderheadArt.react()
                if (cosmetic === "pinball") {
                    const point = stage.mapToItem(pinballArt, hitX, hitY)
                    pinballArt.react(point.x, point.y)
                }
                if (cosmetic === "slot_machine") slotMachineArt.react()
                if (cosmetic === "blacksmith") {
                    blacksmithArt.react()
                }
                if (cosmetic === "comet") cometArt.react()
                if (cosmetic === "rose") roseArt.react()
                if (cosmetic === "sunlight") sunlight.strike(hitX / width, hitY / height)
                if (cosmetic === "event_horizon") eventHorizon.strike(hitX, hitY)
                if (cosmetic === "tidal_planet") tidalPlanet.strike(hitX, hitY)
                if(cosmetic === "snow_globe") {
                    const point=snowGlobe.mapFromItem(stage,hitX,hitY)
                    snowGlobe.strike(point.x,point.y)
                }
                if(cosmetic === "lava_lamp") {
                    const point=lavaLamp.mapFromItem(stage,hitX,hitY)
                    lavaLamp.strike(point.x,point.y)
                }
                if(cosmetic === "marionette") {
                    const point=marionette.mapFromItem(stage,hitX,hitY)
                    const uv=marionette.texturePoint(point.x,point.y)
                    marionette.strike(uv.x,uv.y)
                }
                if (cosmetic === "neon_outline") {
                    const local=fleshArt.mapFromItem(stage,hitX,hitY)
                    neonOutline.strike(local.x/fleshArt.width,local.y/fleshArt.height)
                }
                if (cosmetic === "star_map") {
                    const local=fleshArt.mapFromItem(stage,hitX,hitY)
                    starMap.strike(local.x/fleshArt.width,local.y/fleshArt.height)
                }
                if (cosmetic === "deep_blue") {
                    const local = fleshArt.mapFromItem(stage, hitX, hitY)
                    deepBlue.strike(local.x / fleshArt.width, local.y / fleshArt.height, hitX, hitY)
                }
                if (cosmetic === "aurora_ribbon") {
                    const local = aurora.mapFromItem(stage, hitX, hitY)
                    aurora.strike(local.x, local.y)
                }
                if (cosmetic === "sundial") sundial.advance()
                if (cosmetic === "prism_rain") prismRain.strike(hitX, hitY)
                if (cosmetic === "lightbox") {
                    const local = fleshArt.mapFromItem(stage, hitX, hitY)
                    lightbox.expose(local.x / fleshArt.width, local.y / fleshArt.height)
                }
                if (cosmetic === "firefly_jar") {
                    const point = fireflyJar.mapFromItem(stage, hitX, hitY)
                    fireflyJar.stir(point.x, point.y)
                }
                if (cosmetic === "opal") {
                    const local = fleshArt.mapFromItem(stage, hitX, hitY)
                    opal.strike(local.x / fleshArt.width, local.y / fleshArt.height, hitX, hitY)
                }
                if (cosmetic === "stained_glass") {
                    const local = fleshArt.mapFromItem(stage, hitX, hitY)
                    stainedGlass.strike(local.x / fleshArt.width, local.y / fleshArt.height)
                }
                if (cosmetic === "sandcastle") {
                    const local = fleshArt.mapFromItem(stage, hitX, hitY)
                    sandcastle.crumble(local.x / fleshArt.width)
                }
                if (cosmetic === "shadow_twin") {
                    const local = fleshArt.mapFromItem(stage, hitX, hitY)
                    shadowTwinArt.react(local.x / fleshArt.width, local.y / fleshArt.height)
                }
                if (cosmetic === "liquid_metal") {
                    const local = fleshArt.mapFromItem(stage, hitX, hitY)
                    liquidMetalMotion.strike(local.x / fleshArt.width, local.y / fleshArt.height)
                }
                if (cosmetic === "zero_gravity") {
                    const local = fleshArt.mapFromItem(stage, hitX, hitY)
                    zeroGravity.kick(local.x / fleshArt.width, local.y / fleshArt.height, hitX, hitY)
                }
                if (cosmetic === "clockwork") clockworkArt.advance()
                if (cosmetic === "cat") game.playEffectSound("cat")
                if (cosmetic === "mint") {
                    mintShake.restart()
                    game.playEffectSound("mint")
                    const count = Math.random() < 0.5 ? 1 : 2
                    for (let i = 0; i < count; ++i) {
                        const leaf = mintLeaves.itemAt(mintLeafCursor)
                        mintLeafCursor = (mintLeafCursor + 1) % mintLeaves.count
                        const sources = [[0.28, 0.23, -1], [0.72, 0.20, 1],
                                         [0.36, 0.52, -1], [0.66, 0.66, 1]]
                        const source = sources[Math.floor(Math.random() * sources.length)]
                        const origin = mintPlant.mapToItem(stage,
                            mintPlant.width * source[0], mintPlant.height * source[1])
                        if (leaf) leaf.launch(origin.x, origin.y, source[2])
                    }
                }
                uncommonArt.react()
                if (cosmetic === "price_tag") {
                    tagVelocity = Math.max(-9, Math.min(9, tagVelocity + (Math.random() < 0.5 ? -5 : 5)))
                    tagMotion.start()
                }
                if (cosmetic === "fishbowl") {
                    const point = bowl.mapFromItem(stage, hitX, hitY)
                    fishMotion.kick(point.x / bowl.width, point.y / bowl.height)
                }
                let direction = Math.random() < 0.5 ? -1 : 1
                if (cosmetic === "clockwork" || cosmetic === "fishbowl" || cosmetic === "blacksmith"
                        || cosmetic === "liquid_metal" || cosmetic === "zero_gravity" || cosmetic === "event_horizon"
                        || cosmetic === "tidal_planet" || cosmetic === "snow_globe" || cosmetic === "lava_lamp"
                        || cosmetic === "marionette") {
                    fleshImpulse.rotation = 0
                } else if (cosmetic === "wobble") {
                    if (Math.abs(wobbleAngle) > maxTilt * 0.7 && Math.sign(wobbleAngle) === direction)
                        direction = -direction
                    wobbleVelocity = Math.max(-25, Math.min(25, wobbleVelocity + direction * (12 + Math.random() * 6)))
                    wobbleMotion.start()
                } else {
                    const step = 4 + Math.random() * 5
                    if (Math.abs(fleshImpulse.rotation + direction * step) > maxTilt)
                        direction = -direction
                    fleshImpulse.rotation = Math.max(-maxTilt, Math.min(maxTilt, fleshImpulse.rotation + direction * step))
                }
                if (outcome && outcome.gain > 0) {
                    const label = formatGain(outcome.gain)
                    const tint = outcome.critical ? "#ffdf79" : "#ffffff"
                    if (cosmetic === "event_horizon")
                        eventHorizon.showGain(hitX, hitY - 24, label, tint, outcome.critical)
                    else
                        popup(hitX, hitY - 24, label, tint, outcome.critical)
                }
                if (cosmetic === "fishbowl" || cosmetic === "zero_gravity" || cosmetic === "event_horizon"
                        || cosmetic === "deep_blue" || cosmetic === "tidal_planet" || cosmetic === "snow_globe"
                        || cosmetic === "lava_lamp") return
                const magneticPoint = cosmetic === "magnet"
                    ? magnetArt.mapToItem(stage, magnetArt.width * 0.72, magnetArt.height * 0.32) : null
                for (let i = 0; i < 5; ++i) {
                    const particle = flecks.itemAt(particleCursor)
                    particleCursor = (particleCursor + 1) % flecks.count
                    const angle = Math.random() * Math.PI * 2
                    const distance = 24 + Math.random() * 32
                    particle.launch(hitX + (Math.random() - 0.5) * 8,
                                    hitY + (Math.random() - 0.5) * 8,
                                    magneticPoint ? magneticPoint.x - hitX + (Math.random() - 0.5) * 18 : Math.cos(angle) * distance,
                                    magneticPoint ? magneticPoint.y - hitY + (Math.random() - 0.5) * 18 : Math.sin(angle) * distance - 16)
                }
                if (cosmetic === "gold") {
                    goldCoinPile.launch(hitX, hitY, outcome.streakFill)
                    return
                }
                for (let i = 0; i < 2; ++i) {
                    const drop = droplets.itemAt(dropletCursor)
                    dropletCursor = (dropletCursor + 1) % droplets.count
                    if (drop) drop.launch(hitX + (Math.random() - 0.5) * 12, hitY,
                        cosmetic === "sandcastle" ? height - sandStreak.rise
                        : height * (1 - 0.84 * Math.min(1, (streak.fill || 0) / 100)))
                }
            }
            SequentialAnimation {
                id: mintShake
                NumberAnimation { target: stage; property: "mintShakeAngle"; from: 0; to: -10; duration: 65; easing.type: Easing.OutCubic }
                NumberAnimation { target: stage; property: "mintShakeAngle"; to: 7; duration: 115; easing.type: Easing.OutCubic }
                NumberAnimation { target: stage; property: "mintShakeAngle"; to: -3; duration: 125; easing.type: Easing.OutCubic }
                NumberAnimation { target: stage; property: "mintShakeAngle"; to: 0; duration: 180; easing.type: Easing.OutCubic }
            }
            SequentialAnimation {
                id: skyLiftAnim
                NumberAnimation { target: stage; property: "skyLift"; to: -6 * stage.commonPixelScale; duration: 95; easing.type: Easing.OutCubic }
                NumberAnimation { target: stage; property: "skyLift"; to: 0; duration: 420; easing.type: Easing.OutBack }
            }
            Timer {
                id: tagMotion
                interval: 16
                repeat: true
                onTriggered: {
                    stage.tagVelocity = (stage.tagVelocity + (24 - stage.tagAngle) * 0.055) * 0.94
                    stage.tagAngle = Math.max(-5, Math.min(53, stage.tagAngle + stage.tagVelocity))
                    if (Math.abs(stage.tagAngle - 24) < 0.08 && Math.abs(stage.tagVelocity) < 0.08) {
                        stage.tagAngle = 24
                        stage.tagVelocity = 0
                        stop()
                    }
                }
            }
            SequentialAnimation {
                id: magnetSnap
                ParallelAnimation {
                    NumberAnimation { target: stage; property: "magnetPull"; from: 0; to: 1; duration: 75; easing.type: Easing.OutCubic }
                    NumberAnimation { target: stage; property: "magnetSwing"; from: 0; to: -12; duration: 75; easing.type: Easing.OutCubic }
                }
                ParallelAnimation {
                    NumberAnimation { target: stage; property: "magnetPull"; to: 0; duration: 260; easing.type: Easing.OutBack }
                    NumberAnimation { target: stage; property: "magnetSwing"; to: 0; duration: 260; easing.type: Easing.OutBack }
                }
            }
            SunlightArt {
                id: sunlight
                anchors.fill: parent
                visible: stage.cosmetic === "sunlight"
                sparkLayer: sunlightSparks
            }
            EventHorizonArt {
                id: eventHorizon
                anchors.fill: parent
                visible: stage.cosmetic === "event_horizon"
                source: pane.live.imageUrl || "../flesh.png"
                fontFamily: pane.theme.mono
                fill: visible ? Number(stage.streak.fill || 0) : 0
            }
            StarMapArt {
                id: starMap
                anchors.fill: parent
                visible: stage.cosmetic === "star_map"
                fill: visible ? Number(stage.streak.fill || 0) : 0
            }
            DeepBlueArt {
                id: deepBlue
                anchors.fill: parent
                visible: stage.cosmetic === "deep_blue"
                frontLayer: deepBlueFront
                fill: visible ? Number(stage.streak.fill || 0) : 0
            }
            TidalPlanetArt {
                id: tidalPlanet
                anchors.fill: parent
                visible: stage.cosmetic === "tidal_planet"
                fill: visible ? Number(stage.streak.fill || 0) : 0
            }
            StreakLiquid {
                anchors.fill: parent
                visible: stage.cosmetic !== "gold" && stage.cosmetic !== "sandcastle"
                    && stage.cosmetic !== "opal" && stage.cosmetic !== "event_horizon"
                    && stage.cosmetic !== "star_map" && stage.cosmetic !== "aurora_ribbon"
                    && stage.cosmetic !== "deep_blue"
                    && stage.cosmetic !== "tidal_planet"
                    && stage.cosmetic !== "neon_outline"
                    && stage.cosmetic !== "snow_globe"
                    && stage.cosmetic !== "lava_lamp"
                fill: visible ? Number(stage.streak.fill || 0) : 0
                mercury: stage.cosmetic === "liquid_metal"
            }
            OpalStreak {
                id: opalStreak
                anchors.fill: parent
                visible: stage.cosmetic === "opal"
                fill: visible ? Number(stage.streak.fill || 0) : 0
            }
            MaterialStreak {
                anchors.fill:parent
                fill:stage.cosmetic === "neon_outline" ? Number(stage.streak.fill||0) : 0
                time:neonOutline.time
                energy:neonOutline.energy
            }
            MaterialStreak {
                anchors.fill:parent;material:2
                fill:stage.cosmetic === "lava_lamp" ? Number(stage.streak.fill||0) : 0
                time:lavaLamp.time;energy:lavaLamp.energy
            }
            Item {
                id: auroraPool
                anchors.fill: parent
            }
            SandcastleStreak {
                id: sandStreak
                anchors.fill: parent
                visible: stage.cosmetic === "sandcastle"
                fill: visible ? Number(stage.streak.fill || 0) : 0
            }
            SnowGlobeArt {
                id:snowGlobe
                visible:stage.cosmetic === "snow_globe"
                fill:visible ? Number(stage.streak.fill||0) : 0
                source:pane.live.imageUrl || "../flesh.png"
                pixelSize:Math.max(1,Math.floor(Math.min(stage.width/122,stage.height/140)))
                anchors.centerIn:parent
            }
            LavaLampArt {
                id:lavaLamp
                visible:stage.cosmetic === "lava_lamp"
                source:pane.live.imageUrl || "../flesh.png"
                pixelSize:Math.max(1,Math.floor(Math.min(stage.width/96,stage.height/140)))
                anchors.centerIn:parent
            }
            MarionetteArt {
                id:marionette
                visible:stage.cosmetic === "marionette"
                source:pane.live.imageUrl || "../flesh.png"
                pixelSize:Math.max(1,Math.floor(Math.min(stage.width/134,stage.height/142)))
                anchors.centerIn:parent
            }
            StainedGlassArt {
                id: stainedGlass
                anchors.fill: parent
                visible: stage.cosmetic === "stained_glass"
                flesh: fleshArt
                bodyAngle: fleshImpulse.rotation * Math.PI / 180
                bodySquish: Qt.vector2d(fleshImpulse.scale * compression.xScale,
                                        fleshImpulse.scale * compression.yScale)
            }
            SundialArt {
                id: sundial
                visible: stage.cosmetic === "sundial"
                anchors.centerIn: parent
                width: Math.max(1, Math.min(stage.width - 4, stage.height - 4))
                height: width
                flesh: fleshArt
                bodyAngle: fleshImpulse.rotation * Math.PI / 180
                bodySquish: Qt.vector2d(fleshImpulse.scale * compression.xScale,
                                        fleshImpulse.scale * compression.yScale)
            }
            PrismRainArt {
                id: prismRain
                anchors.fill: parent
                visible: stage.cosmetic === "prism_rain"
                frontLayer: prismRainFront
            }
            LightboxArt {
                id: lightbox
                visible: stage.cosmetic === "lightbox"
                pixelSize: Math.max(1, Math.floor(Math.min(stage.width / 124, stage.height / 140)))
                x: Math.round((stage.width - width) / 2)
                y: Math.round((stage.height - height) / 2)
                flesh: fleshArt
                frontLayer: lightboxFront
                bodyAngle: fleshImpulse.rotation * Math.PI / 180
                bodySquish: Qt.vector2d(fleshImpulse.scale * compression.xScale,
                                        fleshImpulse.scale * compression.yScale)
            }
            FireflyJarArt {
                id: fireflyJar
                visible: stage.cosmetic === "firefly_jar"
                pixelSize: Math.max(1, Math.floor(Math.min(stage.width / 122, stage.height / 142)))
                x: Math.round((stage.width - width) / 2)
                y: Math.round((stage.height - height) / 2)
                frontLayer: fireflyJarFront
            }
            OpalArt {
                id: opal
                visible: stage.cosmetic === "opal"
                anchors.fill: parent
                frontLayer: opalGlints
            }
            GoldCoinPile {
                id: goldCoinPile
                anchors.fill: parent
                visible: stage.cosmetic === "gold"
                fill: Number(stage.streak.fill || 0)
                saveId: pane.live.saveId || ""
                flightLayer: goldCoinFlights
                onCoinLanded: game.playEffectSound("coin")
            }
            Timer {
                id: wobbleMotion
                interval: 16
                repeat: true
                onTriggered: {
                    if (stage.cosmetic !== "wobble") {
                        stop()
                        stage.wobbleAngle = 0
                        stage.wobbleVelocity = 0
                        fleshImpulse.rotation = 0
                        return
                    }
                    stage.wobbleVelocity = (stage.wobbleVelocity - stage.wobbleAngle * 0.055) * 0.93
                    stage.wobbleAngle += stage.wobbleVelocity
                    if (Math.abs(stage.wobbleAngle) > stage.maxTilt) {
                        stage.wobbleAngle = Math.sign(stage.wobbleAngle) * stage.maxTilt
                        stage.wobbleVelocity *= -0.55
                    }
                    fleshImpulse.rotation = stage.wobbleAngle
                    if (Math.abs(stage.wobbleAngle) < 0.15 && Math.abs(stage.wobbleVelocity) < 0.15) {
                        stop()
                        stage.wobbleAngle = 0
                        stage.wobbleVelocity = 0
                        fleshImpulse.rotation = 0
                    }
                }
            }
            Text {
                readonly property bool compactBlacksmith: stage.cosmetic === "blacksmith" && stage.height < 220
                x: parent.width - width - 8
                y: compactBlacksmith ? parent.height - height - 4 : 8
                visible: Number(stage.streak.fill || 0) > 0
                text: "STREAK " + Number(stage.streak.multiplier || 1).toFixed(2) + "x"
                color: stage.cosmetic === "gold" || stage.cosmetic === "sandcastle" || Number(stage.streak.fill || 0) >= 100
                    ? (pane.theme.dark ? "#ffe69b" : "#805800")
                    : stage.cosmetic === "liquid_metal" ? (pane.theme.dark ? "#d7ecf4" : "#36556b")
                    : (pane.theme.dark ? "#ffb9c6" : "#9d3148")
                font.family: pane.theme.mono
                font.pixelSize: compactBlacksmith ? 11 : 13
                font.bold: true
                z: 10
            }
            Connections {
                target: game
                function onCrateDropSpawned(dropId, kind, tier) { stage.spawnCrate(dropId, kind, tier) }
            }
            AbstractButton {
                id: clickTarget
                objectName: "clickTarget"
                property bool fleshPressed: false
                anchors.fill: parent
                hoverEnabled: true
                focusPolicy: Qt.StrongFocus
                Accessible.name: stage.cosmetic === "event_horizon" ? "Feed the black hole" : "Fetch flesh"
                function hits(image, hitX, hitY, reflected) {
                    if (!image.visible) return false
                    if (reflected) {
                        const glass = mirrorGlass.mapFromItem(clickTarget, hitX, hitY)
                        if (glass.x < 0 || glass.y < 0 || glass.x >= mirrorGlass.width || glass.y >= mirrorGlass.height)
                            return false
                    }
                    const local = image.mapFromItem(clickTarget, hitX, hitY)
                    if (image === clockworkArt)
                        return game.isClockworkHit(local.x, local.y, image.width, image.height)
                    let paintedX = local.x - (image.width - image.paintedWidth) / 2
                    let paintedY = local.y - (image.height - image.paintedHeight) / 2
                    if (image === catArt)
                        return game.isCatHit(paintedX, paintedY, image.paintedWidth, image.paintedHeight)
                    if (image === fleshArt && stage.cosmetic === "violet") {
                        const phase = stage.confusionPhase
                        const wave = 0.5 - 0.5 * Math.cos(phase)
                        let u = local.x / image.width
                        let v = local.y / image.height
                        u += (0.002 + 0.006 * wave) * Math.sin(v * 17 + phase)
                            + 0.0015 * Math.sin(v * 34 - phase * 0.7)
                        v += 0.002 * wave * Math.sin(u * 19 - phase)
                        paintedX = u * image.width - (image.width - image.paintedWidth) / 2
                        paintedY = v * image.height - (image.height - image.paintedHeight) / 2
                    }
                    return game.isFleshHit(reflected ? image.paintedWidth - paintedX - 0.01 : paintedX,
                                           paintedY, image.paintedWidth, image.paintedHeight)
                }
                function activate(hitX, hitY) {
                    const horizonHit = stage.cosmetic === "event_horizon" && eventHorizon.hitTest(hitX, hitY)
                    const planetHit = stage.cosmetic === "tidal_planet" && tidalPlanet.hitTest(hitX, hitY)
                    const snowPoint=stage.cosmetic === "snow_globe" ? snowGlobe.mapFromItem(clickTarget,hitX,hitY) : null
                    const lavaPoint=stage.cosmetic === "lava_lamp" ? lavaLamp.mapFromItem(clickTarget,hitX,hitY) : null
                    const puppetPoint=stage.cosmetic === "marionette" ? marionette.mapFromItem(clickTarget,hitX,hitY) : null
                    const reflectionHit = stage.cosmetic === "reflection" && hits(mirrorArt, hitX, hitY, true)
                    const bowlHit = stage.cosmetic === "fishbowl" && bowl.hitTest(hitX, hitY)
                    const anvilPoint = stage.cosmetic === "blacksmith"
                        ? blacksmithArt.mapFromItem(clickTarget, hitX, hitY) : null
                    const anvilHit = anvilPoint && blacksmithArt.hitTest(anvilPoint.x, anvilPoint.y)
                    const mainArt = stage.cosmetic === "clockwork" ? clockworkArt
                        : stage.cosmetic === "cat" ? catArt : fleshArt
                    if (stage.cosmetic === "event_horizon" ? !horizonHit
                            : stage.cosmetic === "tidal_planet" ? !planetHit
                            : stage.cosmetic === "snow_globe" ? !snowGlobe.hitTest(snowPoint.x,snowPoint.y)
                            : stage.cosmetic === "lava_lamp" ? !lavaLamp.hitTest(lavaPoint.x,lavaPoint.y)
                            : stage.cosmetic === "marionette" ? !marionette.hitTest(puppetPoint.x,puppetPoint.y)
                            : stage.cosmetic === "fishbowl" ? !bowlHit
                            : !reflectionHit && !anvilHit && !hits(mainArt, hitX, hitY, false))
                        return
                    stage.lastClickX = hitX
                    stage.lastClickY = hitY
                    const outcome = game.click(hitX, hitY)
                    if (!outcome.accepted)
                        return
                    stage.react(hitX, hitY, outcome)
                    if (reflectionHit) {
                        glassCracks.strike(hitX, hitY)
                        game.playEffectSound("glass")
                    }
                    if (stage.cosmetic === "pixel_tv") {
                        tvCracks.strike(hitX, hitY)
                        game.playEffectSound("glass")
                    }
                }
                onClicked: activate(width / 2, stage.cosmetic === "reflection" ? fleshArt.y + fleshArt.height / 2 : height / 2)
                MouseArea {
                    id: clickSurface
                    anchors.fill: parent
                    hoverEnabled: true
                    onPressed: function(mouse) {
                        const mainArt = stage.cosmetic === "clockwork" ? clockworkArt
                            : stage.cosmetic === "cat" ? catArt : fleshArt
                        const anvilPoint = stage.cosmetic === "blacksmith"
                            ? blacksmithArt.mapFromItem(clickTarget, mouse.x, mouse.y) : null
                        const snowPoint=stage.cosmetic === "snow_globe" ? snowGlobe.mapFromItem(clickTarget,mouse.x,mouse.y) : null
                        const lavaPoint=stage.cosmetic === "lava_lamp" ? lavaLamp.mapFromItem(clickTarget,mouse.x,mouse.y) : null
                        const puppetPoint=stage.cosmetic === "marionette" ? marionette.mapFromItem(clickTarget,mouse.x,mouse.y) : null
                        clickTarget.fleshPressed = stage.cosmetic === "event_horizon"
                            ? eventHorizon.hitTest(mouse.x, mouse.y)
                            : stage.cosmetic === "tidal_planet"
                            ? tidalPlanet.hitTest(mouse.x, mouse.y)
                            : stage.cosmetic === "snow_globe"
                            ? snowGlobe.hitTest(snowPoint.x,snowPoint.y)
                            : stage.cosmetic === "lava_lamp"
                            ? lavaLamp.hitTest(lavaPoint.x,lavaPoint.y)
                            : stage.cosmetic === "marionette"
                            ? marionette.hitTest(puppetPoint.x,puppetPoint.y)
                            : stage.cosmetic === "fishbowl"
                            ? bowl.hitTest(mouse.x, mouse.y)
                            : clickTarget.hits(mainArt, mouse.x, mouse.y, false)
                                || (anvilPoint && blacksmithArt.hitTest(anvilPoint.x, anvilPoint.y))
                                || (stage.cosmetic === "reflection" && clickTarget.hits(mirrorArt, mouse.x, mouse.y, true))
                    }
                    onReleased: clickTarget.fleshPressed = false
                    onCanceled: clickTarget.fleshPressed = false
                    onClicked: function(mouse) {
                        clickTarget.forceActiveFocus()
                        clickTarget.activate(mouse.x, mouse.y)
                    }
                }
                background: Rectangle {
                    color: "transparent"
                    border.width: clickTarget.activeFocus ? 2 : 0
                    border.color: pane.theme.accent
                }
                contentItem: Item {
                    id: fleshSpin
                    objectName: "fleshSpin"
                    Item {
                        id: tvBody
                        visible: stage.cosmetic === "pixel_tv"
                        width: Math.floor(Math.min(parent.width * 0.9,
                            parent.height * 0.8 * 240 / 188) / 4) * 4
                        height: width * 188 / 240
                        x: Math.round((parent.width - width) / 2)
                        y: Math.round((parent.height - height) / 2)
                        Image {
                            anchors.fill: parent
                            source: "../assets/skins/pixel-tv-back.png"
                            smooth: false
                            mipmap: false
                        }
                    }
                    SlotMachineArt {
                        id: slotMachineArt
                        objectName: "slotMachineArt"
                        visible: stage.cosmetic === "slot_machine"
                        pixelScale: Math.max(1, Math.floor(Math.min(parent.width / 120, parent.height / 160)))
                        width: 120 * pixelScale
                        height: 160 * pixelScale
                        x: Math.round((parent.width - width) / 2)
                        y: Math.round((parent.height - height) / 2)
                    }
                    Image {
                        id: mirrorFrame
                        visible: stage.cosmetic === "reflection"
                        readonly property int pixel: Math.max(1,
                            Math.floor(Math.min(parent.width * 0.9 / 104, parent.height * 0.48 / 64)))
                        readonly property int gap: 5 * pixel
                        readonly property int fleshSize: Math.max(1,
                            Math.min(54 * pixel, Math.floor(parent.height - height - gap - 4)))
                        width: 104 * pixel
                        height: 64 * pixel
                        x: Math.round((parent.width - width) / 2)
                        y: Math.max(2, Math.round((parent.height - height - gap - fleshSize) / 2))
                        source: "../assets/skins/reflection-mirror.png"
                        smooth: false
                        Item {
                            id: mirrorGlass
                            objectName: "reflectionGlass"
                            x: 8 * mirrorFrame.pixel
                            y: 7 * mirrorFrame.pixel
                            width: 88 * mirrorFrame.pixel
                            height: 50 * mirrorFrame.pixel
                            clip: true
                            Image {
                                id: mirrorArt
                                objectName: "reflectionFlesh"
                                anchors.centerIn: parent
                                source: mirrorFrame.visible ? fleshArt.source : ""
                                width: parent.width
                                height: parent.height * 0.94
                                mirror: true
                                rotation: -fleshImpulse.rotation
                                opacity: 0.81
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                            }
                        }
                    }
                    FishbowlMotion {
                        id: fishMotion
                        objectName: "fishbowlMotion"
                        visible: stage.cosmetic === "fishbowl"
                        bowlWidth: bowl.width
                        bowlHeight: bowl.height
                    }
                    Canvas {
                        id: bowl
                        objectName: "fishbowlCanvas"
                        visible: stage.cosmetic === "fishbowl"
                        readonly property var innerOutline: [[32, 20], [68, 20], [76, 28], [82, 38],
                            [82, 72], [76, 84], [66, 96], [34, 96],
                            [24, 84], [18, 72], [18, 38], [24, 28]]
                        readonly property var hitOutline: [[26, 4], [74, 4], [74, 18], [78, 24],
                            [86, 34], [88, 42], [88, 74], [82, 88],
                            [68, 102], [70, 108], [70, 116], [30, 116],
                            [30, 108], [32, 102], [18, 88], [12, 74],
                            [12, 42], [14, 34], [22, 24], [26, 18]]
                        width: Math.floor(Math.min(parent.width * 0.93,
                            parent.height * 0.78 * 124 / 120) / 4) * 4
                        height: width * 120 / 124
                        x: (parent.width - width) / 2
                        y: (parent.height - height) / 2
                        function widenedX(x) { return 62 + Math.round((x - 50) * 0.7) * 2 }
                        function hitTest(hitX, hitY) {
                            const point = mapFromItem(clickTarget, hitX, hitY)
                            const x = point.x * 124 / width
                            const y = point.y * 120 / height
                            let inside = false
                            for (let i = 0, j = hitOutline.length - 1; i < hitOutline.length; j = i++) {
                                const xi = widenedX(hitOutline[i][0]), yi = hitOutline[i][1]
                                const xj = widenedX(hitOutline[j][0]), yj = hitOutline[j][1]
                                if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi)
                                    inside = !inside
                            }
                            return inside
                        }
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()
                        Connections {
                            target: fishMotion
                            function onSurfaceTiltChanged() { bowl.requestPaint() }
                        }
                        onPaint: {
                            const ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)
                            const outline = bowl.innerOutline
                            const scale = width / 124
                            ctx.save()
                            ctx.beginPath()
                            for (let i = 0; i < outline.length; ++i) {
                                const x = Math.round(bowl.widenedX(outline[i][0]) * scale / 4) * 4
                                const y = Math.round(outline[i][1] * scale / 4) * 4
                                if (i === 0) ctx.moveTo(x, y)
                                else ctx.lineTo(x, y)
                            }
                            ctx.closePath()
                            ctx.clip()
                            ctx.fillStyle = "#292b2c"
                            ctx.fillRect(0, 0, width, height)
                            const top = Math.round(height * 0.23 / 4) * 4
                            function surface(x) {
                                return Math.round((top + fishMotion.surfaceTilt * (1 - 2 * x / width)) / 4) * 4
                            }
                            ctx.beginPath()
                            ctx.moveTo(0, surface(0))
                            ctx.lineTo(width * 0.3, surface(width * 0.3))
                            ctx.lineTo(width * 0.65, surface(width * 0.65))
                            ctx.lineTo(width, surface(width))
                            ctx.lineTo(width, height)
                            ctx.lineTo(0, height)
                            ctx.closePath()
                            ctx.fillStyle = "#6d1c31"
                            ctx.fill()
                            ctx.beginPath()
                            ctx.moveTo(0, surface(0))
                            ctx.lineTo(width * 0.3, surface(width * 0.3))
                            ctx.lineTo(width * 0.65, surface(width * 0.65))
                            ctx.lineTo(width, surface(width))
                            ctx.strokeStyle = "#d95670"
                            ctx.lineWidth = 2
                            ctx.stroke()
                            ctx.restore()
                        }
                    }
                    Repeater {
                        model: 7
                        delegate: Image {
                            id: bubble
                            visible: stage.cosmetic === "fishbowl"
                            readonly property real lane: [0.23, 0.36, 0.51, 0.68, 0.78, 0.42, 0.61][index]
                            property real travel: 0
                            source: "../assets/skins/fishbowl-bubble.png"
                            width: 12 * stage.commonPixelScale
                            height: width
                            x: Math.round(bowl.x + bowl.width * lane
                                + Math.sin(travel * 7 + index) * 3 * stage.commonPixelScale - width / 2)
                            y: Math.round(bowl.y + bowl.height * (0.81 - 0.56 * travel) - height / 2)
                            opacity: travel <= 0 ? 0 : Math.min(1, travel * 9) * (1 - travel) * 0.8
                            smooth: false
                            mipmap: false
                            SequentialAnimation on travel {
                                running: bubble.visible
                                loops: Animation.Infinite
                                PauseAnimation { duration: index * 360 }
                                NumberAnimation { from: 0; to: 1; duration: 2600 + index * 160; easing.type: Easing.InQuad }
                            }
                        }
                    }
                    Item {
                        anchors.fill: parent
                        HologramArt {
                            id: hologramArt
                            objectName: "hologramArt"
                            anchors.fill: parent
                            visible: stage.cosmetic === "hologram"
                            pixelScale: stage.commonPixelScale
                            fleshLeft: fleshArt.x + (fleshArt.width - fleshArt.paintedWidth) / 2
                            fleshTop: fleshArt.y + (fleshArt.height - fleshArt.paintedHeight) / 2
                            fleshWidth: fleshArt.paintedWidth
                            fleshHeight: fleshArt.paintedHeight
                        }
                        SandcastleArt {
                            id: sandcastle
                            visible: stage.cosmetic === "sandcastle"
                            pixelSize: Math.max(1, Math.floor(Math.min(parent.width / 132, parent.height / 124)))
                            width: 132 * pixelSize
                            height: 124 * pixelSize
                            x: Math.round((parent.width - width) / 2)
                            y: Math.floor((parent.height - height) / 2)
                        }
                        TemporalEchoArt {
                            id: temporalEcho
                            anchors.fill: parent
                            visible: stage.cosmetic === "temporal_echo"
                            source: pane.live.fleshCopyUrl || ""
                            flesh: fleshArt
                            flashLayer: temporalEchoFlashes
                            liveAngle: fleshImpulse.rotation
                            liveScale: fleshImpulse.scale
                            liveScaleX: compression.xScale
                            liveScaleY: compression.yScale
                            clickMotionMs: Number(pane.preferences.squish_ms || 100)
                            saveId: pane.live.saveId || ""
                        }
                        Item {
                            id: fleshImpulse
                            objectName: "fleshImpulse"
                            anchors.fill: parent
                            scale: clickTarget.fleshPressed && stage.cosmetic !== "fishbowl"
                                && stage.cosmetic !== "zero_gravity"
                                && stage.cosmetic !== "event_horizon"
                                ? (stage.cosmetic === "wobble" ? 0.85 : 0.93) : 1
                            Behavior on scale { NumberAnimation { duration: Number(game.preferences.squish_ms || 100); easing.type: Easing.OutQuad } }
                            Behavior on rotation {
                                enabled: stage.cosmetic !== "wobble"
                                NumberAnimation { duration: 130; easing.type: Easing.OutCubic }
                            }
                            transform: Scale {
                                id: compression
                                origin.x: fleshImpulse.width / 2
                                origin.y: fleshImpulse.height / 2
                                xScale: 1
                                yScale: 1
                            }
                            ShadowTwinArt {
                                id: shadowTwinArt
                                anchors.fill: parent
                                visible: stage.cosmetic === "shadow_twin"
                                source: pane.live.fleshCopyUrl || ""
                                fleshLeft: fleshArt.x
                                fleshTop: fleshArt.y
                                fleshWidth: fleshArt.width
                                fleshHeight: fleshArt.height
                            }
                            Item {
                                id: smokeField
                                visible: stage.cosmetic === "smoke"
                                anchors.fill: parent
                                readonly property real fleshLeft: fleshArt.x + (fleshArt.width - fleshArt.paintedWidth) / 2
                                readonly property real fleshTop: fleshArt.y + (fleshArt.height - fleshArt.paintedHeight) / 2
                                onVisibleChanged: {
                                    if (!visible) for (let i = 0; i < smokePuffs.count; ++i) {
                                        const puff = smokePuffs.itemAt(i)
                                        if (puff) puff.life = 1
                                    }
                                }
                                Repeater {
                                    id: smokePuffs
                                    model: 7
                                    delegate: Image {
                                        id: puff
                                        readonly property int slot: index
                                        property real life: 1
                                        property real startX: 0
                                        property real startY: 0
                                        property real drift: 0
                                        readonly property int frame: Math.min(5, Math.floor(life * 6))
                                        source: "../assets/skins/smoke-puff-" + frame + ".png"
                                        width: 24 * stage.commonPixelScale
                                        height: width
                                        x: Math.round(startX + drift * life - width / 2)
                                        y: Math.round(startY - life * fleshArt.paintedHeight * 0.24 - height / 2)
                                        opacity: life < 0.16 ? life / 0.16 * 0.42 : (1 - life) / 0.84 * 0.42
                                        smooth: false
                                        mipmap: false
                                        function launch() {
                                            const left = slot % 2 === 0
                                            startX = Math.round(smokeField.fleshLeft + fleshArt.paintedWidth
                                                * (left ? 0.08 : 0.88) + (Math.random() - 0.5) * 12)
                                            startY = Math.round(smokeField.fleshTop + fleshArt.paintedHeight
                                                * (0.40 + Math.random() * 0.28))
                                            drift = (left ? -1 : 1) * (8 + Math.random() * 14) * stage.commonPixelScale
                                            life = 0
                                        }
                                        SequentialAnimation {
                                            running: stage.cosmetic === "smoke"
                                            loops: Animation.Infinite
                                            PauseAnimation { duration: puff.slot * 250 }
                                            ScriptAction { script: puff.launch() }
                                            NumberAnimation { target: puff; property: "life"; from: 0; to: 1; duration: 2800 + puff.slot * 100 }
                                        }
                                    }
                                }
                            }
                            SkyArt {
                                id: skyArt
                                objectName: "skyArt"
                                anchors.fill: parent
                                visible: stage.cosmetic === "sky"
                                pixelScale: stage.commonPixelScale
                                fleshLeft: fleshArt.x + (fleshArt.width - fleshArt.paintedWidth) / 2
                                fleshTop: fleshArt.y + (fleshArt.height - fleshArt.paintedHeight) / 2 - stage.skyLift
                                fleshWidth: fleshArt.paintedWidth
                                fleshHeight: fleshArt.paintedHeight
                            }
                            Image {
                                visible: stage.cosmetic === "violet"
                                source: fleshArt.source
                                x: fleshArt.x; y: fleshArt.y
                                width: fleshArt.width; height: fleshArt.height
                                fillMode: Image.PreserveAspectFit
                                smooth: false
                                layer.enabled: visible
                                layer.effect: ShaderEffect {
                                    fragmentShader: "shaders/confusion-glow.frag.qsb"
                                    property var source
                                    property real phase: stage.confusionPhase
                                    property real texelX: 1 / Math.max(1, fleshArt.width)
                                    property real texelY: 1 / Math.max(1, fleshArt.height)
                                }
                            }
                            CometArt {
                                id: cometArt
                                objectName: "cometArt"
                                anchors.fill: parent
                                visible: stage.cosmetic === "comet"
                                fleshLeft: fleshArt.x + (fleshArt.width - fleshArt.paintedWidth) / 2
                                fleshTop: fleshArt.y + (fleshArt.height - fleshArt.paintedHeight) / 2
                                fleshWidth: fleshArt.paintedWidth
                                fleshHeight: fleshArt.paintedHeight
                            }
                            Image {
                                visible: stage.cosmetic === "comet"
                                source: fleshArt.source
                                x: fleshArt.x; y: fleshArt.y
                                width: fleshArt.width; height: fleshArt.height
                                fillMode: Image.PreserveAspectFit
                                smooth: false
                                layer.enabled: visible
                                layer.effect: ShaderEffect {
                                    fragmentShader: "shaders/comet-glow.frag.qsb"
                                    property var source
                                    property real strength: 0.45 + cometArt.glowLevel * 0.95
                                    property real outline: cometArt.glowLevel * 0.65
                                    property real texelX: 1 / Math.max(1, fleshArt.width)
                                    property real texelY: 1 / Math.max(1, fleshArt.height)
                                }
                            }
                            Image {
                                visible: stage.cosmetic === "rose"
                                source: "../assets/skins/rose-vine-back.png"
                                x: roseArt.x; y: roseArt.y
                                width: roseArt.width; height: roseArt.height
                                smooth: false
                            }
                            AuroraRibbonArt {
                                id: aurora
                                anchors.fill: parent
                                visible: stage.cosmetic === "aurora_ribbon"
                                flesh: fleshArt
                                frontLayer: auroraFront
                                poolLayer: auroraPool
                                fill: visible ? Number(stage.streak.fill || 0) : 0
                            }
                            NeonOutlineArt {
                                id:neonOutline
                                anchors.fill:parent
                                visible:stage.cosmetic === "neon_outline"
                                flesh:fleshArt
                            }
                            Image {
                                id: fleshArt
                                objectName: "fleshArt"
                                Image {
                                    x: (parent.width - parent.paintedWidth) / 2
                                    y: (parent.height - parent.paintedHeight) / 2
                                    width: parent.paintedWidth
                                    height: parent.paintedHeight
                                    source: (pane.live.progression || {}).skinOverlay || ""
                                    fillMode: Image.Stretch
                                    smooth: false
                                }
                                visible: stage.cosmetic !== "clockwork" && stage.cosmetic !== "cat"
                                    && stage.cosmetic !== "event_horizon" && stage.cosmetic !== "tidal_planet"
                                    && stage.cosmetic !== "snow_globe"
                                    && stage.cosmetic !== "lava_lamp"
                                    && stage.cosmetic !== "marionette"
                                width: stage.cosmetic === "pixel_tv" ? tvBody.width * 0.9
                                    : stage.cosmetic === "fishbowl" ? bowl.width * 0.56
                                    : stage.cosmetic === "slot_machine" ? 96 * slotMachineArt.pixelScale
                                    : stage.cosmetic === "blacksmith" ? 70 * blacksmithArt.pixelScale
                                    : stage.cosmetic === "reflection" ? mirrorFrame.fleshSize
                                    : stage.cosmetic === "rose" ? 120 * stage.rosePixelScale
                                    : stage.cosmetic === "sandcastle" ? 104 * sandcastle.pixelSize
                                    : stage.cosmetic === "shadow_twin" ? Math.min(parent.width, parent.height) * 0.84
                                    : stage.cosmetic === "temporal_echo" ? Math.min(parent.width, parent.height) * 0.81
                                    : stage.cosmetic === "stained_glass" ? Math.min(parent.width, parent.height) * 0.89
                                    : stage.cosmetic === "sundial" ? sundial.width * 0.62
                                    : stage.cosmetic === "prism_rain" ? Math.min(parent.width, parent.height) * 0.76
                                    : stage.cosmetic === "lightbox" ? 88 * lightbox.pixelSize
                                    : stage.cosmetic === "firefly_jar" ? 66 * fireflyJar.pixelSize
                                    : stage.cosmetic === "opal" ? Math.min(parent.width, parent.height) * 0.90
                                    : stage.cosmetic === "aurora_ribbon" ? Math.min(parent.width, parent.height) * 0.70
                                    : stage.cosmetic === "deep_blue" ? Math.min(parent.width, parent.height) * 0.84
                                    : stage.cosmetic === "neon_outline" ? Math.min(parent.width,parent.height)*.82
                                    : stage.cosmetic === "star_map" ? 112 * Math.max(1,Math.floor(Math.min(parent.width,parent.height)/124))
                                    : stage.cosmetic === "sunlight" && stage.height < 180
                                        ? Math.max(1, Math.min(parent.width, parent.height) - 22)
                                    : stage.cosmetic === "zero_gravity" ? Math.max(1,
                                        Math.min(parent.width, parent.height - zeroGravity.topMargin) * 0.70)
                                    : stage.cosmetic === "liquid_metal" ? Math.max(1,
                                        Math.min(parent.width, parent.height) - (parent.height < 180 ? 14 : 0))
                                    : stage.cosmetic === "comet" ? parent.width * 0.62 : parent.width
                                height: stage.cosmetic === "pixel_tv" ? tvBody.height * 0.8
                                    : stage.cosmetic === "fishbowl" ? bowl.height * 0.5
                                    : stage.cosmetic === "slot_machine" ? 104 * slotMachineArt.pixelScale
                                    : stage.cosmetic === "blacksmith" ? 55 * blacksmithArt.pixelScale
                                    : stage.cosmetic === "reflection" ? mirrorFrame.fleshSize
                                    : stage.cosmetic === "rose" || stage.cosmetic === "liquid_metal"
                                        || stage.cosmetic === "shadow_twin" || stage.cosmetic === "zero_gravity"
                                        || stage.cosmetic === "sandcastle" || stage.cosmetic === "temporal_echo"
                                        || stage.cosmetic === "stained_glass" || stage.cosmetic === "sundial"
                                        || stage.cosmetic === "prism_rain"
                                        || stage.cosmetic === "lightbox"
                                        || stage.cosmetic === "firefly_jar"
                                        || stage.cosmetic === "opal"
                                        || stage.cosmetic === "star_map"
                                        || stage.cosmetic === "aurora_ribbon"
                                        || stage.cosmetic === "deep_blue"
                                        || stage.cosmetic === "neon_outline"
                                        || (stage.cosmetic === "sunlight" && stage.height < 180) ? width
                                    : stage.cosmetic === "comet" ? parent.height * 0.72 : parent.height
                                x: stage.cosmetic === "pixel_tv" ? tvBody.x + (tvBody.width - width) / 2
                                    : stage.cosmetic === "slot_machine" ? slotMachineArt.x + 12 * slotMachineArt.pixelScale
                                    : stage.cosmetic === "blacksmith" ? blacksmithArt.x + 37 * blacksmithArt.pixelScale
                                    : stage.cosmetic === "sandcastle" ? sandcastle.x + 14 * sandcastle.pixelSize
                                    : (stage.cosmetic === "comet" ? parent.width * 0.35
                                        : (parent.width - width) / 2)
                                        + (stage.cosmetic === "fishbowl" ? fishMotion.offsetX
                                            : stage.cosmetic === "zero_gravity" ? zeroGravity.offsetX
                                            : stage.cosmetic === "comet" ? cometArt.kickX : 0)
                                y: stage.cosmetic === "reflection" ? mirrorFrame.y + mirrorFrame.height + mirrorFrame.gap
                                    : stage.cosmetic === "firefly_jar" ? fireflyJar.y + 47 * fireflyJar.pixelSize
                                    : stage.cosmetic === "lightbox" ? lightbox.y + 15 * lightbox.pixelSize
                                    : stage.cosmetic === "prism_rain" ? (parent.height - height) / 2 + prismRain.extent * 0.065
                                    : stage.cosmetic === "sundial" ? sundial.y + sundial.height * 0.42 - height / 2
                                    : stage.cosmetic === "rose" && parent.height < 180
                                        ? Math.round((parent.height - height) / 2) + Math.min(8, Math.max(0, (parent.height - height) / 2))
                                    : stage.cosmetic === "pixel_tv" ? tvBody.y + (tvBody.height - height) / 2
                                    : stage.cosmetic === "slot_machine" ? slotMachineArt.y + 10 * slotMachineArt.pixelScale
                                    : stage.cosmetic === "blacksmith" ? blacksmithArt.y + 5 * blacksmithArt.pixelScale
                                    : stage.cosmetic === "zero_gravity" ? zeroGravity.centerY - height / 2 + zeroGravity.offsetY
                                    : stage.cosmetic === "sandcastle" ? sandcastle.y + 5 * sandcastle.pixelSize
                                    : (parent.height - height) / 2 + (stage.cosmetic === "fishbowl" ? fishMotion.offsetY
                                        : stage.cosmetic === "comet" ? cometArt.kickY + cometArt.ambientY
                                        : stage.cosmetic === "aurora_ribbon" ? aurora.floatOffset
                                        : stage.cosmetic === "deep_blue" ? deepBlue.floatOffset : 0)
                                        + (stage.cosmetic === "sky" ? stage.skyLift : 0)
                                rotation: stage.cosmetic === "fishbowl" ? fishMotion.floatAngle
                                    : stage.cosmetic === "zero_gravity" ? zeroGravity.angle : 0
                                source: pane.live.imageUrl || "../flesh.png"
                                fillMode: Image.PreserveAspectFit
                                smooth: stage.cosmetic === "gold" || stage.cosmetic === "reflection"
                                    || stage.cosmetic === "rose" || stage.cosmetic === "liquid_metal"
                                    || stage.cosmetic === "shadow_twin" || stage.cosmetic === "zero_gravity"
                                    || stage.cosmetic === "sandcastle" || stage.cosmetic === "temporal_echo"
                                    || stage.cosmetic === "sunlight" || stage.cosmetic === "stained_glass"
                                    || stage.cosmetic === "sundial"
                                    || stage.cosmetic === "prism_rain"
                                    || stage.cosmetic === "lightbox"
                                    || stage.cosmetic === "firefly_jar"
                                    || stage.cosmetic === "opal"
                                    || stage.cosmetic === "star_map"
                                    || stage.cosmetic === "aurora_ribbon"
                                    || stage.cosmetic === "deep_blue"
                                mipmap: stage.cosmetic === "gold"
                                layer.enabled: stage.cosmetic === "violet" || stage.cosmetic === "liquid_metal"
                                    || stage.cosmetic === "sunlight" || stage.cosmetic === "stained_glass"
                                    || stage.cosmetic === "sundial"
                                    || stage.cosmetic === "prism_rain"
                                    || stage.cosmetic === "lightbox"
                                    || stage.cosmetic === "firefly_jar"
                                    || stage.cosmetic === "opal"
                                    || stage.cosmetic === "star_map"
                                    || stage.cosmetic === "aurora_ribbon"
                                    || stage.cosmetic === "deep_blue"
                                layer.effect: stage.cosmetic === "stained_glass" ? stainedGlassEffect
                                    : stage.cosmetic === "deep_blue" ? deepBlueEffect
                                    : stage.cosmetic === "aurora_ribbon" ? auroraEffect
                                    : stage.cosmetic === "star_map" ? starMapEffect
                                    : stage.cosmetic === "opal" ? opalEffect
                                    : stage.cosmetic === "firefly_jar" ? fireflyJarEffect
                                    : stage.cosmetic === "lightbox" ? lightboxEffect
                                    : stage.cosmetic === "prism_rain" ? prismRainEffect
                                    : stage.cosmetic === "sundial" ? sundialEffect
                                    : stage.cosmetic === "sunlight" ? sunlightEffect
                                    : stage.cosmetic === "liquid_metal" ? metalEffect : confusionEffect
                                SequentialAnimation on opacity {
                                    running: stage.cosmetic === "hologram"
                                    loops: Animation.Infinite
                                    NumberAnimation { from: 1; to: 0.58; duration: 70 }
                                    NumberAnimation { from: 0.58; to: 1; duration: 160 }
                                    PauseAnimation { duration: 560 }
                                }
                            }
                            Component {
                                id: deepBlueEffect
                                ShaderEffect {
                                    fragmentShader: "shaders/deep-blue-flesh.frag.qsb"
                                    property var source
                                    property var caustics: deepBlue.caustics
                                    property var normals: deepBlue.normals
                                    property real time: deepBlue.time
                                    property real flow: deepBlue.flow
                                    property real energy: deepBlue.energy
                                    property vector3d ripple0: deepBlue.ripple0
                                    property vector3d ripple1: deepBlue.ripple1
                                    property vector3d ripple2: deepBlue.ripple2
                                    property vector3d ripple3: deepBlue.ripple3
                                }
                            }
                            Component {
                                id: auroraEffect
                                ShaderEffect {
                                    fragmentShader: "shaders/aurora-flesh.frag.qsb"
                                    property var source
                                    property vector2d bodyOrigin: Qt.vector2d(fleshArt.x, fleshArt.y)
                                    property vector2d bodySize: Qt.vector2d(fleshArt.width, fleshArt.height)
                                    property vector2d center: aurora.center
                                    property real extent: aurora.extent
                                    property real time: aurora.time
                                    property real flow: aurora.flow
                                    property real energy: aurora.energy
                                    property vector3d stroke0: aurora.stroke0
                                    property vector3d stroke1: aurora.stroke1
                                    property vector3d stroke2: aurora.stroke2
                                    property vector3d stroke3: aurora.stroke3
                                }
                            }
                            Item {
                                id: auroraFront
                                anchors.fill: parent
                            }
                            Component {
                                id: confusionEffect
                                ShaderEffect {
                                    fragmentShader: "shaders/confusion-flesh.frag.qsb"
                                    property var source
                                    property real phase: stage.confusionPhase
                                }
                            }
                            Component {
                                id: metalEffect
                                ShaderEffect {
                                    fragmentShader: "shaders/liquid-metal.frag.qsb"
                                    property var source
                                    property vector3d ripple0: liquidMetalMotion.ripple0
                                    property vector3d ripple1: liquidMetalMotion.ripple1
                                    property vector3d ripple2: liquidMetalMotion.ripple2
                                }
                            }
                            Component {
                                id: sunlightEffect
                                ShaderEffect {
                                    fragmentShader: "shaders/sunlight-flesh.frag.qsb"
                                    property var source
                                    property vector2d aim: sunlight.aim
                                    property real aspect: sunlight.aspect
                                    property real flash: sunlight.intensity
                                    property real sweep: sunlight.sweep
                                    property real sunbreak: sunlight.sunbreak
                                    property real charge: sunlight.charge
                                    property vector2d artOrigin: Qt.vector2d(fleshArt.x / Math.max(1, stage.width),
                                                                             fleshArt.y / Math.max(1, stage.height))
                                    property vector2d artSize: Qt.vector2d(fleshArt.width / Math.max(1, stage.width),
                                                                           fleshArt.height / Math.max(1, stage.height))
                                    property vector2d scaleFactors: Qt.vector2d(fleshImpulse.scale * compression.xScale,
                                                                                fleshImpulse.scale * compression.yScale)
                                    property real angle: fleshImpulse.rotation * Math.PI / 180
                                }
                            }
                            Component {
                                id: starMapEffect
                                ShaderEffect {
                                    fragmentShader: "shaders/star-map.frag.qsb"
                                    property var source
                                    property var stars: starMap.stars
                                    property var halo: starMap.halo
                                    property var traits: starMap.traits
                                    property real time: starMap.time
                                    property real glow: starMap.glow
                                    property vector3d stroke0: starMap.stroke0
                                    property vector3d stroke1: starMap.stroke1
                                    property vector3d stroke2: starMap.stroke2
                                    property vector3d stroke3: starMap.stroke3
                                }
                            }
                            Component {
                                id: opalEffect
                                ShaderEffect {
                                    fragmentShader: "shaders/opal.frag.qsb"
                                    property var source
                                    property var normals: opal.normals
                                    property var fire: opal.fire
                                    property vector2d view: opal.view
                                    property real angle: fleshImpulse.rotation * Math.PI / 180
                                    property vector3d stroke0: opal.stroke0
                                    property vector3d stroke1: opal.stroke1
                                    property vector3d stroke2: opal.stroke2
                                    property vector3d stroke3: opal.stroke3
                                }
                            }
                            Component {
                                id: fireflyJarEffect
                                ShaderEffect {
                                    fragmentShader: "shaders/firefly-jar-flesh.frag.qsb"
                                    property var source
                                    property vector3d lamp0: fireflyJar.lamp0
                                    property vector3d lamp1: fireflyJar.lamp1
                                    property vector3d lamp2: fireflyJar.lamp2
                                    property vector3d lamp3: fireflyJar.lamp3
                                    property vector3d lamp4: fireflyJar.lamp4
                                    property vector3d lamp5: fireflyJar.lamp5
                                    property vector3d lamp6: fireflyJar.lamp6
                                    property vector3d lamp7: fireflyJar.lamp7
                                    property vector2d bodyOrigin: Qt.vector2d((fleshArt.x - fireflyJar.x) / fireflyJar.pixelSize,
                                                                             (fleshArt.y - fireflyJar.y) / fireflyJar.pixelSize)
                                    property vector2d bodySize: Qt.vector2d(fleshArt.width / fireflyJar.pixelSize,
                                                                           fleshArt.height / fireflyJar.pixelSize)
                                    property vector2d bodySquish: Qt.vector2d(fleshImpulse.scale * compression.xScale,
                                                                                fleshImpulse.scale * compression.yScale)
                                    property real bodyAngle: fleshImpulse.rotation * Math.PI / 180
                                }
                            }
                            Component {
                                id: lightboxEffect
                                ShaderEffect {
                                    fragmentShader: "shaders/lightbox-flesh.frag.qsb"
                                    property var source
                                    property real exposure: lightbox.exposure
                                    property real scan: lightbox.scan
                                    property vector2d hit: lightbox.hit
                                }
                            }
                            Component {
                                id: prismRainEffect
                                ShaderEffect {
                                    fragmentShader: "shaders/prism-rain-flesh.frag.qsb"
                                    property var source
                                    property vector2d viewport: prismRain.viewport
                                    property vector2d emitter: prismRain.emitter
                                    property real extent: prismRain.extent
                                    property real energy: prismRain.energy
                                    property real sweep: prismRain.sweep
                                    property vector2d bodyOrigin: Qt.vector2d(fleshArt.x, fleshArt.y)
                                    property vector2d bodySize: Qt.vector2d(fleshArt.width, fleshArt.height)
                                    property vector2d bodySquish: Qt.vector2d(fleshImpulse.scale * compression.xScale,
                                                                                fleshImpulse.scale * compression.yScale)
                                    property real bodyAngle: fleshImpulse.rotation * Math.PI / 180
                                }
                            }
                            Component {
                                id: sundialEffect
                                ShaderEffect {
                                    fragmentShader: "shaders/sundial-flesh.frag.qsb"
                                    property var source
                                    property real sunAngle: sundial.sunAngle
                                }
                            }
                            Component {
                                id: stainedGlassEffect
                                ShaderEffect {
                                    fragmentShader: "shaders/stained-glass.frag.qsb"
                                    property var source
                                    property var panes: stainedGlass.paneMap
                                    property vector3d pulse0: stainedGlass.pulse0
                                    property vector3d pulse1: stainedGlass.pulse1
                                    property vector3d pulse2: stainedGlass.pulse2
                                }
                            }
                            LiquidMetalMotion {
                                id: liquidMetalMotion
                                visible: stage.cosmetic === "liquid_metal"
                            }
                            RoseArt {
                                id: roseArt
                                visible: stage.cosmetic === "rose"
                                x: fleshArt.x; y: fleshArt.y
                                width: 120 * pixelSize
                                height: width
                                pixelSize: stage.rosePixelScale
                                particleLayer: rosePetalLayer
                            }
                            Image {
                                id: catArt
                                objectName: "catArt"
                                visible: stage.cosmetic === "cat"
                                anchors.fill: parent
                                source: game.catMeowPlaying ? "../assets/skins/cat-open.png"
                                    : "../assets/skins/cat-closed.png"
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                mipmap: true
                            }
                            Image {
                                id: mintPlant
                                objectName: "mintPlant"
                                visible: stage.cosmetic === "mint"
                                source: "../assets/skins/mint-plant.png"
                                width: 56 * stage.commonPixelScale
                                height: 58 * stage.commonPixelScale
                                x: Math.round(fleshArt.x + (fleshArt.width - fleshArt.paintedWidth) / 2
                                    + fleshArt.paintedWidth * 0.56 - width / 2)
                                y: Math.round(Math.max(4, fleshArt.y + (fleshArt.height - fleshArt.paintedHeight) / 2
                                    + fleshArt.paintedHeight * 0.24 - height))
                                transform: Rotation {
                                    origin.x: mintPlant.width / 2
                                    origin.y: mintPlant.height
                                    angle: stage.mintShakeAngle
                                }
                                smooth: false
                                mipmap: false
                            }
                            ClockworkArt {
                                id: clockworkArt
                                objectName: "clockworkArt"
                                visible: stage.cosmetic === "clockwork"
                                width: stage.clockworkSize
                                height: width
                                x: (parent.width - width) / 2
                                y: (parent.height - height) / 2
                            }
                            Image {
                                id: magnetArt
                                visible: stage.cosmetic === "magnet"
                                source: "../assets/skins/magnet.png"
                                x: fleshArt.x + (fleshArt.width - fleshArt.paintedWidth) / 2 - fleshArt.paintedWidth * 0.01 + stage.magnetPull * 9
                                y: fleshArt.y + (fleshArt.height - fleshArt.paintedHeight) / 2 + fleshArt.paintedHeight * 0.63 - stage.magnetPull * 10
                                width: fleshArt.paintedWidth * 0.59
                                height: width
                                rotation: stage.magnetSwing
                                smooth: false
                                mipmap: false
                                fillMode: Image.PreserveAspectFit
                            }
                            Image {
                                visible: stage.cosmetic === "top_hat"
                                source: "image://skins/accessory/top_hat"
                                x: (parent.width - fleshArt.paintedWidth) / 2 + fleshArt.paintedWidth * 0.31
                                y: (parent.height - fleshArt.paintedHeight) / 2 - fleshArt.paintedHeight * 0.07
                                width: fleshArt.paintedWidth * 0.38
                                height: width
                                smooth: false
                                fillMode: Image.PreserveAspectFit
                            }
                            Image {
                                id: commonAccessory
                                visible: ["paper_crown", "price_tag", "sticky_note", "button_badge"].indexOf(stage.cosmetic) >= 0
                                source: stage.cosmetic === "paper_crown" ? "../assets/skins/paper-crown.png"
                                    : stage.cosmetic === "price_tag" ? "../assets/skins/price-tag.png"
                                    : stage.cosmetic === "sticky_note" ? "../assets/skins/sticky-note.png"
                                    : "../assets/skins/button-badge.png"
                                width: (stage.cosmetic === "paper_crown" ? 40
                                    : stage.cosmetic === "price_tag" ? 32
                                    : stage.cosmetic === "sticky_note" ? 42 : 36) * stage.commonPixelScale
                                height: (stage.cosmetic === "paper_crown" ? 32
                                    : stage.cosmetic === "price_tag" ? 42
                                    : stage.cosmetic === "sticky_note" ? 36 : 36) * stage.commonPixelScale
                                x: Math.round(fleshArt.x + (fleshArt.width - fleshArt.paintedWidth) / 2
                                    + fleshArt.paintedWidth * (stage.cosmetic === "paper_crown" ? 0.55
                                    : stage.cosmetic === "price_tag" ? 0.18
                                    : stage.cosmetic === "sticky_note" ? 0.50 : 0.61) - width / 2)
                                y: Math.round(fleshArt.y + (fleshArt.height - fleshArt.paintedHeight) / 2
                                    + fleshArt.paintedHeight * (stage.cosmetic === "paper_crown" ? 0.01
                                    : stage.cosmetic === "price_tag" ? 0.42
                                    : stage.cosmetic === "sticky_note" ? 0.22 : 0.52))
                                transform: Rotation {
                                    origin.x: 8 * stage.commonPixelScale
                                    origin.y: 12 * stage.commonPixelScale
                                    angle: stage.cosmetic === "price_tag" ? stage.tagAngle : 0
                                }
                                smooth: false
                                mipmap: false
                                fillMode: Image.PreserveAspectFit
                            }
                            UncommonAccessories {
                                id: uncommonArt
                                objectName: "uncommonArt"
                                anchors.fill: parent
                                cosmetic: stage.cosmetic
                                pixelScale: stage.commonPixelScale
                                fleshLeft: fleshArt.x + (fleshArt.width - fleshArt.paintedWidth) / 2
                                fleshTop: fleshArt.y + (fleshArt.height - fleshArt.paintedHeight) / 2
                                fleshWidth: fleshArt.paintedWidth
                                fleshHeight: fleshArt.paintedHeight
                            }
                            TicketRollArt {
                                id: ticketRollArt
                                objectName: "ticketRollArt"
                                anchors.fill: parent
                                visible: stage.cosmetic === "ticket_roll"
                                pixelScale: stage.commonPixelScale
                                fleshLeft: fleshArt.x + (fleshArt.width - fleshArt.paintedWidth) / 2
                                fleshTop: fleshArt.y + (fleshArt.height - fleshArt.paintedHeight) / 2
                                fleshWidth: fleshArt.paintedWidth
                                fleshHeight: fleshArt.paintedHeight
                            }
                            PinballArt {
                                id: pinballArt
                                objectName: "pinballArt"
                                anchors.fill: parent
                                visible: stage.cosmetic === "pinball"
                                pixelScale: stage.commonPixelScale
                                fleshLeft: fleshArt.x + (fleshArt.width - fleshArt.paintedWidth) / 2
                                fleshTop: fleshArt.y + (fleshArt.height - fleshArt.paintedHeight) / 2
                                fleshWidth: fleshArt.paintedWidth
                                fleshHeight: fleshArt.paintedHeight
                            }
                            SequentialAnimation {
                                id: compressionBounce
                                ParallelAnimation {
                                    NumberAnimation { target: compression; property: "xScale"; from: 1; to: stage.cosmetic === "wobble" ? 1.16 : 1.035; duration: stage.cosmetic === "wobble" ? 90 : 65; easing.type: Easing.OutQuad }
                                    NumberAnimation { target: compression; property: "yScale"; from: 1; to: stage.cosmetic === "wobble" ? 0.84 : 0.965; duration: stage.cosmetic === "wobble" ? 90 : 65; easing.type: Easing.OutQuad }
                                }
                                ParallelAnimation {
                                    NumberAnimation { target: compression; property: "xScale"; to: stage.cosmetic === "wobble" ? 0.89 : 0.99; duration: stage.cosmetic === "wobble" ? 150 : 95; easing.type: Easing.OutCubic }
                                    NumberAnimation { target: compression; property: "yScale"; to: stage.cosmetic === "wobble" ? 1.12 : 1.012; duration: stage.cosmetic === "wobble" ? 150 : 95; easing.type: Easing.OutCubic }
                                }
                                ParallelAnimation {
                                    NumberAnimation { target: compression; property: "xScale"; to: 1; duration: stage.cosmetic === "wobble" ? 280 : 120; easing.type: stage.cosmetic === "wobble" ? Easing.OutBack : Easing.OutQuad }
                                    NumberAnimation { target: compression; property: "yScale"; to: 1; duration: stage.cosmetic === "wobble" ? 280 : 120; easing.type: stage.cosmetic === "wobble" ? Easing.OutBack : Easing.OutQuad }
                                }
                            }
                        }
                        BlacksmithArt {
                            id: blacksmithArt
                            objectName: "blacksmithArt"
                            onImpact: compressionBounce.restart()
                            visible: stage.cosmetic === "blacksmith"
                            pixelScale: Math.max(1, Math.floor(Math.min(parent.width / 120, parent.height / 140)))
                            width: 120 * pixelScale
                            height: 140 * pixelScale
                            x: Math.round((parent.width - width) / 2)
                            y: Math.round(parent.height / 2 - 65 * pixelScale)
                        }
                        ThunderheadArt {
                            id: thunderheadArt
                            objectName: "thunderheadArt"
                            anchors.fill: parent
                            visible: stage.cosmetic === "thunderhead"
                            pixelScale: stage.commonPixelScale
                            fleshLeft: fleshArt.x + (fleshArt.width - fleshArt.paintedWidth) / 2
                            fleshTop: fleshArt.y + (fleshArt.height - fleshArt.paintedHeight) / 2
                            fleshWidth: fleshArt.paintedWidth
                            fleshHeight: fleshArt.paintedHeight
                        }
                    }
                    Image {
                        visible: stage.cosmetic === "pixel_tv"
                        source: "../assets/skins/pixel-tv-front.png"
                        width: tvBody.width; height: tvBody.height
                        x: tvBody.x; y: tvBody.y
                        smooth: false
                        mipmap: false
                    }
                    Image {
                        visible: stage.cosmetic === "fishbowl"
                        source: "../assets/skins/fishbowl-frame.png"
                        width: bowl.width; height: bowl.height
                        x: bowl.x; y: bowl.y
                        smooth: false
                        mipmap: false
                    }
                }
            }
            ZeroGravityMotion {
                id: zeroGravity
                anchors.fill: parent
                visible: stage.cosmetic === "zero_gravity"
                bodySize: fleshArt.width
                z: 8
            }
            PixelCracks {
                id: glassCracks
                objectName: "glassCracks"
                anchors.fill: parent
                visible: stage.cosmetic === "reflection"
                screenX: mirrorFrame.x + mirrorGlass.x
                screenY: mirrorFrame.y + mirrorGlass.y
                screenWidth: mirrorGlass.width
                screenHeight: mirrorGlass.height
                pixelSize: mirrorFrame.pixel
                baseRayLength: 8
                crackColor: "#e5fbff"
                edgeColor: "#abc8d5"
                frameBranchDistance: 12
                z: 20
            }
            PixelCracks {
                id: tvCracks
                objectName: "tvCracks"
                anchors.fill: parent
                visible: stage.cosmetic === "pixel_tv"
                screenX: tvBody.x + tvBody.width * 20 / 120
                screenY: tvBody.y + tvBody.height * 24 / 94
                screenWidth: tvBody.width * 80 / 120
                screenHeight: tvBody.height * 44 / 94
                pixelSize: Math.max(4, Math.round(tvBody.width / 60))
                z: 20
            }
            Repeater {
                id: mintLeaves
                model: 24
                delegate: Image {
                    id: looseLeaf
                    objectName: "mintLeafParticle"
                    visible: stage.cosmetic === "mint"
                    source: "../assets/skins/mint-leaf.png"
                    width: 14 * stage.commonPixelScale
                    height: 13 * stage.commonPixelScale
                    smooth: false
                    mipmap: false
                    z: 11
                    property real life: 0
                    property real startX: 0
                    property real startY: 0
                    property real drift: 0
                    property real fall: 0
                    property real spin: 0
                    x: Math.round(startX + drift * life + Math.sin(life * 10) * 6 * stage.commonPixelScale - width / 2)
                    y: Math.round(startY + fall * life * life - height / 2)
                    rotation: spin * life
                    opacity: life <= 0 ? 0 : Math.min(1, life * 12) * (1 - life)
                    function launch(atX, atY, side) {
                        motion.stop()
                        startX = atX
                        startY = atY
                        drift = side * (20 + Math.random() * 20) * stage.commonPixelScale
                        fall = (35 + Math.random() * 28) * stage.commonPixelScale
                        spin = side * (35 + Math.random() * 55)
                        life = 0
                        motion.start()
                    }
                    NumberAnimation {
                        id: motion
                        target: looseLeaf
                        property: "life"
                        from: 0; to: 1
                        duration: 2900
                        easing.type: Easing.Linear
                    }
                }
            }
            Repeater {
                id: flecks
                model: 24
                delegate: Rectangle {
                    id: fleck
                    objectName: "clickParticle"
                    property real startX: 0
                    property real startY: 0
                    property real endX: 0
                    property real endY: 0
                    width: stage.cosmetic === "opal" || stage.cosmetic === "star_map" || stage.cosmetic === "aurora_ribbon"
                        || stage.cosmetic === "neon_outline"
                        ? (index % 3 === 0 ? 3 : 2) : index % 3 === 0 ? 6 : 4
                    height: width
                    color: stage.cosmetic === "magnet" ? (index % 2 === 0 ? "#42d4ef" : "#e5faff")
                        : stage.cosmetic === "clockwork" ? (index % 2 === 0 ? "#ddbd77" : "#899cb8")
                        : stage.cosmetic === "gold" ? (index % 2 === 0 ? "#ffc25c" : "#fff2b4")
                        : stage.cosmetic === "sandcastle" ? (index % 2 === 0 ? "#bd8c4a" : "#f0cb8a")
                        : stage.cosmetic === "liquid_metal" ? (index % 2 === 0 ? "#718b9a" : "#dcecf1")
                        : stage.cosmetic === "opal" ? ["#eaf0de", "#a3dcd9", "#e9b9cd", "#ecd7a4"][index % 4]
                        : stage.cosmetic === "star_map" ? (index % 4 === 0 ? "#f0d69b" : "#b5e7f0")
                        : stage.cosmetic === "neon_outline" ? (index%2===0 ? "#8cecf1" : "#ed85b8")
                        : stage.cosmetic === "aurora_ribbon" ? ["#82f1ca", "#6dd9ef", "#6d8edb"][index % 3]
                        : stage.cosmetic === "comet" ? (index % 2 === 0 ? "#d7b1e0" : "#fff0c1")
                        : stage.cosmetic === "bitcrush" ? (index % 2 === 0 ? "#8ee7eb" : "#f8d477")
                        : index % 3 === 0 ? "#e95b68" : index % 3 === 1 ? "#a32c42" : "#f39292"
                    opacity: 0
                    function launch(x, y, dx, dy) {
                        motion.stop()
                        startX = x
                        startY = y
                        endX = x + dx
                        endY = y + dy
                        fleck.x = x
                        fleck.y = y
                        motion.start()
                    }
                    ParallelAnimation {
                        id: motion
                        NumberAnimation { target: fleck; property: "x"; from: fleck.startX; to: fleck.endX; duration: 340; easing.type: Easing.OutQuad }
                        NumberAnimation { target: fleck; property: "y"; from: fleck.startY; to: fleck.endY; duration: 340; easing.type: Easing.OutQuad }
                        NumberAnimation { target: fleck; property: "opacity"; from: 1; to: 0; duration: 340 }
                    }
                }
            }
            Repeater {
                id: droplets
                model: 24
                delegate: Rectangle {
                    id: droplet
                    objectName: "streakDroplet"
                    width: stellar || auroral ? (index % 3 === 0 ? 2 : 1) : index % 3 === 0 ? 5 : 3
                    height: stellar || sandy ? width : index % 3 === 0 ? 7 : 5
                    readonly property bool mercury: stage.cosmetic === "liquid_metal"
                    readonly property bool sandy: stage.cosmetic === "sandcastle"
                    readonly property bool pearly: stage.cosmetic === "opal"
                    readonly property bool stellar: stage.cosmetic === "star_map"
                    readonly property bool auroral: stage.cosmetic === "aurora_ribbon"
                    property bool pearlLanding: false
                    color: mercury ? "#839aa7" : sandy ? (index % 2 === 0 ? "#ebc38a" : "#af8249")
                        : pearly ? ["#e1eadc", "#a9d9d5", "#e8bbd1", "#ebd5a4"][index % 4]
                        : stellar ? (index % 4 === 0 ? "#d9c594" : "#8cbfd4")
                        : auroral ? (index % 2 === 0 ? "#78dbd4" : "#8bc8ed")
                        : index % 2 === 0 ? "#ed6880" : "#ac334d"
                    radius: mercury ? width / 2 : sandy || stellar ? 0 : 1
                    opacity: 0
                    Rectangle {
                        visible: droplet.mercury || droplet.pearly
                        x: 1; y: 1
                        width: 2; height: 2
                        color: "#f1fbff"
                        radius: 1
                    }
                    property real startY: 0
                    property real endY: 0
                    function launch(atX, atY, bottomY) {
                        motion.stop()
                        pearlLanding = pearly && index % 2 === 0
                        x = atX + (Math.random() - 0.5) * 22
                        startY = atY
                        endY = Math.max(atY + 12, bottomY)
                        y = startY
                        motion.start()
                    }
                    ParallelAnimation {
                        id: motion
                        onFinished: {
                            if (droplet.pearlLanding && droplet.pearly)
                                opalStreak.splash((droplet.x + droplet.width / 2) / Math.max(1, stage.width))
                        }
                        NumberAnimation { target: droplet; property: "y"; from: droplet.startY; to: droplet.endY; duration: 500; easing.type: Easing.InQuad }
                        SequentialAnimation {
                            NumberAnimation { target: droplet; property: "opacity"; from: 1; to: 0.85; duration: 420 }
                            NumberAnimation { target: droplet; property: "opacity"; to: 0; duration: 80 }
                        }
                    }
                }
            }
            Item {
                id: goldCoinFlights
                anchors.fill: parent
            }
            Item {
                id: rosePetalLayer
                anchors.fill: parent
                z: 11
            }
            Item {
                id: temporalEchoFlashes
                anchors.fill: parent
                z: 11
            }
            Item {
                id: sunlightSparks
                anchors.fill: parent
                z: 11
            }
            Item {
                id: prismRainFront
                anchors.fill: parent
                z: 8
            }
            Item {
                id: lightboxFront
                anchors.fill: parent
                z: 8
            }
            Item {
                id: fireflyJarFront
                anchors.fill: parent
                z: 8
            }
            Item {
                id: opalGlints
                anchors.fill: parent
                z: 8
            }
            Item {
                id: deepBlueFront
                anchors.fill: parent
                z: 8
            }
            Repeater {
                id: fallingCrates
                model: 8
                delegate: FallingCrate {
                    onLanded: function(dropId, atX, atY) {
                        stage.burst(atX, atY)
                        const info = ((game.catalog.progression || {}).crateTiers || []).find(function(item) { return item.id === tier })
                        stage.popup(atX, atY - 24, "+1 " + (info ? info.name : tier) + " Crate", "#ffffff", true)
                        game.collectCrateDrop(dropId)
                        game.playEffectSound("collect")
                    }
                }
            }
            Repeater {
                id: whiteBurst
                model: 32
                delegate: Rectangle {
                    id: spark
                    width: index % 4 === 0 ? 12 : 7
                    height: width
                    radius: width / 2
                    color: "#96ffffff"
                    opacity: 0
                    property real endX: 0
                    property real endY: 0
                    Rectangle {
                        anchors.centerIn: parent
                        width: 3; height: 3; radius: 1.5
                        color: "white"
                    }
                    function launch(atX, atY, dx, dy) {
                        flare.stop()
                        x = atX - width / 2
                        y = atY - height / 2
                        endX = x + dx
                        endY = y + dy
                        flare.start()
                    }
                    ParallelAnimation {
                        id: flare
                        NumberAnimation { target: spark; property: "x"; to: spark.endX; duration: 430; easing.type: Easing.OutCubic }
                        NumberAnimation { target: spark; property: "y"; to: spark.endY; duration: 430; easing.type: Easing.OutCubic }
                        NumberAnimation { target: spark; property: "opacity"; from: 1; to: 0; duration: 430 }
                    }
                }
            }
            Repeater {
                id: gainTexts
                model: 16
                delegate: Text {
                    id: gainText
                    z: 12
                    opacity: 0
                    font.family: pane.theme.mono
                    font.bold: true
                    font.pixelSize: 24
                    style: Text.Outline
                    styleColor: "#271217"
                    property real endY: 0
                    function launch(atX, atY, label, tint, large) {
                        floatAway.stop()
                        text = label
                        color = tint
                        font.pixelSize = large ? 27 : 24
                        x = Math.max(0, Math.min(stage.width - width, atX - width / 2))
                        y = Math.max(34, Math.min(stage.height - height - 4, atY))
                        endY = Math.max(34, y - (large ? 58 : 52))
                        opacity = 1
                        floatAway.start()
                    }
                    ParallelAnimation {
                        id: floatAway
                        NumberAnimation { target: gainText; property: "y"; to: gainText.endY; duration: 790; easing.type: Easing.OutCubic }
                        NumberAnimation { target: gainText; property: "scale"; from: 1.22; to: 1; duration: 290; easing.type: Easing.OutBack }
                        SequentialAnimation {
                            PauseAnimation { duration: 220 }
                            NumberAnimation { target: gainText; property: "opacity"; from: 1; to: 0; duration: 570 }
                        }
                    }
                }
            }
        }
    }
    Text {
        text: CurrencyFormat.format(pane.live.totalClicks, true) + " total clicks"
        color: pane.theme.muted
        font.pixelSize: 13
        horizontalAlignment: Text.AlignHCenter
        Layout.fillWidth: true
        elide: Text.ElideRight
    }
    function amount(value) {
        return CurrencyFormat.format(value, pane.preferences.show_full_numbers === true)
    }
}

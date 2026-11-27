import QtQuick

Item {
    id: art
    property int pixelScale: 2
    property real reelA: 0
    property real reelB: 2
    property real reelC: 4
    property real leverPull: 0
    property real winFlash: 0
    property bool spinning: false

    function symbolAt(reel, position) {
        return ((Math.floor(position) + reel * 2) % 5 + 5) % 5
    }

    function reelTarget(current, reel, matchSymbol) {
        let target = Math.ceil(current) + 12 + Math.floor(Math.random() * 7)
        if (matchSymbol >= 0)
            while (symbolAt(reel, target) !== matchSymbol) ++target
        return target
    }

    function react() {
        if (!leverMotion.running) leverMotion.start()
        if (spinning) return
        spinning = true
        const matchSymbol = Math.random() < 0.08 ? Math.floor(Math.random() * 5) : -1
        reelAnimA.from = reelA
        reelAnimA.to = reelTarget(reelA, 0, matchSymbol)
        reelAnimB.from = reelB
        reelAnimB.to = reelTarget(reelB, 1, matchSymbol)
        reelAnimC.from = reelC
        reelAnimC.to = reelTarget(reelC, 2, matchSymbol)
        reelAnimA.start()
        reelAnimB.start()
        reelAnimC.start()
        stopTickA.restart()
        stopTickB.restart()
        spinFinish.restart()
    }

    onVisibleChanged: {
        if (visible) return
        reelAnimA.stop()
        reelAnimB.stop()
        reelAnimC.stop()
        leverMotion.stop()
        winMotion.stop()
        stopTickA.stop()
        stopTickB.stop()
        spinFinish.stop()
        spinning = false
        reelA = Math.round(reelA)
        reelB = Math.round(reelB)
        reelC = Math.round(reelC)
        leverPull = 0
        winFlash = 0
    }
    onReelAChanged: cabinet.requestPaint()
    onReelBChanged: cabinet.requestPaint()
    onReelCChanged: cabinet.requestPaint()
    onLeverPullChanged: cabinet.requestPaint()
    onWinFlashChanged: cabinet.requestPaint()

    NumberAnimation { id: reelAnimA; target: art; property: "reelA"; duration: 620; easing.type: Easing.OutCubic }
    NumberAnimation { id: reelAnimB; target: art; property: "reelB"; duration: 860; easing.type: Easing.OutCubic }
    NumberAnimation { id: reelAnimC; target: art; property: "reelC"; duration: 1100; easing.type: Easing.OutCubic }
    SequentialAnimation {
        id: leverMotion
        NumberAnimation { target: art; property: "leverPull"; from: 0; to: 1; duration: 90; easing.type: Easing.OutCubic }
        NumberAnimation { target: art; property: "leverPull"; to: 0; duration: 230; easing.type: Easing.OutBack }
    }
    SequentialAnimation {
        id: winMotion
        NumberAnimation { target: art; property: "winFlash"; from: 0; to: 1; duration: 110 }
        NumberAnimation { target: art; property: "winFlash"; to: 0; duration: 180 }
        NumberAnimation { target: art; property: "winFlash"; to: 1; duration: 110 }
        NumberAnimation { target: art; property: "winFlash"; to: 0; duration: 240 }
    }
    Timer { id: stopTickA; interval: 620; onTriggered: game.playEffectSound("roll") }
    Timer { id: stopTickB; interval: 860; onTriggered: game.playEffectSound("roll") }
    Timer {
        id: spinFinish
        interval: 1200
        onTriggered: {
            art.spinning = false
            game.playEffectSound("roll")
            if (art.symbolAt(0, Math.round(art.reelA)) === art.symbolAt(1, Math.round(art.reelB))
                    && art.symbolAt(1, Math.round(art.reelB)) === art.symbolAt(2, Math.round(art.reelC))) {
                winMotion.restart()
                game.playEffectSound("rare")
            }
        }
    }

    Canvas {
        id: cabinet
        anchors.fill: parent
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            ctx.scale(art.pixelScale, art.pixelScale)
            ctx.imageSmoothingEnabled = false
            function block(x, y, w, h, color) {
                ctx.fillStyle = color
                ctx.fillRect(x, y, w, h)
            }
            function symbol(x, centerY, kind) {
                const y = Math.round(centerY - 6)
                if (kind === 0) {
                    block(x + 8, y, 4, 12, "#a03b50")
                    block(x + 4, y + 4, 12, 4, "#a03b50")
                } else if (kind === 1) {
                    block(x + 4, y + 2, 12, 4, "#ad7937")
                    block(x + 10, y + 6, 4, 6, "#ad7937")
                } else if (kind === 2) {
                    block(x + 6, y + 4, 8, 8, "#3b8391")
                    block(x + 8, y, 4, 12, "#3b8391")
                } else if (kind === 3) {
                    block(x + 4, y + 2, 12, 4, "#6c744b")
                    block(x + 4, y + 8, 12, 4, "#6c744b")
                } else {
                    block(x + 8, y, 4, 12, "#d7c6a7")
                    block(x + 4, y + 4, 12, 4, "#d7c6a7")
                    block(x + 6, y + 2, 8, 8, "#b6a889")
                }
            }

            // Compact cabinet with stepped, two-pixel bevels.
            block(8, 0, 104, 160, "#121518")
            block(4, 4, 112, 150, "#121518")
            block(2, 8, 116, 138, "#121518")
            block(4, 6, 112, 142, "#44484c")
            block(8, 2, 104, 152, "#44484c")
            block(10, 4, 100, 148, "#644150")
            block(10, 4, 100, 4, "#8b6672")
            block(10, 148, 100, 4, "#33282f")
            block(6, 16, 4, 120, "#73505b")
            block(110, 16, 4, 120, "#30272e")

            // The original flesh stays in this unlit viewing window.
            block(10, 10, 100, 106, "#6c4e34")
            block(12, 12, 96, 102, art.winFlash > 0.5 ? "#fff0b8" : "#d2ad69")
            block(14, 14, 92, 98, "#4d3b31")
            block(16, 16, 88, 94, "#1c2023")
            block(16, 16, 88, 2, "#0c1013")
            block(16, 18, 2, 90, "#0c1013")
            block(102, 18, 2, 90, "#7b684d")
            block(18, 108, 84, 2, "#7b684d")

            block(8, 118, 104, 36, "#191d21")
            block(10, 120, 100, 32, "#a18051")
            block(12, 122, 96, 28, "#35373a")
            block(14, 124, 92, 24, "#171c20")
            const reelX = [16, 46, 76]
            for (let i = 0; i < 3; ++i) {
                const x = reelX[i]
                block(x, 126, 28, 20, "#0c1013")
                block(x + 2, 128, 24, 16, "#c9c3ac")
                block(x + 2, 128, 24, 2, "#eee1b6")
                block(x + 2, 142, 24, 2, "#938e7f")
            }
            const reels = [art.reelA, art.reelB, art.reelC]
            for (let i = 0; i < 3; ++i) {
                const x = reelX[i]
                const position = reels[i]
                const whole = Math.floor(position)
                const offset = position - whole
                ctx.save()
                ctx.beginPath()
                ctx.rect(x + 2, 128, 24, 16)
                ctx.clip()
                for (let row = -1; row <= 1; ++row)
                    symbol(x + 4, 136 + row * 16 - offset * 16, art.symbolAt(i, whole + row))
                ctx.restore()
            }

            const leverY = Math.round(art.leverPull * 20)
            block(114, 72 + leverY, 4, 30 - leverY, "#22282c")
            block(116, 74 + leverY, 2, 24 - leverY, "#88949a")
            block(112, 66 + leverY, 8, 8, "#16191c")
            block(114, 66 + leverY, 6, 6, "#c8a25e")
            block(114, 66 + leverY, 4, 2, "#efcf88")
        }
    }
}

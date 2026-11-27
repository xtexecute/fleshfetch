function format(value, full) {
    const n = Number(value || 0)
    if (!isFinite(n)) return String(value)
    const magnitude = Math.abs(n)
    if (full || magnitude < 1000) {
        const places = Number.isInteger(n) ? 0 : magnitude < 1 ? 3 : 2
        return n.toLocaleString(Qt.locale(), 'f', places)
    }

    const suffixes = ["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No"]
    let group = Math.floor(Math.log(magnitude) / Math.log(1000))
    if (group >= suffixes.length) return n.toExponential(2)
    let scaled = magnitude / Math.pow(1000, group)
    let places = scaled < 10 ? 2 : scaled < 100 ? 1 : 0
    let rounded = Math.round(scaled * Math.pow(10, places)) / Math.pow(10, places)
    if (rounded >= 1000) {
        group++
        if (group >= suffixes.length) return n.toExponential(2)
        scaled = magnitude / Math.pow(1000, group)
        places = scaled < 10 ? 2 : scaled < 100 ? 1 : 0
        rounded = Math.round(scaled * Math.pow(10, places)) / Math.pow(10, places)
    }
    return (n < 0 ? "-" : "") + rounded + suffixes[group]
}

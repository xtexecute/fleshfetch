.pragma library

function sync(model, entries) {
    for (let i = 0; i < entries.length; ++i) {
        const entry = entries[i]
        let found = i
        while (found < model.count && model.get(found).id !== entry.id) ++found
        if (found === model.count) {
            model.insert(i, entry)
        } else {
            if (found !== i) model.move(found, i, 1)
            const current = model.get(i)
            if (Object.keys(entry).some(function(key) { return current[key] !== entry[key] }))
                model.set(i, entry)
        }
    }
    if (model.count > entries.length) model.remove(entries.length, model.count - entries.length)
}

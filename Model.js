function parseStatus(text) {
  try {
    var obj = JSON.parse(String(text || "").trim())
    return {
      keydInstalled: !!obj.keydInstalled,
      active: !!obj.active,
      configPresent: !!obj.configPresent,
      navKey: obj.navKey === "control" ? "control" : "capslock",
      swapCapsCtrl: !!obj.swapCapsCtrl,
      resize: !!obj.resize,
      liveNavKey: obj.liveNavKey === "control" ? "control" : "capslock",
      liveSwapCapsCtrl: !!obj.liveSwapCapsCtrl,
      liveResize: !!obj.liveResize,
      dirty: !!obj.dirty,
      resizeTogglePresent: !!obj.resizeTogglePresent,
      foreignResizeToggle: !!obj.foreignResizeToggle
    }
  } catch (e) {
    return {
      keydInstalled: false,
      active: false,
      configPresent: false,
      navKey: "capslock",
      swapCapsCtrl: false,
      resize: false,
      liveNavKey: "capslock",
      liveSwapCapsCtrl: false,
      liveResize: false,
      dirty: false,
      resizeTogglePresent: false,
      foreignResizeToggle: false
    }
  }
}

function ready(status) {
  return !!(status && status.keydInstalled && status.active && status.configPresent && !status.dirty)
}

function arrowMod(status) {
  if (status && status.navKey === "control") return "Ctrl"
  return "Caps"
}

function statusLabel(status) {
  if (ready(status)) return "On"
  if (status && status.dirty && status.configPresent) return "Apply"
  if (status && status.configPresent && !status.active) return "Stopped"
  if (status && status.keydInstalled) return "Not mapped"
  return "Not installed"
}

function statusMeta(status) {
  var mod = arrowMod(status)
  if (ready(status)) {
    var bits = [mod + " + hjkl are arrow keys"]
    if (status.swapCapsCtrl) bits.push("Caps and Ctrl swapped")
    if (status.resize) bits.push("Shift resizes")
    return bits.join(" · ")
  }
  if (status && status.dirty && status.configPresent)
    return "Options changed — apply the mapping to update keyd"
  if (status && status.configPresent && !status.active) return "keyd is installed but not running"
  if (status && status.keydInstalled) return "Install the mapping to turn " + mod + " + hjkl on"
  return "Install keyd and the " + mod + " + hjkl mapping"
}

function tooltip(status) {
  if (ready(status)) return "Vi Mode on — " + arrowMod(status) + " + hjkl"
  if (status && status.dirty) return "Vi Mode — apply mapping"
  return "Vi Mode off"
}

function swapDescription(status) {
  var mod = arrowMod(status)
  if (!status || !status.swapCapsCtrl)
    return "Swap Caps Lock and Left Ctrl. " + mod + " + hjkl stay the arrows."
  if (status.navKey === "control")
    return "Caps Lock becomes Ctrl, Left Ctrl becomes Caps Lock. Arrows stay on Ctrl."
  return "Left Ctrl becomes Caps Lock. Caps Lock stays the arrow layer."
}

function resizeDescription(status) {
  var mod = arrowMod(status)
  var extra = ""
  if (status && !status.resize && status.foreignResizeToggle)
    extra = " The separate Vi Resize plugin still binds SUPER + SHIFT + hjkl."
  return "Hold " + mod + " + Shift + hjkl to resize the window (also SUPER + SHIFT + hjkl)." + extra
}

function bindings(status) {
  var mod = arrowMod(status)
  var rows = [
    { keys: mod + " + h", action: "Left" },
    { keys: mod + " + j", action: "Down" },
    { keys: mod + " + k", action: "Up" },
    { keys: mod + " + l", action: "Right" }
  ]
  if (status && status.resize) {
    rows.push({ keys: mod + " + Shift + hjkl", action: "Resize window" })
    rows.push({ keys: "SUPER + SHIFT + hjkl", action: "Same, without " + mod })
  } else {
    rows.push({ keys: mod + " + Shift + hjkl", action: "Select" })
  }
  if (status && status.navKey === "control")
    rows.push({ keys: mod + " + Alt + hjkl", action: "Jump by word" })
  else
    rows.push({ keys: mod + " + Ctrl + hjkl", action: "Jump by word" })
  return rows
}

function footer(status) {
  var mod = arrowMod(status)
  var lines = []
  if (status && status.navKey === "control") {
    lines.push("Ctrl + hjkl send arrows; other Ctrl chords (copy, paste, C-c) still work. Right Ctrl is unchanged.")
    if (status.swapCapsCtrl)
      lines.push("After swap, Ctrl lives on the Caps Lock key, so the chords above are still Ctrl + hjkl.")
  } else {
    lines.push("Caps Lock itself is off. Tap does nothing. Both Shift keys together still toggles real Caps Lock.")
    lines.push("Omarchy CapsLock compose emojis stop working; Super + Ctrl + E still opens the picker.")
  }
  if (status && status.resize)
    lines.push(mod + " + Shift + hjkl no longer selects; use Shift + arrows for that.")
  return lines.join("\n")
}

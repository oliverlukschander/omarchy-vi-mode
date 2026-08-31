function parseStatus(text) {
  try {
    var obj = JSON.parse(String(text || "").trim())
    return {
      keydInstalled: !!obj.keydInstalled,
      active: !!obj.active,
      configPresent: !!obj.configPresent
    }
  } catch (e) {
    return { keydInstalled: false, active: false, configPresent: false }
  }
}

function ready(status) {
  return !!(status && status.keydInstalled && status.active && status.configPresent)
}

function statusLabel(status) {
  if (ready(status)) return "On"
  if (status && status.configPresent && !status.active) return "Stopped"
  if (status && status.keydInstalled) return "Not mapped"
  return "Not installed"
}

function statusMeta(status) {
  if (ready(status)) return "Caps + hjkl are arrow keys"
  if (status && status.configPresent && !status.active) return "keyd is installed but not running"
  if (status && status.keydInstalled) return "Install the mapping to turn Caps + hjkl on"
  return "Install keyd and the Caps + hjkl mapping"
}

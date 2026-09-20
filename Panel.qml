import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as Model

Panel {
  id: root
  moduleName: "oliverlukschander.vi-mode"
  ipcTarget: "oliverlukschander.vi-mode"
  manageIpc: false

  property var anchorItem: null
  property var hostWidget: null
  property bool openedFromHotkey: false
  property var status: Model.parseStatus("")
  property int actionCursor: 0
  property int navChip: 0
  property string pendingSet: ""
  property string navKey: "capslock"
  property bool swapOn: false
  property bool resizeOn: false

  readonly property var barIdentity: hostWidget || root
  readonly property string pluginDir: Quickshell.env("HOME") + "/.config/omarchy/plugins/oliverlukschander.vi-mode"
  readonly property string settingsPath: Quickshell.env("HOME") + "/.config/omarchy/oliverlukschander.vi-mode.json"
  readonly property bool mappingReady: Model.ready(status)
  readonly property color foreground: bar ? bar.foreground : Color.foreground
  readonly property color dim: Qt.darker(foreground, 1.55)
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family
  readonly property string label: ""
  readonly property string arrowMod: navKey === "control" ? "Ctrl" : "Caps"
  readonly property string tooltip: mappingReady ? ("Vi Mode on — " + arrowMod + " + hjkl") : (status.dirty ? "Vi Mode — apply mapping" : "Vi Mode off")
  readonly property var exampleRows: {
    var mod = root.arrowMod
    var rows = [
      { keys: mod + " + h", action: "Left" },
      { keys: mod + " + j", action: "Down" },
      { keys: mod + " + k", action: "Up" },
      { keys: mod + " + l", action: "Right" }
    ]
    if (root.resizeOn) {
      rows.push({ keys: mod + " + Shift + hjkl", action: "Resize window" })
      rows.push({ keys: "SUPER + SHIFT + hjkl", action: "Same, without " + mod })
    } else {
      rows.push({ keys: mod + " + Shift + hjkl", action: "Select" })
    }
    if (root.navKey === "control")
      rows.push({ keys: mod + " + Alt + hjkl", action: "Jump by word" })
    else
      rows.push({ keys: mod + " + Ctrl + hjkl", action: "Jump by word" })
    return rows
  }
  readonly property var navOptions: [
    { value: "capslock", label: "Caps Lock" },
    { value: "control", label: "Ctrl" }
  ]

  readonly property var actions: {
    if (!status.keydInstalled)
      return [{ id: "install", label: "Install mapping" }]
    if (!status.configPresent)
      return [{ id: "install", label: "Install mapping" }]
    if (status.dirty)
      return [
        { id: "apply", label: "Apply mapping" },
        { id: "remove", label: "Remove mapping" }
      ]
    return [
      { id: "reload", label: "Reload mapping" },
      { id: "remove", label: "Remove mapping" }
    ]
  }

  // 0 = nav chips, 1 = swap, 2 = resize, then action buttons
  readonly property int optionCount: 3
  readonly property int cursorCount: optionCount + actions.length

  function open() {
    openedFromHotkey = false
    setCenterHoverRevealSuppressed(false)
    root.refresh()
    root.controller.show()
  }

  function openFromHotkey() {
    openedFromHotkey = true
    root.refresh()
    root.controller.show()
    Qt.callLater(function() {
      if (root.opened) setCenterHoverRevealSuppressed(true)
    })
  }

  function close() {
    root.controller.hide()
    setCenterHoverRevealSuppressed(false)
  }

  function toggle() {
    if (root.opened) root.close()
    else root.openFromHotkey()
  }

  function switchPanel(direction) {
    if (root.bar && typeof root.bar.switchPanelFrom === "function")
      return root.bar.switchPanelFrom(root.barIdentity, direction)
    return false
  }

  function setCenterHoverRevealSuppressed(value) {
    var bar = root.bar
    if (!bar) return
    if (typeof bar.setCenterHoverRevealSuppressed === "function") {
      bar.setCenterHoverRevealSuppressed(value)
      return
    }
    try {
      bar.centerHoverRevealSuppressed = value
    } catch (e) {}
  }

  function refresh() {
    if (!statusProc.running) statusProc.running = true
  }

  readonly property var pythonEnv: ({
    PATH: "/usr/bin:/bin",
    LANG: "C.UTF-8",
    LC_ALL: "C.UTF-8",
    HOME: Quickshell.env("HOME"),
    USER: Quickshell.env("USER"),
    LOGNAME: Quickshell.env("LOGNAME"),
    XDG_CONFIG_HOME: Quickshell.env("XDG_CONFIG_HOME"),
    XDG_STATE_HOME: Quickshell.env("XDG_STATE_HOME"),
    XDG_RUNTIME_DIR: Quickshell.env("XDG_RUNTIME_DIR"),
    XDG_DATA_HOME: Quickshell.env("XDG_DATA_HOME"),
    HYPRLAND_INSTANCE_SIGNATURE: Quickshell.env("HYPRLAND_INSTANCE_SIGNATURE"),
    WAYLAND_DISPLAY: Quickshell.env("WAYLAND_DISPLAY"),
    DBUS_SESSION_BUS_ADDRESS: Quickshell.env("DBUS_SESSION_BUS_ADDRESS"),
    XDG_SESSION_TYPE: Quickshell.env("XDG_SESSION_TYPE")
  })

  FileView {
    path: root.settingsPath
    watchChanges: true
    printErrors: false
    onLoaded: root.applySettingsJson(text())
    onFileChanged: reload()
  }

  function applySettingsJson(text) {
    try {
      var obj = JSON.parse(String(text || "").trim())
      if (obj.navKey === "control" || obj.navKey === "capslock")
        root.navKey = obj.navKey
      if (Object.prototype.hasOwnProperty.call(obj, "swapCapsCtrl"))
        root.swapOn = !!obj.swapCapsCtrl
      if (Object.prototype.hasOwnProperty.call(obj, "resize"))
        root.resizeOn = !!obj.resize
      root.navChip = root.navKey === "control" ? 1 : 0
    } catch (e) {}
  }

  function applyParsed(s) {
    root.status = s
    if (s.navKey === "control" || s.navKey === "capslock")
      root.navKey = s.navKey
    root.swapOn = !!s.swapCapsCtrl
    root.resizeOn = !!s.resize
    root.navChip = root.navKey === "control" ? 1 : 0
  }

  function runScript(name) {
    if (name !== "install.sh" && name !== "uninstall.sh")
      return
    Quickshell.execDetached([
      "/usr/bin/omarchy-launch-floating-terminal-with-presentation",
      root.pluginDir + "/" + name
    ])
    Qt.callLater(root.refresh)
    delayedRefresh.restart()
  }

  function previewStatus(key, value) {
    return {
      keydInstalled: status.keydInstalled,
      active: status.active,
      configPresent: status.configPresent,
      navKey: key === "navKey" ? value : status.navKey,
      swapCapsCtrl: key === "swapCapsCtrl" ? value === "true" : status.swapCapsCtrl,
      resize: key === "resize" ? value === "true" : status.resize,
      liveNavKey: status.liveNavKey,
      liveSwapCapsCtrl: status.liveSwapCapsCtrl,
      liveResize: status.liveResize,
      dirty: true,
      resizeTogglePresent: status.resizeTogglePresent,
      foreignResizeToggle: status.foreignResizeToggle
    }
  }

  function setOption(key, value) {
    status = previewStatus(key, value)
    if (key === "navKey") {
      navKey = value
      navChip = value === "control" ? 1 : 0
    } else if (key === "swapCapsCtrl") {
      swapOn = value === "true"
    } else if (key === "resize") {
      resizeOn = value === "true"
    }
    var arg = key + "=" + value
    if (setProc.running) {
      pendingSet = arg
      return
    }
    pendingSet = ""
    setProc.command = ["/usr/bin/python3", "-I", root.pluginDir + "/scripts/settings.py", "set", arg]
    setProc.running = true
  }

  function activateCursor() {
    if (actionCursor === 0) {
      setOption("navKey", navChip === 1 ? "control" : "capslock")
      return
    }
    if (actionCursor === 1) {
      setOption("swapCapsCtrl", swapOn ? "false" : "true")
      return
    }
    if (actionCursor === 2) {
      setOption("resize", resizeOn ? "false" : "true")
      return
    }
    activateAction(actionCursor - optionCount)
  }

  function activateAction(index) {
    var item = actions[Math.max(0, Math.min(index, actions.length - 1))]
    if (!item) return
    if (item.id === "install" || item.id === "reload" || item.id === "apply")
      runScript("install.sh")
    else if (item.id === "remove")
      runScript("uninstall.sh")
  }

  function moveCursor(dx, dy) {
    if (dy !== 0) {
      actionCursor = Math.max(0, Math.min(cursorCount - 1, actionCursor + dy))
      return
    }
    if (dx !== 0 && actionCursor === 0) {
      navChip = Math.max(0, Math.min(1, navChip + dx))
      setOption("navKey", navChip === 1 ? "control" : "capslock")
    }
  }



  onOpenedChanged: {
    if (opened) {
      actionCursor = 0
      refresh()
      Qt.callLater(function() { if (keyCatcher) keyCatcher.forceActiveFocus() })
    }
  }

  Timer {
    id: delayedRefresh
    interval: 4000
    repeat: false
    onTriggered: root.refresh()
  }

  Timer {
    interval: 5000
    running: true
    repeat: true
    onTriggered: if (!setProc.running && root.pendingSet === "") root.refresh()
  }

  Process {
    id: statusProc
    command: ["/usr/bin/python3", "-I", root.pluginDir + "/scripts/status.py"]
    workingDirectory: "/"
    clearEnvironment: true
    environment: root.pythonEnv
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        if (!setProc.running && root.pendingSet === "")
          root.applyParsed(Model.parseStatus(text))
      }
    }
  }

  Process {
    id: setProc
    workingDirectory: "/"
    clearEnvironment: true
    environment: root.pythonEnv
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        if (root.pendingSet !== "") {
          var arg = root.pendingSet
          root.pendingSet = ""
          setProc.command = ["/usr/bin/python3", "-I", root.pluginDir + "/scripts/settings.py", "set", arg]
          setProc.running = true
          return
        }
        root.applyParsed(Model.parseStatus(text))
      }
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.barIdentity
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(420))
    contentHeight: panel.fittedContentHeight(column.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }
      onMoveRequested: function(dx, dy) { root.moveCursor(dx, dy) }
      onActivateRequested: root.activateCursor()
      onTextKey: function(t) {
        if (t === "r" || t === "R") root.refresh()
        else if (t === "i" || t === "I") root.runScript("install.sh")
        else if (t === "u" || t === "U") root.runScript("uninstall.sh")
      }

      Column {
        id: column
        width: parent.width
        spacing: Style.space(12)

        PanelHero {
          width: parent.width
          title: "Vi Mode"
          detail: Model.statusLabel(root.status)
          meta: root.arrowMod + " + hjkl are arrow keys"
          foreground: root.foreground
          fontFamily: root.fontFamily
          iconComponent: Component {
            Text {
              text: ""
              color: root.mappingReady ? root.foreground : root.dim
              font.family: root.fontFamily
              font.pixelSize: Style.font.display
            }
          }
        }

        PanelSeparator { width: parent.width }

        PanelSectionHeader {
          text: "ARROW KEYS"
          foreground: root.foreground
          fontFamily: root.fontFamily
        }

        ButtonGroup {
          width: parent.width
          options: root.navOptions
          value: root.navKey
          foreground: root.foreground
          fontFamily: root.fontFamily
          focusable: false
          cursorIndex: root.actionCursor === 0 ? root.navChip : -1
          onChanged: function(v) {
            if (v && v !== root.navKey) root.setOption("navKey", v)
          }
          onHovered: function(index, isHovered) {
            if (isHovered) {
              root.actionCursor = 0
              root.navChip = index
            }
          }
        }

        Toggle {
          width: parent.width
          label: "Swap Caps Lock and Ctrl"
          description: root.swapOn
            ? (root.navKey === "control"
              ? "Caps Lock becomes Ctrl, Left Ctrl becomes Caps Lock. Arrows stay on Ctrl."
              : "Left Ctrl becomes Caps Lock. Caps Lock stays the arrow layer.")
            : ("Swap Caps Lock and Left Ctrl. " + root.arrowMod + " + hjkl stay the arrows.")
          checked: root.swapOn
          hasCursor: root.actionCursor === 1
          foreground: root.foreground
          fontFamily: root.fontFamily
          onClicked: root.setOption("swapCapsCtrl", root.swapOn ? "false" : "true")
          onHovered: function(isHovered) { if (isHovered) root.actionCursor = 1 }
        }

        Toggle {
          width: parent.width
          label: "Resize mode"
          description: "Hold " + root.arrowMod + " + Shift + hjkl to resize the window (also SUPER + SHIFT + hjkl)."
          checked: root.resizeOn
          hasCursor: root.actionCursor === 2
          foreground: root.foreground
          fontFamily: root.fontFamily
          onClicked: root.setOption("resize", root.resizeOn ? "false" : "true")
          onHovered: function(isHovered) { if (isHovered) root.actionCursor = 2 }
        }

        PanelSeparator { width: parent.width }

        PanelSectionHeader {
          text: "HOLD " + root.arrowMod.toUpperCase()
          foreground: root.foreground
          fontFamily: root.fontFamily
        }

        Column {
          width: parent.width
          spacing: Style.space(4)

          Repeater {
            model: root.exampleRows
            delegate: Row {
              required property var modelData
              width: parent.width
              spacing: Style.space(12)

              Text {
                width: Style.space(200)
                text: modelData ? modelData.keys : ""
                color: root.foreground
                font.family: root.fontFamily
                font.pixelSize: Style.font.body
              }

              Text {
                text: modelData ? modelData.action : ""
                color: root.dim
                font.family: root.fontFamily
                font.pixelSize: Style.font.body
              }
            }
          }
        }

        Text {
          width: parent.width
          text: {
            var mod = root.arrowMod
            var lines = []
            if (root.navKey === "control") {
              lines.push("Ctrl + hjkl send arrows; other Ctrl chords (copy, paste, C-c) still work. Right Ctrl is unchanged.")
              if (root.swapOn)
                lines.push("After swap, Ctrl lives on the Caps Lock key, so the chords above are still Ctrl + hjkl.")
            } else {
              lines.push("Caps Lock itself is off. Tap does nothing. Both Shift keys together still toggles real Caps Lock.")
              lines.push("Omarchy CapsLock compose emojis stop working; Super + Ctrl + E still opens the picker.")
            }
            if (root.resizeOn)
              lines.push(mod + " + Shift + hjkl no longer selects; use Shift + arrows for that.")
            return lines.join("\n")
          }
          wrapMode: Text.WordWrap
          color: root.dim
          font.family: root.fontFamily
          font.pixelSize: Style.font.caption
        }

        PanelSeparator { width: parent.width }

        Column {
          width: parent.width
          spacing: Style.space(6)

          Repeater {
            model: root.actions
            delegate: Button {
              width: parent.width
              text: modelData.label
              foreground: root.foreground
              fontFamily: root.fontFamily
              hasCursor: root.actionCursor === (root.optionCount + index)
              bordered: true
              onClicked: root.activateAction(index)
              onHovered: function(isHovered) {
                if (isHovered) root.actionCursor = root.optionCount + index
              }
            }
          }
        }
      }
    }
  }
}

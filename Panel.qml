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
  property var status: ({ keydInstalled: false, active: false, configPresent: false })
  property int actionCursor: 0

  readonly property var barIdentity: hostWidget || root
  readonly property string pluginDir: Quickshell.env("HOME") + "/.config/omarchy/plugins/oliverlukschander.vi-mode"
  readonly property bool mappingReady: Model.ready(status)
  readonly property color foreground: bar ? bar.foreground : Color.foreground
  readonly property color dim: Qt.darker(foreground, 1.55)
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family
  readonly property string label: ""

  readonly property var bindings: [
    { keys: "Caps + h", action: "Left" },
    { keys: "Caps + j", action: "Down" },
    { keys: "Caps + k", action: "Up" },
    { keys: "Caps + l", action: "Right" },
    { keys: "Caps + Shift + hjkl", action: "Select" },
    { keys: "Caps + Ctrl + hjkl", action: "Jump by word" }
  ]

  readonly property var actions: mappingReady
    ? [
        { id: "reload", label: "Reload mapping" },
        { id: "remove", label: "Remove mapping" }
      ]
    : [
        { id: "install", label: "Install mapping" }
      ]

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
    setCenterHoverRevealSuppressed(false)
    root.controller.hide()
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
    if (root.bar && "centerHoverRevealSuppressed" in root.bar)
      root.bar.centerHoverRevealSuppressed = value
  }

  function refresh() {
    if (!statusProc.running) statusProc.running = true
  }

  function runScript(name) {
    var cmd = "omarchy-launch-floating-terminal-with-presentation '" + pluginDir + "/" + name + "'"
    if (root.bar && typeof root.bar.run === "function")
      root.bar.run(cmd)
    else
      Quickshell.execDetached(["bash", "-lc", cmd])
    Qt.callLater(root.refresh)
    delayedRefresh.restart()
  }

  function activateAction(index) {
    var item = actions[Math.max(0, Math.min(index, actions.length - 1))]
    if (!item) return
    if (item.id === "install" || item.id === "reload") runScript("install.sh")
    else if (item.id === "remove") runScript("uninstall.sh")
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
    onTriggered: root.refresh()
  }

  Process {
    id: statusProc
    command: [root.pluginDir + "/scripts/status.sh"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.status = Model.parseStatus(text)
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.barIdentity
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(360))
    contentHeight: panel.fittedContentHeight(column.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }
      onMoveRequested: function(dx, dy) {
        if (dy === 0) return
        root.actionCursor = Math.max(0, Math.min(root.actions.length - 1, root.actionCursor + dy))
      }
      onActivateRequested: root.activateAction(root.actionCursor)
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
          meta: Model.statusMeta(root.status)
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
          text: "HOLD CAPS LOCK"
          foreground: root.foreground
          fontFamily: root.fontFamily
        }

        Column {
          width: parent.width
          spacing: Style.space(4)

          Repeater {
            model: root.bindings
            delegate: Row {
              width: parent.width
              spacing: Style.space(12)

              Text {
                width: Style.space(180)
                text: modelData.keys
                color: root.foreground
                font.family: root.fontFamily
                font.pixelSize: Style.font.body
              }

              Text {
                text: modelData.action
                color: root.dim
                font.family: root.fontFamily
                font.pixelSize: Style.font.body
              }
            }
          }
        }

        Text {
          width: parent.width
          text: "Caps Lock itself is off. Tap does nothing. Both Shift keys together still toggles real Caps Lock.\nOmarchy CapsLock compose emojis stop working; Super + Ctrl + E still opens the picker."
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
              hasCursor: root.actionCursor === index
              bordered: true
              onClicked: root.activateAction(index)
              onHovered: function(isHovered) { if (isHovered) root.actionCursor = index }
            }
          }
        }
      }
    }
  }
}

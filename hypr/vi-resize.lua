-- SUPER + SHIFT + hjkl grows the active window by 1/4 of the monitor
-- per keypress, on a 25/50/75 grid.
--
-- Two tiled windows at 50:50: grow one once → 25:75. It cannot grow
-- again. Grow the other twice to reach 75:25.
--
-- Leaves SUPER + J / K / L (split, keybindings, layout) alone.
-- SUPER + SHIFT + arrows still swaps windows. SUPER + right-click is unchanged.
--
-- The arrow-layer key (Caps or Ctrl) + Shift + hjkl reaches these binds
-- through keyd: that chord emits SUPER + SHIFT + hjkl instead of Shift + arrows.

local FRACTION = 4

local function logical_size(mon)
  local scale = tonumber(mon.scale) or 1
  if scale <= 0 then
    scale = 1
  end
  local width = tonumber(mon.width) or 0
  local height = tonumber(mon.height) or 0
  return width / scale, height / scale
end

local function axis(size, key, fallback)
  if size == nil then
    return fallback
  end
  local ok, value = pcall(function()
    return tonumber(size[key])
  end)
  if ok and value then
    return value
  end
  return fallback
end

-- Next size on the 1/4 grid, never past 3/4 of the monitor.
local function grow_amount(current, total)
  local step = total / FRACTION
  if step <= 0 or current <= 0 then
    return 0
  end
  local q = math.floor(current / step + 0.5)
  local next_q = q + 1
  if next_q > FRACTION - 1 then
    return 0
  end
  local delta = math.floor(next_q * step - current + 0.5)
  if delta <= 0 then
    return 0
  end
  return delta
end

local function resize(dx, dy)
  return function()
    local win = hl.get_active_window()
    local mon = (win and win.monitor) or hl.get_active_monitor() or hl.get_monitor_at_cursor()
    if not mon then
      return
    end
    local width, height = logical_size(mon)
    if width <= 0 or height <= 0 then
      return
    end
    local size = win and win.size
    local cur_w = axis(size, "x", width)
    local cur_h = axis(size, "y", height)
    local ax = 0
    local ay = 0
    if dx ~= 0 then
      ax = dx * grow_amount(cur_w, width)
    end
    if dy ~= 0 then
      ay = dy * grow_amount(cur_h, height)
    end
    if ax == 0 and ay == 0 then
      return
    end
    hl.dispatch(hl.dsp.window.resize({
      x = ax,
      y = ay,
      relative = true,
    }))
  end
end

o.bind("SUPER + SHIFT + H", "Grow window left", resize(-1, 0))
o.bind("SUPER + SHIFT + J", "Grow window down", resize(0, 1))
o.bind("SUPER + SHIFT + K", "Grow window up", resize(0, -1))
o.bind("SUPER + SHIFT + L", "Grow window right", resize(1, 0))

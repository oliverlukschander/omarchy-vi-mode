-- SUPER + SHIFT + hjkl resizes the active window, repeating while held.
-- Same dispatcher as SUPER + minus/plus, mapped onto vim directions.
--
-- Leaves SUPER + J / K / L (split, keybindings, layout) alone.
-- SUPER + SHIFT + arrows still swaps windows. SUPER + right-click is unchanged.
--
-- The arrow-layer key (Caps or Ctrl) + Shift + hjkl reaches these binds
-- through keyd: that chord emits SUPER + SHIFT + hjkl instead of Shift + arrows.

local step = 40
local opts = { repeating = true }

o.bind("SUPER + SHIFT + H", "Grow window left", hl.dsp.window.resize({ x = -step, y = 0, relative = true }), opts)
o.bind("SUPER + SHIFT + J", "Grow window down", hl.dsp.window.resize({ x = 0, y = step, relative = true }), opts)
o.bind("SUPER + SHIFT + K", "Grow window up", hl.dsp.window.resize({ x = 0, y = -step, relative = true }), opts)
o.bind("SUPER + SHIFT + L", "Grow window right", hl.dsp.window.resize({ x = step, y = 0, relative = true }), opts)

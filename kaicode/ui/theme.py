"""KaiCode color theme and styling constants."""

from rich.theme import Theme


KAICODE_VERSION = "2.1.0"

# Dual-mode palette — mid-saturation colors readable on dark AND light terminals
KAICODE_THEME = Theme({
    "kaicode.logo":            "bold #2196f3",        # blue — pops on dark, solid on light
    "kaicode.assistant":       "bold #00838f",        # teal — readable on both
    "kaicode.model":           "bold #e65100",        # deep orange — warm, visible on both
    "kaicode.user":            "bold default",        # inherits terminal default
    "kaicode.prompt":          "bold #1976d2",        # darker blue prompt
    "kaicode.tool_call":       "bold #6a1b9a",        # deep purple
    "kaicode.tool_result":     "#2e7d32",             # dark green
    "kaicode.success":         "bold #2e7d32",        # dark green
    "kaicode.error":           "bold #c62828",        # dark red
    "kaicode.warning":         "bold #e65100",        # deep orange
    "kaicode.info":            "#01579b",             # dark blue-grey
    "kaicode.tokens":          "#00838f",             # teal
    "kaicode.separator":       "#888888",             # mid-grey — neutral on both
    "kaicode.muted":           "#aaaaaa",             # light-ish grey — OK on both
    "kaicode.footer":          "#999999",             # mid-grey
    "kaicode.dir":             "#888888",
    "kaicode.branch":          "#6a1b9a",             # deep purple
    "kaicode.diff.add":        "bold #2e7d32",
    "kaicode.diff.remove":     "bold #c62828",
    "kaicode.diff.header":     "bold #01579b",
    "kaicode.file_tree":       "#00838f",
    "kaicode.file_tree.dir":   "bold #1976d2",
    "kaicode.file_tree.file":  "default",
    "kaicode.header":          "bold #1976d2",
    "kaicode.system":          "italic #e65100",
    "kaicode.status_bar":      "default",
    "kaicode.tag":             "bold default on #1976d2",
    # ── Refined message bubbles (transparent — no fill) ───────────────────
    "kaicode.bubble.kai":      "#9e9e9e",        # KaiCode border  — gray
    "kaicode.bubble.kai.name": "bold #bdbdbd",   # KaiCode title text
    "kaicode.bubble.user":     "#2196f3",        # You border      — blue
    "kaicode.bubble.user.name":"bold #64b5f6",   # You title text
    "kaicode.bubble.plan":     "#e65100",        # Plan border     — amber
    "kaicode.bubble.plan.name":"bold #ffcc80",   # Plan title text
    "kaicode.msg.kai":         "#a8a8a8",        # KaiCode body text — gray
    "kaicode.msg.user":        "#90caf9",        # You body text     — blue
    "kaicode.msg.plan":        "#fff3e0",        # Plan body text
})

# Vertical blue→teal gradient for the launch logo (one color per glyph row).
# Interpolated from kaicode.logo (#2196f3) to kaicode.assistant (#00838f).
LOGO_GRADIENT = [
    "#2196f3", "#1a92df", "#148ecb", "#0d8bb7", "#0787a3", "#00838f",
]

ASCII_LOGO = r"""
 ██╗  ██╗ █████╗ ██╗ ██████╗ ██████╗ ██████╗ ███████╗
 ██║ ██╔╝██╔══██╗██║██╔════╝██╔═══██╗██╔══██╗██╔════╝
 █████╔╝ ███████║██║██║     ██║   ██║██║  ██║█████╗
 ██╔═██╗ ██╔══██║██║██║     ██║   ██║██║  ██║██╔══╝
 ██║  ██╗██║  ██║██║╚██████╗╚██████╔╝██████╔╝███████╗
 ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝"""

LOGO_COMPACT = "⟨ KaiCode ⟩"

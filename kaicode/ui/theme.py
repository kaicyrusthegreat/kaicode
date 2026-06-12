"""KaiCode color theme and styling constants."""

from rich.theme import Theme


KAICODE_VERSION = "2.2.0"

# Dual-mode palette — mid-saturation colors readable on dark AND light terminals
KAICODE_THEME = Theme(
    {
        "kaicode.logo": "bold #2196f3",  # blue — pops on dark, solid on light
        "kaicode.assistant": "bold #00838f",  # teal — readable on both
        "kaicode.model": "bold #e65100",  # deep orange — warm, visible on both
        "kaicode.user": "bold default",  # inherits terminal default
        "kaicode.prompt": "bold #1976d2",  # darker blue prompt
        "kaicode.tool_call": "bold #6a1b9a",  # deep purple
        "kaicode.tool_result": "#2e7d32",  # dark green
        "kaicode.success": "bold #2e7d32",  # dark green
        "kaicode.error": "bold #c62828",  # dark red
        "kaicode.warning": "bold #e65100",  # deep orange
        "kaicode.info": "#01579b",  # dark blue-grey
        "kaicode.tokens": "#00838f",  # teal
        "kaicode.separator": "#888888",  # mid-grey — neutral on both
        "kaicode.muted": "#aaaaaa",  # light-ish grey — OK on both
        "kaicode.footer": "#999999",  # mid-grey
        "kaicode.dir": "#888888",
        "kaicode.branch": "#6a1b9a",  # deep purple
        "kaicode.diff.add": "bold #2e7d32",
        "kaicode.diff.remove": "bold #c62828",
        "kaicode.diff.header": "bold #01579b",
        "kaicode.file_tree": "#00838f",
        "kaicode.file_tree.dir": "bold #1976d2",
        "kaicode.file_tree.file": "default",
        "kaicode.header": "bold #1976d2",
        "kaicode.system": "italic #e65100",
        "kaicode.status_bar": "default",
        "kaicode.tag": "bold default on #1976d2",
        # ── Refined message bubbles (transparent — no fill) ───────────────────
        # You = blue, KaiCode = brand teal (the logo gradient's two ends), Plan = amber.
        "kaicode.bubble.kai": "#00838f",  # KaiCode border  — brand teal
        "kaicode.bubble.kai.name": "bold #26c6da",  # KaiCode title text
        "kaicode.bubble.user": "#2196f3",  # You border      — blue
        "kaicode.bubble.user.name": "bold #64b5f6",  # You title text
        "kaicode.bubble.plan": "#e65100",  # Plan border     — amber
        "kaicode.bubble.plan.name": "bold #ffcc80",  # Plan title text
        "kaicode.msg.kai": "default",  # body inherits terminal fg — readable on dark AND light
        "kaicode.msg.user": "#90caf9",  # You body text     — blue
        "kaicode.msg.plan": "#fff3e0",  # Plan body text
    }
)

# ── prompt_toolkit chrome (REPL prompt + bottom toolbar) ─────────────────────
# Kept beside the Rich theme so the terminal chrome and the panels share one
# palette: PT_PROVIDER mirrors kaicode.assistant, PT_MODEL mirrors kaicode.model.
PT_PROMPT = "#50fa7b"  # prompt arrow / accents
PT_TEXT = "#e8f5e9"  # typed input text
PT_PROVIDER = "#00838f"  # = kaicode.assistant
PT_MODEL = "#e65100"  # = kaicode.model
PT_MUTED = "#555555"  # toolbar body text
PT_HINT = "#666666"  # toolbar key hints
PT_SEP = "#444444"  # toolbar separators

# Vertical blue→teal gradient for the launch logo (one color per glyph row).
# Interpolated from kaicode.logo (#2196f3) to kaicode.assistant (#00838f).
LOGO_GRADIENT = [
    "#2196f3",
    "#1a92df",
    "#148ecb",
    "#0d8bb7",
    "#0787a3",
    "#00838f",
]

ASCII_LOGO = r"""
 ██╗  ██╗ █████╗ ██╗ ██████╗ ██████╗ ██████╗ ███████╗
 ██║ ██╔╝██╔══██╗██║██╔════╝██╔═══██╗██╔══██╗██╔════╝
 █████╔╝ ███████║██║██║     ██║   ██║██║  ██║█████╗
 ██╔═██╗ ██╔══██║██║██║     ██║   ██║██║  ██║██╔══╝
 ██║  ██╗██║  ██║██║╚██████╗╚██████╔╝██████╔╝███████╗
 ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝"""

LOGO_COMPACT = "⟨ KaiCode ⟩"

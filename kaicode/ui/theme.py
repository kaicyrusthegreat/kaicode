"""KaiCode color theme and styling constants."""

from rich.theme import Theme
from rich.style import Style


KAICODE_THEME = Theme({
    "kaicode.header": "bold cyan on black",
    "kaicode.logo": "bold bright_cyan",
    "kaicode.model": "bold yellow",
    "kaicode.dir": "dim white",
    "kaicode.user": "bold bright_white",
    "kaicode.assistant": "bold cyan",
    "kaicode.system": "dim italic yellow",
    "kaicode.tool_call": "bold magenta",
    "kaicode.tool_result": "dim green",
    "kaicode.error": "bold red",
    "kaicode.success": "bold green",
    "kaicode.warning": "bold yellow",
    "kaicode.info": "dim cyan",
    "kaicode.status_bar": "white on #1a1a2e",
    "kaicode.tokens": "dim cyan",
    "kaicode.separator": "dim #444444",
    "kaicode.file_tree": "dim cyan",
    "kaicode.file_tree.dir": "bold blue",
    "kaicode.file_tree.file": "white",
    "kaicode.diff.add": "bold green",
    "kaicode.diff.remove": "bold red",
    "kaicode.diff.header": "bold cyan",
    "kaicode.prompt": "bold cyan",
    "kaicode.footer": "dim italic white",
})

ASCII_LOGO = r"""
 ██╗  ██╗ █████╗ ██╗ ██████╗ ██████╗ ██████╗ ███████╗
 ██║ ██╔╝██╔══██╗██║██╔════╝██╔═══██╗██╔══██╗██╔════╝
 █████╔╝ ███████║██║██║     ██║   ██║██║  ██║█████╗
 ██╔═██╗ ██╔══██║██║██║     ██║   ██║██║  ██║██╔══╝
 ██║  ██╗██║  ██║██║╚██████╗╚██████╔╝██████╔╝███████╗
 ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
"""

LOGO_COMPACT = "⟨ KaiCode ⟩"

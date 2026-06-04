"""Keyboard and mouse control tools via pyautogui."""

from __future__ import annotations

import time
from typing import Any


def type_text(text: str, interval: float = 0.02) -> dict[str, Any]:
    """Type text using the keyboard. Each character is typed with a small delay."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = True  # move mouse to corner to abort
        time.sleep(0.3)  # brief pause before typing
        pyautogui.typewrite(text, interval=float(interval))
        return {"success": True, "typed": text[:100], "chars": len(text)}
    except ImportError:
        return {"error": "pyautogui not installed. Run: pip install pyautogui"}
    except Exception as e:
        return {"error": str(e)}


def key_press(keys: str) -> dict[str, Any]:
    """Press a key combination. Examples: 'cmd+c', 'ctrl+shift+t', 'enter', 'tab'.
    
    Use '+' to combine keys. Single keys: enter, tab, space, escape, backspace,
    delete, up, down, left, right, home, end, pageup, pagedown, f1-f12.
    Modifiers: cmd/command, ctrl/control, alt/option, shift.
    """
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        
        # Normalize key names
        key_map = {
            "cmd": "command", "ctrl": "ctrl", "control": "ctrl",
            "alt": "alt", "option": "alt", "shift": "shift",
            "enter": "enter", "return": "enter", "tab": "tab",
            "space": "space", "esc": "escape", "escape": "escape",
            "backspace": "backspace", "delete": "delete",
            "up": "up", "down": "down", "left": "left", "right": "right",
        }
        
        parts = [k.strip().lower() for k in keys.split("+")]
        normalized = [key_map.get(k, k) for k in parts]
        
        time.sleep(0.2)
        if len(normalized) == 1:
            pyautogui.press(normalized[0])
        else:
            pyautogui.hotkey(*normalized)
        
        return {"success": True, "keys": keys}
    except ImportError:
        return {"error": "pyautogui not installed. Run: pip install pyautogui"}
    except Exception as e:
        return {"error": str(e)}


def mouse_click(
    x: int = 0, y: int = 0,
    button: str = "left",
    clicks: int = 1,
) -> dict[str, Any]:
    """Click the mouse at the given screen coordinates.
    
    Args:
        x: X screen coordinate
        y: Y screen coordinate  
        button: 'left', 'right', or 'middle'
        clicks: Number of clicks (2 for double-click)
    """
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        x, y, clicks = int(x), int(y), int(clicks)
        button = str(button).lower()
        if button not in ("left", "right", "middle"):
            button = "left"
        
        time.sleep(0.2)
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)
        return {"success": True, "x": x, "y": y, "button": button, "clicks": clicks}
    except ImportError:
        return {"error": "pyautogui not installed. Run: pip install pyautogui"}
    except Exception as e:
        return {"error": str(e)}


def screenshot(path: str = "screenshot.png") -> dict[str, Any]:
    """Take a screenshot and save it to a file."""
    try:
        import pyautogui
        img = pyautogui.screenshot()
        img.save(path)
        return {"success": True, "path": path, "size": f"{img.width}x{img.height}"}
    except ImportError:
        return {"error": "pyautogui not installed. Run: pip install pyautogui"}
    except Exception as e:
        return {"error": str(e)}

"""
Global hotkey listener.
Uses pynput's Listener (not GlobalHotKeys) for better macOS reliability.
Tracks pressed keys manually and fires callbacks on matching combos.
"""

import platform
import threading
from typing import Callable, Optional, Set

from pynput import keyboard


# Map modifier names to pynput Key objects
_MOD_MAP = {
    "cmd":   keyboard.Key.cmd,
    "ctrl":  keyboard.Key.ctrl,
    "shift": keyboard.Key.shift,
    "alt":   keyboard.Key.alt,
}


class HotkeyListener:
    """
    Registers global hotkeys and invokes callbacks.
    Uses keyboard.Listener with manual key tracking for reliability.
    """

    def __init__(self) -> None:
        self._listener: Optional[keyboard.Listener] = None
        self._combos: list[dict] = []      # [{mods: set, key: str, callback: fn}]
        self._pressed: Set = set()          # currently held keys

    # ── Public API ─────────────────────────────────────────────────────
    def register(
        self,
        key: str,
        callback: Callable,
        modifier1: str = "cmd",
        modifier2: str = "shift",
    ) -> None:
        """Register a hotkey combination."""
        mods = set()
        if modifier1 and modifier1 in _MOD_MAP:
            mods.add(_MOD_MAP[modifier1])
        if modifier2 and modifier2 in _MOD_MAP:
            mods.add(_MOD_MAP[modifier2])

        self._combos.append({
            "mods": mods,
            "key": key.lower(),
            "callback": callback,
        })
        print(f"[hotkey] registered: {modifier1}+{modifier2}+{key}")

    def start(self) -> None:
        """Start listening in a background daemon thread."""
        if not self._combos:
            raise RuntimeError("No hotkeys registered")

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()
        print("[hotkey] listener started")

    def stop(self) -> None:
        """Stop the listener."""
        if self._listener:
            self._listener.stop()
            self._listener = None

    # ── Key tracking ───────────────────────────────────────────────────
    def _on_press(self, key) -> None:
        """Track key presses and check for matching combos."""
        self._pressed.add(key)

        # Get the character for regular keys
        char = None
        if hasattr(key, 'char') and key.char:
            char = key.char.lower()
        elif hasattr(key, 'vk') and key.vk:
            # On macOS, when modifiers are held, .char may be None
            # but .vk (virtual keycode) is still available
            # vk codes: a=0, s=1, d=2, ... (macOS keycodes)
            vk_to_char = {
                0: 'a', 1: 's', 2: 'd', 3: 'f', 4: 'h', 5: 'g',
                6: 'z', 7: 'x', 8: 'c', 9: 'v', 11: 'b', 12: 'q',
                13: 'w', 14: 'e', 15: 'r', 16: 'y', 17: 't',
                18: '1', 19: '2', 20: '3', 21: '4', 22: '6', 23: '5',
                24: '=', 25: '9', 26: '7', 27: '-', 28: '8', 29: '0',
                30: ']', 31: 'o', 32: 'u', 33: '[', 34: 'i', 35: 'p',
                37: 'l', 38: 'j', 39: "'", 40: 'k', 41: ';', 42: '\\',
                43: ',', 44: '/', 45: 'n', 46: 'm', 47: '.', 50: '`'
            }
            char = vk_to_char.get(key.vk)

        if char is None:
            return

        # Check each registered combo
        for combo in self._combos:
            if char != combo["key"]:
                continue

            # Check if all required modifiers are pressed
            mods_held = True
            for mod in combo["mods"]:
                # Check both left and right variants
                if mod == keyboard.Key.cmd:
                    if keyboard.Key.cmd not in self._pressed and keyboard.Key.cmd_r not in self._pressed:
                        mods_held = False
                elif mod == keyboard.Key.ctrl:
                    if keyboard.Key.ctrl not in self._pressed and keyboard.Key.ctrl_r not in self._pressed:
                        mods_held = False
                elif mod == keyboard.Key.shift:
                    if keyboard.Key.shift not in self._pressed and keyboard.Key.shift_r not in self._pressed:
                        mods_held = False
                elif mod == keyboard.Key.alt:
                    if keyboard.Key.alt not in self._pressed and keyboard.Key.alt_r not in self._pressed:
                        mods_held = False
                else:
                    if mod not in self._pressed:
                        mods_held = False

            if mods_held:
                print(f"[hotkey] combo matched: {combo['key']}")
                # Fire callback in a new thread to not block the listener
                threading.Thread(target=combo["callback"], daemon=True).start()
                return

    def _on_release(self, key) -> None:
        """Track key releases."""
        self._pressed.discard(key)

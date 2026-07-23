"""A small wall-clock timer used for every timed rule in the game."""

from settings import *
from typing import Callable


class Timer:
    """
    A one-shot (or repeating) countdown driven by pygame's millisecond clock.

    The pattern: something calls `activate()`, other code checks
    `if timer.active:` to see whether the window is still open, and `update()`
    runs once per frame to close it. Durations are real milliseconds, not dt,
    so timers never drift with framerate.

    Args:
        duration:   how long the timer stays active, in milliseconds.
        repeat:     restart automatically the moment it expires.
        func:       optional callback fired once, at the moment it expires.
        auto_start: start counting immediately on construction.

    Example -- the coyote window in Player:
        self.timers["coyote"].activate()          # just left the ground
        if self.timers["coyote"].active: jump()   # late jump still allowed
    """

    def __init__(
        self,
        duration: int,
        repeat: bool = False,
        func: Callable[[], None] | None = None,
        auto_start: bool = False,
    ) -> None:
        self.duration = duration
        self.repeat = repeat
        self.func = func
        self.start_time = 0
        self.active = False
        if auto_start:
            self.activate()

    def activate(self) -> None:
        """Open the window and (re)start the countdown from now."""
        self.start_time = get_ticks()
        self.active = True

    def deactivate(self) -> None:
        """Close the window early. Restarts immediately if `repeat` is set."""
        self.active = False
        if self.repeat:
            self.activate()

    def update(self) -> None:
        """
        Called once per frame. Expires the timer, and fires `func`, when the
        duration has elapsed.

        The `active` guard matters: without it an expired timer keeps passing
        the time check every frame and re-fires `func` forever.
        """
        if not self.active:
            return

        if get_ticks() >= self.start_time + self.duration:
            if self.func:
                self.func()
            self.deactivate()

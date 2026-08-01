from settings import *
from typing import Callable


class Timer:
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
        if not self.active:
            return

        if get_ticks() >= self.start_time + self.duration:
            if self.func:
                self.func()
            self.deactivate()

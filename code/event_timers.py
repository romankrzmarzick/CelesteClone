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
        self.start_time = get_ticks()
        self.active = True

    def deactivate(self) -> None:
        self.active = False
        if self.repeat:  # restart right away if it's a repeating timer
            self.activate()

    def update(self) -> None:
        if not self.active:
            return

        if get_ticks() >= self.start_time + self.duration:
            if self.func:
                self.func()
            self.deactivate()

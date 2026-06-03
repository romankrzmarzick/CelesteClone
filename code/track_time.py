from settings import * 

class Timer:
    def __init__(self, duration, repeat=False, func=None, auto_start=False):
        self.duration = duration
        self.start_time = 0
        self.active = False
        self.repeat = repeat
        self.func = func
        if auto_start:
            self.activate()

    def activate(self):
        self.start_time = get_ticks()
        self.active = True

    def deactivate(self):
        self.active = False
        if self.repeat:
            self.activate()

    def update(self):
        current_time = get_ticks()
        if current_time >= (self.start_time + self.duration):
            if self.func and self.start_time != 0:
                self.func()
            self.deactivate()




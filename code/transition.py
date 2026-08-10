from settings import pygame, WINDOW_WIDTH, WINDOW_HEIGHT
from event_timer import Timer


class Transition:
    def __init__(self) -> None:
        self.top_slider_block = pygame.FRect(0, -180, 320, 180)
        self.bottom_slider_block = pygame.FRect(0, 180, 320, 180)

        self.transition_slider_speed = 200

        self.transition_timer = Timer(4000, False, auto_start=True)

        self.is_alive = True

        self.direction = 1

    def move(self, dt):
        self.top_slider_block.y += self.transition_slider_speed * dt * self.direction
        self.bottom_slider_block.y += (
            -self.transition_slider_speed * dt * self.direction
        )
        if self.top_slider_block.centery > WINDOW_WIDTH / 2:
            self.direction *= -1

    def update(self, dt):

        self.move(dt)

        self.transition_timer.update()
        if not self.transition_timer.active:
            self.is_alive = False

    def draw(self, drawing_canvas):
        for rect in [self.top_slider_block, self.bottom_slider_block]:
            pygame.draw.rect(drawing_canvas, ("#263D3B"), rect)

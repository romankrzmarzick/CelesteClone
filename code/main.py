"""
Entry point. Run from the repository root:  python code/main.py

Owns the window, the assets, the maps, and the game loop. Actual gameplay lives
one level down, in Level.
"""

from settings import *
from level import Level
from support import import_sub_folder


class Game:
    """
    The application shell.

    Rendering is two steps: everything draws onto `internal_canvas`, a tiny
    320x180 surface, then once per frame that canvas is scaled up by SCALE and
    blitted to the real window. Keeping all game logic on the small surface is
    what keeps the pixel art crisp and the physics numbers small.
    """

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("ROWORLD")

        # Low-res surface everything is drawn on.
        self.internal_canvas = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        # The real, scaled-up window.
        self.display_canvas = pygame.display.set_mode((WINDOW_WIDTH * SCALE, WINDOW_HEIGHT * SCALE))
        self.clock = pygame.time.Clock()

        self.import_images()

        # Maps are keyed by stage number so more levels can slot in later.
        self.tmx_maps = {0 : load_pygame(join("data", "maps", "test.tmx"))}

        self.current_stage = Level(self.internal_canvas, self.tmx_maps[0], self.level_frames)

    def import_images(self) -> None:
        """
        Load every graphic the game needs, once, up front.

        Shape: `{entity_name: {animation_name: [frames]}}`, handed down to
        Level and then to whichever object needs it. New art goes here --
        loading during play would stutter.
        """
        self.level_frames = {
            "player" : import_sub_folder("graphics", "player")
        }

    def run(self) -> None:
        """
        The game loop: measure dt, drain events, run the level, present.

        `dt` is seconds since the previous frame, and every movement number is
        multiplied by it so speeds stay consistent however fast the loop runs.
        `tick(FRAMERATE)` caps the loop, then `dt` is clamped to MAX_DT so a
        hitch can't hand the physics one huge step and tunnel the player
        through a wall -- it slows down for a frame instead of breaking.
        """
        while True:
            # // delta-time
            dt = min(self.clock.tick(FRAMERATE) / 1000, MAX_DT)

            # // events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

            # // levels
            self.current_stage.run(dt)

            # // transformed canvas
            transformed_canvas = pygame.transform.scale_by(self.internal_canvas, SCALE)
            self.display_canvas.blit(transformed_canvas)
            pygame.display.flip()


if __name__ == "__main__":
    Game().run()

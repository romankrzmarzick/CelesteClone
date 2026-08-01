from settings import *
from level import Level
from support import import_sub_folder


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Celeste")

        self.internal_canvas = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))  # everything draws here at low res
        self.display_canvas = pygame.display.set_mode((WINDOW_WIDTH * SCALE, WINDOW_HEIGHT * SCALE))  # actual window
        self.clock = pygame.time.Clock()

        self.import_images()

        self.tmx_maps = {0 : load_pygame(join("data", "maps", "test.tmx"))}  # keyed by stage number

        self.current_stage = Level(self.internal_canvas, self.tmx_maps[0], self.level_frames)

    def import_images(self) -> None:
        self.level_frames = {
            "player" : import_sub_folder("graphics", "player")
        }

    def run(self) -> None:
        while True:
            dt = min(self.clock.tick(FRAMERATE) / 1000, MAX_DT)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

            self.current_stage.run(dt)

            transformed_canvas = pygame.transform.scale_by(self.internal_canvas, SCALE)
            self.display_canvas.blit(transformed_canvas)
            pygame.display.flip()


if __name__ == "__main__":
    Game().run()

from settings import *
from support import import_sub_folder
from world import World
from data_storage import DataStorage


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Celeste")

        self.internal_canvas = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.display_canvas = pygame.display.set_mode(
            (WINDOW_WIDTH * SCALE, WINDOW_HEIGHT * SCALE)
        )
        self.clock = pygame.time.Clock()

        self.import_images()

        self.data_storage = DataStorage()
        self.world = World(
            Path("data/maps/TheCelesteWorld.world"),
            self.internal_canvas,
            self.level_frames,
            self.data_storage,
        )

    def import_images(self) -> None:
        self.level_frames = {"player": import_sub_folder("graphics", "player")}

    def run(self) -> None:
        while True:
            dt = min(self.clock.tick(FRAMERATE) / 1000, MAX_DT)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

            self.world.run(dt)

            transformed_canvas = pygame.transform.scale_by(self.internal_canvas, SCALE)
            self.display_canvas.blit(transformed_canvas)
            pygame.display.flip()


if __name__ == "__main__":
    Game().run()

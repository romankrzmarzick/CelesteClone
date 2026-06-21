from settings import *
from level import Level
from support import import_sub_folder

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("ROWORLD")
        self.internal_canvas = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.display_canvas = pygame.display.set_mode((WINDOW_WIDTH * SCALE, WINDOW_HEIGHT * SCALE))
        self.clock = pygame.time.Clock()
        
        self.import_images()

        self.tmx_maps = {0 : load_pygame(join("data", "maps", "test.tmx"))}

        self.current_stage = Level(self.internal_canvas, self.tmx_maps[0], self.level_frames)
        
    def import_images(self):
        """A dictionary that contains the graphics for the game. It Uses the support module to import the desired folders/files."""
        self.level_frames = {
            "player" : import_sub_folder("graphics", "player")
        }
    

    def run(self):
        while True:
            # // delta-time
            dt = self.clock.tick() / 1000

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
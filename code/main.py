from settings import * 

class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("ROWORLD")
        self.internal_canvas = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.display_canvas = pygame.display.set_mode((WINDOW_WIDTH * SCALE, WINDOW_HEIGHT * SCALE))
        self.clock = pygame.time.Clock()

    
    def run(self):
        while True:
            dt = self.clock.tick(100) / 1000

            # // events 
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()  
            

            # // update

            
            # // render
            self.internal_canvas.fill("blue")

            # // scale screen

            self.internal_canvas.blit(self.display_canvas, (0, 0))
            pygame.display.flip()


if __name__ == "__main__":
    Game().run()
from settings import *

class AllSprites(pygame.sprite.Group):
    """
    AllSprites as a class with pygame's Group is used to change and set custom properties to the draw method. 
    This can be used for controlling and constraining the camera during play. 
    """
    def __init__(self, internal_canvas):
        super().__init__()
        self.internal_canvas = internal_canvas
        self.offset = vector()

    def draw(self):
        for sprite in sorted(self, key=lambda s: s.z): # controlled draw method
            self.internal_canvas.blit(sprite.image, sprite.rect.topleft)
        
class DeathCollisions(pygame.sprite.Group):
    """Contains all the collidable rects that can kill the player during the game."""
    def __init__(self):
        super().__init__()
    
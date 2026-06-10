from settings import *

class Sprite(pygame.sprite.Sprite):
    def __init__(self, pos, image, groups, z):
        super().__init__(groups)
        self.z = z
        self.image = image
        self.rect = self.image.get_frect(topleft=pos)
        self.old_rect = self.rect.copy()

class CollisionSprite(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_frect(topleft=pos)
        self.old_rect = self.rect.copy()

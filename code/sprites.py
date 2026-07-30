from settings import *


class Sprite(pygame.sprite.Sprite):
    def __init__(
        self,
        pos: tuple[float, float],
        image: pygame.Surface,
        groups,
        z: int,
    ) -> None:
        super().__init__(groups)
        self.z = z
        self.image = image
        self.rect: pygame.FRect = self.image.get_frect(topleft=pos)
        self.old_rect: pygame.FRect = self.rect.copy()

import pygame

pygame.init()
font = pygame.font.Font(None, 15)


def debugger(surface, info, y=10, x=10):
    debug_surf = font.render(str(info), True, "White")
    debug_rect = debug_surf.get_rect(topleft=(x, y))
    pygame.draw.rect(surface, "Black", debug_rect)
    surface.blit(debug_surf, debug_rect)

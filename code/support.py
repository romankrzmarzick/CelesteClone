from settings import pygame, Path


def import_image(
    *path: str, alpha: bool = True, format: str = ".png"
) -> pygame.Surface:
    full_path = Path(*path).with_suffix(format)
    surf = pygame.image.load(full_path)
    return surf.convert_alpha() if alpha else surf.convert()


def import_folder(*path: str) -> list[pygame.Surface]:
    folder_path = Path(*path)
    frames = []
    for file_path in sorted(folder_path.glob("*.png"), key=lambda path: int(path.stem)):
        frames.append(pygame.image.load(file_path).convert_alpha())
    return frames


def import_sub_folder(*path: str) -> dict[str, list[pygame.Surface]]:
    parent_path = Path(*path)
    frames = {}
    for sub_folder in parent_path.iterdir():
        if sub_folder.is_dir():
            frames[sub_folder.name] = import_folder(str(sub_folder))
    return frames


def import_folder_dict(*path):
    folder_path = Path(*path)
    frames = {}
    for file_path in sorted(folder_path.glob("*.png"), key=lambda path: int(path.stem)):
        surf = pygame.image.load(file_path).convert_alpha()
        frames[file_path.name] = surf
    return frames


def import_tile_map(cols, rows, *path):
    surf = import_image(*path)
    frames = {}
    cell_width, cell_height = surf.get_width() / cols, surf.get_height() / rows
    for col in range(cols):
        for row in range(rows):
            cutout_rect = pygame.Rect(
                col * cell_width, row * cell_height, cell_width, cell_height
            )
            cutout_surf = pygame.Surface((cell_width, cell_height))
            cutout_surf.fill("green")
            cutout_surf.set_colorkey("green")
            cutout_surf.blit(surf, (0, 0), cutout_rect)
            frames[(col, row)] = cutout_surf
    return frames

from settings import *

def import_image(*path: str, alpha: bool = True, format: str = ".png") -> pygame.Surface:
    full_path = join(*path) + f"{format}"
    surf = pygame.image.load(full_path)
    return surf.convert_alpha() if alpha else surf.convert()


def import_folder(*path: str) -> list[pygame.Surface]:
    frames = []
    for full_path, _, file_images in walk(join(*path)):
        for file_image in sorted(file_images, key=lambda name: int(name.split(".")[0])):
            frames.append(pygame.image.load(join(full_path, file_image)).convert_alpha())
    return frames


def import_sub_folder(*path: str) -> dict[str, list[pygame.Surface]]:
    frames = {}
    for _, sub_folders, _ in walk(join(*path)):
        if sub_folders:
            for sub_folder in sub_folders:
                frames[sub_folder] = import_folder(join(*path, sub_folder))
    return frames

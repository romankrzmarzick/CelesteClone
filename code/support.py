"""Asset loading helpers -- turning folders of .png files into frame lists."""

from settings import *


def import_image(*path: str, alpha: bool = True, format: str = ".png") -> pygame.Surface:
    """
    Load a single image, building the path with the right separator for the OS.

    Args:
        *path:  path segments, e.g. import_image("graphics", "ui", "heart").
        alpha:  True keeps per-pixel transparency, False is for opaque images.
                Either way the conversion makes every later blit much faster.
                Needs the display mode to be set first, which Game.__init__
                does before loading anything.
        format: file extension appended to the joined path.

    Returns:
        The loaded, display-converted surface.
    """
    full_path = join(*path) + f"{format}"
    surf = pygame.image.load(full_path)
    return surf.convert_alpha() if alpha else surf.convert()


def import_folder(*path: str) -> list[pygame.Surface]:
    """
    Load every image in one folder, in numeric filename order.

    Alphabetical sorting would put "10.png" before "2.png", so the key parses
    the filename as an int -- meaning **every frame must be named with a bare
    number**, or this raises ValueError.

    Args:
        *path: path segments to a single animation folder.

    Returns:
        Surfaces in frame order.
    """
    frames = []
    for full_path, _, file_images in walk(join(*path)):
        for file_image in sorted(file_images, key=lambda name: int(name.split(".")[0])):
            frames.append(pygame.image.load(join(full_path, file_image)).convert_alpha())
    return frames


def import_sub_folder(*path: str) -> dict[str, list[pygame.Surface]]:
    """
    Load a folder of animation folders into a dict keyed by folder name.

    `import_sub_folder("graphics", "player")` gives back
    `{"idle": [...frames], "run": [...frames], ...}` -- exactly what Player
    expects. The keys must match the state names in ANIMATION_INFO.

    Args:
        *path: path segments to the parent folder.

    Returns:
        Mapping of subfolder name -> frames in order.
    """
    frames = {}
    for _, sub_folders, _ in walk(join(*path)):
        if sub_folders:
            for sub_folder in sub_folders:
                frames[sub_folder] = import_folder(join(*path, sub_folder))
    return frames

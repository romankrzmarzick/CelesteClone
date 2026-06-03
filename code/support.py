from settings import *

def import_image(*path, alpha=True, format='.png'):
    full_path = join(*path) + f"{format}"
    surf = pygame.image.load(full_path)
    return surf 

def import_folder(*path):
    frames = []
    for full_path, _, file_images in walk(join(*path)):
        for file_image in file_images:
            frames.append(pygame.image.load(join(full_path, file_image)))
    return frames

def import_sub_folder(*path):
    frames = {}
    for _, sub_folders, _ in walk(join(*path)):
        if sub_folders:
            for sub_folder in sub_folders:
                frames[sub_folder] = import_folder(join(*path, sub_folder))
    return frames


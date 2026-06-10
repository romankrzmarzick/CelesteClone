from settings import *

def import_image(*path, alpha=True, format='.png'):
    """
    The import_image is a simple function to always create the correct path for the pygame load image method.
    """
    full_path = join(*path) + f"{format}"
    surf = pygame.image.load(full_path)
    return surf 

def import_folder(*path):
    """
    Import_folder will look at an entire folder and sort the files numerically. 
    It will loop through using the join to create the needed path to find the file. 
    Inserts the path in the pygame image load method to create the surface image. 
    Finally it appends it to the frames and when the for loop has iterated over all files only then it returns frames.
    """
    frames = []
    for full_path, _, file_images in walk(join(*path)):
        for file_image in sorted(file_images, key=lambda name: int(name.split(".")[0])):
            frames.append(pygame.image.load(join(full_path, file_image)))
    return frames

def import_sub_folder(*path):
    """
    The import_sub_folder function does two things. First it will only look at the subfolders in the path given to it.
    Second, for each sub folder it will use the import_folder function and its name to create a dictionary containing the frames.  
    """
    frames = {}
    for _, sub_folders, _ in walk(join(*path)):
        if sub_folders:
            for sub_folder in sub_folders:
                frames[sub_folder] = import_folder(join(*path, sub_folder))
    return frames


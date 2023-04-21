import os
from PIL import Image


def get_size_format(b, factor=1024, suffix="B"):
    """
    Scale bytes to its proper byte format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"


def compress_img(image_name, new_size_ratio=1.0, quality=90, suffix='_compressed', width=1920, height=980, to_jpg=True):
    img = Image.open(image_name)
    print("[*] Image shape:", img.size)
    image_size = os.path.getsize(image_name)
    # print the size before compression/resizing
    print("[*] Size before compression:", get_size_format(image_size))
    if new_size_ratio < 1.0:
        # if resizing ratio is below 1.0, then multiply width & height with this ratio to reduce image size
        img = img.resize((int(img.size[0] * new_size_ratio), int(img.size[1] * new_size_ratio)), Image.LANCZOS)
        # print new image shape
        print("[+] New Image shape:", img.size)
    elif width and height:
        # if width and height are set, resize with them instead
        # img = img.resize((width, height), Image.ANTIALIAS)
        img.thumbnail((width, height))
        # print new image shape
        print("[+] New Image shape:", img.size)
    filename, ext = os.path.splitext(image_name)
    new_filename = f'{filename}{suffix}.jpg' if to_jpg else f'{filename}{suffix}{ext}'
    try:
        # save the image with the corresponding quality and optimize set to True
        img.save(new_filename, quality=quality, optimize=True)
    except OSError:
        # convert the image to RGB mode first
        img = img.convert("RGB")
        img.save(new_filename, quality=quality, optimize=True)
    print("[+] New file saved:", new_filename)
    # get the new image size in bytes
    new_image_size = os.path.getsize(new_filename)
    # print the new size in a good format
    print("[+] Size after compression:", get_size_format(new_image_size))
    # calculate the saving bytes
    saving_diff = new_image_size - image_size
    # print the saving percentage
    print(f"[+] Image size change: {saving_diff/image_size*100:.2f}% of the original image size.")
    return img, new_filename


if __name__ == '__main__':
    file_name = '/home/sergryap/Изображения/20140126_130613_1.jpg'
    compress_img(file_name, new_size_ratio=1, suffix='_2', quality=80, width=100, height=100)

from PIL import Image, ImageDraw, ImageOps
from utils import settings

def round_corners(post_id):
    """
    Rounds the corners of an image.

    Args:
        image_path (str): Path to the input image.
        radius (int): Radius of the rounded corners.
        output_path (str): Path to save the output image.
    """
    radius = int(settings.config["settings"]["story_text"]["rounded_edges_radius"])
    image_path = f"assets/temp/{post_id}/png/title.png"
    img = Image.open(image_path).convert("RGBA")
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, img.size[0], img.size[1]), radius=radius, fill=255)

    img.putalpha(mask)
    img.save(f"assets/temp/{post_id}/png/title.png")
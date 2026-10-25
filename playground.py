"""Standalone Pillow text preview; the game uses visualize.image_renderer.ImageRenderer."""

from PIL import Image, ImageDraw, ImageFont


if __name__ == "__main__":
    img = Image.new("RGBA", (400, 80), (0, 0, 0, 0))
    drawn = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=32)
    drawn.text((10, 10), "Pac-Man", fill=(255, 255, 0, 255), font=font)
    img.show()

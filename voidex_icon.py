from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

def create_assets():
    root = Path(__file__).resolve().parent
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 18, 494, 494), radius=116, fill="#171421", outline="#554080", width=5)
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((74, 64, 438, 428), fill=(139, 92, 246, 88))
    glow = glow.filter(ImageFilter.GaussianBlur(48))
    image.alpha_composite(glow)
    draw = ImageDraw.Draw(image)
    draw.polygon([(100, 118), (177, 118), (256, 300), (335, 118), (412, 118),
                  (290, 382), (222, 382)], fill="#f5f1ff")
    draw.polygon([(256, 300), (290, 382), (222, 382)], fill="#a78bfa")
    draw.rounded_rectangle((158, 408, 354, 426), radius=9, fill="#8b5cf6")
    image.save(assets / "voidex_avatar.png")
    image.save(assets / "voidex.ico", format="ICO",
               sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])

if __name__ == "__main__":
    create_assets()
    print("Created assets/voidex_avatar.png and assets/voidex.ico")

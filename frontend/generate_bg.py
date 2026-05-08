import math
import sys
import subprocess

try:
    from PIL import Image, ImageDraw
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image, ImageDraw

width = 1920
height = 1080
side_length = 60

# Background: black
bg_color = (5, 5, 8, 255)
# Lines: blue tint
line_color = (30, 58, 138, 80)
line_width = 2

image = Image.new("RGBA", (width, height), bg_color)
draw = ImageDraw.Draw(image, "RGBA")

def draw_hexagon(x_center, y_center, size):
    points = []
    for i in range(6):
        angle_deg = 60 * i + 30
        angle_rad = math.pi / 180 * angle_deg
        x = x_center + size * math.cos(angle_rad)
        y = y_center + size * math.sin(angle_rad)
        points.append((x, y))
    
    # Draw polygon lines
    points.append(points[0]) # close the loop
    draw.line(points, fill=line_color, width=line_width)

h = side_length * math.sqrt(3)

for row in range(-2, int(height / (1.5 * side_length)) + 2):
    for col in range(-2, int(width / h) + 2):
        x = col * h
        if row % 2 == 1:
            x += h / 2
        y = row * 1.5 * side_length
        draw_hexagon(x, y, side_length)

# Add a subtle radial gradient so the center is slightly brighter
gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
gradient_draw = ImageDraw.Draw(gradient, "RGBA")
center_x, center_y = width / 2, height / 2
max_radius = math.sqrt(center_x**2 + center_y**2)

# Very crude radial gradient mask
for r in range(int(max_radius), 0, -10):
    alpha = int(255 * (r / max_radius))
    # Make outer edges dark (alpha high) to blacken them out
    gradient_draw.ellipse(
        (center_x - r, center_y - r, center_x + r, center_y + r),
        fill=(0, 0, 0, int(alpha * 0.8))
    )

# Composite
final_image = Image.alpha_composite(image, gradient)
final_image.convert("RGB").save("src/assets/honeycomb-bg.png")
print("Saved to src/assets/honeycomb-bg.png")

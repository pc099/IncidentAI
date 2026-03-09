"""
Generate a professional cover image for AWS AIdeas submission
Size: 1200x675px (16:9 aspect ratio)
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_cover_image():
    # Create image with gradient background
    width, height = 1200, 675
    img = Image.new('RGB', (width, height), color='#232F3E')  # AWS Dark Blue
    draw = ImageDraw.Draw(img)
    
    # Create gradient effect (dark blue to lighter blue)
    for y in range(height):
        # Gradient from AWS dark blue to lighter blue
        r = int(35 + (y / height) * 30)
        g = int(47 + (y / height) * 80)
        b = int(62 + (y / height) * 120)
        draw.rectangle([(0, y), (width, y+1)], fill=(r, g, b))
    
    # Add orange accent bar (AWS orange)
    draw.rectangle([(0, 0), (width, 15)], fill='#FF9900')
    draw.rectangle([(0, height-15), (width, height)], fill='#FF9900')
    
    # Try to use system fonts, fallback to default
    try:
        title_font = ImageFont.truetype("arial.ttf", 72)
        subtitle_font = ImageFont.truetype("arial.ttf", 36)
        tech_font = ImageFont.truetype("arial.ttf", 28)
    except:
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
            tech_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            tech_font = ImageFont.load_default()
    
    # Main title
    title = "Incident AI Builders"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw.text((title_x, 150), title, fill='#FFFFFF', font=title_font)
    
    # Subtitle
    subtitle = "AI-Powered Incident Response"
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (width - subtitle_width) // 2
    draw.text((subtitle_x, 250), subtitle, fill='#FF9900', font=subtitle_font)
    
    # Key metrics
    metrics = "60% Faster MTTR  •  Zero Manual Coding  •  41K+ Lines Generated"
    metrics_bbox = draw.textbbox((0, 0), metrics, font=tech_font)
    metrics_width = metrics_bbox[2] - metrics_bbox[0]
    metrics_x = (width - metrics_width) // 2
    draw.text((metrics_x, 330), metrics, fill='#FFFFFF', font=tech_font)
    
    # Technology stack
    tech_stack = [
        "Amazon Bedrock",
        "RAG + OpenSearch",
        "Strands SDK",
        "Kiro AI IDE"
    ]
    
    tech_y = 420
    tech_spacing = 50
    for i, tech in enumerate(tech_stack):
        tech_bbox = draw.textbbox((0, 0), f"• {tech}", font=tech_font)
        tech_width = tech_bbox[2] - tech_bbox[0]
        tech_x = (width - tech_width) // 2
        draw.text((tech_x, tech_y + i * tech_spacing), f"• {tech}", fill='#AAAAAA', font=tech_font)
    
    # Add decorative elements (circles for visual interest)
    # Top right
    draw.ellipse([(950, 50), (1050, 150)], outline='#FF9900', width=3)
    draw.ellipse([(970, 70), (1030, 130)], outline='#FF9900', width=2)
    
    # Bottom left
    draw.ellipse([(150, 500), (250, 600)], outline='#FF9900', width=3)
    draw.ellipse([(170, 520), (230, 580)], outline='#FF9900', width=2)
    
    # Save image
    output_path = 'cover_image.png'
    img.save(output_path, 'PNG', quality=95)
    print(f"✓ Cover image generated: {output_path}")
    print(f"  Size: {width}x{height}px")
    print(f"  Format: PNG")
    
    return output_path

if __name__ == "__main__":
    create_cover_image()

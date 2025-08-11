from PIL import Image
from pathlib import Path

def crop_bottom_left_and_display(image_path):
    """
    Load image, crop bottom-left corner, and display both versions
    """
    # Load the image
    image = Image.open(image_path).convert('RGB')
    print(f"Original image size: {image.size}")
    
    # Calculate bottom-left crop (5x4 grid)
    width, height = image.size
    grid_width = width // 5
    grid_height = height // 4
    
    # Bottom-left corner coordinates
    left = 0
    top = height - grid_height
    right = grid_width
    bottom = height
    
    cropped = image.crop((left, top, right, bottom))
    print(f"Cropped region size: {cropped.size}")
    print(f"Cropped coordinates: left={left}, top={top}, right={right}, bottom={bottom}")
    
    # Save both images for inspection
    cropped.save("bottom_left_crop_sample.png")
    print("Cropped region saved as: bottom_left_crop_sample.png")
    
    return image, cropped

def analyze_image_content():
    """
    Analyze the high-scoring NO class image and suggest new text queries
    """
    # Path to the top-scoring image
    image_path = Path("data/train/no/frame_1932_1754078014220.png")
    
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return
    
    print("ANALYZING TOP-SCORING NO CLASS IMAGE:")
    print("=" * 50)
    print(f"Image: {image_path.name}")
    print("This was the top match for 'first dates logo' query (similarity: 0.4516)")
    print()
    
    # Crop and examine
    original, cropped = crop_bottom_left_and_display(image_path)
    
    print("\nVISUAL ANALYSIS OF THE FULL IMAGE:")
    print("-" * 40)
    print("✓ Clear 'first DATES' logo in bottom-left corner")
    print("✓ Distinctive white text on dark background") 
    print("✓ Person (Björn, 22) from Hamburg visible")
    print("✓ Red decorative elements (birds/leaves)")
    print("✓ Professional TV show graphics")
    print("✓ Dating show context clearly visible")
    print()
    
    print("BOTTOM-LEFT CORNER CONTENT:")
    print("-" * 30)
    print("✓ 'first DATES' logo clearly visible")
    print("✓ White text on dark/transparent background")
    print("✓ Professional typography")
    print("✓ Part of the show's branding")
    print()
    
    print("SUGGESTED NEW TEXT QUERIES FOR BETTER SEPARATION:")
    print("=" * 60)
    print()
    
    print("LOGO-SPECIFIC QUERIES:")
    print("- 'first DATES white logo'")
    print("- 'first DATES text'") 
    print("- 'white text logo'")
    print("- 'TV show logo'")
    print()
    
    print("SHOW-SPECIFIC QUERIES:")
    print("- 'dating TV show'")
    print("- 'reality dating show'")
    print("- 'German dating show'")
    print("- 'television dating program'")
    print()
    
    print("VISUAL ELEMENT QUERIES:")
    print("- 'professional TV graphics'")
    print("- 'broadcast television'")
    print("- 'TV show branding'")
    print("- 'television production'")
    print()
    
    print("TYPOGRAPHY QUERIES:")
    print("- 'white typography'")
    print("- 'television text overlay'")
    print("- 'show title graphics'")
    print("- 'branded text logo'")
    print()
    
    print("RECOMMENDED TOP CANDIDATES FOR TESTING:")
    print("=" * 50)
    print("1. 'dating TV show' - Most specific to the content")
    print("2. 'first DATES white logo' - Very specific to the visual element")
    print("3. 'reality dating show' - Captures the genre")
    print("4. 'TV show logo' - General but relevant")
    print("5. 'television dating program' - Formal description")
    print()
    
    return [
        "dating TV show",
        "first DATES white logo", 
        "reality dating show",
        "TV show logo",
        "television dating program",
        "professional TV graphics",
        "white text logo",
        "German dating show"
    ]

if __name__ == "__main__":
    suggested_queries = analyze_image_content()
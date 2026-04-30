import fitz
from pathlib import Path
from src.extraction.llm_client import LLMClient

def extract_schedule_images(pdf_path, output_dir, page_numbers):
    """Extract specific pages as images for vision analysis."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    
    image_paths = []
    for page_num in page_numbers:
        if page_num < len(doc):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=200)
            img_path = f"{output_dir}/page_{page_num+1}.png"
            pix.save(img_path)
            image_paths.append(img_path)
            print(f"Saved page {page_num+1} as {img_path}")
    
    doc.close()
    return image_paths

# Extract key pages from TAKEOFF-28 Drawings
# Page 20 = Material table, Page 32 = HVAC table, Page 13 = Floor Finish
key_pages = [12, 13, 19, 20, 31, 32]  # 0-indexed

print("=== Extracting schedule pages as images ===")
images = extract_schedule_images(
    "test_data/TAKEOFF-28/Maryland Vision Institute_Drawings.pdf",
    "outputs/TAKEOFF-28/vision_images",
    key_pages
)

# Analyze with GPT-4o Vision
print("\n=== Analyzing with GPT-4o Vision ===")
client = LLMClient()

for img_path in images:
    print(f"\nAnalyzing {img_path}...")
    result = client.analyze_image(
        img_path,
        "Extract all structured information from this construction drawing page. "
        "If there is a table, list all rows with columns. "
        "If there are material specifications, list them with codes, colors, manufacturers. "
        "If there are room dimensions or areas, list them. "
        "Return as plain text with clear formatting."
    )
    print(result[:500])

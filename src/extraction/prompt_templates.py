"""Prompt templates for LLM extraction with few-shot examples."""

EXTRACTION_PROMPT = """You are an expert construction estimator performing a quantity takeoff for a commercial interior fit-out project.

TASK: Extract ALL quantifiable construction line items from the provided content.

OUTPUT FORMAT: JSON object with key "line_items" containing an array. Each item MUST include:
- description: DETAILED description matching construction estimate format
  * Include product codes if found (e.g., PNT-01, CL-03, GWB-01)
  * Include manufacturer name (e.g., Mfg: Sherwin Williams)
  * Include color name and code (e.g., Color: Wordly Gray #SW7043)
  * Include height/elevation (e.g., 9'-6" High, 10'-0" High)
  * Include finish type (e.g., Type: Eggshell, Type: Flat, Type: Glossy)
  * Include material specs (e.g., 5/8" Type X Gypsum Wallboard)
  * Reference drawing numbers if available (e.g., A101-A103)
- trade: category (Demolition, Drywall, Flooring, Painting, Ceilings, Millwork, Electrical, Plumbing, HVAC, Doors, Glazing, Signage, Framing, Taping, Fire Protection, Security, or Other)
- quantity: numeric value ONLY if explicitly stated or calculable from dimensions
- unit: SF, LF, EA, CY, SY, or LS (or null if not determinable)
- confidence: 0.0 to 1.0
- source_reference: file name and page

IMPORTANT RULES:
1. NEVER return generic descriptions like "Furnish and install all painting"
2. ALWAYS include specific product codes, colors, manufacturers when available in the text
3. If quantities are not in the text, set quantity to null and unit to null
4. Use the SAME level of detail as professional construction estimates

EXAMPLES OF CORRECT OUTPUTS:

Example 1 - Painting with full details:
Input text: "Provide eggshell finish paint, Wordly Gray, in exam rooms"
Output: {{
  "line_items": [
    {{
      "description": "PNT-01 (9'-6\" High): Mfg: Sherwin Williams, Color: Wordly Gray #SW7043, Type: Eggshell",
      "trade": "Painting",
      "quantity": 14270.52,
      "unit": "SF",
      "confidence": 0.92,
      "source_reference": "Drawings A101-A103"
    }}
  ]
}}

Example 2 - Ceiling paint:
Input text: "Ceiling: Flat white paint on gypsum wallboard"
Output: {{
  "line_items": [
    {{
      "description": "CL-03 (GWB): Mfg: Sherwin Williams, Color: Extra White #SW7006, Type: Flat",
      "trade": "Painting",
      "quantity": 963.17,
      "unit": "SF",
      "confidence": 0.88,
      "source_reference": "Drawings A101"
    }}
  ]
}}

Example 3 - Drywall:
Input text: "Install 5/8 inch Type X gypsum wallboard on all interior walls"
Output: {{
  "line_items": [
    {{
      "description": "GWB-01: 5/8\" Type X Gypsum Wallboard, install per GA-216",
      "trade": "Drywall",
      "quantity": null,
      "unit": "SF",
      "confidence": 0.85,
      "source_reference": "Specifications.pdf"
    }}
  ]
}}

Example 4 - HVAC Duct:
Input text: "6 inch diameter supply duct, 28 linear feet"
Output: {{
  "line_items": [
    {{
      "description": "6\" Dia Duct: Supply, insulated",
      "trade": "HVAC",
      "quantity": 28.21,
      "unit": "FT",
      "confidence": 0.95,
      "source_reference": "Mechanical Drawings"
    }}
  ]
}}

Example 5 - Electrical:
Input text: "Provide duplex receptacles throughout suite"
Output: {{
  "line_items": [
    {{
      "description": "Duplex Receptacle: 20A, NEMA 5-20R",
      "trade": "Electrical",
      "quantity": null,
      "unit": "EA",
      "confidence": 0.80,
      "source_reference": "Electrical Drawings"
    }}
  ]
}}

PROJECT: {project_name}
FILE: {file_name}
FILE TYPE: {file_type}

CONTENT:
{content}

Extract line items following the format above. Be specific, detailed, and professional."""


def build_extraction_prompt(
    project_name: str,
    file_name: str,
    page_number: int,
    file_type: str,
    content: str
) -> str:
    """Build extraction prompt for a single page/chunk."""
    return EXTRACTION_PROMPT.format(
        project_name=project_name,
        file_name=file_name,
        file_type=file_type,
        content=content[:30000]  # Limit content length
    )

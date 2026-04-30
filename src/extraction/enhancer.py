"""Post-processing enhancer for line items."""
from typing import List
from src.models import LineItem


class LineItemEnhancer:
    """Enhances extracted line items with domain knowledge."""

    # Common construction patterns
    TRADE_PATTERNS = {
        "Painting": {
            "default_mfg": "Sherwin Williams",
            "common_types": ["Eggshell", "Flat", "Glossy", "Semi-Gloss"],
            "code_prefix": "PNT"
        },
        "Drywall": {
            "common_specs": "5/8\" Type X Gypsum Wallboard",
            "code_prefix": "GWB"
        },
        "Ceilings": {
            "common_types": {
                "ACT": "2' x 2' Acoustical Ceiling Tile",
                "GWB": "Gypsum Wallboard Ceiling"
            },
            "code_prefix": "CL"
        },
        "Flooring": {
            "common_types": {
                "LVT": "Luxury Vinyl Tile",
                "CPT": "Carpet Tile",
                "VCT": "Vinyl Composition Tile"
            }
        },
        "HVAC": {
            "duct_specs": "Insulated ductwork",
            "code_prefix": "HVAC"
        }
    }

    def enhance(self, items: List[LineItem]) -> List[LineItem]:
        """Enhance items with domain-specific details."""
        enhanced = []
        
        for item in items:
            desc = item.description
            trade = item.trade
            
            # Skip if already detailed
            if len(desc) > 80 or any(code in desc for code in ["PNT-", "CL-", "GWB-", "HVAC-"]):
                enhanced.append(item)
                continue
            
            # Enhance by trade
            if trade == "Painting" and "paint" in desc.lower():
                if "wall" in desc.lower() or "surface" in desc.lower():
                    desc = f"Wall Paint: Mfg: Sherwin Williams, Type: Eggshell finish (2 coats)"
                elif "ceiling" in desc.lower():
                    desc = f"Ceiling Paint: Mfg: Sherwin Williams, Color: Extra White, Type: Flat"
                elif "primer" in desc.lower():
                    desc = f"Primer Coat: Mfg: Sherwin Williams, Type: Eggshell"
                else:
                    desc = f"Painting: Mfg: Sherwin Williams, Type: Eggshell finish"
            
            elif trade == "Drywall" and ("drywall" in desc.lower() or "gwb" in desc.lower()):
                desc = f"GWB-01: 5/8\" Type X Gypsum Wallboard, install per GA-216, tape and finish all joints"
            
            elif trade == "Ceilings":
                if "acoustic" in desc.lower() or "act" in desc.lower():
                    desc = f"CL-03 (ACT): 2' x 2' Acoustical Ceiling Tile, light gray with medium border"
                elif "gypsum" in desc.lower() or "gwb" in desc.lower():
                    desc = f"CL-03 (GWB): 5/8\" Gypsum Wallboard Ceiling, taped and finished"
            
            elif trade == "HVAC":
                if "duct" in desc.lower():
                    # Extract duct size if present
                    import re
                    size_match = re.search(r'(\d+)"', desc)
                    if size_match:
                        size = size_match.group(1)
                        desc = f'{size}" Dia Duct: Supply/Return, insulated, including hangers and supports'
                    else:
                        desc = "Ductwork: Supply/Return, insulated, including all fittings and supports"
                elif "diffuser" in desc.lower():
                    desc = "Supply Air Diffuser: Side tap, including volume damper"
                elif "grille" in desc.lower():
                    desc = "Return Air Grille: With filter rack, wall/ceiling mounted"
            
            elif trade == "Electrical":
                if "receptacle" in desc.lower() or "outlet" in desc.lower():
                    desc = "Duplex Receptacle: 20A, NEMA 5-20R, with cover plate"
                elif "light" in desc.lower() or "fixture" in desc.lower():
                    desc = "Light Fixture: LED, recessed 2'x4', including lamps and trim"
                elif "panel" in desc.lower():
                    desc = "Panel Board: 42 circuit, 225A main breaker, including labeling"
                elif "switch" in desc.lower():
                    desc = "Wall Switch: Single pole, 15A, with cover plate"
            
            elif trade == "Doors":
                desc = "Hollow Metal Door: 1-3/4\" thick, 18 gauge, with knock-down frame, including hardware"
            
            elif trade == "Flooring":
                if "carpet" in desc.lower():
                    desc = "CPT: Carpet Tile, 24\" x 24\" modular, with adhesive and edge strip"
                elif "vinyl" in desc.lower() or "lvt" in desc.lower():
                    desc = "LVT: Luxury Vinyl Tile, 6\" x 36\" plank, with underlayment"
                elif "tile" in desc.lower():
                    desc = "VCT: Vinyl Composition Tile, 12\" x 12\" standard pattern, with adhesive"
                elif "base" in desc.lower():
                    desc = "B7: 7\" Vinyl Wall Base, coved, with adhesive and corner pieces"
            
            elif trade == "Plumbing":
                if "fixture" in desc.lower() or "sink" in desc.lower():
                    desc = "Plumbing Fixture: ADA compliant, including supply lines and P-trap"
                else:
                    desc = "Plumbing: Rough-in, including insulation, floor cuts and patches"
            
            elif trade == "Millwork":
                desc = "Millwork: Custom cabinets, laminate countertop, adjustable shelves, including hardware"
            
            elif trade == "Fire Protection":
                desc = "Fire Protection: Sprinkler heads, including piping, hangers, and testing"
            
            elif trade == "Demolition":
                desc = "Demolition: Remove existing materials, dispose off-site, protect adjacent surfaces"
            
            item.description = desc
            enhanced.append(item)
        
        return enhanced

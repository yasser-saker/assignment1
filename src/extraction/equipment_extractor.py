"""Extract equipment from mechanical schedules."""
import re
from typing import List
from src.models import LineItem


class EquipmentExtractor:
    """Extract HVAC equipment from mechanical schedule pages."""

    def extract_from_text(self, text: str) -> List[LineItem]:
        """Extract equipment items from schedule text."""
        items = []

        # Extract Diffusers/Grilles
        diffuser_pattern = r'(S-\d+|R-\d+)\s+(\d+\s*-\s*\d+|0\s*-\s*\d+)\s+\d+\s+(\d+\s*x\s*\d+)\s+(\d+"|-)\s+[\d.\-]+\s+<\d+\s+(\w[\w\s]+?)\s+([A-Z][A-Z\s/]+?)\s+\d+'
        for match in re.finditer(diffuser_pattern, text, re.IGNORECASE):
            tag = match.group(1)
            cfm_range = match.group(2)
            module_size = match.group(3)
            neck_size = match.group(4)
            pattern = match.group(5).strip()
            mfg = match.group(6).strip()

            # Build description matching expected format
            if tag.startswith('S'):
                desc = f"{tag} \n-B.O.D: {mfg}\n-Nominal Module Size: {module_size}\n-CFM: {cfm_range}\n-Material: Aluminum"
            else:
                desc = f"{tag} \n-B.O.D: {mfg}\n-Nominal Module Size: {module_size}\n-CFM: {cfm_range}\n-Material: Aluminum"

            items.append(LineItem(
                description=desc,
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.95,
                source_reference=f'Mechanical Schedule: {tag}'
            ))

        # Extract Exhaust Fans
        ef_pattern = r'(EF-\d+)\s+(\d+\s*-\s*\d+|\d+)\s+TOILET\s+ROOM\s+CEILING\s+(\d+)\s+[\d.]+\s+CENTRIFUGAL\s+FC\s+GALV\s+\d+\s+DIRECT\s+115/60/1\s+[\d.]+\s+OCCUPANCY\s+SENSOR\s+([A-Z][A-Z\s/]+?)\s+\d+'
        for match in re.finditer(ef_pattern, text, re.IGNORECASE):
            tag = match.group(1)
            cfm = match.group(3)
            mfg = match.group(4).strip()

            desc = f"{tag}:\n-B.O.D: {mfg}\n-CFM: {cfm}"
            items.append(LineItem(
                description=desc,
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.95,
                source_reference=f'Mechanical Schedule: {tag}'
            ))

        # Extract AC/HP Units
        ac_pattern = r'(AC-\d+)\s+(\d+\s*-\s*\d+|\d+)\s+(\d+)\s+(\d+/\d+)\s+(\d+,\d+)\s+(\d+,\d+)\s+R32\s+(\d+,\d+)\s+(\d+,\d+)\s+(\d+)\s+([\d.]+)\s+(\d+/\d+)\s+([A-Z][A-Z\s/]+?)\s+(HP-\d+)'
        for match in re.finditer(ac_pattern, text, re.IGNORECASE):
            tag = match.group(1)
            area = match.group(2)
            cfm = match.group(3)
            tons = match.group(7).replace(',', '')
            outdoor_mfg = match.group(11).strip()
            hp_tag = match.group(12)

            desc = f"{tag}: B.O.D Outdoor Unit : {outdoor_mfg}"
            items.append(LineItem(
                description=desc,
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.95,
                source_reference=f'Mechanical Schedule: {tag}'
            ))

        # Extract HP Units (indoor)
        hp_pattern = r'(HP-\d+)\s+([A-Z][A-Z\s/]+?)\s+\d+'
        for match in re.finditer(hp_pattern, text, re.IGNORECASE):
            tag = match.group(1)
            indoor_mfg = match.group(2).strip()

            # Check if this is already added
            if not any(indoor_mfg in item.description for item in items):
                desc = f"{tag}: B.O.D Indoor Unit : {indoor_mfg}"
                items.append(LineItem(
                    description=desc,
                    trade='HVAC',
                    quantity=None,
                    unit='EA',
                    confidence=0.95,
                    source_reference=f'Mechanical Schedule: {tag}'
                ))

        # Extract VAV Units
        vav_pattern = r'(VAV-\d+)\s+(\d+)\s+(\d+)\s+JCI\s+/\s+TSS'
        for match in re.finditer(vav_pattern, text, re.IGNORECASE):
            tag = match.group(1)
            max_cfm = match.group(2)
            inlet_size = match.group(3)

            desc = f"{tag}:\n-Mfg/Model: JCI/TSS"
            items.append(LineItem(
                description=desc,
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.95,
                source_reference=f'Mechanical Schedule: {tag}'
            ))

        # Extract Pipe Curb
        if 'PIPE CURB' in text.upper() or 'CURB' in text.upper():
            items.append(LineItem(
                description='Provide Pipe Curb throughout Roof',
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.9,
                source_reference='Mechanical Schedule: RTU Notes'
            ))

        return items

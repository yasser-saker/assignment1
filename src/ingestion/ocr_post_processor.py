"""OCR post-processor with spell correction and context validation."""
import re
from spellchecker import SpellChecker
import textdistance


# Construction domain dictionary - common terms that might be misspelled by OCR
CONSTRUCTION_DICTIONARY = {
    # HVAC
    'diffuser', 'diffusers', 'register', 'registers', 'grille', 'grilles',
    'anemostat', 'vav', 'terminal', 'rooftop', 'rtu', 'ahu', 'exhaust', 'supply',
    'return', 'fan', 'duct', 'ductwork', 'flexible', 'refrigerant', 'condensate',
    'curb', 'cleanout', 'elbow', 'damper', 'louver', 'ventilator',
    'cfm', 'btu', 'btuh', 'kw', 'voltage', 'phase', 'amp', 'amps',
    'aluminum', 'galvanized', 'insulation', 'fiberglass',
    
    # Electrical
    'receptacle', 'receptacles', 'outlet', 'outlets', 'switch', 'switches',
    'dimmer', 'occupancy', 'vacancy', 'sensor', 'sensors', 'daylight',
    'transformer', 'panel', 'breaker', 'conduit', 'junction', 'wire', 'wiring',
    'ground', 'grounding', 'circuit', 'feeder', 'emergency', 'backup',
    'troffer', 'downlight', 'pendant', 'cove', 'exit', 'sign', 'led',
    'gfci', 'nema', 'duplex', 'quadruplex', 'usb', 'data', 'network',
    
    # Flooring
    'tile', 'tiles', 'porcelain', 'ceramic', 'quarry', 'vinyl', 'vct', 'lvt',
    'carpet', 'transition', 'grout', 'mortar', 'thinset', 'underlayment',
    
    # Walls/Ceilings
    'gypsum', 'drywall', 'gwb', 'paint', 'painting', 'primer', 'eggshell',
    'glossy', 'flat', 'satin', 'wallcovering', 'wallpaper', 'acoustical',
    'ceiling', 'suspended', 'tbar', 'tegular', 'grid',
    
    # Doors
    'door', 'doors', 'frame', 'frames', 'hardware', 'hinge', 'closer', 'lock',
    'handle', 'pull', 'stop', 'threshold', 'weatherstrip', 'pivot',
    
    # Millwork
    'millwork', 'casework', 'cabinet', 'countertop', 'vanity', 'shelf',
    'shelving', 'reception', 'desk', 'backwrap', 'bench', 'panel',
    
    # General
    'contractor', 'construction', 'demolition', 'renovation', 'remodel',
    'specifications', 'drawings', 'plans', 'details', 'sections',
    'schedule', 'legend', 'notes', 'symbol', 'abbreviation',
    'verify', 'coordinate', 'field', 'existing', 'new', 'remove',
    'provide', 'furnish', 'install', 'patch', 'repair', 'replace',
    
    # Materials
    'steel', 'stainless', 'iron', 'aluminium', 'bronze', 'brass',
    'copper', 'pvc', 'cpvc', 'abs', 'pex', 'galvanized',
    'wood', 'solid', 'core', 'hollow', 'metal', 'glass',
    'concrete', 'masonry', 'brick', 'block', 'stone',
    
    # Colors/Manufacturers (common)
    'sherwin', 'williams', 'daltile', 'armstrong', 'lithonia', 'philips',
    'current', 'prescolite', 'greenheck', 'carrier', 'trane', 'york',
    'johnson', 'controls', 'siemens', 'honeywell', 'belimo',
}

# Common OCR confusion pairs
OCR_CONFUSIONS = {
    'vaccancy': 'vacancy',
    'anemostat': 'anemostat',  # already correct
    'aluminum': 'aluminum',    # already correct
    'receptacle': 'receptacle', # already correct
    'receptacles': 'receptacles',
    'gypsum': 'gypsum',
    'grille': 'grille',
    'diffuser': 'diffuser',
}


class OCRPostProcessor:
    """Post-process OCR text to fix spelling errors and validate context."""
    
    def __init__(self):
        self.spell = SpellChecker()
        # Add construction dictionary to spell checker
        self.spell.word_frequency.load_words(list(CONSTRUCTION_DICTIONARY))
    
    def correct_word(self, word: str) -> str:
        """Correct a single word using spell checker and domain dictionary."""
        if not word or len(word) < 3:
            return word
        
        word_lower = word.lower()
        
        # Check if word is in our domain dictionary
        if word_lower in CONSTRUCTION_DICTIONARY:
            return word
        
        # Check for known OCR confusions
        if word_lower in OCR_CONFUSIONS:
            return OCR_CONFUSIONS[word_lower]
        
        # Use spell checker for unknown words
        correction = self.spell.correction(word_lower)
        if correction and correction != word_lower:
            # Preserve capitalization
            if word.isupper():
                return correction.upper()
            elif word[0].isupper():
                return correction.capitalize()
            return correction
        
        return word
    
    def process_line(self, line: str) -> str:
        """Process a single line of OCR text."""
        words = line.split()
        corrected = []
        
        for word in words:
            # Keep punctuation attached
            clean = re.sub(r'[^\w]', '', word)
            if not clean:
                corrected.append(word)
                continue
            
            # Try to correct
            corrected_word = self.correct_word(clean)
            
            # Reattach punctuation
            if word.startswith('(') and not corrected_word.startswith('('):
                corrected_word = '(' + corrected_word
            if word.endswith(')') and not corrected_word.endswith(')'):
                corrected_word = corrected_word + ')'
            if word.endswith(',') and not corrected_word.endswith(','):
                corrected_word = corrected_word + ','
            if word.endswith('.') and not corrected_word.endswith('.'):
                corrected_word = corrected_word + '.'
            
            corrected.append(corrected_word)
        
        return ' '.join(corrected)
    
    def process_text(self, text: str) -> str:
        """Process full OCR text."""
        lines = text.split('\n')
        corrected_lines = [self.process_line(line) for line in lines]
        return '\n'.join(corrected_lines)
    
    def find_unknown_words(self, text: str) -> list:
        """Find potentially misspelled words in text."""
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        unknown = []
        for word in words:
            word_lower = word.lower()
            if word_lower not in CONSTRUCTION_DICTIONARY and not self.spell.known([word_lower]):
                correction = self.spell.correction(word_lower)
                if correction and correction != word_lower:
                    unknown.append((word, correction))
        return unknown

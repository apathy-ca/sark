"""Text normalization utilities for robust injection detection.

Provides normalization functions to handle Unicode obfuscation,
character substitution, and other evasion techniques.
"""

import re
import unicodedata
import structlog

logger = structlog.get_logger()


class TextNormalizer:
    """Normalizes text to detect obfuscated injection attempts."""

    # Zero-width characters that should be removed
    ZERO_WIDTH_CHARS = [
        '\u200B',  # Zero-width space
        '\u200C',  # Zero-width non-joiner
        '\u200D',  # Zero-width joiner
        '\u2060',  # Word joiner
        '\uFEFF',  # Zero-width no-break space
    ]

    # Homoglyph mapping (visually similar Unicode -> ASCII)
    HOMOGLYPH_MAP = {
        # Cyrillic
        'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x',
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O',
        'Р': 'P', 'С': 'C', 'Т': 'T', 'Х': 'X',

        # Greek
        'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z', 'η': 'h',
        'θ': 'th', 'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'u', 'ν': 'v', 'ξ': 'x',
        'ο': 'o', 'π': 'p', 'ρ': 'r', 'σ': 's', 'τ': 't', 'υ': 'u', 'φ': 'f',
        'χ': 'ch', 'ψ': 'ps', 'ω': 'o',
        'Α': 'A', 'Β': 'B', 'Γ': 'G', 'Δ': 'D', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'H',
        'Θ': 'TH', 'Ι': 'I', 'Κ': 'K', 'Λ': 'L', 'Μ': 'M', 'Ν': 'N', 'Ξ': 'X',
        'Ο': 'O', 'Π': 'P', 'Ρ': 'R', 'Σ': 'S', 'Τ': 'T', 'Υ': 'Y', 'Φ': 'F',
        'Χ': 'CH', 'Ψ': 'PS', 'Ω': 'O',
    }

    # Leet speak mapping (1337 -> normal)
    LEET_MAP = {
        '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
        '7': 't', '8': 'b', '9': 'g',
    }

    def __init__(self):
        """Initialize normalizer."""
        self._zero_width_pattern = re.compile('[' + ''.join(self.ZERO_WIDTH_CHARS) + ']')

    def normalize(self, text: str, aggressive: bool = False) -> str:
        """
        Normalize text to canonical form for detection.

        Args:
            text: Text to normalize
            aggressive: If True, apply aggressive normalization (may cause false positives)

        Returns:
            Normalized text
        """
        if not text:
            return text

        # Apply normalization steps
        normalized = text

        # 1. Remove zero-width characters
        normalized = self.remove_zero_width_characters(normalized)

        # 2. Unicode normalization (NFC form)
        normalized = unicodedata.normalize('NFC', normalized)

        # 3. Replace homoglyphs
        normalized = self.replace_homoglyphs(normalized)

        # 4. Convert fullwidth to halfwidth
        normalized = self.fullwidth_to_halfwidth(normalized)

        # 5. Remove combining diacritical marks
        normalized = self.remove_combining_marks(normalized)

        # 6. Normalize whitespace
        normalized = self.normalize_whitespace(normalized)

        if aggressive:
            # 7. Decode leet speak (may cause false positives)
            normalized = self.decode_leet_speak(normalized)

            # 8. Normalize case to lowercase
            normalized = normalized.lower()

        return normalized

    def remove_zero_width_characters(self, text: str) -> str:
        """
        Remove zero-width characters.

        Args:
            text: Input text

        Returns:
            Text with zero-width characters removed
        """
        return self._zero_width_pattern.sub('', text)

    def replace_homoglyphs(self, text: str) -> str:
        """
        Replace homoglyphs with ASCII equivalents.

        Args:
            text: Input text

        Returns:
            Text with homoglyphs replaced
        """
        result = []
        for char in text:
            result.append(self.HOMOGLYPH_MAP.get(char, char))
        return ''.join(result)

    def fullwidth_to_halfwidth(self, text: str) -> str:
        """
        Convert fullwidth characters to halfwidth.

        Args:
            text: Input text

        Returns:
            Text with fullwidth characters converted
        """
        result = []
        for char in text:
            code = ord(char)
            # Fullwidth ASCII variants (U+FF01-U+FF5E)
            if 0xFF01 <= code <= 0xFF5E:
                # Convert to normal ASCII
                result.append(chr(code - 0xFEE0))
            else:
                result.append(char)
        return ''.join(result)

    def remove_combining_marks(self, text: str) -> str:
        """
        Remove combining diacritical marks.

        Args:
            text: Input text

        Returns:
            Text with combining marks removed
        """
        # Decompose then remove combining marks
        nfd = unicodedata.normalize('NFD', text)
        return ''.join(
            char for char in nfd
            if unicodedata.category(char) != 'Mn'  # Mn = Nonspacing_Mark
        )

    def normalize_whitespace(self, text: str) -> str:
        """
        Normalize all whitespace to single spaces.

        Handles:
        - Multiple spaces
        - Tabs
        - Newlines
        - Non-breaking spaces
        - Other Unicode whitespace

        Args:
            text: Input text

        Returns:
            Text with normalized whitespace
        """
        # Replace all whitespace characters with single space
        normalized = re.sub(r'\s+', ' ', text)
        return normalized.strip()

    def decode_leet_speak(self, text: str) -> str:
        """
        Decode common leet speak substitutions.

        WARNING: This is aggressive and may cause false positives.
        Only use when specifically looking for obfuscated text.

        Args:
            text: Input text

        Returns:
            Text with leet speak decoded
        """
        result = []
        for char in text:
            # Only replace if it's a number (don't replace in actual numbers)
            if char in self.LEET_MAP:
                # Simple heuristic: if surrounded by letters, likely leet speak
                result.append(self.LEET_MAP.get(char, char))
            else:
                result.append(char)
        return ''.join(result)

    def detect_obfuscation(self, text: str) -> dict[str, bool]:
        """
        Detect various obfuscation techniques in text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary of detected obfuscation techniques
        """
        detections = {
            'has_zero_width': bool(self._zero_width_pattern.search(text)),
            'has_homoglyphs': any(char in self.HOMOGLYPH_MAP for char in text),
            'has_fullwidth': any(0xFF01 <= ord(char) <= 0xFF5E for char in text),
            'has_combining_marks': any(
                unicodedata.category(char) == 'Mn'
                for char in unicodedata.normalize('NFD', text)
            ),
            'has_non_ascii': any(ord(char) > 127 for char in text),
            'has_leet_speak': any(char in self.LEET_MAP for char in text.lower()),
        }

        detections['is_obfuscated'] = any(detections.values())
        return detections


# Singleton instance
_normalizer: TextNormalizer | None = None


def get_normalizer() -> TextNormalizer:
    """
    Get singleton text normalizer instance.

    Returns:
        TextNormalizer instance
    """
    global _normalizer
    if _normalizer is None:
        _normalizer = TextNormalizer()
    return _normalizer


def normalize_text(text: str, aggressive: bool = False) -> str:
    """
    Convenience function to normalize text.

    Args:
        text: Text to normalize
        aggressive: Enable aggressive normalization

    Returns:
        Normalized text
    """
    return get_normalizer().normalize(text, aggressive=aggressive)

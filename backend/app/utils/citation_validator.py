import re

def split_into_sentences(text: str) -> list[str]:
    """
    Robustly split text into sentences while ignoring common abbreviations and decimals.
    Handles Dr., Mr., Mrs., Ms., Prof., Rs., No., e.g., i.e., vs., list markers (1., a.), and decimals (3.5).
    """
    # A regex to match sentence boundaries without breaking on abbreviations.
    # It looks for ending punctuation (.?!) followed by whitespace and a capital letter,
    # making sure it's not preceded by a known abbreviation or a single letter/digit (list markers).
    # Using a simpler but robust approach:
    
    # 1. Temporarily replace dots in known abbreviations/decimals/initials with a special token
    abbrevs = [
        r'(?i)\b(dr)\.', r'(?i)\b(mr)\.', r'(?i)\b(mrs)\.', r'(?i)\b(ms)\.', r'(?i)\b(prof)\.', 
        r'(?i)\b(rs)\.', r'(?i)\b(no)\.', r'(?i)\b(e\.g)\.', r'(?i)\b(i\.e)\.', r'(?i)\b(vs)\.',
        r'(?i)\b(etc)\.', r'(?i)\b(et al)\.', r'(?i)\b(vol)\.', r'(?i)\b(fig)\.',
        r'(?i)\b([a-z])\.'  # Single letter initials like M. in M. Puri
    ]
    
    # Temporarily hide decimals (e.g. 3.5) and list numbers (e.g. 1. )
    text = re.sub(r'(\d)\.(\d)', r'\1<DOT>\2', text)
    
    # Temporarily hide list markers (e.g., "1. ", "a. ", "(1) ") 
    # Actually, if a list marker is at the start of a line, we don't want it to break the PREVIOUS sentence incorrectly,
    # but the previous sentence ended with a period. The period before the list marker is fine to split on.
    
    for abbrev in abbrevs:
        text = re.sub(abbrev, lambda m: m.group(0).replace('.', '<DOT>'), text)
        
    # Split on period, question mark, or exclamation mark followed by whitespace and capital letter
    # Or followed by a newline.
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9\-\*\[])', text)
    
    # Restore the dots
    cleaned_sentences = []
    for s in sentences:
        restored = s.replace('<DOT>', '.')
        # Strip whitespace
        restored = restored.strip()
        if restored:
            cleaned_sentences.append(restored)
            
    return cleaned_sentences

def extract_normalized_numbers(text: str) -> set[str]:
    """
    Extracts numbers, dates, and percentages from text and normalizes them for comparison.
    - Strips commas (1,50,000 -> 150000)
    - Treats '15%' and '15 percent' identically (extracts '15')
    - Ignores small standalone numbers likely to be list markers or fractions like 1/2.
    """
    # Normalize percent
    text_lower = text.lower().replace(" percent", "%")
    
    # Remove commas in numbers
    text_nocomma = re.sub(r'(\d),(\d)', r'\1\2', text_lower)
    # Run twice for things like 1,500,000
    text_nocomma = re.sub(r'(\d),(\d)', r'\1\2', text_nocomma)
    
    # Find all standalone numbers or percentages
    # We want to capture numbers even if attached to units like 3.5m
    matches = re.finditer(r'(\d+(?:\.\d+)?)', text_nocomma)
    
    normalized = set()
    for m in matches:
        num_str = m.group(1)
        # Check if there is a % sign shortly after
        pct_str = "%" if "%" in text_nocomma[m.end():m.end()+2] else ""
        
        val = float(num_str) if '.' in num_str else int(num_str)
        if isinstance(val, int) and val < 10 and not pct_str:
            continue
            
        normalized.add(str(val))
        
    return normalized

def is_factual_sentence(sentence: str) -> bool:
    """
    Skip non-factual sentences (greetings, 'I don't have enough...', headings).
    """
    s = sentence.strip()
    if not s:
        return False
    if s.startswith("#"):
        return False
    
    s_lower = s.lower()
    non_factual_starts = [
        "i don't have enough",
        "i do not have enough",
        "the provided documents do not",
        "based on the provided",
        "according to the documents",
        "hello",
        "here is the",
        "here are the",
    ]
    for start in non_factual_starts:
        if s_lower.startswith(start):
            return False
            
    # Check if it has a verb (very crude heuristic: length > 3 words and not all caps)
    words = s.split()
    if len(words) < 4:
        return False
        
    return True

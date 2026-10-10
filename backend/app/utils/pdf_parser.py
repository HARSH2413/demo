import logging

logger = logging.getLogger(__name__)

def sort_blocks_column_aware(blocks: list, max_gutter_cross_fraction: float = 0.10, page_rotation: int = 0) -> list:
    """
    Sorts blocks to preserve column reading order using page-level gutter detection.
    A gutter is a vertical band near the center (45%-55%) crossed by < 10% of blocks.
    blocks: (x0, y0, x1, y1, text, block_no, block_type)
    """
    if not blocks:
        return []
        
    # We only care about text blocks (type 0)
    text_blocks = [b for b in blocks if len(b) >= 7 and b[6] == 0]
    if not text_blocks:
        return blocks
        
    if page_rotation != 0:
        logger.warning(f"Page is rotated ({page_rotation} degrees). Falling back to naive (y, x) sorting.")
        return sorted(text_blocks, key=lambda b: (b[1], b[0]))
        
    min_x = min(b[0] for b in text_blocks)
    max_x = max(b[2] for b in text_blocks)
    width = max_x - min_x
    if width <= 0:
        return sorted(text_blocks, key=lambda b: (b[1], b[0]))
        
    # Define center gutter bounds (45% to 55% of the content width)
    gutter_min = min_x + (width * 0.45)
    gutter_max = min_x + (width * 0.55)
    
    crossers = 0
    left_blocks = []
    right_blocks = []
    
    for b in text_blocks:
        x0, x1 = b[0], b[2]
        # A block crosses the gutter only if it fully spans across it
        if x0 < gutter_min and x1 > gutter_max:
            crossers += 1
        elif x1 <= gutter_max:
            left_blocks.append(b)
        else:
            right_blocks.append(b)
            
    total_blocks = len(text_blocks)
    crossing_fraction = crossers / total_blocks if total_blocks > 0 else 0
    
    # Valid gutter exists if few blocks cross it AND there is text on BOTH sides
    has_gutter = crossing_fraction <= max_gutter_cross_fraction and len(left_blocks) > 0 and len(right_blocks) > 0
    
    if not has_gutter:
        # Fallback to (y, x) naive reading order
        return sorted(text_blocks, key=lambda b: (b[1], b[0]))
        
    # Gutter exists! Group by Y to maintain header/footer/middle full-width blocks
    bands = []
    current_band = []
    
    sorted_by_y = sorted(text_blocks, key=lambda b: b[1])
    for b in sorted_by_y:
        x0, x1 = b[0], b[2]
        is_full_width = (x0 < gutter_min and x1 > gutter_max)
        
        if is_full_width:
            if current_band:
                bands.append(("col", current_band))
                current_band = []
            bands.append(("full", [b]))
        else:
            current_band.append(b)
            
    if current_band:
        bands.append(("col", current_band))
        
    final_blocks = []
    for band_type, band_blocks in bands:
        if band_type == "full":
            final_blocks.extend(band_blocks)
        else:
            # Sort this band's blocks into left/right, then sort each by Y
            left = sorted([b for b in band_blocks if b[2] <= gutter_max], key=lambda b: (b[1], b[0]))
            right = sorted([b for b in band_blocks if b[0] >= gutter_min], key=lambda b: (b[1], b[0]))
            final_blocks.extend(left)
            final_blocks.extend(right)
            
    return final_blocks

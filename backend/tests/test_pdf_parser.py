import pytest
import logging
from app.utils.pdf_parser import sort_blocks_column_aware

def test_empty_page():
    assert sort_blocks_column_aware([]) == []

def test_single_column():
    blocks = [
        (10, 50, 100, 100, "Block 2", 2, 0),
        (10, 10, 100, 40, "Block 1", 1, 0),
    ]
    res = sort_blocks_column_aware(blocks)
    assert res[0][4] == "Block 1"
    assert res[1][4] == "Block 2"

def test_rotated_page(caplog):
    blocks = [
        (10, 10, 100, 40, "Block 1", 1, 0),
        (10, 50, 100, 100, "Block 2", 2, 0),
    ]
    with caplog.at_level(logging.WARNING):
        res = sort_blocks_column_aware(blocks, page_rotation=90)
    assert "Page is rotated" in caplog.text
    
def test_uneven_column_lengths_and_offset_tops():
    # Width = 500 (from 10 to 510)
    # Gutter is ~ 235 to 285.
    blocks = [
        (10, 20, 200, 60, "Col1 Top", 1, 0),
        (10, 80, 200, 120, "Col1 Middle", 2, 0),
        (10, 140, 200, 180, "Col1 Bottom", 3, 0),
        
        # Col 2 is shorter and its top block is slightly offset vertically from Col1 Top
        (300, 25, 510, 65, "Col2 Top", 4, 0),
        (300, 85, 510, 125, "Col2 Bottom", 5, 0),
    ]
    res = sort_blocks_column_aware(blocks)
    assert res[0][4] == "Col1 Top"
    assert res[1][4] == "Col1 Middle"
    assert res[2][4] == "Col1 Bottom"
    assert res[3][4] == "Col2 Top"
    assert res[4][4] == "Col2 Bottom"

def test_full_width_header_and_middle():
    # Width = 500
    # Gutter = 235 to 285.
    blocks = [
        (10, 10, 500, 30, "Full Width Title", 1, 0),  # crosses gutter
        (10, 40, 200, 80, "Col1 Top", 2, 0),
        (300, 40, 500, 80, "Col2 Top", 3, 0),
        (10, 90, 500, 110, "Full Width Middle", 4, 0), # crosses gutter
        (10, 120, 200, 160, "Col1 Bottom", 5, 0),
        (300, 120, 500, 160, "Col2 Bottom", 6, 0),
    ]
    res = sort_blocks_column_aware(blocks)
    
    assert res[0][4] == "Full Width Title"
    assert res[1][4] == "Col1 Top"
    assert res[2][4] == "Col2 Top"
    assert res[3][4] == "Full Width Middle"
    assert res[4][4] == "Col1 Bottom"
    assert res[5][4] == "Col2 Bottom"

def test_columns_edges_inside_band():
    """
    Test where both columns' edges lie inside the 45-55% band.
    Page width is typically 595. 45% = 267.75, 55% = 327.25
    If left column ends at 270 (inside band) and right column starts at 320 (inside band),
    the empty strip is [270, 320]. This empty strip fully overlaps the 45-55% band.
    We need to ensure it's still detected as a two-column layout.
    """
    blocks = [
        # Left column
        (50.0, 100.0, 270.0, 120.0, "left_col\n", 0, 0),
        # Right column
        (320.0, 100.0, 500.0, 120.0, "right_col\n", 1, 0),
    ]
    
    sorted_blocks = sort_blocks_column_aware(blocks, page_rotation=0)
    # They should be sorted left column then right column
    assert "".join(b[4] for b in sorted_blocks).strip() == "left_col\nright_col"

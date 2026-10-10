from app.services.hierarchical_chunking import HierarchicalChunker


class Splitter:
    def split_text(self, text: str) -> list[str]:
        return [text]


def test_docx_heading_hierarchy_is_preserved_in_children():
    children = HierarchicalChunker(chunk_size=1400).build_children(
        "# Benefits\nHealth insurance details.\n\n## Eligibility\nAll employees are eligible.",
        "Word Document",
        Splitter(),
    )

    assert len(children) == 2
    assert children[0].section_path == ("Benefits",)
    assert children[1].section_path == ("Benefits", "Eligibility")
    assert children[1].metadata()["parent_id"] == "section-2"


def test_spreadsheet_rows_are_grouped_without_splitting_rows():
    children = HierarchicalChunker(chunk_size=45).build_children(
        "--- Sheet: Revenue ---\nMonth: Jan | Sales: 10\nMonth: Feb | Sales: 20",
        "Excel Spreadsheet",
        Splitter(),
    )

    assert len(children) == 2
    assert children[0].parent_title == "Revenue"
    assert "Month: Jan | Sales: 10" in children[0].content
    assert "Month: Feb | Sales: 20" in children[1].content
    assert all(child.block_type == "spreadsheet_rows" for child in children)


def test_csv_uses_dataset_parent_and_complete_row_groups():
    children = HierarchicalChunker(chunk_size=30).build_children(
        "Name: Ada | Team: Research\nName: Lin | Team: Product",
        "CSV Spreadsheet",
        Splitter(),
    )

    assert len(children) == 2
    assert {child.parent_title for child in children} == {"Dataset"}
    assert all(child.metadata()["chunk_kind"] == "child" for child in children)

"""Tests for the MCP server tool functions."""

from unittest.mock import MagicMock, patch

import pytest

import scribus_mcp.server as server_module
from scribus_mcp.server import (
    add_page,
    apply_master_page,
    close_master_page,
    create_char_style,
    create_document,
    create_master_page,
    create_paragraph_style,
    define_color,
    draw_shape,
    edit_master_page,
    export_pdf,
    get_document_info,
    link_text_frames,
    list_master_pages,
    modify_object,
    place_image,
    place_text,
    run_script,
    set_baseline_grid,
    set_guides,
    unlink_text_frames,
)


@pytest.fixture(autouse=True)
def mock_client():
    """Replace the global client with a mock for all tests."""
    mock = MagicMock()
    mock.send_command.return_value = {}
    mock.save_document.return_value = None

    with (
        patch.object(server_module, "_client", mock),
        patch.object(server_module, "_get_client", return_value=mock),
    ):
        yield mock


class TestCreateDocument:
    def test_defaults(self, mock_client):
        mock_client.send_command.return_value = {
            "width": 210,
            "height": 297,
            "unit": "mm",
            "pages": 1,
        }
        result = create_document()
        assert "210x297mm" in result
        call_params = mock_client.send_command.call_args[0][1]
        assert call_params["margins"] == 20
        assert call_params["facing_pages"] is False

    def test_custom_params(self, mock_client):
        mock_client.send_command.return_value = {
            "width": 100,
            "height": 200,
            "unit": "pt",
            "pages": 3,
        }
        result = create_document(width=100, height=200, unit="pt", pages=3)
        assert "100x200pt" in result
        assert "3 page(s)" in result

    def test_asymmetric_margins(self, mock_client):
        mock_client.send_command.return_value = {
            "width": 245,
            "height": 290,
            "unit": "mm",
            "pages": 1,
        }
        create_document(
            width=245, height=290, margin_top=17, margin_bottom=20,
            margin_left=20, margin_right=15
        )
        call_params = mock_client.send_command.call_args[0][1]
        assert call_params["margin_top"] == 17
        assert call_params["margin_bottom"] == 20
        assert call_params["margin_left"] == 20
        assert call_params["margin_right"] == 15

    def test_facing_pages(self, mock_client):
        mock_client.send_command.return_value = {
            "width": 245,
            "height": 290,
            "unit": "mm",
            "pages": 4,
        }
        create_document(width=245, height=290, facing_pages=True, pages=4)
        call_params = mock_client.send_command.call_args[0][1]
        assert call_params["facing_pages"] is True

    def test_bleeds(self, mock_client):
        mock_client.send_command.return_value = {
            "width": 245,
            "height": 290,
            "unit": "mm",
            "pages": 1,
        }
        create_document(bleed_top=3, bleed_bottom=3, bleed_left=3, bleed_right=3)
        call_params = mock_client.send_command.call_args[0][1]
        assert call_params["bleed_top"] == 3
        assert call_params["bleed_right"] == 3


class TestDefineColor:
    def test_cmyk(self, mock_client):
        mock_client.send_command.return_value = {"name": "MyRed", "mode": "cmyk"}
        result = define_color("MyRed", mode="cmyk", c=0, m=100, y=100, k=0)
        assert "CMYK" in result
        assert "MyRed" in result

    def test_rgb(self, mock_client):
        mock_client.send_command.return_value = {"name": "Blue", "mode": "rgb"}
        result = define_color("Blue", mode="rgb", r=0, g=0, b=255)
        assert "RGB" in result


class TestPlaceText:
    def test_basic(self, mock_client):
        mock_client.send_command.return_value = {"name": "text_1"}
        result = place_text(10, 20, 100, 50, text="Hello")
        assert "text_1" in result
        assert "Hello" in result

    def test_with_styling(self, mock_client):
        mock_client.send_command.return_value = {"name": "text_2"}
        place_text(
            10,
            20,
            100,
            50,
            text="Styled",
            font="Arial Regular",
            font_size=14,
            color="Black",
            alignment="center",
        )
        call_params = mock_client.send_command.call_args[0][1]
        assert call_params["font"] == "Arial Regular"
        assert call_params["font_size"] == 14
        assert call_params["alignment"] == "center"

    def test_line_spacing_and_columns(self, mock_client):
        mock_client.send_command.return_value = {"name": "text_3"}
        place_text(
            0, 0, 100, 50,
            line_spacing=13, line_spacing_mode=0,
            columns=2, column_gap=5,
        )
        call_params = mock_client.send_command.call_args[0][1]
        assert call_params["line_spacing"] == 13
        assert call_params["line_spacing_mode"] == 0
        assert call_params["columns"] == 2
        assert call_params["column_gap"] == 5

    def test_paragraph_style(self, mock_client):
        mock_client.send_command.return_value = {"name": "text_4"}
        place_text(0, 0, 100, 50, style="Body")
        call_params = mock_client.send_command.call_args[0][1]
        assert call_params["style"] == "Body"


class TestPlaceImage:
    def test_basic(self, mock_client):
        mock_client.send_command.return_value = {"name": "img_1"}
        result = place_image(10, 20, 100, 100, "/path/to/image.png")
        assert "img_1" in result
        assert "/path/to/image.png" in result


class TestDrawShape:
    def test_rectangle(self, mock_client):
        mock_client.send_command.return_value = {"name": "rect_1", "shape": "rectangle"}
        result = draw_shape("rectangle", x=10, y=20, w=100, h=50)
        assert "rectangle" in result

    def test_line(self, mock_client):
        mock_client.send_command.return_value = {"name": "line_1", "shape": "line"}
        result = draw_shape("line", x1=0, y1=0, x2=100, y2=100)
        assert "line" in result


class TestModifyObject:
    def test_position(self, mock_client):
        mock_client.send_command.return_value = {"name": "obj_1", "modified": ["position"]}
        result = modify_object("obj_1", x=50, y=60)
        assert "position" in result

    def test_only_sends_non_none(self, mock_client):
        mock_client.send_command.return_value = {"name": "obj_1", "modified": ["fill_color"]}
        modify_object("obj_1", fill_color="Red")
        call_params = mock_client.send_command.call_args[0][1]
        assert "x" not in call_params
        assert "fill_color" in call_params

    def test_line_spacing_and_columns(self, mock_client):
        mock_client.send_command.return_value = {
            "name": "obj_1",
            "modified": ["line_spacing", "columns"],
        }
        modify_object("obj_1", line_spacing=14, columns=3)
        call_params = mock_client.send_command.call_args[0][1]
        assert call_params["line_spacing"] == 14
        assert call_params["columns"] == 3


class TestAddPage:
    def test_default(self, mock_client):
        mock_client.send_command.return_value = {"added": 1, "total_pages": 2}
        result = add_page()
        assert "1 page(s)" in result
        assert "2 pages" in result


class TestSetBaselineGrid:
    def test_basic(self, mock_client):
        mock_client.send_command.return_value = {"grid": 13, "offset": 0}
        result = set_baseline_grid(13)
        assert "13" in result
        mock_client.send_command.assert_called_once_with(
            "set_baseline_grid", {"grid": 13, "offset": 0}
        )


class TestCreateParagraphStyle:
    def test_basic(self, mock_client):
        mock_client.send_command.return_value = {"name": "Body"}
        result = create_paragraph_style("Body", font="DejaVu Serif", font_size=9.5)
        assert "Body" in result
        call_params = mock_client.send_command.call_args[0][1]
        assert call_params["font"] == "DejaVu Serif"
        assert call_params["font_size"] == 9.5

    def test_only_sends_non_none(self, mock_client):
        mock_client.send_command.return_value = {"name": "Body"}
        create_paragraph_style("Body", alignment="justify")
        call_params = mock_client.send_command.call_args[0][1]
        assert "font" not in call_params
        assert call_params["alignment"] == "justify"


class TestCreateCharStyle:
    def test_basic(self, mock_client):
        mock_client.send_command.return_value = {"name": "Emphasis"}
        result = create_char_style("Emphasis", font="Arial Italic")
        assert "Emphasis" in result


class TestLinkTextFrames:
    def test_basic(self, mock_client):
        mock_client.send_command.return_value = {"from_frame": "t1", "to_frame": "t2"}
        result = link_text_frames("t1", "t2")
        assert "t1" in result
        assert "t2" in result


class TestUnlinkTextFrames:
    def test_basic(self, mock_client):
        mock_client.send_command.return_value = {"frame": "t1"}
        result = unlink_text_frames("t1")
        assert "t1" in result


class TestSetGuides:
    def test_horizontal(self, mock_client):
        mock_client.send_command.return_value = {"horizontal": [50, 100], "vertical": None}
        result = set_guides(horizontal=[50, 100])
        assert "2 horizontal" in result


class TestMasterPages:
    def test_create(self, mock_client):
        mock_client.send_command.return_value = {"name": "LeftPage"}
        result = create_master_page("LeftPage")
        assert "LeftPage" in result

    def test_edit(self, mock_client):
        mock_client.send_command.return_value = {"name": "LeftPage"}
        result = edit_master_page("LeftPage")
        assert "LeftPage" in result

    def test_close(self, mock_client):
        mock_client.send_command.return_value = {}
        result = close_master_page()
        assert "Closed" in result

    def test_apply(self, mock_client):
        mock_client.send_command.return_value = {"master_page": "LeftPage", "page": 2}
        result = apply_master_page("LeftPage", 2)
        assert "LeftPage" in result
        assert "2" in result

    def test_list(self, mock_client):
        mock_client.send_command.return_value = {"master_pages": ["A", "B"]}
        result = list_master_pages()
        assert "A" in result
        assert "B" in result

    def test_list_empty(self, mock_client):
        mock_client.send_command.return_value = {"master_pages": []}
        result = list_master_pages()
        assert "No master pages" in result


class TestExportPdf:
    def test_basic(self, mock_client):
        mock_client.send_command.return_value = {"file_path": "/tmp/out.pdf"}
        result = export_pdf("/tmp/out.pdf")
        assert "/tmp/out.pdf" in result


class TestGetDocumentInfo:
    def test_output_format(self, mock_client):
        mock_client.send_command.return_value = {
            "page_count": 2,
            "pages": [
                {"number": 1, "width": 210, "height": 297},
                {"number": 2, "width": 210, "height": 297},
            ],
            "objects": [
                {"name": "text_1", "type": 4, "page": 1},
            ],
            "colors": ["Black", "White", "MyRed"],
            "margins": {"left": 20, "right": 20, "top": 20, "bottom": 20},
            "master_pages": [],
            "paragraph_styles": [],
            "char_styles": [],
        }
        result = get_document_info()
        assert "2 page(s)" in result
        assert "text_1" in result
        assert "MyRed" in result

    def test_margins_display(self, mock_client):
        mock_client.send_command.return_value = {
            "page_count": 1,
            "pages": [],
            "objects": [],
            "colors": [],
            "margins": {"left": 20, "right": 15, "top": 17, "bottom": 20},
            "master_pages": ["LeftPage"],
            "paragraph_styles": ["Body"],
            "char_styles": ["Bold"],
        }
        result = get_document_info()
        assert "top=17" in result
        assert "LeftPage" in result
        assert "Body" in result
        assert "Bold" in result


class TestRunScript:
    def test_with_result(self, mock_client):
        mock_client.send_command.return_value = {"result": 42}
        result = run_script("result = 21 * 2")
        assert "42" in result

    def test_without_result(self, mock_client):
        mock_client.send_command.return_value = {"result": None}
        result = run_script("scribus.gotoPage(1)")
        assert "successfully" in result


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------


class TestCreateDocumentEdgeCases:
    def test_landscape_orientation(self, mock_client):
        mock_client.send_command.return_value = {
            "width": 297,
            "height": 210,
            "unit": "mm",
            "pages": 1,
        }
        create_document(width=297, height=210, orientation=1)
        call_params = mock_client.send_command.call_args[0][1]
        assert call_params["orientation"] == 1


class TestPlaceTextEdgeCases:
    def test_empty_text_no_preview(self, mock_client):
        mock_client.send_command.return_value = {"name": "text_1"}
        result = place_text(0, 0, 100, 50, text="")
        assert "with text:" not in result

    def test_long_text_truncated(self, mock_client):
        mock_client.send_command.return_value = {"name": "text_1"}
        long_text = "A" * 60
        result = place_text(0, 0, 100, 50, text=long_text)
        assert "..." in result


class TestDrawShapeEdgeCases:
    def test_ellipse_shape(self, mock_client):
        mock_client.send_command.return_value = {"name": "ellipse_1", "shape": "ellipse"}
        result = draw_shape("ellipse", x=10, y=20, w=50, h=50)
        assert "ellipse" in result

    def test_line_defaults(self, mock_client):
        mock_client.send_command.return_value = {"name": "line_1", "shape": "line"}
        draw_shape("line")
        call_params = mock_client.send_command.call_args[0][1]
        assert call_params["x1"] == 0
        assert call_params["y1"] == 0
        assert call_params["x2"] == 100
        assert call_params["y2"] == 100


class TestPlaceImageEdgeCases:
    def test_image_with_page(self, mock_client):
        mock_client.send_command.return_value = {"name": "img_1"}
        place_image(0, 0, 100, 100, "/img.png", page=3)
        call_params = mock_client.send_command.call_args[0][1]
        assert call_params["page"] == 3


class TestExportPdfEdgeCases:
    def test_export_with_version_and_pages(self, mock_client):
        mock_client.send_command.return_value = {"file_path": "/tmp/out.pdf"}
        export_pdf("/tmp/out.pdf", pdf_version="1.4", pages=[1, 2])
        call_params = mock_client.send_command.call_args[0][1]
        assert call_params["pdf_version"] == "1.4"
        assert call_params["pages"] == [1, 2]

    def test_prepress_options(self, mock_client):
        mock_client.send_command.return_value = {"file_path": "/tmp/out.pdf"}
        export_pdf(
            "/tmp/out.pdf",
            pdf_version="x-4",
            crop_marks=True,
            bleed_marks=True,
            use_doc_bleeds=True,
            output_profile="ISOcoated_v2_300_eci",
            embed_profiles=True,
            info="Test",
            font_embedding="outline",
            resolution=600,
        )
        call_params = mock_client.send_command.call_args[0][1]
        assert call_params["pdf_version"] == "x-4"
        assert call_params["crop_marks"] is True
        assert call_params["bleed_marks"] is True
        assert call_params["output_profile"] == "ISOcoated_v2_300_eci"
        assert call_params["embed_profiles"] is True
        assert call_params["font_embedding"] == "outline"
        assert call_params["resolution"] == 600


class TestGetDocumentInfoEdgeCases:
    def test_empty_document_info(self, mock_client):
        mock_client.send_command.return_value = {
            "page_count": 1,
            "pages": [{"number": 1, "width": 210, "height": 297}],
            "objects": [],
            "colors": [],
            "margins": {},
            "master_pages": [],
            "paragraph_styles": [],
            "char_styles": [],
        }
        result = get_document_info()
        assert "1 page(s)" in result
        assert "Objects" not in result
        assert "Colors" not in result


class TestSaveAfterFailure:
    def test_save_after_failure_logged(self, mock_client):
        mock_client.send_command.return_value = {
            "width": 210,
            "height": 297,
            "unit": "mm",
            "pages": 1,
        }
        mock_client.save_document.side_effect = RuntimeError("save failed")
        # Should not propagate the save error
        result = create_document()
        assert "210x297mm" in result


class TestModifyObjectEdgeCases:
    def test_modify_empty_returns_nothing(self, mock_client):
        mock_client.send_command.return_value = {"name": "obj_1", "modified": []}
        result = modify_object("obj_1")
        assert "obj_1" in result

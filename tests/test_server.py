"""Tests for the MCP server tool functions."""

from unittest.mock import MagicMock, patch

import pytest

import scribus_mcp.server as server_module
from scribus_mcp.server import (
    add_page,
    create_document,
    define_color,
    draw_shape,
    export_pdf,
    get_document_info,
    modify_object,
    place_image,
    place_text,
    run_script,
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
        mock_client.send_command.assert_called_once_with(
            "create_document",
            {
                "width": 210,
                "height": 297,
                "margins": 20,
                "unit": "mm",
                "pages": 1,
                "orientation": 0,
            },
        )

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


class TestAddPage:
    def test_default(self, mock_client):
        mock_client.send_command.return_value = {"added": 1, "total_pages": 2}
        result = add_page()
        assert "1 page(s)" in result
        assert "2 pages" in result


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
        }
        result = get_document_info()
        assert "2 page(s)" in result
        assert "text_1" in result
        assert "MyRed" in result


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


class TestGetDocumentInfoEdgeCases:
    def test_empty_document_info(self, mock_client):
        mock_client.send_command.return_value = {
            "page_count": 1,
            "pages": [{"number": 1, "width": 210, "height": 297}],
            "objects": [],
            "colors": [],
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

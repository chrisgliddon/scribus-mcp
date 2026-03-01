"""Tests for the bridge.py command handlers running against mock_scribus."""

import io
import json
import sys

import pytest

# Inject mock_scribus as the "scribus" module before importing bridge
from tests import mock_scribus

sys.modules["scribus"] = mock_scribus

from scribus_mcp.bridge import (  # noqa: E402
    COMMANDS,
    _alignment_constant,
    _go_to_page,
    _unit_constant,
    cmd_add_page,
    cmd_create_document,
    cmd_define_color,
    cmd_draw_shape,
    cmd_export_pdf,
    cmd_get_document_info,
    cmd_modify_object,
    cmd_place_image,
    cmd_place_text,
    cmd_run_script,
    cmd_save_document,
    cmd_shutdown,
    main,
)


@pytest.fixture(autouse=True)
def reset_scribus():
    mock_scribus._reset()
    yield
    mock_scribus._reset()


def _create_doc(**kwargs):
    defaults = {"width": 210, "height": 297, "unit": "mm", "margins": 20, "pages": 1}
    defaults.update(kwargs)
    return cmd_create_document(defaults)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


class TestUtilities:
    def test_unit_mm(self):
        assert _unit_constant("mm") == mock_scribus.UNIT_MILLIMETERS

    def test_unit_pt(self):
        assert _unit_constant("pt") == mock_scribus.UNIT_POINTS

    def test_unit_inch_aliases(self):
        assert _unit_constant("in") == mock_scribus.UNIT_INCHES
        assert _unit_constant("inch") == mock_scribus.UNIT_INCHES

    def test_unit_unknown_defaults_mm(self):
        assert _unit_constant("furlongs") == mock_scribus.UNIT_MILLIMETERS

    def test_alignment_constants(self):
        assert _alignment_constant("left") == mock_scribus.ALIGN_LEFT
        assert _alignment_constant("center") == mock_scribus.ALIGN_CENTERED
        assert _alignment_constant("right") == mock_scribus.ALIGN_RIGHT
        assert _alignment_constant("justify") == mock_scribus.ALIGN_BLOCK
        assert _alignment_constant("forced") == mock_scribus.ALIGN_FORCED

    def test_alignment_unknown_defaults_left(self):
        assert _alignment_constant("wiggle") == mock_scribus.ALIGN_LEFT


class TestGoToPage:
    def test_navigates_to_page(self):
        _create_doc(pages=3)
        _go_to_page(2)
        assert mock_scribus._doc.current_page == 2

    def test_none_is_noop(self):
        _create_doc()
        _go_to_page(None)
        assert mock_scribus._doc.current_page == 1


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


class TestCmdCreateDocument:
    def test_defaults(self):
        result = _create_doc()
        assert result["width"] == 210
        assert result["height"] == 297
        assert result["pages"] == 1
        assert mock_scribus._doc is not None

    def test_custom_dims(self):
        result = cmd_create_document(
            {"width": 100, "height": 200, "unit": "pt", "margins": 10, "pages": 2}
        )
        assert result["width"] == 100
        assert result["height"] == 200
        assert result["pages"] == 2

    def test_uniform_margins(self):
        _create_doc(margins=15)
        assert mock_scribus._doc.margins == (15, 15, 15, 15)

    def test_dict_margins(self):
        cmd_create_document({"margins": {"top": 10, "right": 20, "bottom": 30, "left": 40}})
        assert mock_scribus._doc.margins == (40, 20, 10, 30)


class TestCmdDefineColor:
    def test_cmyk(self):
        _create_doc()
        params = {"name": "TestCyan", "mode": "cmyk", "c": 100, "m": 0, "y": 0, "k": 0}
        result = cmd_define_color(params)
        assert result["name"] == "TestCyan"
        assert result["mode"] == "cmyk"
        assert "TestCyan" in mock_scribus._doc.colors

    def test_rgb(self):
        _create_doc()
        result = cmd_define_color({"name": "Blue", "mode": "rgb", "r": 0, "g": 0, "b": 255})
        assert result["name"] == "Blue"
        assert result["mode"] == "rgb"

    def test_cmyk_percentage_conversion(self):
        _create_doc()
        # 100% should map to int(100 * 2.55) = 255
        cmd_define_color({"name": "FullCyan", "mode": "cmyk", "c": 100, "m": 0, "y": 0, "k": 0})
        assert "FullCyan" in mock_scribus._doc.colors


class TestCmdPlaceText:
    def test_basic(self):
        _create_doc()
        result = cmd_place_text({"x": 10, "y": 20, "w": 100, "h": 50, "text": "Hello"})
        assert "name" in result
        obj = mock_scribus._doc.objects[result["name"]]
        assert obj["text"] == "Hello"

    def test_empty_text(self):
        _create_doc()
        result = cmd_place_text({"x": 0, "y": 0, "w": 50, "h": 50, "text": ""})
        obj = mock_scribus._doc.objects[result["name"]]
        assert obj["text"] == ""

    def test_all_styling(self):
        _create_doc()
        result = cmd_place_text(
            {
                "x": 0,
                "y": 0,
                "w": 100,
                "h": 50,
                "text": "Styled",
                "font": "Helvetica",
                "font_size": 14,
                "color": "Black",
                "alignment": "center",
            }
        )
        obj = mock_scribus._doc.objects[result["name"]]
        assert obj["font"] == "Helvetica"
        assert obj["font_size"] == 14
        assert obj["color"] == "Black"
        assert obj["alignment"] == mock_scribus.ALIGN_CENTERED

    def test_page_navigation(self):
        _create_doc(pages=3)
        cmd_place_text({"x": 0, "y": 0, "w": 50, "h": 50, "page": 2})
        assert mock_scribus._doc.current_page == 2

    def test_returns_name(self):
        _create_doc()
        result = cmd_place_text({"x": 0, "y": 0, "w": 50, "h": 50})
        assert result["name"].startswith("text_")


class TestCmdPlaceImage:
    def test_basic(self):
        _create_doc()
        result = cmd_place_image({"x": 10, "y": 20, "w": 100, "h": 100, "file_path": "/img.png"})
        assert "name" in result
        obj = mock_scribus._doc.objects[result["name"]]
        assert obj["image"] == "/img.png"

    def test_scale_default(self):
        _create_doc()
        result = cmd_place_image({"x": 0, "y": 0, "w": 50, "h": 50, "file_path": "/a.png"})
        assert result["name"].startswith("img_")

    def test_scale_disabled(self):
        _create_doc()
        result = cmd_place_image(
            {
                "x": 0,
                "y": 0,
                "w": 50,
                "h": 50,
                "file_path": "/a.png",
                "scale_to_frame": False,
            }
        )
        assert "name" in result

    def test_page_navigation(self):
        _create_doc(pages=2)
        cmd_place_image({"x": 0, "y": 0, "w": 50, "h": 50, "file_path": "/a.png", "page": 2})
        assert mock_scribus._doc.current_page == 2


class TestCmdDrawShape:
    def test_rect_default(self):
        _create_doc()
        result = cmd_draw_shape({})
        assert result["shape"] == "rectangle"
        assert result["name"].startswith("rect_")

    def test_ellipse(self):
        _create_doc()
        result = cmd_draw_shape({"shape": "ellipse", "x": 5, "y": 5, "w": 50, "h": 50})
        assert result["shape"] == "ellipse"
        assert result["name"].startswith("ellipse_")

    def test_line(self):
        _create_doc()
        result = cmd_draw_shape({"shape": "line", "x1": 0, "y1": 0, "x2": 100, "y2": 100})
        assert result["shape"] == "line"
        assert result["name"].startswith("line_")

    def test_fill_and_line_color(self):
        _create_doc()
        result = cmd_draw_shape(
            {
                "shape": "rectangle",
                "fill_color": "Red",
                "line_color": "Blue",
            }
        )
        obj = mock_scribus._doc.objects[result["name"]]
        assert obj["fill_color"] == "Red"
        assert obj["line_color"] == "Blue"

    def test_line_width(self):
        _create_doc()
        result = cmd_draw_shape({"shape": "rectangle", "line_width": 2.5})
        obj = mock_scribus._doc.objects[result["name"]]
        assert obj["line_width"] == 2.5


class TestCmdModifyObject:
    def test_move(self):
        _create_doc()
        text = cmd_place_text({"x": 0, "y": 0, "w": 50, "h": 50})
        name = text["name"]
        result = cmd_modify_object({"name": name, "x": 100, "y": 200})
        assert "position" in result["modified"]
        obj = mock_scribus._doc.objects[name]
        assert obj["x"] == 100
        assert obj["y"] == 200

    def test_resize(self):
        _create_doc()
        text = cmd_place_text({"x": 0, "y": 0, "w": 50, "h": 50})
        name = text["name"]
        result = cmd_modify_object({"name": name, "w": 200, "h": 300})
        assert "size" in result["modified"]
        obj = mock_scribus._doc.objects[name]
        assert obj["w"] == 200
        assert obj["h"] == 300

    def test_rotation(self):
        _create_doc()
        text = cmd_place_text({"x": 0, "y": 0, "w": 50, "h": 50})
        name = text["name"]
        result = cmd_modify_object({"name": name, "rotation": 45})
        assert "rotation" in result["modified"]
        assert mock_scribus._doc.objects[name]["rotation"] == 45

    def test_colors(self):
        _create_doc()
        rect = cmd_draw_shape({"shape": "rectangle"})
        name = rect["name"]
        result = cmd_modify_object({"name": name, "fill_color": "Red", "line_color": "Blue"})
        assert "fill_color" in result["modified"]
        assert "line_color" in result["modified"]

    def test_text_props(self):
        _create_doc()
        text = cmd_place_text({"x": 0, "y": 0, "w": 50, "h": 50, "text": "old"})
        name = text["name"]
        result = cmd_modify_object(
            {
                "name": name,
                "text": "new",
                "font": "Courier",
                "font_size": 12,
                "text_color": "Red",
                "alignment": "right",
            }
        )
        assert "text" in result["modified"]
        assert "font" in result["modified"]
        assert "font_size" in result["modified"]
        assert "text_color" in result["modified"]
        assert "alignment" in result["modified"]

    def test_only_specified(self):
        _create_doc()
        text = cmd_place_text({"x": 10, "y": 20, "w": 50, "h": 50})
        name = text["name"]
        result = cmd_modify_object({"name": name, "x": 99})
        assert result["modified"] == ["position"]
        assert mock_scribus._doc.objects[name]["x"] == 99
        assert mock_scribus._doc.objects[name]["y"] == 20

    def test_returns_modified_list(self):
        _create_doc()
        text = cmd_place_text({"x": 0, "y": 0, "w": 50, "h": 50})
        result = cmd_modify_object({"name": text["name"]})
        assert result["modified"] == []


class TestCmdAddPage:
    def test_add_one(self):
        _create_doc()
        result = cmd_add_page({})
        assert result["added"] == 1
        assert result["total_pages"] == 2

    def test_add_multiple(self):
        _create_doc()
        result = cmd_add_page({"count": 3})
        assert result["added"] == 3
        assert result["total_pages"] == 4

    def test_returns_counts(self):
        _create_doc(pages=2)
        result = cmd_add_page({"count": 2})
        assert result["total_pages"] == 4


class TestCmdExportPdf:
    def test_basic(self):
        _create_doc()
        result = cmd_export_pdf({"file_path": "/tmp/out.pdf"})
        assert result["file_path"] == "/tmp/out.pdf"
        assert mock_scribus._last_pdf is not None
        assert mock_scribus._last_pdf.file == "/tmp/out.pdf"

    def test_screen_quality(self):
        _create_doc()
        cmd_export_pdf({"file_path": "/tmp/out.pdf", "quality": "screen"})
        assert mock_scribus._last_pdf.quality == 2
        assert mock_scribus._last_pdf.resolution == 150

    def test_pdf_version(self):
        _create_doc()
        cmd_export_pdf({"file_path": "/tmp/out.pdf", "pdf_version": "1.4"})
        assert mock_scribus._last_pdf.version == 14

    def test_pages_list(self):
        _create_doc(pages=3)
        cmd_export_pdf({"file_path": "/tmp/out.pdf", "pages": [1, 3]})
        assert mock_scribus._last_pdf.pages == [1, 3]


class TestCmdGetDocumentInfo:
    def test_empty_doc(self):
        _create_doc()
        result = cmd_get_document_info({})
        assert result["page_count"] == 1
        assert len(result["objects"]) == 0
        assert "Black" in result["colors"]

    def test_with_objects(self):
        _create_doc()
        cmd_place_text({"x": 0, "y": 0, "w": 50, "h": 50, "text": "Hi"})
        cmd_draw_shape({"shape": "rectangle"})
        result = cmd_get_document_info({})
        assert len(result["objects"]) == 2

    def test_colors(self):
        _create_doc()
        cmd_define_color({"name": "MyColor", "mode": "rgb", "r": 255, "g": 0, "b": 0})
        result = cmd_get_document_info({})
        assert "MyColor" in result["colors"]


class TestCmdRunScript:
    def test_returns_result(self):
        _create_doc()
        result = cmd_run_script({"code": "result = 42"})
        assert result["result"] == 42

    def test_none_result(self):
        _create_doc()
        result = cmd_run_script({"code": "x = 1"})
        assert result["result"] is None

    def test_non_serializable_becomes_string(self):
        result = cmd_run_script({"code": "result = object()"})
        assert isinstance(result["result"], str)


class TestCmdSaveDocument:
    def test_with_path(self):
        _create_doc()
        result = cmd_save_document({"file_path": "/tmp/doc.sla"})
        assert result["saved"] is True
        assert mock_scribus._saved_path == "/tmp/doc.sla"

    def test_without_path(self):
        _create_doc()
        result = cmd_save_document({})
        assert result["saved"] is True
        assert mock_scribus._saved_path is True


class TestCmdShutdown:
    def test_exits_cleanly(self):
        _create_doc()
        with pytest.raises(SystemExit) as exc_info:
            cmd_shutdown({})
        assert exc_info.value.code == 0

    def test_handles_no_document(self):
        # No doc created — should still exit cleanly
        with pytest.raises(SystemExit) as exc_info:
            cmd_shutdown({})
        assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


class TestMainLoop:
    def _run_main(self, input_lines):
        """Run main() with given stdin lines, return captured protocol output."""
        from scribus_mcp import bridge

        stdin_data = "\n".join(input_lines) + "\n"
        old_real_stdin = bridge._real_stdin
        bridge._real_stdin = io.StringIO(stdin_data)

        captured = []
        original_send = bridge._send

        def capture_send(obj):
            captured.append(obj)

        bridge._send = capture_send
        try:
            main()
        except (SystemExit, StopIteration):
            pass
        finally:
            bridge._real_stdin = old_real_stdin
            bridge._send = original_send

        return captured

    def test_ready_sentinel(self):
        output = self._run_main([])
        assert output[0] == {"ready": True}

    def test_dispatches_command(self):
        _create_doc()
        cmd = json.dumps({"command": "add_page", "params": {"count": 1}})
        output = self._run_main([cmd])
        # First is ready, second is the response
        assert output[1]["ok"] is True
        assert output[1]["result"]["added"] == 1

    def test_unknown_command_error(self):
        cmd = json.dumps({"command": "fly_to_moon", "params": {}})
        output = self._run_main([cmd])
        assert output[1]["ok"] is False
        assert "Unknown command" in output[1]["error"]

    def test_invalid_json(self):
        output = self._run_main(["this is not json"])
        assert output[1]["ok"] is False
        assert "Invalid JSON" in output[1]["error"]


class TestCommandDispatch:
    def test_all_handlers_registered(self):
        expected = {
            "create_document",
            "define_color",
            "place_text",
            "place_image",
            "draw_shape",
            "modify_object",
            "add_page",
            "export_pdf",
            "get_document_info",
            "run_script",
            "save_document",
            "shutdown",
        }
        assert set(COMMANDS.keys()) == expected

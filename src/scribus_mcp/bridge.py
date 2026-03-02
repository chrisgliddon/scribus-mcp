#!/usr/bin/env python
"""Bridge script that runs inside Scribus's embedded Python interpreter.

Launched via: Scribus -g -ns -py bridge.py
Reads JSON commands from stdin, executes them against the scribus module,
and writes JSON responses to stdout.

IMPORTANT: This file must only use stdlib + the scribus module.
No third-party imports allowed.
"""

import json
import os
import sys
import traceback

# ---------------------------------------------------------------------------
# stdio contamination mitigation
#
# Scribus replaces sys.stdin with a StringIO and emits diagnostic messages to
# stdout during startup. We save the real file descriptors for both stdin and
# stdout, then redirect sys.stdout to stderr so stray prints don't corrupt
# the NDJSON protocol.
# ---------------------------------------------------------------------------

_real_stdout_fd = os.dup(sys.stdout.fileno())
_real_stdout = os.fdopen(_real_stdout_fd, "w", buffering=1)  # line-buffered

# Scribus replaces sys.stdin with a StringIO, so open fd 0 directly
_real_stdin = os.fdopen(0, "r", buffering=1)  # line-buffered

# Redirect sys.stdout to stderr so stray prints don't corrupt the protocol
sys.stdout = sys.stderr


def _send(obj):
    """Write a JSON object to the real stdout (protocol channel)."""
    _real_stdout.write(json.dumps(obj) + "\n")
    _real_stdout.flush()


def _ok(result=None):
    """Send a success response."""
    _send({"ok": True, "result": result})


def _error(message, code=None):
    """Send an error response."""
    resp = {"ok": False, "error": message}
    if code:
        resp["code"] = code
    _send(resp)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

import scribus


def _unit_constant(unit_str):
    """Convert a unit string to a Scribus constant."""
    mapping = {
        "mm": scribus.UNIT_MILLIMETERS,
        "pt": scribus.UNIT_POINTS,
        "in": scribus.UNIT_INCHES,
        "inch": scribus.UNIT_INCHES,
        "p": scribus.UNIT_PICAS,
        "pica": scribus.UNIT_PICAS,
    }
    return mapping.get(unit_str, scribus.UNIT_MILLIMETERS)


def _alignment_constant(align_str):
    """Convert an alignment string to a Scribus constant."""
    mapping = {
        "left": scribus.ALIGN_LEFT,
        "center": scribus.ALIGN_CENTERED,
        "right": scribus.ALIGN_RIGHT,
        "justify": scribus.ALIGN_BLOCK,
        "block": scribus.ALIGN_BLOCK,
        "forced": scribus.ALIGN_FORCED,
    }
    return mapping.get(align_str, scribus.ALIGN_LEFT)


def _go_to_page(page):
    """Navigate to a page if specified (1-based)."""
    if page is not None:
        scribus.gotoPage(int(page))


def cmd_create_document(params):
    """Create new document with given dimensions, margins, and page count."""
    width = params.get("width", 210)
    height = params.get("height", 297)
    unit = _unit_constant(params.get("unit", "mm"))

    # Asymmetric margins: individual values override uniform 'margins'
    margins_val = params.get("margins", 20)
    if isinstance(margins_val, dict):
        mt = margins_val.get("top", 20)
        mr = margins_val.get("right", 20)
        mb = margins_val.get("bottom", 20)
        ml = margins_val.get("left", 20)
    else:
        mt = mr = mb = ml = margins_val

    mt = params.get("margin_top", mt)
    mb = params.get("margin_bottom", mb)
    ml = params.get("margin_left", ml)
    mr = params.get("margin_right", mr)

    pages = params.get("pages", 1)
    orientation = params.get("orientation", 0)  # 0=portrait, 1=landscape

    facing_pages = params.get("facing_pages", False)
    pages_type = 1 if facing_pages else 0

    first_page_left = params.get("first_page_left", False)
    first_page_order = 0 if first_page_left else 1 if facing_pages else 0

    scribus.newDocument(
        (width, height),
        (ml, mr, mt, mb),
        orientation,
        1,  # firstPageNumber
        unit,
        pages_type,
        first_page_order,
        pages,
    )

    # Bleeds
    bt = params.get("bleed_top", 0)
    bb = params.get("bleed_bottom", 0)
    bl = params.get("bleed_left", 0)
    br = params.get("bleed_right", 0)
    if bt or bb or bl or br:
        scribus.setBleeds(bl, br, bt, bb)

    return {
        "width": width,
        "height": height,
        "unit": params.get("unit", "mm"),
        "pages": pages,
    }


def cmd_define_color(params):
    """Define a named CMYK or RGB color in the document palette."""
    name = params["name"]
    mode = params.get("mode", "cmyk")

    if mode == "cmyk":
        # Input: 0-100 percentage, Scribus wants 0-255
        c = int(params.get("c", 0) * 2.55)
        m = int(params.get("m", 0) * 2.55)
        y = int(params.get("y", 0) * 2.55)
        k = int(params.get("k", 0) * 2.55)
        scribus.defineColorCMYK(name, c, m, y, k)
    else:
        r = int(params.get("r", 0))
        g = int(params.get("g", 0))
        b = int(params.get("b", 0))
        scribus.defineColorRGB(name, r, g, b)

    return {"name": name, "mode": mode}


def cmd_place_text(params):
    """Create a text frame and optionally set content and styling."""
    x = params.get("x", 0)
    y = params.get("y", 0)
    w = params.get("w", 100)
    h = params.get("h", 50)
    text = params.get("text", "")
    page = params.get("page")

    _go_to_page(page)

    frame_name = scribus.createText(x, y, w, h)

    if text:
        scribus.setText(text, frame_name)

    font = params.get("font")
    if font:
        scribus.setFont(font, frame_name)

    font_size = params.get("font_size")
    if font_size:
        scribus.setFontSize(font_size, frame_name)

    color = params.get("color")
    if color:
        scribus.setTextColor(color, frame_name)

    alignment = params.get("alignment")
    if alignment:
        scribus.setTextAlignment(_alignment_constant(alignment), frame_name)

    # Line spacing
    ls_mode = params.get("line_spacing_mode")
    if ls_mode is not None:
        scribus.setLineSpacingMode(ls_mode, frame_name)

    ls = params.get("line_spacing")
    if ls is not None:
        scribus.setLineSpacing(ls, frame_name)

    # Text columns
    cols = params.get("columns")
    if cols is not None:
        scribus.setColumns(cols, frame_name)

    col_gap = params.get("column_gap")
    if col_gap is not None:
        scribus.setColumnGap(col_gap, frame_name)

    # Paragraph style
    style = params.get("style")
    if style:
        scribus.setStyle(style, frame_name)

    return {"name": frame_name}


def cmd_place_image(params):
    """Create an image frame, load a file, and optionally scale to fit."""
    x = params.get("x", 0)
    y = params.get("y", 0)
    w = params.get("w", 100)
    h = params.get("h", 100)
    file_path = params["file_path"]
    page = params.get("page")

    _go_to_page(page)

    frame_name = scribus.createImage(x, y, w, h)
    scribus.loadImage(file_path, frame_name)

    scale_to_frame = params.get("scale_to_frame", True)
    if scale_to_frame:
        proportional = params.get("proportional", True)
        scribus.setScaleImageToFrame(True, proportional, frame_name)

    return {"name": frame_name}


def cmd_draw_shape(params):
    """Draw a rectangle, ellipse, or line with optional fill and stroke."""
    shape = params.get("shape", "rectangle")

    if shape == "line":
        x1 = params.get("x1", 0)
        y1 = params.get("y1", 0)
        x2 = params.get("x2", 100)
        y2 = params.get("y2", 100)
        frame_name = scribus.createLine(x1, y1, x2, y2)
    elif shape == "ellipse":
        x = params.get("x", 0)
        y = params.get("y", 0)
        w = params.get("w", 100)
        h = params.get("h", 100)
        frame_name = scribus.createEllipse(x, y, w, h)
    else:  # rectangle
        x = params.get("x", 0)
        y = params.get("y", 0)
        w = params.get("w", 100)
        h = params.get("h", 100)
        frame_name = scribus.createRect(x, y, w, h)

    fill_color = params.get("fill_color")
    if fill_color:
        scribus.setFillColor(fill_color, frame_name)

    line_color = params.get("line_color")
    if line_color:
        scribus.setLineColor(line_color, frame_name)

    line_width = params.get("line_width")
    if line_width is not None:
        scribus.setLineWidth(line_width, frame_name)

    return {"name": frame_name, "shape": shape}


def cmd_modify_object(params):
    """Modify position, size, rotation, colors, or text props of a named object."""
    name = params["name"]
    modified = []

    x = params.get("x")
    y = params.get("y")
    if x is not None or y is not None:
        pos = scribus.getPosition(name)
        new_x = x if x is not None else pos[0]
        new_y = y if y is not None else pos[1]
        scribus.moveObjectAbs(new_x, new_y, name)
        modified.append("position")

    w = params.get("w")
    h = params.get("h")
    if w is not None or h is not None:
        size = scribus.getSize(name)
        new_w = w if w is not None else size[0]
        new_h = h if h is not None else size[1]
        scribus.sizeObject(new_w, new_h, name)
        modified.append("size")

    rotation = params.get("rotation")
    if rotation is not None:
        scribus.rotateObjectAbs(rotation, name)
        modified.append("rotation")

    fill_color = params.get("fill_color")
    if fill_color is not None:
        scribus.setFillColor(fill_color, name)
        modified.append("fill_color")

    line_color = params.get("line_color")
    if line_color is not None:
        scribus.setLineColor(line_color, name)
        modified.append("line_color")

    line_width = params.get("line_width")
    if line_width is not None:
        scribus.setLineWidth(line_width, name)
        modified.append("line_width")

    # Text properties (only applicable to text frames)
    text = params.get("text")
    if text is not None:
        scribus.setText(text, name)
        modified.append("text")

    font = params.get("font")
    if font is not None:
        scribus.setFont(font, name)
        modified.append("font")

    font_size = params.get("font_size")
    if font_size is not None:
        scribus.setFontSize(font_size, name)
        modified.append("font_size")

    text_color = params.get("text_color")
    if text_color is not None:
        scribus.setTextColor(text_color, name)
        modified.append("text_color")

    alignment = params.get("alignment")
    if alignment is not None:
        scribus.setTextAlignment(_alignment_constant(alignment), name)
        modified.append("alignment")

    # Line spacing
    ls_mode = params.get("line_spacing_mode")
    if ls_mode is not None:
        scribus.setLineSpacingMode(ls_mode, name)
        modified.append("line_spacing_mode")

    ls = params.get("line_spacing")
    if ls is not None:
        scribus.setLineSpacing(ls, name)
        modified.append("line_spacing")

    # Text columns
    cols = params.get("columns")
    if cols is not None:
        scribus.setColumns(cols, name)
        modified.append("columns")

    col_gap = params.get("column_gap")
    if col_gap is not None:
        scribus.setColumnGap(col_gap, name)
        modified.append("column_gap")

    return {"name": name, "modified": modified}


def cmd_add_page(params):
    """Append one or more pages to the document."""
    count = params.get("count", 1)
    where = params.get("where", -1)
    master_page = params.get("master_page", "")

    for _ in range(count):
        scribus.newPage(where, master_page)

    return {"added": count, "total_pages": scribus.pageCount()}


def cmd_export_pdf(params):
    """Export document as PDF with configurable quality, version, and prepress options."""
    file_path = params["file_path"]

    pdf = scribus.PDFfile()
    pdf.file = file_path

    quality = params.get("quality", "press")
    if quality == "screen":
        pdf.quality = 2  # lower quality, smaller file
        pdf.resolution = 150
    elif quality == "ebook":
        pdf.quality = 1
        pdf.resolution = 150
    else:  # press
        pdf.quality = 0  # max quality
        pdf.resolution = 300

    # Custom resolution overrides quality preset
    resolution = params.get("resolution")
    if resolution is not None:
        pdf.resolution = resolution

    pdf_version = params.get("pdf_version")
    if pdf_version:
        version_map = {
            "1.3": 13,
            "1.4": 14,
            "1.5": 15,
            "x-1a": 11,
            "x-3": 12,
            "x-4": 10,
        }
        ver = version_map.get(str(pdf_version))
        if ver:
            pdf.version = ver

    pages_param = params.get("pages")
    if pages_param and isinstance(pages_param, list):
        pdf.pages = pages_param

    # Printer marks
    if params.get("crop_marks"):
        pdf.cropMarks = True
    if params.get("bleed_marks"):
        pdf.bleedMarks = True
    if params.get("registration_marks"):
        pdf.registrationMarks = True
    if params.get("color_marks"):
        pdf.colorMarks = True

    mark_length = params.get("mark_length")
    if mark_length is not None:
        pdf.markLength = mark_length

    mark_offset = params.get("mark_offset")
    if mark_offset is not None:
        pdf.markOffset = mark_offset

    # Bleeds
    if params.get("use_doc_bleeds", True):
        pdf.useDocBleeds = True

    # Color management
    output_profile = params.get("output_profile")
    if output_profile:
        pdf.outputProfile = output_profile

    if params.get("embed_profiles"):
        pdf.embedProfiles = True

    info = params.get("info")
    if info:
        pdf.info = info

    # Font embedding
    font_embedding = params.get("font_embedding", "embed")
    if font_embedding == "outline":
        pdf.fontEmbedding = 1
    elif font_embedding == "none":
        pdf.fontEmbedding = 2
    else:
        pdf.fontEmbedding = 0

    pdf.save()
    return {"file_path": file_path}


def cmd_get_document_info(params):
    """Return page dims, object list, and color palette."""
    page_count = scribus.pageCount()
    pages = []
    for i in range(1, page_count + 1):
        scribus.gotoPage(i)
        size = scribus.getPageSize()
        pages.append({"number": i, "width": size[0], "height": size[1]})

    items = []
    for item_info in scribus.getPageItems():
        name, obj_type, page_num = item_info
        items.append(
            {
                "name": name,
                "type": obj_type,
                "page": page_num,
            }
        )

    colors = scribus.getColorNames()
    margins = scribus.getPageMargins()
    master_pages = list(scribus.masterPageNames())
    paragraph_styles = list(scribus.getParagraphStyles())
    char_styles = list(scribus.getCharStyles())

    return {
        "page_count": page_count,
        "pages": pages,
        "objects": items,
        "colors": list(colors),
        "margins": {
            "left": margins[0],
            "right": margins[1],
            "top": margins[2],
            "bottom": margins[3],
        },
        "master_pages": master_pages,
        "paragraph_styles": paragraph_styles,
        "char_styles": char_styles,
    }


def cmd_run_script(params):
    """Execute arbitrary Python code inside the Scribus interpreter."""
    code = params["code"]
    namespace = {"scribus": scribus, "result": None}
    exec(code, namespace)
    result = namespace.get("result")
    # Ensure result is JSON-serializable
    if result is not None:
        try:
            json.dumps(result)
        except (TypeError, ValueError):
            result = str(result)
    return {"result": result}


def cmd_set_baseline_grid(params):
    """Set the document baseline grid spacing and offset."""
    grid = params["grid"]
    offset = params.get("offset", 0)
    scribus.setBaseLine(grid, offset)
    return {"grid": grid, "offset": offset}


def cmd_create_paragraph_style(params):
    """Create a named paragraph style."""
    kwargs = {"name": params["name"]}
    if "font" in params:
        kwargs["font"] = params["font"]
    if "font_size" in params:
        kwargs["fontsize"] = params["font_size"]
    if "line_spacing" in params:
        kwargs["linespacing"] = params["line_spacing"]
    if "line_spacing_mode" in params:
        kwargs["linespacingmode"] = params["line_spacing_mode"]
    if "alignment" in params:
        kwargs["alignment"] = _alignment_constant(params["alignment"])
    if "first_indent" in params:
        kwargs["firstindent"] = params["first_indent"]
    if "space_above" in params:
        kwargs["spaceabove"] = params["space_above"]
    if "space_below" in params:
        kwargs["spacebelow"] = params["space_below"]
    if "drop_cap" in params:
        kwargs["hasdropcap"] = params["drop_cap"]
    if "drop_cap_lines" in params:
        kwargs["dropcaplines"] = params["drop_cap_lines"]
    if "char_style" in params:
        kwargs["charstyle"] = params["char_style"]

    scribus.createParagraphStyle(**kwargs)
    return {"name": params["name"]}


def cmd_create_char_style(params):
    """Create a named character style."""
    kwargs = {"name": params["name"]}
    if "font" in params:
        kwargs["font"] = params["font"]
    if "font_size" in params:
        kwargs["fontsize"] = params["font_size"]
    if "fill_color" in params:
        kwargs["fillcolor"] = params["fill_color"]
    if "features" in params:
        kwargs["features"] = params["features"]
    if "tracking" in params:
        kwargs["tracking"] = params["tracking"]

    scribus.createCharStyle(**kwargs)
    return {"name": params["name"]}


def cmd_link_text_frames(params):
    """Link two text frames for text flow."""
    from_frame = params["from_frame"]
    to_frame = params["to_frame"]
    scribus.linkTextFrames(from_frame, to_frame)
    return {"from_frame": from_frame, "to_frame": to_frame}


def cmd_unlink_text_frames(params):
    """Unlink a text frame from its chain."""
    frame = params["frame"]
    scribus.unlinkTextFrames(frame)
    return {"frame": frame}


def cmd_set_guides(params):
    """Set horizontal and/or vertical guides on a page."""
    page = params.get("page")
    _go_to_page(page)

    horizontal = params.get("horizontal")
    if horizontal is not None:
        scribus.setHGuides(horizontal)

    vertical = params.get("vertical")
    if vertical is not None:
        scribus.setVGuides(vertical)

    return {"horizontal": horizontal, "vertical": vertical}


def cmd_create_master_page(params):
    """Create a new master page."""
    name = params["name"]
    scribus.createMasterPage(name)
    return {"name": name}


def cmd_edit_master_page(params):
    """Enter editing mode for a master page."""
    name = params["name"]
    scribus.editMasterPage(name)
    return {"name": name}


def cmd_close_master_page(params):
    """Exit master page editing mode."""
    scribus.closeMasterPage()
    return {}


def cmd_apply_master_page(params):
    """Apply a master page to a document page."""
    master_page = params["master_page"]
    page = params["page"]
    scribus.applyMasterPage(master_page, page)
    return {"master_page": master_page, "page": page}


def cmd_list_master_pages(params):
    """List all master page names."""
    names = scribus.masterPageNames()
    return {"master_pages": list(names)}


def cmd_save_document(params):
    """Save document to a path, or current path if none given."""
    file_path = params.get("file_path")
    if file_path:
        scribus.saveDocAs(file_path)
    else:
        scribus.saveDoc()
    return {"saved": True}


def cmd_shutdown(params):
    """Graceful shutdown."""
    try:
        if scribus.haveDoc():
            scribus.closeDoc()
    except Exception:
        pass
    _ok({"shutdown": True})
    sys.exit(0)


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------

COMMANDS = {
    "create_document": cmd_create_document,
    "define_color": cmd_define_color,
    "place_text": cmd_place_text,
    "place_image": cmd_place_image,
    "draw_shape": cmd_draw_shape,
    "modify_object": cmd_modify_object,
    "add_page": cmd_add_page,
    "export_pdf": cmd_export_pdf,
    "get_document_info": cmd_get_document_info,
    "run_script": cmd_run_script,
    "save_document": cmd_save_document,
    "shutdown": cmd_shutdown,
    "set_baseline_grid": cmd_set_baseline_grid,
    "create_paragraph_style": cmd_create_paragraph_style,
    "create_char_style": cmd_create_char_style,
    "link_text_frames": cmd_link_text_frames,
    "unlink_text_frames": cmd_unlink_text_frames,
    "set_guides": cmd_set_guides,
    "create_master_page": cmd_create_master_page,
    "edit_master_page": cmd_edit_master_page,
    "close_master_page": cmd_close_master_page,
    "apply_master_page": cmd_apply_master_page,
    "list_master_pages": cmd_list_master_pages,
}


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main():
    """Read NDJSON commands from stdin and dispatch to handlers in a loop."""
    # Send ready sentinel
    _send({"ready": True})

    for line in _real_stdin:
        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            _error(f"Invalid JSON: {e}")
            continue

        command = msg.get("command")
        params = msg.get("params", {})

        if command not in COMMANDS:
            _error(f"Unknown command: {command}", code="unknown_command")
            continue

        try:
            result = COMMANDS[command](params)
            _ok(result)
        except Exception as e:
            _error(f"{type(e).__name__}: {e}", code="execution_error")
            # Also log traceback to stderr for debugging
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    main()

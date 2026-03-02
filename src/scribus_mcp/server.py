"""FastMCP server exposing Scribus layout tools to LLMs."""

import atexit
import logging
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import ScribusClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("Scribus")

# Lazy singleton client
_client: ScribusClient | None = None


def _get_client() -> ScribusClient:
    """Get or create the ScribusClient singleton."""
    global _client
    if _client is None:
        _client = ScribusClient()
        atexit.register(_client.shutdown)
    return _client


def _save_after(result):
    """Save the document after a mutation."""
    try:
        _get_client().save_document()
    except Exception as e:
        logger.warning("Auto-save failed: %s", e)
    return result


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def create_document(
    width: float = 210,
    height: float = 297,
    margins: float = 20,
    margin_top: float | None = None,
    margin_bottom: float | None = None,
    margin_left: float | None = None,
    margin_right: float | None = None,
    facing_pages: bool = False,
    first_page_left: bool = False,
    bleed_top: float = 0,
    bleed_bottom: float = 0,
    bleed_left: float = 0,
    bleed_right: float = 0,
    unit: str = "mm",
    pages: int = 1,
    orientation: int = 0,
) -> str:
    """Create a new Scribus document.

    Args:
        width: Page width in the specified unit (default: 210 for A4)
        height: Page height in the specified unit (default: 297 for A4)
        margins: Uniform page margins on all sides (default: 20)
        margin_top: Top margin (overrides uniform margins)
        margin_bottom: Bottom margin (overrides uniform margins)
        margin_left: Left/inner margin (overrides uniform margins)
        margin_right: Right/outer margin (overrides uniform margins)
        facing_pages: Enable facing pages (spreads) for book layouts
        first_page_left: Start book with a left page (default: right start)
        bleed_top: Top bleed in document units (default: 0)
        bleed_bottom: Bottom bleed in document units (default: 0)
        bleed_left: Left bleed in document units (default: 0)
        bleed_right: Right bleed in document units (default: 0)
        unit: Measurement unit - "mm", "pt", "in", or "p" (default: "mm")
        pages: Number of initial pages (default: 1)
        orientation: 0 for portrait, 1 for landscape (default: 0)

    """
    client = _get_client()
    params: dict[str, Any] = {
        "width": width,
        "height": height,
        "margins": margins,
        "unit": unit,
        "pages": pages,
        "orientation": orientation,
        "facing_pages": facing_pages,
        "first_page_left": first_page_left,
        "bleed_top": bleed_top,
        "bleed_bottom": bleed_bottom,
        "bleed_left": bleed_left,
        "bleed_right": bleed_right,
    }
    if margin_top is not None:
        params["margin_top"] = margin_top
    if margin_bottom is not None:
        params["margin_bottom"] = margin_bottom
    if margin_left is not None:
        params["margin_left"] = margin_left
    if margin_right is not None:
        params["margin_right"] = margin_right

    result = client.send_command("create_document", params)
    client._document_path = None
    _save_after(result)
    w, h, u, p = result["width"], result["height"], result["unit"], result["pages"]
    return f"Created {w}x{h}{u} document with {p} page(s)."


@mcp.tool()
def define_color(
    name: str,
    mode: str = "cmyk",
    c: float = 0,
    m: float = 0,
    y: float = 0,
    k: float = 0,
    r: int = 0,
    g: int = 0,
    b: int = 0,
) -> str:
    """Define a named color in the document palette.

    Args:
        name: Color name (e.g. "BrandRed")
        mode: "cmyk" or "rgb" (default: "cmyk")
        c: Cyan 0-100% (CMYK mode)
        m: Magenta 0-100% (CMYK mode)
        y: Yellow 0-100% (CMYK mode)
        k: Black 0-100% (CMYK mode)
        r: Red 0-255 (RGB mode)
        g: Green 0-255 (RGB mode)
        b: Blue 0-255 (RGB mode)

    """
    client = _get_client()
    params: dict[str, Any] = {"name": name, "mode": mode}
    if mode == "cmyk":
        params.update({"c": c, "m": m, "y": y, "k": k})
    else:
        params.update({"r": r, "g": g, "b": b})

    result = client.send_command("define_color", params)
    _save_after(result)

    if mode == "cmyk":
        return f"Defined CMYK color '{name}' (C={c} M={m} Y={y} K={k})."
    else:
        return f"Defined RGB color '{name}' (R={r} G={g} B={b})."


@mcp.tool()
def place_text(
    x: float,
    y: float,
    w: float,
    h: float,
    text: str = "",
    font: str | None = None,
    font_size: float | None = None,
    color: str | None = None,
    alignment: str | None = None,
    page: int | None = None,
    line_spacing: float | None = None,
    line_spacing_mode: int | None = None,
    columns: int | None = None,
    column_gap: float | None = None,
    style: str | None = None,
) -> str:
    """Create a text frame and optionally fill it with styled text.

    Args:
        x: X position of the text frame
        y: Y position of the text frame
        w: Width of the text frame
        h: Height of the text frame
        text: Text content to place in the frame
        font: Font name (e.g. "Arial Regular")
        font_size: Font size in points
        color: Color name (must be defined in the document palette)
        alignment: Text alignment - "left", "center", "right", "justify"
        page: Page number (1-based) to place the text on
        line_spacing: Line spacing (leading) in points
        line_spacing_mode: 0=fixed, 1=automatic, 2=align to baseline grid
        columns: Number of text columns
        column_gap: Gap between columns in document units
        style: Paragraph style name to apply

    """
    client = _get_client()
    params: dict[str, Any] = {"x": x, "y": y, "w": w, "h": h, "text": text}
    for key, val in [
        ("font", font),
        ("font_size", font_size),
        ("color", color),
        ("alignment", alignment),
        ("page", page),
        ("line_spacing", line_spacing),
        ("line_spacing_mode", line_spacing_mode),
        ("columns", columns),
        ("column_gap", column_gap),
        ("style", style),
    ]:
        if val is not None:
            params[key] = val

    result = client.send_command("place_text", params)
    _save_after(result)

    desc = f"Created text frame '{result['name']}' at ({x}, {y})"
    if text:
        preview = text[:50] + "..." if len(text) > 50 else text
        desc += f' with text: "{preview}"'
    return desc + "."


@mcp.tool()
def place_image(
    x: float,
    y: float,
    w: float,
    h: float,
    file_path: str,
    scale_to_frame: bool = True,
    proportional: bool = True,
    page: int | None = None,
) -> str:
    """Create an image frame and load an image file into it.

    Args:
        x: X position of the image frame
        y: Y position of the image frame
        w: Width of the image frame
        h: Height of the image frame
        file_path: Absolute path to the image file
        scale_to_frame: Whether to scale image to fit the frame (default: True)
        proportional: Keep aspect ratio when scaling (default: True)
        page: Page number (1-based) to place the image on

    """
    client = _get_client()
    params: dict[str, Any] = {
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "file_path": file_path,
        "scale_to_frame": scale_to_frame,
        "proportional": proportional,
    }
    if page is not None:
        params["page"] = page

    result = client.send_command("place_image", params)
    _save_after(result)
    return f"Placed image '{file_path}' in frame '{result['name']}' at ({x}, {y})."


@mcp.tool()
def draw_shape(
    shape: str = "rectangle",
    x: float = 0,
    y: float = 0,
    w: float = 100,
    h: float = 100,
    x1: float | None = None,
    y1: float | None = None,
    x2: float | None = None,
    y2: float | None = None,
    fill_color: str | None = None,
    line_color: str | None = None,
    line_width: float | None = None,
) -> str:
    """Draw a shape: rectangle, ellipse, or line.

    For rectangles and ellipses, use x/y/w/h.
    For lines, use x1/y1/x2/y2.

    Args:
        shape: Shape type - "rectangle", "ellipse", or "line"
        x: X position (rectangles/ellipses)
        y: Y position (rectangles/ellipses)
        w: Width (rectangles/ellipses)
        h: Height (rectangles/ellipses)
        x1: Start X (lines only)
        y1: Start Y (lines only)
        x2: End X (lines only)
        y2: End Y (lines only)
        fill_color: Fill color name (must be defined in palette)
        line_color: Stroke/line color name
        line_width: Line width in points

    """
    client = _get_client()
    params: dict[str, Any] = {"shape": shape}

    if shape == "line":
        params.update(
            {
                "x1": x1 if x1 is not None else 0,
                "y1": y1 if y1 is not None else 0,
                "x2": x2 if x2 is not None else 100,
                "y2": y2 if y2 is not None else 100,
            }
        )
    else:
        params.update({"x": x, "y": y, "w": w, "h": h})

    if fill_color is not None:
        params["fill_color"] = fill_color
    if line_color is not None:
        params["line_color"] = line_color
    if line_width is not None:
        params["line_width"] = line_width

    result = client.send_command("draw_shape", params)
    _save_after(result)
    return f"Drew {result['shape']} '{result['name']}'."


@mcp.tool()
def modify_object(
    name: str,
    x: float | None = None,
    y: float | None = None,
    w: float | None = None,
    h: float | None = None,
    rotation: float | None = None,
    fill_color: str | None = None,
    line_color: str | None = None,
    line_width: float | None = None,
    text: str | None = None,
    font: str | None = None,
    font_size: float | None = None,
    text_color: str | None = None,
    alignment: str | None = None,
    line_spacing: float | None = None,
    line_spacing_mode: int | None = None,
    columns: int | None = None,
    column_gap: float | None = None,
) -> str:
    """Modify properties of an existing object.

    Only provided parameters will be changed; others are left untouched.

    Args:
        name: Object name (returned by create functions)
        x: New X position
        y: New Y position
        w: New width
        h: New height
        rotation: Rotation angle in degrees
        fill_color: New fill color name
        line_color: New line/stroke color name
        line_width: New line width in points
        text: New text content (text frames only)
        font: New font name (text frames only)
        font_size: New font size in points (text frames only)
        text_color: New text color name (text frames only)
        alignment: New text alignment (text frames only)
        line_spacing: Line spacing (leading) in points (text frames only)
        line_spacing_mode: 0=fixed, 1=automatic, 2=align to baseline grid (text frames only)
        columns: Number of text columns (text frames only)
        column_gap: Gap between columns in document units (text frames only)

    """
    client = _get_client()
    params: dict[str, Any] = {"name": name}

    for key, val in [
        ("x", x),
        ("y", y),
        ("w", w),
        ("h", h),
        ("rotation", rotation),
        ("fill_color", fill_color),
        ("line_color", line_color),
        ("line_width", line_width),
        ("text", text),
        ("font", font),
        ("font_size", font_size),
        ("text_color", text_color),
        ("alignment", alignment),
        ("line_spacing", line_spacing),
        ("line_spacing_mode", line_spacing_mode),
        ("columns", columns),
        ("column_gap", column_gap),
    ]:
        if val is not None:
            params[key] = val

    result = client.send_command("modify_object", params)
    _save_after(result)
    modified = ", ".join(result.get("modified", []))
    return f"Modified '{name}': updated {modified}."


@mcp.tool()
def add_page(
    count: int = 1,
    where: int = -1,
    master_page: str = "",
) -> str:
    """Add one or more pages to the document.

    Args:
        count: Number of pages to add (default: 1)
        where: Position to insert (-1 = append at end, or page number)
        master_page: Name of the master page to apply

    """
    client = _get_client()
    result = client.send_command(
        "add_page",
        {
            "count": count,
            "where": where,
            "master_page": master_page,
        },
    )
    _save_after(result)
    return f"Added {result['added']} page(s). Document now has {result['total_pages']} pages."


@mcp.tool()
def export_pdf(
    file_path: str,
    quality: str = "press",
    pdf_version: str | None = None,
    pages: list[int] | None = None,
    crop_marks: bool = False,
    bleed_marks: bool = False,
    registration_marks: bool = False,
    color_marks: bool = False,
    mark_length: float | None = None,
    mark_offset: float | None = None,
    use_doc_bleeds: bool = True,
    output_profile: str | None = None,
    embed_profiles: bool = False,
    info: str | None = None,
    font_embedding: str = "embed",
    resolution: int | None = None,
) -> str:
    """Export the document as a PDF file.

    Args:
        file_path: Output PDF file path
        quality: Quality preset - "screen" (150dpi), "ebook" (150dpi), "press" (300dpi)
        pdf_version: PDF version - "1.3", "1.4", "1.5", "x-1a", "x-3", "x-4"
        pages: List of page numbers to export (default: all pages)
        crop_marks: Add crop/trim marks
        bleed_marks: Add bleed marks
        registration_marks: Add registration marks
        color_marks: Add color calibration marks
        mark_length: Length of printer marks in points
        mark_offset: Offset of marks from page edge in points
        use_doc_bleeds: Use document bleed settings (default: True)
        output_profile: ICC output color profile name (e.g. "ISOcoated_v2_300_eci")
        embed_profiles: Embed ICC color profiles in the PDF
        info: PDF info string (required for PDF/X)
        font_embedding: "embed", "outline", or "none" (default: "embed")
        resolution: Custom DPI resolution (overrides quality preset)

    """
    client = _get_client()
    params: dict[str, Any] = {"file_path": file_path, "quality": quality}
    if pdf_version is not None:
        params["pdf_version"] = pdf_version
    if pages is not None:
        params["pages"] = pages

    # Prepress options
    params["crop_marks"] = crop_marks
    params["bleed_marks"] = bleed_marks
    params["registration_marks"] = registration_marks
    params["color_marks"] = color_marks
    params["use_doc_bleeds"] = use_doc_bleeds
    params["embed_profiles"] = embed_profiles
    params["font_embedding"] = font_embedding

    for key, val in [
        ("mark_length", mark_length),
        ("mark_offset", mark_offset),
        ("output_profile", output_profile),
        ("info", info),
        ("resolution", resolution),
    ]:
        if val is not None:
            params[key] = val

    result = client.send_command("export_pdf", params)
    return f"Exported PDF to {result['file_path']}."


@mcp.tool()
def get_document_info() -> str:
    """Get information about the current document.

    Includes pages, objects, colors, margins, master pages, and styles.
    """
    client = _get_client()
    result = client.send_command("get_document_info", {})

    lines = [f"Document has {result['page_count']} page(s)."]

    if result.get("pages"):
        lines.append("Pages:")
        for p in result["pages"]:
            lines.append(f"  Page {p['number']}: {p['width']}x{p['height']}")

    if result.get("margins"):
        m = result["margins"]
        lines.append(
            f"Margins: top={m['top']}, bottom={m['bottom']}, left={m['left']}, right={m['right']}"
        )

    if result.get("objects"):
        lines.append(f"Objects ({len(result['objects'])}):")
        for obj in result["objects"]:
            lines.append(f"  {obj['name']} (type={obj['type']}, page={obj['page']})")

    if result.get("colors"):
        lines.append(f"Colors: {', '.join(result['colors'])}")

    if result.get("master_pages"):
        lines.append(f"Master pages: {', '.join(result['master_pages'])}")

    if result.get("paragraph_styles"):
        lines.append(f"Paragraph styles: {', '.join(result['paragraph_styles'])}")

    if result.get("char_styles"):
        lines.append(f"Character styles: {', '.join(result['char_styles'])}")

    return "\n".join(lines)


@mcp.tool()
def open_document(file_path: str) -> str:
    """Open an existing Scribus .sla document for inspection and editing.

    Args:
        file_path: Absolute path to the .sla file to open

    """
    client = _get_client()
    result = client.send_command("open_document", {"file_path": file_path})
    client._document_path = Path(file_path)

    lines = [f"Opened '{file_path}' ({result['page_count']} page(s))."]
    if result.get("pages"):
        lines.append("Pages:")
        for p in result["pages"]:
            lines.append(f"  Page {p['number']}: {p['width']}x{p['height']}")
    if result.get("objects"):
        lines.append(f"Objects ({len(result['objects'])}):")
        for obj in result["objects"]:
            lines.append(f"  {obj['name']} (type={obj['type']}, page={obj['page']})")
    return "\n".join(lines)


@mcp.tool()
def get_object_properties(name: str) -> str:
    """Get detailed properties of a named object in the document.

    Returns position, size, rotation, and type-specific properties
    (text content, font, colors, etc.).

    Args:
        name: Object name (as returned by create functions or get_document_info)

    """
    client = _get_client()
    result = client.send_command("get_object_properties", {"name": name})

    obj_type = result["type"]
    lines = [
        f"Object '{name}' ({obj_type})",
        f"  Position: ({result['x']}, {result['y']})",
        f"  Size: {result['w']} x {result['h']}",
    ]
    if result.get("rotation"):
        lines.append(f"  Rotation: {result['rotation']}°")

    if obj_type == "text":
        text = result.get("text", "")
        preview = text[:80] + "..." if len(text) > 80 else text
        lines.append(f'  Text: "{preview}"')
        if result.get("font"):
            lines.append(f"  Font: {result['font']} {result.get('font_size', '')}pt")
        if result.get("text_color"):
            lines.append(f"  Text color: {result['text_color']}")
        if result.get("columns", 1) > 1:
            lines.append(f"  Columns: {result['columns']} (gap: {result.get('column_gap', 0)})")

    if obj_type in ("text", "image", "shape") and result.get("fill_color"):
        lines.append(f"  Fill: {result['fill_color']}")
    if result.get("line_color"):
        lines.append(f"  Line color: {result['line_color']}")
    if result.get("line_width"):
        lines.append(f"  Line width: {result['line_width']}")

    return "\n".join(lines)


@mcp.tool()
def delete_object(name: str) -> str:
    """Delete a named object from the document.

    Args:
        name: Object name to delete

    """
    client = _get_client()
    client.send_command("delete_object", {"name": name})
    _save_after({})
    return f"Deleted object '{name}'."


@mcp.tool()
def set_baseline_grid(
    grid: float,
    offset: float = 0,
) -> str:
    """Set the document baseline grid for aligning text across columns.

    Args:
        grid: Grid spacing in points
        offset: Grid offset from top of page in points (default: 0)

    """
    client = _get_client()
    result = client.send_command("set_baseline_grid", {"grid": grid, "offset": offset})
    _save_after(result)
    return f"Set baseline grid: {result['grid']}pt spacing, {result['offset']}pt offset."


@mcp.tool()
def create_paragraph_style(
    name: str,
    font: str | None = None,
    font_size: float | None = None,
    line_spacing: float | None = None,
    line_spacing_mode: int | None = None,
    alignment: str | None = None,
    first_indent: float | None = None,
    space_above: float | None = None,
    space_below: float | None = None,
    drop_cap: bool | None = None,
    drop_cap_lines: int | None = None,
    char_style: str | None = None,
) -> str:
    """Create a named paragraph style for consistent text formatting.

    Args:
        name: Style name
        font: Font name (e.g. "DejaVu Serif")
        font_size: Font size in points
        line_spacing: Line spacing (leading) in points
        line_spacing_mode: 0=fixed, 1=automatic, 2=align to baseline grid
        alignment: Text alignment - "left", "center", "right", "justify"
        first_indent: First line indent in document units
        space_above: Space above paragraph in points
        space_below: Space below paragraph in points
        drop_cap: Enable drop caps
        drop_cap_lines: Number of lines for drop cap
        char_style: Associated character style name

    """
    client = _get_client()
    params: dict[str, Any] = {"name": name}
    for key, val in [
        ("font", font),
        ("font_size", font_size),
        ("line_spacing", line_spacing),
        ("line_spacing_mode", line_spacing_mode),
        ("alignment", alignment),
        ("first_indent", first_indent),
        ("space_above", space_above),
        ("space_below", space_below),
        ("drop_cap", drop_cap),
        ("drop_cap_lines", drop_cap_lines),
        ("char_style", char_style),
    ]:
        if val is not None:
            params[key] = val

    result = client.send_command("create_paragraph_style", params)
    _save_after(result)
    return f"Created paragraph style '{result['name']}'."


@mcp.tool()
def create_char_style(
    name: str,
    font: str | None = None,
    font_size: float | None = None,
    fill_color: str | None = None,
    features: str | None = None,
    tracking: float | None = None,
) -> str:
    """Create a named character style.

    Args:
        name: Style name
        font: Font name
        font_size: Font size in points
        fill_color: Text color name
        features: Comma-separated features (e.g. "bold,italic,smallcaps")
        tracking: Letter spacing adjustment

    """
    client = _get_client()
    params: dict[str, Any] = {"name": name}
    for key, val in [
        ("font", font),
        ("font_size", font_size),
        ("fill_color", fill_color),
        ("features", features),
        ("tracking", tracking),
    ]:
        if val is not None:
            params[key] = val

    result = client.send_command("create_char_style", params)
    _save_after(result)
    return f"Created character style '{result['name']}'."


@mcp.tool()
def link_text_frames(
    from_frame: str,
    to_frame: str,
) -> str:
    """Link two text frames so text flows from one to the next.

    Args:
        from_frame: Source text frame name
        to_frame: Destination text frame name

    """
    client = _get_client()
    result = client.send_command(
        "link_text_frames", {"from_frame": from_frame, "to_frame": to_frame}
    )
    _save_after(result)
    return f"Linked '{from_frame}' → '{to_frame}'."


@mcp.tool()
def unlink_text_frames(
    frame: str,
) -> str:
    """Unlink a text frame from its text flow chain.

    Args:
        frame: Text frame name to unlink

    """
    client = _get_client()
    result = client.send_command("unlink_text_frames", {"frame": frame})
    _save_after(result)
    return f"Unlinked '{frame}'."


@mcp.tool()
def set_guides(
    horizontal: list[float] | None = None,
    vertical: list[float] | None = None,
    page: int | None = None,
) -> str:
    """Set horizontal and/or vertical guides on a page.

    Args:
        horizontal: List of Y positions for horizontal guides
        vertical: List of X positions for vertical guides
        page: Page number (1-based); defaults to current page

    """
    client = _get_client()
    params: dict[str, Any] = {}
    if horizontal is not None:
        params["horizontal"] = horizontal
    if vertical is not None:
        params["vertical"] = vertical
    if page is not None:
        params["page"] = page

    result = client.send_command("set_guides", params)
    _save_after(result)
    parts = []
    if result.get("horizontal") is not None:
        parts.append(f"{len(result['horizontal'])} horizontal")
    if result.get("vertical") is not None:
        parts.append(f"{len(result['vertical'])} vertical")
    return f"Set {' and '.join(parts)} guide(s)."


@mcp.tool()
def create_master_page(
    name: str,
) -> str:
    """Create a new master page.

    Args:
        name: Master page name

    """
    client = _get_client()
    result = client.send_command("create_master_page", {"name": name})
    _save_after(result)
    return f"Created master page '{result['name']}'."


@mcp.tool()
def edit_master_page(
    name: str,
) -> str:
    """Enter editing mode for a master page.

    Args:
        name: Master page name to edit

    """
    client = _get_client()
    result = client.send_command("edit_master_page", {"name": name})
    _save_after(result)
    return f"Editing master page '{result['name']}'."


@mcp.tool()
def close_master_page() -> str:
    """Exit master page editing mode and return to normal editing."""
    client = _get_client()
    client.send_command("close_master_page", {})
    _save_after({})
    return "Closed master page editing."


@mcp.tool()
def apply_master_page(
    master_page: str,
    page: int,
) -> str:
    """Apply a master page to a document page.

    Args:
        master_page: Name of the master page to apply
        page: Target page number (1-based)

    """
    client = _get_client()
    result = client.send_command(
        "apply_master_page", {"master_page": master_page, "page": page}
    )
    _save_after(result)
    return f"Applied master page '{master_page}' to page {page}."


@mcp.tool()
def list_master_pages() -> str:
    """List all master pages in the document."""
    client = _get_client()
    result = client.send_command("list_master_pages", {})
    names = result.get("master_pages", [])
    if names:
        return f"Master pages: {', '.join(names)}"
    return "No master pages defined."


@mcp.tool()
def run_script(code: str) -> str:
    """Execute raw Scribus Python code (escape hatch for advanced operations).

    The `scribus` module is available in the execution namespace.
    Set a `result` variable to return data.

    Args:
        code: Python code to execute inside Scribus

    """
    client = _get_client()
    result = client.send_command("run_script", {"code": code})
    _save_after(result)

    script_result = result.get("result")
    if script_result is not None:
        return f"Script executed. Result: {script_result}"
    return "Script executed successfully."


def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()

"""FastMCP server exposing Scribus layout tools to LLMs."""

import atexit
import logging

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
    unit: str = "mm",
    pages: int = 1,
    orientation: int = 0,
) -> str:
    """Create a new Scribus document.

    Args:
        width: Page width in the specified unit (default: 210 for A4)
        height: Page height in the specified unit (default: 297 for A4)
        margins: Page margins, uniform on all sides (default: 20)
        unit: Measurement unit - "mm", "pt", "in", or "p" (default: "mm")
        pages: Number of initial pages (default: 1)
        orientation: 0 for portrait, 1 for landscape (default: 0)

    """
    client = _get_client()
    result = client.send_command(
        "create_document",
        {
            "width": width,
            "height": height,
            "margins": margins,
            "unit": unit,
            "pages": pages,
            "orientation": orientation,
        },
    )
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
    params = {"name": name, "mode": mode}
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

    """
    client = _get_client()
    params = {"x": x, "y": y, "w": w, "h": h, "text": text}
    if font is not None:
        params["font"] = font
    if font_size is not None:
        params["font_size"] = font_size
    if color is not None:
        params["color"] = color
    if alignment is not None:
        params["alignment"] = alignment
    if page is not None:
        params["page"] = page

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
    params = {
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
    params = {"shape": shape}

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

    """
    client = _get_client()
    params: dict = {"name": name}

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
) -> str:
    """Export the document as a PDF file.

    Args:
        file_path: Output PDF file path
        quality: Quality preset - "screen" (150dpi), "ebook" (150dpi), "press" (300dpi)
        pdf_version: PDF version - "1.3", "1.4", "1.5", "x-1a", "x-3"
        pages: List of page numbers to export (default: all pages)

    """
    client = _get_client()
    params: dict = {"file_path": file_path, "quality": quality}
    if pdf_version is not None:
        params["pdf_version"] = pdf_version
    if pages is not None:
        params["pages"] = pages

    result = client.send_command("export_pdf", params)
    return f"Exported PDF to {result['file_path']}."


@mcp.tool()
def get_document_info() -> str:
    """Get information about the current document including pages, objects, and colors."""
    client = _get_client()
    result = client.send_command("get_document_info", {})

    lines = [f"Document has {result['page_count']} page(s)."]

    if result.get("pages"):
        lines.append("Pages:")
        for p in result["pages"]:
            lines.append(f"  Page {p['number']}: {p['width']}x{p['height']}")

    if result.get("objects"):
        lines.append(f"Objects ({len(result['objects'])}):")
        for obj in result["objects"]:
            lines.append(f"  {obj['name']} (type={obj['type']}, page={obj['page']})")

    if result.get("colors"):
        lines.append(f"Colors: {', '.join(result['colors'])}")

    return "\n".join(lines)


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

#!/usr/bin/env python
"""End-to-end test: create a landscape layout with sky, grass, and lorem ipsum.

Drives ScribusClient directly (no MCP layer) to verify the full stack:
  client → subprocess → bridge → Scribus

Usage:
    uv run python scripts/test_layout.py
"""

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

from scribus_mcp.client import ScribusClient

LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim "
    "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea "
    "commodo consequat. Duis aute irure dolor in reprehenderit in voluptate "
    "velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint "
    "occaecat cupidatat non proident, sunt in culpa qui officia deserunt "
    "mollit anim id est laborum."
)

PDF_PATH = "/tmp/scribus_test_layout.pdf"

# Layout constants (A4 portrait, millimetres)
PAGE_W, PAGE_H = 210, 297
MARGIN = 20
SKY_H = 178  # top ~60%
GRASS_Y = SKY_H
GRASS_H = PAGE_H - SKY_H  # bottom ~40%

# Text grid
USABLE_W = PAGE_W - 2 * MARGIN  # 170mm
COL_GAP = 5
COL_W = (USABLE_W - 2 * COL_GAP) / 3  # ~53.3mm
COL_X = [MARGIN, MARGIN + COL_W + COL_GAP, MARGIN + 2 * (COL_W + COL_GAP)]
COL_Y = 55
COL_H = 200


def main() -> int:
    client = ScribusClient()

    try:
        # 1. Create A4 document
        log.info("Creating A4 document...")
        r = client.send_command("create_document", {
            "width": PAGE_W,
            "height": PAGE_H,
            "unit": "mm",
            "margins": MARGIN,
            "pages": 1,
            "orientation": 0,
        })
        log.info("  → %s", r)

        # 2. Define colours
        colours = [
            ("SkyBlue", 135, 206, 235),
            ("GrassGreen", 34, 139, 34),
            ("White", 255, 255, 255),
        ]
        for name, red, green, blue in colours:
            log.info("Defining colour %s...", name)
            r = client.send_command("define_color", {
                "name": name, "mode": "rgb",
                "r": red, "g": green, "b": blue,
            })
            log.info("  → %s", r)

        # 3. Draw sky rectangle (full-bleed)
        log.info("Drawing sky...")
        r = client.send_command("draw_shape", {
            "shape": "rectangle",
            "x": 0, "y": 0, "w": PAGE_W, "h": SKY_H,
            "fill_color": "SkyBlue", "line_color": "SkyBlue",
        })
        log.info("  → %s", r)

        # 4. Draw grass rectangle (full-bleed)
        log.info("Drawing grass...")
        r = client.send_command("draw_shape", {
            "shape": "rectangle",
            "x": 0, "y": GRASS_Y, "w": PAGE_W, "h": GRASS_H,
            "fill_color": "GrassGreen", "line_color": "GrassGreen",
        })
        log.info("  → %s", r)

        # 5. Headline
        log.info("Placing headline...")
        r = client.send_command("place_text", {
            "x": MARGIN, "y": 25, "w": USABLE_W, "h": 20,
            "text": "LOREM IPSUM",
            "font_size": 28,
            "color": "White",
            "alignment": "center",
        })
        log.info("  → %s", r)

        # 6. Three columns of body text
        for i, x in enumerate(COL_X):
            log.info("Placing column %d...", i + 1)
            r = client.send_command("place_text", {
                "x": x, "y": COL_Y, "w": COL_W, "h": COL_H,
                "text": LOREM,
                "font_size": 10,
                "color": "White",
                "alignment": "justify",
            })
            log.info("  → %s", r)

        # 7. Export PDF
        log.info("Exporting PDF to %s...", PDF_PATH)
        r = client.send_command("export_pdf", {
            "file_path": PDF_PATH,
            "quality": "press",
        })
        log.info("  → %s", r)

        # 8. Document info summary
        log.info("Fetching document info...")
        info = client.send_command("get_document_info", {})
        log.info("Pages: %d", info["page_count"])
        for obj in info.get("objects", []):
            log.info("  object: %s (type=%s, page=%s)", obj["name"], obj["type"], obj["page"])
        log.info("Colours: %s", ", ".join(info.get("colors", [])))

    except Exception:
        log.exception("Test failed")
        return 1
    finally:
        log.info("Shutting down Scribus...")
        client.shutdown()

    log.info("Done! PDF written to %s", PDF_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())

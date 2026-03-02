"""Stub scribus module for testing bridge.py without a running Scribus instance.

This module mimics the scribus Python API that is available inside Scribus's
embedded interpreter. It tracks state in-memory so tests can verify behavior.
"""

# Constants
UNIT_MILLIMETERS = 0
UNIT_POINTS = 1
UNIT_INCHES = 2
UNIT_PICAS = 3

ALIGN_LEFT = 0
ALIGN_CENTERED = 1
ALIGN_RIGHT = 2
ALIGN_BLOCK = 3
ALIGN_FORCED = 4

# In-memory document state
_doc = None
_counter = 0
_saved_path = None
_last_pdf = None
_mock_documents = {}  # path -> doc_data for openDoc


def _next_name(prefix="obj"):
    global _counter
    _counter += 1
    return f"{prefix}_{_counter}"


def _reset():
    """Reset all state (call between tests)."""
    global _doc, _counter, _saved_path, _last_pdf, _mock_documents
    _doc = None
    _counter = 0
    _saved_path = None
    _last_pdf = None
    _mock_documents = {}


def _register_mock_document(path, doc_data):
    """Register a pre-populated document state for openDoc to load."""
    _mock_documents[path] = doc_data


class _Document:
    def __init__(
        self, size, margins, orientation, first_page, unit, page_type, first_page_order, num_pages
    ):
        self.size = size
        self.margins = margins
        self.orientation = orientation
        self.unit = unit
        self.pages = [{"number": i + 1, "size": size} for i in range(num_pages)]
        self.page_type = page_type
        self.first_page_order = first_page_order
        self.items = []
        self.colors = ["Black", "White"]
        self.current_page = 1
        self.objects = {}  # name -> properties dict


def haveDoc():
    return _doc is not None


def newDocument(
    size, margins, orientation, first_page, unit, page_type, first_page_order, num_pages
):
    global _doc
    _doc = _Document(
        size, margins, orientation, first_page, unit, page_type, first_page_order, num_pages
    )


def gotoPage(page):
    if _doc:
        _doc.current_page = page


def pageCount():
    return len(_doc.pages) if _doc else 0


def getPageSize():
    if _doc:
        return _doc.size
    return (0, 0)


def getPageItems():
    if _doc:
        return [(item["name"], item["type"], item["page"]) for item in _doc.items]
    return []


def getColorNames():
    if _doc:
        return tuple(_doc.colors)
    return ()


def defineColorCMYK(name, c, m, y, k):
    if _doc:
        _doc.colors.append(name)


def defineColorRGB(name, r, g, b):
    if _doc:
        _doc.colors.append(name)


def createText(x, y, w, h):
    name = _next_name("text")
    if _doc:
        obj = {
            "name": name,
            "type": 4,
            "page": _doc.current_page,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "text": "",
            "font": None,
            "font_size": None,
            "color": None,
        }
        _doc.items.append(obj)
        _doc.objects[name] = obj
    return name


def setText(text, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["text"] = text


def setFont(font, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["font"] = font


def setFontSize(size, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["font_size"] = size


def setTextColor(color, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["color"] = color


def setTextAlignment(align, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["alignment"] = align


def createImage(x, y, w, h):
    name = _next_name("img")
    if _doc:
        obj = {
            "name": name,
            "type": 2,
            "page": _doc.current_page,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "image": None,
        }
        _doc.items.append(obj)
        _doc.objects[name] = obj
    return name


def loadImage(path, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["image"] = path


def setScaleImageToFrame(scale, proportional, name):
    pass


def createRect(x, y, w, h):
    name = _next_name("rect")
    if _doc:
        obj = {"name": name, "type": 6, "page": _doc.current_page, "x": x, "y": y, "w": w, "h": h}
        _doc.items.append(obj)
        _doc.objects[name] = obj
    return name


def createEllipse(x, y, w, h):
    name = _next_name("ellipse")
    if _doc:
        obj = {"name": name, "type": 6, "page": _doc.current_page, "x": x, "y": y, "w": w, "h": h}
        _doc.items.append(obj)
        _doc.objects[name] = obj
    return name


def createLine(x1, y1, x2, y2):
    name = _next_name("line")
    if _doc:
        obj = {
            "name": name,
            "type": 5,
            "page": _doc.current_page,
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
        }
        _doc.items.append(obj)
        _doc.objects[name] = obj
    return name


def setFillColor(color, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["fill_color"] = color


def setLineColor(color, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["line_color"] = color


def setLineWidth(width, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["line_width"] = width


def getPosition(name):
    if _doc and name in _doc.objects:
        obj = _doc.objects[name]
        return (obj.get("x", 0), obj.get("y", 0))
    return (0, 0)


def getSize(name):
    if _doc and name in _doc.objects:
        obj = _doc.objects[name]
        return (obj.get("w", 0), obj.get("h", 0))
    return (0, 0)


def getText(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("text", "")
    return ""


def getAllText(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("text", "")
    return ""


def getFont(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("font", "")
    return ""


def getFontSize(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("font_size", 12.0)
    return 12.0


def getTextColor(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("color", "Black")
    return "Black"


def getRotation(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("rotation", 0.0)
    return 0.0


def getFillColor(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("fill_color", "None")
    return "None"


def getLineColor(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("line_color", "Black")
    return "Black"


def getLineWidth(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("line_width", 1.0)
    return 1.0


def getColumns(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("columns", 1)
    return 1


def getColumnGap(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("column_gap", 0.0)
    return 0.0


def moveObjectAbs(x, y, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["x"] = x
        _doc.objects[name]["y"] = y


def sizeObject(w, h, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["w"] = w
        _doc.objects[name]["h"] = h


def rotateObjectAbs(angle, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["rotation"] = angle


def newPage(where, masterpage=""):
    if _doc:
        page_num = len(_doc.pages) + 1
        _doc.pages.append({"number": page_num, "size": _doc.size})


class PDFfile:
    def __init__(self):
        global _last_pdf
        self.file = ""
        self.quality = 0
        self.resolution = 300
        self.version = 15
        self.pages = []
        _last_pdf = self

    def save(self):
        pass  # No-op in mock


def saveDoc():
    global _saved_path
    _saved_path = True


def saveDocAs(path):
    global _saved_path
    _saved_path = path


def closeDoc():
    global _doc
    _doc = None


def openDoc(path):
    global _doc
    if path in _mock_documents:
        data = _mock_documents[path]
        size = data.get("size", (210, 297))
        margins = data.get("margins", (20, 20, 20, 20))
        _doc = _Document(size, margins, 0, 1, UNIT_MILLIMETERS, 0, 0, data.get("num_pages", 1))
        for obj in data.get("objects", []):
            obj_copy = dict(obj)
            name = obj_copy["name"]
            _doc.items.append(obj_copy)
            _doc.objects[name] = obj_copy
    else:
        # Minimal empty document
        _doc = _Document((210, 297), (20, 20, 20, 20), 0, 1, UNIT_MILLIMETERS, 0, 0, 1)


def deleteObject(name):
    if _doc is None:
        raise Exception("No document open")
    if name not in _doc.objects:
        raise ValueError(f"Object not found: {name}")
    del _doc.objects[name]
    _doc.items = [item for item in _doc.items if item["name"] != name]


# ---------------------------------------------------------------------------
# Phase 1: Bleeds + baseline grid
# ---------------------------------------------------------------------------


def setBleeds(bl, br, bt, bb):
    if _doc:
        _doc.bleeds = (bl, br, bt, bb)


def setBaseLine(grid, offset):
    if _doc:
        _doc.baseline_grid = grid
        _doc.baseline_offset = offset


# ---------------------------------------------------------------------------
# Phase 2: Typography
# ---------------------------------------------------------------------------


def setLineSpacingMode(mode, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["line_spacing_mode"] = mode


def setLineSpacing(spacing, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["line_spacing"] = spacing


def setColumns(cols, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["columns"] = cols


def setColumnGap(gap, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["column_gap"] = gap


def createParagraphStyle(**kwargs):
    if _doc:
        if not hasattr(_doc, "paragraph_styles"):
            _doc.paragraph_styles = []
        _doc.paragraph_styles.append(kwargs)


def createCharStyle(**kwargs):
    if _doc:
        if not hasattr(_doc, "char_styles"):
            _doc.char_styles = []
        _doc.char_styles.append(kwargs)


def setStyle(style, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["style"] = style


def getParagraphStyles():
    if _doc and hasattr(_doc, "paragraph_styles"):
        return tuple(s.get("name", "") for s in _doc.paragraph_styles)
    return ()


def getCharStyles():
    if _doc and hasattr(_doc, "char_styles"):
        return tuple(s.get("name", "") for s in _doc.char_styles)
    return ()


# ---------------------------------------------------------------------------
# Phase 3: (PDFfile already exists, enhanced in-place)
# ---------------------------------------------------------------------------


def getPageMargins():
    if _doc:
        return _doc.margins
    return (0, 0, 0, 0)


# ---------------------------------------------------------------------------
# Phase 4: Layout & Structure
# ---------------------------------------------------------------------------


def linkTextFrames(from_name, to_name):
    if _doc:
        if not hasattr(_doc, "linked_frames"):
            _doc.linked_frames = []
        _doc.linked_frames.append((from_name, to_name))


def unlinkTextFrames(name):
    if _doc and hasattr(_doc, "linked_frames"):
        _doc.linked_frames = [
            pair for pair in _doc.linked_frames if pair[0] != name
        ]


def setHGuides(guides):
    if _doc:
        if not hasattr(_doc, "h_guides"):
            _doc.h_guides = {}
        _doc.h_guides[_doc.current_page] = list(guides)


def setVGuides(guides):
    if _doc:
        if not hasattr(_doc, "v_guides"):
            _doc.v_guides = {}
        _doc.v_guides[_doc.current_page] = list(guides)


def createMasterPage(name):
    if _doc:
        if not hasattr(_doc, "master_pages"):
            _doc.master_pages = []
        _doc.master_pages.append(name)


def editMasterPage(name):
    if _doc:
        _doc.editing_master = name


def closeMasterPage():
    if _doc:
        _doc.editing_master = None


def applyMasterPage(name, page):
    if _doc:
        if not hasattr(_doc, "applied_masters"):
            _doc.applied_masters = {}
        _doc.applied_masters[page] = name


def masterPageNames():
    if _doc and hasattr(_doc, "master_pages"):
        return tuple(_doc.master_pages)
    return ()


# ---------------------------------------------------------------------------
# Phase A: Extended object properties
# ---------------------------------------------------------------------------


def setCornerRadius(radius, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["corner_radius"] = radius


def getCornerRadius(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("corner_radius", 0)
    return 0


def setTextFlowMode(name, state):
    if _doc and name in _doc.objects:
        _doc.objects[name]["text_flow_mode"] = state


def getTextFlowMode(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("text_flow_mode", 0)
    return 0


def setFillTransparency(transparency, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["fill_transparency"] = transparency


def getFillTransparency(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("fill_transparency", 0.0)
    return 0.0


def setLineStyle(style, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["line_style"] = style


# ---------------------------------------------------------------------------
# Phase B: Text operations
# ---------------------------------------------------------------------------


def insertText(text, position, name):
    if _doc and name in _doc.objects:
        current = _doc.objects[name].get("text", "")
        if position == -1:
            _doc.objects[name]["text"] = current + text
        else:
            _doc.objects[name]["text"] = current[:position] + text + current[position:]


def selectText(start, count, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["_selection"] = (start, count)


def setCharacterStyle(style, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["char_style"] = style


def setParagraphStyle(style, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["para_style"] = style


def hyphenateText(name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["hyphenated"] = True


def dehyphenateText(name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["hyphenated"] = False


def textOverflows(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("text_overflows", 0)
    return 0


def getTextLength(name):
    if _doc and name in _doc.objects:
        return len(_doc.objects[name].get("text", ""))
    return 0


def getTextLines(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("text_lines", 1)
    return 1


def layoutTextChain(name):
    pass  # No-op in mock


# ---------------------------------------------------------------------------
# Phase C: Layers + Grouping/Z-order
# ---------------------------------------------------------------------------


def createLayer(name):
    if _doc:
        if not hasattr(_doc, "layers"):
            _doc.layers = ["Background"]
        _doc.layers.append(name)


def deleteLayer(name):
    if _doc and hasattr(_doc, "layers"):
        _doc.layers = [layer for layer in _doc.layers if layer != name]


def getLayers():
    if _doc and hasattr(_doc, "layers"):
        return tuple(_doc.layers)
    return ("Background",)


def getActiveLayer():
    if _doc:
        return getattr(_doc, "active_layer", "Background")
    return "Background"


def setActiveLayer(name):
    if _doc:
        _doc.active_layer = name


def sendToLayer(layer, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["layer"] = layer


def setLayerVisible(layer, visible):
    if _doc:
        if not hasattr(_doc, "layer_props"):
            _doc.layer_props = {}
        if layer not in _doc.layer_props:
            _doc.layer_props[layer] = {}
        _doc.layer_props[layer]["visible"] = visible


def setLayerLocked(layer, locked):
    if _doc:
        if not hasattr(_doc, "layer_props"):
            _doc.layer_props = {}
        if layer not in _doc.layer_props:
            _doc.layer_props[layer] = {}
        _doc.layer_props[layer]["locked"] = locked


def setLayerPrintable(layer, printable):
    if _doc:
        if not hasattr(_doc, "layer_props"):
            _doc.layer_props = {}
        if layer not in _doc.layer_props:
            _doc.layer_props[layer] = {}
        _doc.layer_props[layer]["printable"] = printable


def isLayerVisible(layer):
    if _doc and hasattr(_doc, "layer_props") and layer in _doc.layer_props:
        return _doc.layer_props[layer].get("visible", True)
    return True


def isLayerLocked(layer):
    if _doc and hasattr(_doc, "layer_props") and layer in _doc.layer_props:
        return _doc.layer_props[layer].get("locked", False)
    return False


def isLayerPrintable(layer):
    if _doc and hasattr(_doc, "layer_props") and layer in _doc.layer_props:
        return _doc.layer_props[layer].get("printable", True)
    return True


def groupObjects(names=None):
    name = _next_name("group")
    if _doc:
        obj = {
            "name": name,
            "type": 12,
            "page": _doc.current_page,
            "x": 0, "y": 0, "w": 0, "h": 0,
            "members": list(names) if names else [],
        }
        _doc.items.append(obj)
        _doc.objects[name] = obj
    return name


def unGroupObjects(name):
    if _doc and name in _doc.objects:
        del _doc.objects[name]
        _doc.items = [item for item in _doc.items if item["name"] != name]


def selectObject(name):
    if _doc:
        if not hasattr(_doc, "selection"):
            _doc.selection = []
        _doc.selection.append(name)


def deselectAll():
    if _doc:
        _doc.selection = []


def moveSelectionToFront():
    pass  # No-op in mock


def moveSelectionToBack():
    pass  # No-op in mock


# ---------------------------------------------------------------------------
# Phase D: Tables
# ---------------------------------------------------------------------------


def createTable(x, y, w, h, rows, cols):
    name = _next_name("table")
    if _doc:
        # Build cell storage
        cells = {}
        for r in range(rows):
            for c in range(cols):
                cells[(r, c)] = {"text": "", "props": {}}
        obj = {
            "name": name,
            "type": 16,
            "page": _doc.current_page,
            "x": x, "y": y, "w": w, "h": h,
            "rows": rows, "cols": cols,
            "cells": cells,
            "row_heights": [h / rows] * rows,
            "col_widths": [w / cols] * cols,
        }
        _doc.items.append(obj)
        _doc.objects[name] = obj
    return name


def getTableRows(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("rows", 0)
    return 0


def getTableColumns(name):
    if _doc and name in _doc.objects:
        return _doc.objects[name].get("cols", 0)
    return 0


def insertTableRows(name, index, count):
    if _doc and name in _doc.objects:
        obj = _doc.objects[name]
        obj["rows"] += count
        cols = obj["cols"]
        # Shift existing cells down and add new empty cells
        new_cells = {}
        for (r, c), val in obj["cells"].items():
            new_r = r if r < index else r + count
            new_cells[(new_r, c)] = val
        for i in range(count):
            for c in range(cols):
                new_cells[(index + i, c)] = {"text": "", "props": {}}
        obj["cells"] = new_cells
        for _ in range(count):
            obj["row_heights"].insert(index, obj["row_heights"][0] if obj["row_heights"] else 20)


def insertTableColumns(name, index, count):
    if _doc and name in _doc.objects:
        obj = _doc.objects[name]
        obj["cols"] += count
        rows = obj["rows"]
        new_cells = {}
        for (r, c), val in obj["cells"].items():
            new_c = c if c < index else c + count
            new_cells[(r, new_c)] = val
        for r in range(rows):
            for i in range(count):
                new_cells[(r, index + i)] = {"text": "", "props": {}}
        obj["cells"] = new_cells
        for _ in range(count):
            obj["col_widths"].insert(index, obj["col_widths"][0] if obj["col_widths"] else 20)


def removeTableRows(name, index, count):
    if _doc and name in _doc.objects:
        obj = _doc.objects[name]
        obj["rows"] -= count
        new_cells = {}
        for (r, c), val in obj["cells"].items():
            if r < index or r >= index + count:
                new_r = r if r < index else r - count
                new_cells[(new_r, c)] = val
        obj["cells"] = new_cells
        del obj["row_heights"][index:index + count]


def removeTableColumns(name, index, count):
    if _doc and name in _doc.objects:
        obj = _doc.objects[name]
        obj["cols"] -= count
        new_cells = {}
        for (r, c), val in obj["cells"].items():
            if c < index or c >= index + count:
                new_c = c if c < index else c - count
                new_cells[(r, new_c)] = val
        obj["cells"] = new_cells
        del obj["col_widths"][index:index + count]


def resizeTableRow(name, row, height):
    if _doc and name in _doc.objects:
        _doc.objects[name]["row_heights"][row] = height


def resizeTableColumn(name, col, width):
    if _doc and name in _doc.objects:
        _doc.objects[name]["col_widths"][col] = width


def getTableRowHeight(name, row):
    if _doc and name in _doc.objects:
        return _doc.objects[name]["row_heights"][row]
    return 0


def getTableColumnWidth(name, col):
    if _doc and name in _doc.objects:
        return _doc.objects[name]["col_widths"][col]
    return 0


def mergeTableCells(name, row, col, num_rows, num_cols):
    if _doc and name in _doc.objects:
        obj = _doc.objects[name]
        if not hasattr(obj, "get"):
            return
        merges = obj.get("merged_cells", [])
        merges.append({"row": row, "col": col, "num_rows": num_rows, "num_cols": num_cols})
        obj["merged_cells"] = merges


def setCellText(name, row, col, text):
    if _doc and name in _doc.objects:
        cells = _doc.objects[name].get("cells", {})
        if (row, col) in cells:
            cells[(row, col)]["text"] = text


def getCellText(name, row, col):
    if _doc and name in _doc.objects:
        cells = _doc.objects[name].get("cells", {})
        if (row, col) in cells:
            return cells[(row, col)]["text"]
    return ""


def setCellFillColor(name, row, col, color):
    if _doc and name in _doc.objects:
        cells = _doc.objects[name].get("cells", {})
        if (row, col) in cells:
            cells[(row, col)]["props"]["fill_color"] = color


def setCellStyle(name, row, col, style):
    if _doc and name in _doc.objects:
        cells = _doc.objects[name].get("cells", {})
        if (row, col) in cells:
            cells[(row, col)]["props"]["style"] = style


def setCellTopBorder(name, row, col, width, color):
    if _doc and name in _doc.objects:
        _doc.objects[name]["cells"][(row, col)]["props"]["border_top"] = {
            "width": width, "color": color,
        }


def setCellBottomBorder(name, row, col, width, color):
    if _doc and name in _doc.objects:
        _doc.objects[name]["cells"][(row, col)]["props"]["border_bottom"] = {
            "width": width, "color": color,
        }


def setCellLeftBorder(name, row, col, width, color):
    if _doc and name in _doc.objects:
        _doc.objects[name]["cells"][(row, col)]["props"]["border_left"] = {
            "width": width, "color": color,
        }


def setCellRightBorder(name, row, col, width, color):
    if _doc and name in _doc.objects:
        _doc.objects[name]["cells"][(row, col)]["props"]["border_right"] = {
            "width": width, "color": color,
        }


def setCellTopPadding(name, row, col, padding):
    if _doc and name in _doc.objects:
        _doc.objects[name]["cells"][(row, col)]["props"]["padding_top"] = padding


def setCellBottomPadding(name, row, col, padding):
    if _doc and name in _doc.objects:
        _doc.objects[name]["cells"][(row, col)]["props"]["padding_bottom"] = padding


def setCellLeftPadding(name, row, col, padding):
    if _doc and name in _doc.objects:
        _doc.objects[name]["cells"][(row, col)]["props"]["padding_left"] = padding


def setCellRightPadding(name, row, col, padding):
    if _doc and name in _doc.objects:
        _doc.objects[name]["cells"][(row, col)]["props"]["padding_right"] = padding


def setTableFillColor(name, color):
    if _doc and name in _doc.objects:
        _doc.objects[name]["table_fill_color"] = color


def setTableStyle(name, style):
    if _doc and name in _doc.objects:
        _doc.objects[name]["table_style"] = style


# ---------------------------------------------------------------------------
# Phase E: Image control + misc standalone tools
# ---------------------------------------------------------------------------


def setImageOffset(x, y, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["image_offset_x"] = x
        _doc.objects[name]["image_offset_y"] = y


def setImageScale(x, y, name):
    if _doc and name in _doc.objects:
        _doc.objects[name]["image_scale_x"] = x
        _doc.objects[name]["image_scale_y"] = y


def getImageOffset(name):
    if _doc and name in _doc.objects:
        obj = _doc.objects[name]
        return (obj.get("image_offset_x", 0.0), obj.get("image_offset_y", 0.0))
    return (0.0, 0.0)


def getImageScale(name):
    if _doc and name in _doc.objects:
        obj = _doc.objects[name]
        return (obj.get("image_scale_x", 1.0), obj.get("image_scale_y", 1.0))
    return (1.0, 1.0)


def setScaleFrameToImage(name):
    pass  # No-op in mock


def deletePage(page):
    if _doc:
        if page < 1 or page > len(_doc.pages):
            raise ValueError(f"Invalid page number: {page}")
        _doc.pages.pop(page - 1)


def getFontNames():
    return ("Arial Regular", "Times New Roman", "Courier New", "Helvetica")


def duplicateObjects(names=None):
    result = []
    if _doc and names:
        for name in names:
            if name in _doc.objects:
                new_name = _next_name("dup")
                obj_copy = dict(_doc.objects[name])
                obj_copy["name"] = new_name
                _doc.items.append(obj_copy)
                _doc.objects[new_name] = obj_copy
                result.append(new_name)
    return result


def placeSVG(file_path, x, y):
    name = _next_name("svg")
    if _doc:
        obj = {
            "name": name,
            "type": 2,
            "page": _doc.current_page,
            "x": x, "y": y,
            "w": 0, "h": 0,
            "svg_path": file_path,
        }
        _doc.items.append(obj)
        _doc.objects[name] = obj
    return name

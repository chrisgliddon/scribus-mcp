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


def _next_name(prefix="obj"):
    global _counter
    _counter += 1
    return f"{prefix}_{_counter}"


def _reset():
    """Reset all state (call between tests)."""
    global _doc, _counter, _saved_path, _last_pdf
    _doc = None
    _counter = 0
    _saved_path = None
    _last_pdf = None


class _Document:
    def __init__(
        self, size, margins, orientation, first_page, unit, page_type, first_page_order, num_pages
    ):
        self.size = size
        self.margins = margins
        self.orientation = orientation
        self.unit = unit
        self.pages = [{"number": i + 1, "size": size} for i in range(num_pages)]
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
        name = kwargs.get("name", "unnamed")
        if not hasattr(_doc, "paragraph_styles"):
            _doc.paragraph_styles = []
        _doc.paragraph_styles.append(kwargs)


def createCharStyle(**kwargs):
    if _doc:
        name = kwargs.get("name", "unnamed")
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
    if _doc:
        if hasattr(_doc, "linked_frames"):
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

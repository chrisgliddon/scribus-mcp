# Scribus MCP

MCP server for [Scribus](https://www.scribus.net/) — lets LLMs create professional RGB/CMYK layouts programmatically.

## Architecture

```
Claude Code/Desktop ←(MCP stdio)→ server.py ←(subprocess NDJSON)→ Scribus -g -py bridge.py
```

Scribus runs headless as a persistent subprocess. The bridge script executes inside Scribus's embedded Python, receives JSON commands over stdin, returns results over stdout. Document state auto-saves to `~/.scribus-mcp/workspace/document.sla` after each mutation.

## Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **Scribus** installed at `/Applications/Scribus.app/Contents/MacOS/Scribus` (macOS) or `/usr/bin/scribus` (Linux), or set `SCRIBUS_EXECUTABLE` env var

## Setup

```bash
git clone https://github.com/chrisgliddon/scribus-mcp.git
cd scribus-mcp
uv sync
```

## Configure in Claude Code

Add to `.mcp.json` (project root or `~/.claude/.mcp.json` for global):

```json
{
  "mcpServers": {
    "scribus": {
      "command": "uv",
      "args": ["--directory", "/path/to/scribus-mcp", "run", "scribus-mcp"]
    }
  }
}
```

## Configure in Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "scribus": {
      "command": "uv",
      "args": ["--directory", "/path/to/scribus-mcp", "run", "scribus-mcp"]
    }
  }
}
```

## Tools

| Tool | What it does |
|------|-------------|
| `create_document` | New document. Params: `width`, `height`, `margins`, `unit` (mm/pt/in), `pages`, `orientation` |
| `define_color` | Named color. Params: `name`, `mode` (cmyk/rgb), `c/m/y/k` (0-100%) or `r/g/b` (0-255) |
| `place_text` | Text frame with content. Params: `x`, `y`, `w`, `h`, `text`, `font`, `font_size`, `color`, `alignment`, `page` |
| `place_image` | Image frame. Params: `x`, `y`, `w`, `h`, `file_path`, `scale_to_frame`, `proportional`, `page` |
| `draw_shape` | Rectangle, ellipse, or line. Params: `shape`, `x/y/w/h` or `x1/y1/x2/y2`, `fill_color`, `line_color`, `line_width` |
| `modify_object` | Change object props. Params: `name`, + any of: position, size, rotation, colors, text props |
| `add_page` | Add pages. Params: `count`, `where` (-1=append), `master_page` |
| `export_pdf` | Export PDF. Params: `file_path`, `quality` (screen/ebook/press), `pdf_version`, `pages` |
| `get_document_info` | Query doc state — pages, objects, colors |
| `run_script` | Execute raw Scribus Python. Params: `code`. Set `result` variable to return data |

## Example Prompts

> Create an A4 document, define a CMYK color called "BrandBlue" at C=100 M=80 Y=0 K=20, add a heading "Hello World" in 36pt centered at the top, draw a blue rectangle behind it, then export as PDF to ~/Desktop/test.pdf

> Open a US Letter landscape document, place the image at ~/logo.png in the top-left corner scaled to 50x50mm, add body text below it, export to PDF

## Development

```bash
# install dev deps
uv sync

# run tests
uv run pytest tests/ -v

# test with MCP Inspector
npx @modelcontextprotocol/inspector uv run scribus-mcp
```

## Custom Scribus Path

If Scribus isn't in a standard location:

```bash
export SCRIBUS_EXECUTABLE=/path/to/scribus
```

## How It Works

1. On first tool call, `client.py` launches Scribus headless (`-g -ns -py bridge.py`)
2. `bridge.py` redirects stdout to avoid protocol contamination, sends `{"ready": true}` sentinel
3. Client sends NDJSON commands over stdin, reads JSON responses from stdout
4. If Scribus crashes, next tool call auto-restarts the subprocess
5. All mutations auto-save to `~/.scribus-mcp/workspace/document.sla`

## License

GPL-2.0 — see [LICENSE](LICENSE)

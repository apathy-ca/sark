#!/usr/bin/env python3
"""Convert markdown presentation to PDF."""

import markdown2
from weasyprint import HTML, CSS
from pathlib import Path

# Read markdown
md_file = Path("SARK_MCP_Security_Presentation.md")
md_content = md_file.read_text()

# Remove pandoc YAML header
if md_content.startswith("---"):
    parts = md_content.split("---", 2)
    if len(parts) >= 3:
        md_content = parts[2].strip()

# Convert to HTML
html_body = markdown2.markdown(
    md_content,
    extras=["fenced-code-blocks", "tables", "break-on-newline"]
)

# Create full HTML with styling
html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SARK MCP Governance Architecture</title>
    <style>
        @page {{
            size: letter;
            margin: 0.5in 0.6in;
            @bottom-center {{
                content: "SARK MCP Governance - Page " counter(page);
                font-size: 9pt;
                color: #666;
            }}
        }}

        body {{
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #222;
        }}

        h1 {{
            color: #1a5490;
            font-size: 18pt;
            margin-top: 0;
            margin-bottom: 12pt;
            border-bottom: 2px solid #1a5490;
            padding-bottom: 6pt;
            page-break-before: always;
        }}

        h1:first-of-type {{
            page-break-before: avoid;
        }}

        h2 {{
            color: #2e5c8a;
            font-size: 13pt;
            margin-top: 14pt;
            margin-bottom: 8pt;
        }}

        h3 {{
            color: #444;
            font-size: 11pt;
            margin-top: 10pt;
            margin-bottom: 6pt;
        }}

        p {{
            margin: 6pt 0;
        }}

        pre {{
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-left: 3px solid #1a5490;
            padding: 8pt;
            font-size: 8pt;
            line-height: 1.3;
            overflow-x: auto;
            margin: 8pt 0;
        }}

        code {{
            background-color: #f0f0f0;
            padding: 1pt 3pt;
            font-family: 'Courier New', monospace;
            font-size: 9pt;
        }}

        pre code {{
            background-color: transparent;
            padding: 0;
        }}

        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 10pt 0;
            font-size: 9pt;
        }}

        th {{
            background-color: #1a5490;
            color: white;
            padding: 6pt;
            text-align: left;
            font-weight: bold;
        }}

        td {{
            border: 1px solid #ddd;
            padding: 5pt;
        }}

        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}

        ul, ol {{
            margin: 6pt 0;
            padding-left: 20pt;
        }}

        li {{
            margin: 3pt 0;
        }}

        strong {{
            color: #1a5490;
        }}

        .page-break {{
            page-break-after: always;
        }}

        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 12pt 0;
        }}

        blockquote {{
            margin: 8pt 0;
            padding: 8pt 12pt;
            background-color: #f0f7ff;
            border-left: 4px solid #1a5490;
        }}
    </style>
</head>
<body>
    <div style="text-align: center; padding: 20pt 0; margin-bottom: 30pt; border-bottom: 3px solid #1a5490;">
        <h1 style="font-size: 24pt; margin: 0; border: none; padding: 0;">SARK MCP Governance Architecture</h1>
        <p style="font-size: 14pt; color: #666; margin: 10pt 0 0 0;">Enterprise Security & Authorization for Model Context Protocol</p>
        <p style="font-size: 11pt; color: #888; margin: 5pt 0 0 0;">Security Architecture Overview • November 2025</p>
    </div>
    {html_body}
</body>
</html>
"""

# Write HTML for debugging
Path("presentation.html").write_text(html_template)

# Convert to PDF
HTML(string=html_template).write_pdf("SARK_MCP_Security_Presentation.pdf")

print("✅ PDF created: SARK_MCP_Security_Presentation.pdf")
print("📄 Preview HTML: presentation.html")

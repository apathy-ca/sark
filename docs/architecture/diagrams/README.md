# SARK v2.0 Architecture Diagrams

This directory contains architecture diagrams for SARK v2.0. All diagrams are in Mermaid format and can be rendered in GitHub, GitLab, or using Mermaid CLI.

## Viewing Diagrams

### In GitHub/GitLab
Simply view the `.md` files - they will automatically render the Mermaid diagrams.

### Locally
```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Generate SVG
mmdc -i system-overview.mmd -o system-overview.svg

# Generate PNG
mmdc -i system-overview.mmd -o system-overview.png
```

### Online
Visit [Mermaid Live Editor](https://mermaid.live/) and paste the diagram code.

## Available Diagrams

1. **system-overview.mmd** - High-level system architecture
2. **adapter-pattern.mmd** - Protocol adapter pattern
3. **federation-flow.mmd** - Cross-organization federation flow
4. **policy-evaluation.mmd** - Policy evaluation sequence
5. **data-model.mmd** - Database schema and relationships
6. **deployment-ha.mmd** - High-availability deployment architecture

## Diagram Format

All diagrams use [Mermaid](https://mermaid.js.org/) syntax, which provides:
- Version control friendly (text-based)
- Easy to update and maintain
- Automatic rendering in modern documentation platforms
- Export to SVG/PNG for presentations

---

**Document Version:** 1.0
**Last Updated:** December 2025

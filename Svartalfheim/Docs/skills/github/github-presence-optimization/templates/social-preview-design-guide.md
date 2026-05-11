# Social Preview SVG for Norse/Ecosystem-themed Projects
# Place at docs/social-preview.svg
# GitHub Settings > General > Social Preview accepts SVG
#
# Key design elements:
# - 1280x640 dimensions (GitHub's social preview size)
# - Dark background (#0B0F19) matching project theme
# - Radial gradient for depth
# - Tree/branch motif (Yggdrasil)
# - Amber (#F59E0B) for title/roots, Cyan (#22D3EE) for branches/tech
# - Rune unicode characters as subtle decoration
# - Tech stack pill badges at bottom
# - SVG filters for glow effects on text and nodes
#
# To convert SVG to PNG (GitHub accepts both):
#   inkscape social-preview.svg -w 1280 -h 640 -e social-preview.png
#   OR: chromium --headless --screenshot=social-preview.png --window-size=1280,640 file://$(pwd)/social-preview.svg
#
# Then upload at: https://github.com/OWNER/REPO/settings
# Social preview section > Edit > Upload image
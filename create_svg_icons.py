"""
Скрипт для создания простых SVG иконок вместо emoji.
"""

import os

# Создаем папку для иконок
os.makedirs("assets/icons/emoji", exist_ok=True)

# SVG шаблоны для разных типов иконок
SVG_TEMPLATES = {
    "chart": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <rect x="4" y="20" width="4" height="8" fill="#4682B4"/>
  <rect x="10" y="12" width="4" height="16" fill="#4682B4"/>
  <rect x="16" y="16" width="4" height="12" fill="#4682B4"/>
  <rect x="22" y="8" width="4" height="20" fill="#4682B4"/>
</svg>""",
    
    "settings": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="6" fill="none" stroke="#808080" stroke-width="2"/>
  <circle cx="16" cy="16" r="2" fill="#808080"/>
  <path d="M 16 4 L 16 8 M 16 24 L 16 28 M 4 16 L 8 16 M 24 16 L 28 16" stroke="#808080" stroke-width="2"/>
  <path d="M 7.5 7.5 L 10.5 10.5 M 21.5 21.5 L 24.5 24.5" stroke="#808080" stroke-width="2"/>
  <path d="M 24.5 7.5 L 21.5 10.5 M 10.5 21.5 L 7.5 24.5" stroke="#808080" stroke-width="2"/>
</svg>""",
    
    "checkmark": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <path d="M 8 16 L 14 22 L 24 10" stroke="#228B22" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",
    
    "cross": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <path d="M 8 8 L 24 24 M 24 8 L 8 24" stroke="#DC143C" stroke-width="3" stroke-linecap="round"/>
</svg>""",
    
    "package": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <rect x="6" y="10" width="20" height="16" fill="#8B4513" stroke="#654321" stroke-width="1"/>
  <path d="M 6 10 L 16 6 L 26 10" stroke="#654321" stroke-width="1" fill="#A0522D"/>
  <line x1="16" y1="6" x2="16" y2="26" stroke="#654321" stroke-width="1"/>
</svg>""",
    
    "money": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="8" fill="#32CD32" stroke="#228B22" stroke-width="1"/>
  <text x="16" y="20" font-family="Arial" font-size="12" font-weight="bold" fill="white" text-anchor="middle">$</text>
</svg>""",
    
    "prohibited": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="12" fill="none" stroke="#FF0000" stroke-width="2"/>
  <line x1="8" y1="8" x2="24" y2="24" stroke="#FF0000" stroke-width="3" stroke-linecap="round"/>
</svg>""",
    
    "refresh": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <path d="M 20 8 Q 24 8 26 10 Q 28 12 28 16" stroke="#1E90FF" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M 12 24 Q 8 24 6 22 Q 4 20 4 16" stroke="#1E90FF" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M 20 8 L 16 4 L 20 4" stroke="#1E90FF" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M 12 24 L 16 28 L 12 28" stroke="#1E90FF" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",
    
    "receipt": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="6" width="16" height="20" fill="white" stroke="#696969" stroke-width="1"/>
  <line x1="10" y1="10" x2="22" y2="10" stroke="#696969" stroke-width="1"/>
  <line x1="10" y1="14" x2="22" y2="14" stroke="#696969" stroke-width="1"/>
  <line x1="10" y1="18" x2="22" y2="18" stroke="#696969" stroke-width="1"/>
</svg>""",
    
    "save": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="6" width="14" height="18" fill="#0064C8" stroke="#004080" stroke-width="1"/>
  <rect x="10" y="8" width="10" height="8" fill="#0080FF"/>
  <line x1="10" y1="18" x2="20" y2="18" stroke="white" stroke-width="1"/>
  <line x1="10" y1="20" x2="20" y2="20" stroke="white" stroke-width="1"/>
  <line x1="10" y1="22" x2="18" y2="22" stroke="white" stroke-width="1"/>
</svg>""",
    
    "memo": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="6" width="16" height="20" fill="white" stroke="#191970" stroke-width="1"/>
  <line x1="10" y1="12" x2="22" y2="12" stroke="#191970" stroke-width="1"/>
  <line x1="10" y1="16" x2="22" y2="16" stroke="#191970" stroke-width="1"/>
  <line x1="10" y1="20" x2="18" y2="20" stroke="#191970" stroke-width="1"/>
  <path d="M 10 10 L 12 8 L 10 8 Z" fill="#FFD700"/>
</svg>""",
    
    "document": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="6" width="14" height="20" fill="white" stroke="#4682B4" stroke-width="1"/>
  <line x1="10" y1="12" x2="20" y2="12" stroke="#4682B4" stroke-width="1"/>
  <line x1="10" y1="16" x2="20" y2="16" stroke="#4682B4" stroke-width="1"/>
  <line x1="10" y1="20" x2="18" y2="20" stroke="#4682B4" stroke-width="1"/>
</svg>""",
    
    "info": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="10" fill="none" stroke="#007BFF" stroke-width="2"/>
  <text x="16" y="22" font-family="Arial" font-size="16" font-weight="bold" fill="#007BFF" text-anchor="middle">i</text>
</svg>""",
    
    "pin": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <path d="M 16 6 L 20 14 L 16 18 L 12 14 Z" fill="#FF0000"/>
  <line x1="16" y1="18" x2="16" y2="26" stroke="#FF0000" stroke-width="2" stroke-linecap="round"/>
</svg>""",
    
    "truck": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <rect x="6" y="14" width="12" height="8" fill="#FF8C00" stroke="#FF6600" stroke-width="1"/>
  <rect x="18" y="12" width="8" height="10" fill="#FF8C00" stroke="#FF6600" stroke-width="1"/>
  <circle cx="10" cy="24" r="3" fill="#333"/>
  <circle cx="22" cy="24" r="3" fill="#333"/>
</svg>""",
    
    "location": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <path d="M 16 6 C 12 6 8 10 8 14 C 8 18 16 26 16 26 C 16 26 24 18 24 14 C 24 10 20 6 16 6 Z" fill="#FF0000"/>
  <circle cx="16" cy="14" r="3" fill="white"/>
</svg>""",
    
    "oil_barrel": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <rect x="10" y="8" width="12" height="16" fill="#8B4513" stroke="#654321" stroke-width="1"/>
  <ellipse cx="16" cy="8" rx="6" ry="2" fill="#A0522D"/>
  <line x1="12" y1="12" x2="20" y2="12" stroke="#654321" stroke-width="1"/>
  <line x1="12" y1="16" x2="20" y2="16" stroke="#654321" stroke-width="1"/>
  <line x1="12" y1="20" x2="20" y2="20" stroke="#654321" stroke-width="1"/>
</svg>""",
    
    "house": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <path d="M 16 6 L 6 14 L 6 24 L 12 24 L 12 18 L 20 18 L 20 24 L 26 24 L 26 14 Z" fill="#A0522D" stroke="#8B4513" stroke-width="1"/>
  <rect x="14" y="20" width="4" height="4" fill="#654321"/>
</svg>""",
    
    "download": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <path d="M 16 8 L 16 20 M 16 20 L 12 16 M 16 20 L 20 16" stroke="#000000" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <line x1="8" y1="24" x2="24" y2="24" stroke="#000000" stroke-width="2" stroke-linecap="round"/>
</svg>""",
    
    "rocket": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <path d="M 16 6 L 20 18 L 16 22 L 12 18 Z" fill="#FF1493" stroke="#C71585" stroke-width="1"/>
  <path d="M 16 22 L 14 26 L 16 28 L 18 26 Z" fill="#FF1493" stroke="#C71585" stroke-width="1"/>
  <circle cx="16" cy="14" r="2" fill="white"/>
</svg>""",
    
    "folder": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <path d="M 8 10 L 12 10 L 14 12 L 24 12 L 24 24 L 8 24 Z" fill="#FFA500" stroke="#FF8C00" stroke-width="1"/>
</svg>""",
    
    "tools": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <path d="M 20 8 L 24 12 L 18 18 L 14 14 Z" fill="none" stroke="#808080" stroke-width="2" stroke-linecap="round"/>
  <circle cx="16" cy="16" r="2" fill="#808080"/>
  <path d="M 12 20 L 8 24" stroke="#808080" stroke-width="2" stroke-linecap="round"/>
</svg>""",
    
    "target": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="10" fill="none" stroke="#FF0000" stroke-width="2"/>
  <circle cx="16" cy="16" r="6" fill="none" stroke="#FF0000" stroke-width="1"/>
  <circle cx="16" cy="16" r="2" fill="#FF0000"/>
</svg>""",
    
    "clipboard": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <rect x="10" y="6" width="12" height="18" fill="white" stroke="#4682B4" stroke-width="1"/>
  <rect x="8" y="8" width="4" height="4" fill="#4682B4"/>
  <line x1="12" y1="12" x2="20" y2="12" stroke="#4682B4" stroke-width="1"/>
  <line x1="12" y1="16" x2="20" y2="16" stroke="#4682B4" stroke-width="1"/>
  <line x1="12" y1="20" x2="18" y2="20" stroke="#4682B4" stroke-width="1"/>
</svg>""",
    
    "warning": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <path d="M 16 6 L 6 26 L 26 26 Z" fill="#FFA500" stroke="#FF8C00" stroke-width="1"/>
  <text x="16" y="22" font-family="Arial" font-size="12" font-weight="bold" fill="white" text-anchor="middle">!</text>
</svg>""",
    
    "chart_up": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <rect x="4" y="20" width="4" height="8" fill="#32CD32"/>
  <rect x="10" y="16" width="4" height="12" fill="#32CD32"/>
  <rect x="16" y="12" width="4" height="16" fill="#32CD32"/>
  <rect x="22" y="8" width="4" height="20" fill="#32CD32"/>
  <path d="M 6 18 L 12 14 L 18 10 L 24 6" stroke="#228B22" stroke-width="2" fill="none"/>
</svg>""",
    
    "lock": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <rect x="12" y="16" width="8" height="10" fill="#808080" stroke="#666" stroke-width="1"/>
  <path d="M 12 16 L 12 12 C 12 8 15 6 16 6 C 17 6 20 8 20 12 L 20 16" fill="none" stroke="#666" stroke-width="2"/>
</svg>""",
    
    "paintbrush": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <path d="M 8 8 L 18 18" stroke="#FF1493" stroke-width="3" stroke-linecap="round"/>
  <path d="M 18 18 L 24 12" stroke="#FF1493" stroke-width="2" stroke-linecap="round"/>
  <circle cx="24" cy="12" r="2" fill="#FF1493"/>
</svg>""",
    
    "mobile": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <rect x="10" y="6" width="12" height="20" rx="2" fill="#000000" stroke="#333" stroke-width="1"/>
  <rect x="12" y="8" width="8" height="14" fill="#333"/>
  <circle cx="16" cy="24" r="1" fill="#666"/>
</svg>""",
    
    "phone": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <path d="M 10 6 L 14 6 L 16 10 L 14 14 L 18 18 L 22 16 L 26 18 L 26 22 L 22 26 C 18 26 10 18 6 14 C 6 10 10 6 10 6 Z" fill="#32CD32" stroke="#228B22" stroke-width="1"/>
</svg>""",
    
    "pdf": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="6" width="14" height="20" fill="#DC143C" stroke="#B22222" stroke-width="1"/>
  <text x="15" y="20" font-family="Arial" font-size="10" font-weight="bold" fill="white" text-anchor="middle">PDF</text>
</svg>""",
    
    "clock": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="10" fill="none" stroke="#FF8C00" stroke-width="2"/>
  <line x1="16" y1="16" x2="16" y2="10" stroke="#FF8C00" stroke-width="2" stroke-linecap="round"/>
  <line x1="16" y1="16" x2="20" y2="16" stroke="#FF8C00" stroke-width="2" stroke-linecap="round"/>
</svg>""",
    
    "alarm": """<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="8" fill="#FF0000" stroke="#CC0000" stroke-width="1"/>
  <path d="M 16 10 L 16 14 M 16 18 L 16 22" stroke="white" stroke-width="2" stroke-linecap="round"/>
  <path d="M 10 16 L 14 16 M 18 16 L 22 16" stroke="white" stroke-width="2" stroke-linecap="round"/>
</svg>""",
}

def main():
    """Создает все SVG иконки"""
    for name, svg_content in SVG_TEMPLATES.items():
        filename = f"assets/icons/emoji/{name}.svg"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"Created: {filename}")
    
    print("\nВсе SVG иконки созданы!")

if __name__ == "__main__":
    main()


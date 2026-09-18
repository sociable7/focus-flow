THEMES = {
    "Minimal": {
        "background": "#F4F4F5",
        "card": "#FFFFFF",
        "text": "#18181B",
        "secondary_text": "#71717A",
        "accent": "#18181B",
        "button_text": "#FFFFFF",
        "border": "#E4E4E7",
    },

    "Classic Tomato": {
        "background": "#FFF7F5",
        "card": "#FFFFFF",
        "text": "#2B1715",
        "secondary_text": "#8C5A54",
        "accent": "#E74C3C",
        "button_text": "#FFFFFF",
        "border": "#F2D5D0",
    },

    "Forest": {
        "background": "#F2F7F3",
        "card": "#FFFFFF",
        "text": "#17301F",
        "secondary_text": "#64806B",
        "accent": "#2E7D4F",
        "button_text": "#FFFFFF",
        "border": "#D4E4D8",
    },

    "Midnight": {
        "background": "#111827",
        "card": "#1F2937",
        "text": "#F9FAFB",
        "secondary_text": "#9CA3AF",
        "accent": "#8B5CF6",
        "button_text": "#FFFFFF",
        "border": "#374151",
    },
}


def get_theme(name):
    return THEMES.get(name, THEMES["Midnight"])
THEMES = {
    "Minimal": {
        "background": "#F5F5F7",
        "surface": "#FFFFFF",
        "surface_alt": "#F0F0F2",
        "text": "#1D1D1F",
        "secondary_text": "#6E6E73",
        "accent": "#1D1D1F",
        "button_text": "#FFFFFF",
        "border": "#D2D2D7",
        "input": "#FFFFFF",
        "input_text": "#1D1D1F",
    },

    "Classic Tomato": {
        "background": "#FFF8F6",
        "surface": "#FFFFFF",
        "surface_alt": "#FFF0ED",
        "text": "#2B1715",
        "secondary_text": "#8C5A54",
        "accent": "#E74C3C",
        "button_text": "#FFFFFF",
        "border": "#F0D5D0",
        "input": "#FFFFFF",
        "input_text": "#2B1715",
    },

    "Forest": {
        "background": "#F3F7F4",
        "surface": "#FFFFFF",
        "surface_alt": "#EAF2EC",
        "text": "#17301F",
        "secondary_text": "#64806B",
        "accent": "#2E7D4F",
        "button_text": "#FFFFFF",
        "border": "#D3E2D7",
        "input": "#FFFFFF",
        "input_text": "#17301F",
    },

    "Midnight": {
        "background": "#101114",
        "surface": "#191B20",
        "surface_alt": "#22252C",
        "text": "#F5F5F7",
        "secondary_text": "#A1A1AA",
        "accent": "#8B5CF6",
        "button_text": "#FFFFFF",
        "border": "#30333B",
        "input": "#22252C",
        "input_text": "#F5F5F7",
    },
}


def get_theme(name):
    return THEMES.get(name, THEMES["Midnight"])
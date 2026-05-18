def build_theme_menu(self):
        menu = QMenu(self)

        themes = [
            "light_blue",
            "dark_blue",
            "light_pink",
            "dark_pink",
            "light_cyan",
            "dark_cyan",
        ]

        for theme in themes:
            action = menu.addAction(theme)
            action.triggered.connect(lambda checked=False, t=theme: self.apply_theme(t))

        return menu

def apply_theme(self, theme_name: str):
    import qt_material
    qt_material.apply_stylesheet(self, theme=theme_name)
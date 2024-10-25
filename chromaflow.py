#!/usr/bin/env python3
import json
import subprocess
import os
import argparse
from pathlib import Path
import colorsys
from typing import Optional, Dict, List
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGridLayout,
    QMessageBox,
)
from PyQt5.QtGui import QPixmap, QColor, QFontDatabase, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
import sys


class ModernButton(QPushButton):
    def __init__(self, text="", is_primary=False):
        super().__init__(text)
        self.is_primary = is_primary
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self.update_style()

    def update_style(self):
        if self.is_primary:
            self.setStyleSheet(
                """
                QPushButton {
                    background-color: #0EA5E9;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 14px;
                }
                QPushButton:disabled {
                    background-color: rgba(255, 255, 255, 0.2);
                    color: rgba(255, 255, 255, 0.5);
                }
            """
            )
        else:
            self.setStyleSheet(
                """
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.05);
                    color: white;
                    border: 1px solid #333333;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                    border-color: rgba(255, 255, 255, 0.2);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.15);
                }
            """
            )

    def set_color(self, color: str):
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 14px;
            }}
        """
        )


class ColorSwatch(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, color: str, size: int = 40):
        super().__init__()
        self.color = color
        self.size = size
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.update_style()

    def update_style(self):
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {self.color};
                border: 2px solid #333333;
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: #828282;
            }}
        """
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.color)


class ColorPreviewCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title
        title = QLabel("Selected Color")
        title.setStyleSheet(
            """
            font-size: 16px;
            font-weight: 600;
            color: #E2E8F0;
        """
        )
        layout.addWidget(title)

        # Color preview and info container
        preview_layout = QHBoxLayout()
        preview_layout.setSpacing(10)

        # Large color swatch
        self.swatch = QLabel()
        self.swatch.setFixedSize(85, 85)
        preview_layout.addWidget(self.swatch)

        # Color information
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(0, 0, 0, 0)

        self.hex_label = QLabel("HEX: #000000")
        self.hsl_label = QLabel("HSL: 0°, 0%, 0%")
        for label in [self.hex_label, self.hsl_label]:
            label.setStyleSheet(
                """
                color: #CBD5E1;
                font-size: 14px;
                font-weight: 500;
            """
            )
            info_layout.addWidget(label)

        preview_layout.addWidget(info_widget)
        preview_layout.addStretch()
        layout.addLayout(preview_layout)

        self.setStyleSheet(
            """
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid #333333;
                border-radius: 14px;
            }

            QLabel {
                border-radius: 10px;
                padding: 8px;
                background-color: rgba(0, 0, 0, 0.15);
            }
        """
        )

    def update_color(self, color: str, hsl: Dict[str, int]):
        self.swatch.setStyleSheet(
            f"""
            QFrame {{
                background-color: {color};
                border-radius: 8px;
                border: 2px solid #333333;
            }}
        """
        )
        self.hex_label.setText(f"HEX: {color.upper()}")
        self.hsl_label.setText(f"HSL: {hsl['h']}°, {hsl['s']}%, {hsl['l']}%")


class ImageViewer(QLabel):
    colorPicked = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            """
            QLabel {
                border: 2px solid #333333;
                border-radius: 12px;
                padding: 0;
            }
        """
        )

    def mousePressEvent(self, event):
        if self.pixmap() and event.button() == Qt.LeftButton:
            pos = event.pos()
            image = self.pixmap().toImage()

            # Calculate the top-left corner of the image within the QLabel
            x_offset = (self.width() - self.pixmap().width()) // 2
            y_offset = (self.height() - self.pixmap().height()) // 2

            # Adjust the position based on the alignment
            adjusted_pos = pos - QPoint(x_offset, y_offset)

            if (
                0 <= adjusted_pos.x() < image.width()
                and 0 <= adjusted_pos.y() < image.height()
            ):
                color = QColor(image.pixel(adjusted_pos))
                if color.isValid():
                    self.colorPicked.emit(color.name())


class ModernColorPicker(QMainWindow):
    def __init__(self, wallpaper_path: str):
        super().__init__()
        self.wallpaper_path = wallpaper_path
        self.selected_color = None
        self.setup_ui()
        self.load_content()

    def setup_ui(self):
        self.setWindowTitle("Chromaflow")
        self.setMinimumSize(800, 650)

        # Set dark theme
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #0F172A;
            }
            QLabel {
                color: #E2E8F0;
                font-family: 'Inter', -apple-system, sans-serif;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """
        )

        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("Pick a Color")
        header.setStyleSheet(
            """
            font-size: 24px;
            font-weight: 600;
            color: #F8FAFC;
        """
        )
        layout.addWidget(header)

        # Description
        description = QLabel(
            "Select a color from your wallpaper or palette to customize your theme."
        )
        description.setStyleSheet(
            """
            font-size: 14px;
            color: rgba(255, 255, 255, 0.75);
            margin-bottom: 16px;
        """
        )
        layout.addWidget(description)

        # Image viewer
        self.image_viewer = ImageViewer()
        self.image_viewer.colorPicked.connect(self.handle_color_picked)
        layout.addWidget(self.image_viewer)

        # Color preview and palette
        row = QHBoxLayout()
        row.setSpacing(16)
        layout.addLayout(row)

        # Color preview
        self.color_preview = ColorPreviewCard()
        row.addWidget(self.color_preview)

        # Palette section
        palette = QVBoxLayout()
        row.addLayout(palette)

        palette_header = QLabel("Color Palette")
        palette_header.setStyleSheet(
            """
            font-size: 16px;
            font-weight: 600;
            color: #F8FAFC;
        """
        )
        palette.addWidget(palette_header)

        # Palette grid
        palette_widget = QWidget()
        self.palette_grid = QGridLayout(palette_widget)
        self.palette_grid.setSpacing(8)
        self.palette_grid.setContentsMargins(0, 0, 0, 0)
        palette.addWidget(palette_widget)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 12, 0, 0)

        cancel_button = ModernButton("Cancel")
        cancel_button.clicked.connect(self.close)

        self.apply_button = ModernButton("Apply Theme", is_primary=True)
        self.apply_button.clicked.connect(self.accept)
        self.apply_button.setEnabled(False)

        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.apply_button)
        layout.addLayout(button_layout)

    def load_content(self):
        try:
            # Load wallpaper
            pixmap = QPixmap(self.wallpaper_path)
            scaled_pixmap = pixmap.scaled(
                self.image_viewer.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.image_viewer.setPixmap(scaled_pixmap)

            # Load palette
            colors = self._get_pywal_colors()
            for i, color in enumerate(colors):
                swatch = ColorSwatch(color)
                swatch.clicked.connect(lambda c=color: self.handle_color_picked(c))
                self.palette_grid.addWidget(swatch, i // 8, i % 8)

            self.setStyleSheet(
                f"""
                    QMainWindow {{
                        background-color: {colors[0]};
                    }}
                """
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.close()

    def _get_pywal_colors(self) -> List[str]:
        subprocess.run(["wal", "-i", self.wallpaper_path, "-n"], check=True)
        cache_path = os.path.expanduser("~/.cache/wal/colors.json")
        with open(cache_path, "r") as f:
            data = json.load(f)
        return [data["colors"][f"color{i}"] for i in range(16)]

    def handle_color_picked(self, color: str):
        self.selected_color = color
        hsl = hex_to_hsl(color)
        self.color_preview.update_color(color, hsl)
        self.apply_button.setEnabled(True)
        self.apply_button.set_color(color)

    def accept(self):
        self.close()

    def get_result(self) -> Optional[str]:
        return self.selected_color


def hex_to_hsl(hex_color: str) -> Dict[str, int]:
    """Convert hex color to HSL values"""
    hex_color = str(hex_color).lstrip("#")
    rgb = tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(*rgb)
    return {"h": round(h * 360), "s": round(s * 100), "l": round(l * 100)}


class ThemeManager:
    def __init__(self, colors_path: str, wallpaper_path: str):
        self.colors_path = Path(colors_path)
        self.wallpaper_path = wallpaper_path
        self.current_color = None

    def update_colors(self, theme_values: Dict[str, int]) -> None:
        """Update theme colors configuration"""
        try:
            with open(self.colors_path, "r") as f:
                marble_data = json.load(f)

            marble_data["colors"] = {
                "extracted": {"h": theme_values["hue"], "s": theme_values["saturation"]}
            }

            with open(self.colors_path, "w") as f:
                json.dump(marble_data, f, indent=4)
        except Exception as e:
            raise Exception(f"Failed to update theme colors: {str(e)}")

    def install_theme(
        self,
        theme_values: Dict[str, int],
        mode: str,
        filled: bool,
        name: Optional[str] = None,
        panel_default_size: bool = False,
        panel_no_pill: bool = False,
        panel_text_color: bool = False,
        opaque: bool = False,
        launchpad: bool = False,
    ) -> None:
        """Install theme with given parameters"""
        if name is None:
            # Get wallpaper filename without extension and combine with color
            wallpaper_name = Path(self.wallpaper_path).stem
            color_hex = "".join(f"{x:02x}" for x in self.current_color.getRgb()[:3])
            name = f"{wallpaper_name}-#{color_hex}"

        install_cmd = [
            "python",
            "install.py",
            f'--hue={theme_values["hue"]}',
            f'--sat={theme_values["saturation"]}',
            f"--name={name}",
            f"--mode={mode}",
        ]

        if filled:
            install_cmd.append("--filled")
        if panel_default_size:
            install_cmd.append("--panel_default_size")
        if panel_no_pill:
            install_cmd.append("--panel_no_pill")
        if panel_text_color:
            install_cmd.append("--panel_text_color")
        if opaque:
            install_cmd.append("--opaque")
        if launchpad:
            install_cmd.append("--launchpad")

        subprocess.run(install_cmd, check=True)


def main():
    parser = argparse.ArgumentParser(
        description="Chromaflow - Extract colors from wallpaper and apply to Marble shell theme"
    )
    parser.add_argument("--wallpaper", required=True, help="Path to wallpaper image")
    parser.add_argument(
        "--colors-path",
        default="./colors.json",
        help="Path to Marble theme colors.json",
    )
    parser.add_argument(
        "--mode",
        choices=["light", "dark"],
        default="dark",
        help="Theme mode (default: dark)",
    )
    parser.add_argument(
        "--filled", action="store_true", help="Use more vibrant accent colors"
    )
    parser.add_argument(
        "--name",
        help="Custom name for the theme (default: based on wallpaper and color)",
    )
    parser.add_argument(
        "-O", "--opaque", action="store_true", help="Make background color opaque"
    )
    parser.add_argument(
        "--launchpad",
        action="store_true",
        help="Change Show Apps icon to macOS Launchpad icon",
    )
    panel_group = parser.add_mutually_exclusive_group()
    panel_group.add_argument(
        "-Pds",
        "--panel_default_size",
        action="store_true",
        help="Set default panel size",
    )
    panel_group.add_argument(
        "-Pnp",
        "--panel_no_pill",
        action="store_true",
        help="Remove panel button background",
    )
    panel_group.add_argument(
        "-Ptc", "--panel_text_color", action="store_true", help="Set panel text color"
    )

    args = parser.parse_args()

    try:
        app = QApplication(sys.argv)

        # Load Inter font
        QFontDatabase.addApplicationFont(":/fonts/Inter-Regular.ttf")
        app.setFont(QFont("Inter"))

        # Create and show picker
        picker = ModernColorPicker(args.wallpaper)
        picker.show()
        app.exec_()

        selected_color = picker.get_result()
        if not selected_color:
            print("No color selected. Exiting...")
            return

        # Process selected color
        hsl = hex_to_hsl(selected_color)
        theme_values = {
            "hue": hsl["h"],
            "saturation": min(max(hsl["s"], 30), 100),  # Ensure minimum visibility
        }

        # Update and install theme
        theme_manager = ThemeManager(args.colors_path, args.wallpaper)
        theme_manager.current_color = QColor(selected_color)
        theme_manager.update_colors(theme_values)
        theme_manager.install_theme(
            theme_values,
            args.mode,
            args.filled,
            name=args.name,
            panel_default_size=args.panel_default_size,
            panel_no_pill=args.panel_no_pill,
            panel_text_color=args.panel_text_color,
            opaque=args.opaque,
            launchpad=args.launchpad,
        )

        print(f"\nTheme created successfully!")
        print("\nTo apply the theme:")
        print("1. Open Extensions app")
        print("2. Go to 'User Themes' settings")
        print(f"3. Select 'Marble-{args.name}-{args.mode}' from the dropdown")
        print("4. Give Chromaflow a star on GitHub if you liked it! 🌟")

    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()

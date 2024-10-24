#!/usr/bin/env python3
import json
import subprocess
import os
import argparse
from pathlib import Path
import colorsys
from typing import Optional, Dict, List, Tuple
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea,
                           QGridLayout, QMessageBox, QStackedWidget)
from PyQt5.QtGui import (QPixmap, QImage, QColor, QPainter, QPainterPath, 
                        QFontDatabase, QFont)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
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
            self.setStyleSheet("""
                QPushButton {
                    background-color: #0EA5E9;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #0284C7;
                }
                QPushButton:pressed {
                    background-color: #0369A1;
                }
                QPushButton:disabled {
                    background-color: #94A3B8;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: white;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #334155;
                    border-color: #475569;
                }
                QPushButton:pressed {
                    background-color: #0F172A;
                }
            """)

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
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.color};
                border: 2px solid #334155;
                border-radius: 8px;
            }}
            QFrame:hover {{
                border: 2px solid #94A3B8;
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.color)

class ColorPreviewCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("Selected Color")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #E2E8F0;
        """)
        layout.addWidget(title)

        # Color preview and info container
        preview_layout = QHBoxLayout()
        preview_layout.setSpacing(20)

        # Large color swatch
        self.swatch = QFrame()
        self.swatch.setFixedSize(80, 80)
        preview_layout.addWidget(self.swatch)

        # Color information
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(8)

        self.hex_label = QLabel()
        self.hsl_label = QLabel()
        for label in [self.hex_label, self.hsl_label]:
            label.setStyleSheet("""
                color: #CBD5E1;
                font-size: 14px;
                font-weight: 500;
            """)
            info_layout.addWidget(label)

        preview_layout.addWidget(info_widget)
        preview_layout.addStretch()
        layout.addLayout(preview_layout)

        self.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 20px;
            }
        """)

    def update_color(self, color: str, hsl: Dict[str, int]):
        self.swatch.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 8px;
                border: 2px solid #334155;
            }}
        """)
        self.hex_label.setText(f"HEX: {color.upper()}")
        self.hsl_label.setText(f"HSL: {hsl['h']}°, {hsl['s']}%, {hsl['l']}%")

class ImageViewer(QLabel):
    colorPicked = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(500, 300)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 16px;
            }
        """)

    def mousePressEvent(self, event):
        if self.pixmap() and event.button() == Qt.LeftButton:
            pos = event.pos()
            image = self.pixmap().toImage()
            color = QColor(image.pixel(pos))
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
        self.setMinimumSize(800, 900)
        
        # Set dark theme
        self.setStyleSheet("""
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
        """)

        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(24)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("Pick a Color")
        header.setStyleSheet("""
            font-size: 24px;
            font-weight: 600;
            color: #F8FAFC;
            margin-bottom: 8px;
        """)
        layout.addWidget(header)

        # Description
        description = QLabel("Select a color from your wallpaper or palette to customize your theme.")
        description.setStyleSheet("""
            font-size: 14px;
            color: #94A3B8;
            margin-bottom: 16px;
        """)
        layout.addWidget(description)

        # Image viewer
        self.image_viewer = ImageViewer()
        self.image_viewer.colorPicked.connect(self.handle_color_picked)
        layout.addWidget(self.image_viewer)

        # Color preview
        self.color_preview = ColorPreviewCard()
        layout.addWidget(self.color_preview)

        # Palette section
        palette_header = QLabel("Color Palette")
        palette_header.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #F8FAFC;
            margin-top: 8px;
        """)
        layout.addWidget(palette_header)

        # Palette grid
        palette_widget = QWidget()
        self.palette_grid = QGridLayout(palette_widget)
        self.palette_grid.setSpacing(8)
        layout.addWidget(palette_widget)

        # Action buttons
        button_layout = QHBoxLayout()
        
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
                Qt.SmoothTransformation
            )
            self.image_viewer.setPixmap(scaled_pixmap)

            # Load palette
            colors = self._get_pywal_colors()
            for i, color in enumerate(colors):
                swatch = ColorSwatch(color)
                swatch.clicked.connect(lambda c=color: self.handle_color_picked(c))
                self.palette_grid.addWidget(swatch, i//8, i%8)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.close()

    def _get_pywal_colors(self) -> List[str]:
        subprocess.run(['wal', '-i', self.wallpaper_path, '-n'], check=True)
        cache_path = os.path.expanduser('~/.cache/wal/colors.json')
        with open(cache_path, 'r') as f:
            data = json.load(f)
        return [data['colors'][f'color{i}'] for i in range(16)]

    def handle_color_picked(self, color: str):
        self.selected_color = color
        hsl = hex_to_hsl(color)
        self.color_preview.update_color(color, hsl)
        self.apply_button.setEnabled(True)

    def accept(self):
        self.close()

    def get_result(self) -> Optional[str]:
        return self.selected_color

def hex_to_hsl(hex_color: str) -> Dict[str, int]:
    """Convert hex color to HSL values"""
    hex_color = str(hex_color).lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(*rgb)
    return {
        "h": round(h * 360),
        "s": round(s * 100),
        "l": round(l * 100)
    }

class ThemeManager:
    def __init__(self, colors_path: str):
        self.colors_path = Path(colors_path)
    
    def update_colors(self, theme_values: Dict[str, int]) -> None:
        """Update theme colors configuration"""
        try:
            with open(self.colors_path, 'r') as f:
                marble_data = json.load(f)
            
            marble_data["colors"] = {
                "extracted": {
                    "h": theme_values['hue'],
                    "s": theme_values['saturation']
                }
            }
            
            with open(self.colors_path, 'w') as f:
                json.dump(marble_data, f, indent=4)
        except Exception as e:
            raise Exception(f"Failed to update theme colors: {str(e)}")
    
    def install_theme(self, theme_values: Dict[str, int], mode: str, filled: bool) -> None:
        install_cmd = [
            'python', 'install.py',
            f'--hue={theme_values["hue"]}',
            f'--sat={theme_values["saturation"]}',
            '--name=extracted',
            f'--mode={mode}'
        ]
        
        if filled:
            install_cmd.append('--filled')
        
        subprocess.run(install_cmd, check=True)

def main():
    parser = argparse.ArgumentParser(
        description='Chromaflow - Extract colors from wallpaper and apply to Marble shell theme')
    parser.add_argument('--wallpaper', required=True,
                       help='Path to wallpaper image')
    parser.add_argument('--colors-path', default='./colors.json',
                       help='Path to Marble theme colors.json')
    parser.add_argument('--mode', choices=['light', 'dark'], default='dark',
                       help='Theme mode (default: dark)')
    parser.add_argument('--filled', action='store_true',
                       help='Use more vibrant accent colors')
    
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
            'hue': hsl['h'],
            'saturation': min(max(hsl['s'], 30), 100)  # Ensure minimum visibility
        }
        
        # Update and install theme
        theme_manager = ThemeManager(args.colors_path)
        theme_manager.update_colors(theme_values)
        theme_manager.install_theme(theme_values, args.mode, args.filled)
        
        print(f"\nTheme created successfully!")
        print("\nTo apply the theme:")
        print("1. Open Extensions app")
        print("2. Go to 'User Themes' settings")
        print("3. Select 'Marble-extracted-dark' from the dropdown")
        print("4. Give Chromaflow a star on GitHub if you liked it! 🌟")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
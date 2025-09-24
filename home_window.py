from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QApplication, QFrame
)
from PySide6.QtGui import QPixmap, QFont, QCursor
from PySide6.QtCore import Qt
from organs_viewer import OrgansViewer

class ClickableFrame(QFrame):
    def __init__(self, text, image_path, click_callback):
        super().__init__()
        self.text = text
        self.image_path = image_path
        self.click_callback = click_callback
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                border-radius: 16px;
                background-color: #232946;
                background-image: url('{image_path}');
                background-position: center;
                background-repeat: no-repeat;
                background-size: cover;
                border: 2px solid #eee;
                transition: box-shadow 0.2s, border-color 0.2s;
            }}
        """)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # self.setMinimumSize(300, 400)
        self.setFixedSize(300, 400)
        self.label = QLabel(text, self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont('Segoe UI', 18, QFont.Bold))
        self.label.setStyleSheet("color: white; background: transparent; border: none;")
        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self.label)
        layout.addStretch()
        self.setLayout(layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.click_callback(self.text)

    def enterEvent(self, event):
        self.setStyleSheet(f"""
            QFrame {{
                border-radius: 16px;
                background-color: #232946;
                background-image: url('{self.image_path}');
                background-position: center;
                background-repeat: no-repeat;
                background-size: cover;
                border: 2px solid #0078d7;
                box-shadow: 0 0 24px #0078d788;
            }}
        """)

    def leaveEvent(self, event):
        self.setStyleSheet(f"""
            QFrame {{
                border-radius: 16px;
                background-color: #232946;
                background-image: url('{self.image_path}');
                background-position: center;
                background-repeat: no-repeat;
                background-size: cover;
                border: 2px solid #eee;
            }}
        """)

class HomeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Medical Segmentation App")
        self.setStyleSheet("background: #202933;")
        layout = QHBoxLayout()
        layout.setSpacing(32)  # horizontal space between frames
        layout.setContentsMargins(100, 48, 100, 48)  # top and bottom vertical padding
        self.frames = []
        frame_data = [
            ("kidney", "appImages/kidney.jpg"),
            ("stomach", "appImages/stomach.jpg"),
            ("Liver", "appImages/liver.jpg"),
        ]
        for text, img in frame_data:
            frame = ClickableFrame(text, img, self.on_frame_clicked)
            layout.addWidget(frame)
            self.frames.append(frame)
        self.setLayout(layout)
        # self.setFixedSize(800, 400)

    def on_frame_clicked(self, frame_text):
        print(f"Frame clicked: {frame_text}")
        # Remove all frames from layout
        for frame in self.frames:
            frame.setParent(None)
        # Remove old layout before setting new one
        old_layout = self.layout()
        if old_layout is not None:
            QWidget().setLayout(old_layout)
        # Replace with OrgansViewer, passing selected organ
        self.organs_viewer = OrgansViewer(selected_organ=frame_text.lower(), return_callback=self.show_home)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.organs_viewer)
        self.setLayout(main_layout)

    def show_home(self):
        # Remove organs_viewer and restore home layout
        if hasattr(self, 'organs_viewer'):
            self.organs_viewer.setParent(None)
        old_layout = self.layout()
        if old_layout is not None:
            QWidget().setLayout(old_layout)
        layout = QHBoxLayout()
        layout.setSpacing(32)
        layout.setContentsMargins(100, 48, 100, 48)
        self.frames = []
        frame_data = [
            ("kidney", "appImages/kidney.jpg"),
            ("stomach", "appImages/stomach.jpg"),
            ("Liver", "appImages/liver.jpg"),
        ]
        for text, img in frame_data:
            frame = ClickableFrame(text, img, self.on_frame_clicked)
            layout.addWidget(frame)
            self.frames.append(frame)
        self.setLayout(layout)

        
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    win = HomeWindow()
    win.show()
    sys.exit(app.exec_())

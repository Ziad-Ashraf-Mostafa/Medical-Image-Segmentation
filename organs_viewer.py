from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton
from PySide6.QtCore import Qt

class OrgansViewer(QWidget):
    def __init__(self, return_callback=None):
        super().__init__()
        main_layout = QHBoxLayout(self)
        # Sidebar controller
        sidebar = QFrame(self)
        sidebar.setFixedWidth(120)
        sidebar.setStyleSheet("background: #232946; border-right: 2px solid #0078d7;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setAlignment(Qt.AlignTop)
        # Return button
        back_btn = QPushButton("←", sidebar)
        back_btn.setFixedSize(48, 48)
        back_btn.setStyleSheet("font-size: 28px; color: #fff; background: #0078d7; border-radius: 24px;")
        if return_callback:
            back_btn.clicked.connect(return_callback)
        sidebar_layout.addWidget(back_btn)
        # Placeholder for future sidebar controls
        sidebar_layout.addStretch()
        # Main 3D view area
        view_layout = QVBoxLayout()
        nav_bar = QFrame(self)
        nav_bar.setFixedHeight(60)
        nav_bar.setStyleSheet("background: #232946; border-bottom: 2px solid #0078d7;")
        view_layout.addWidget(nav_bar)
        pyvista_placeholder = QLabel("PyVista 3D View Area", self)
        pyvista_placeholder.setAlignment(Qt.AlignCenter)
        pyvista_placeholder.setStyleSheet("color: #fff; font-size: 24px; background: #202933; border-radius: 16px;")
        view_layout.addWidget(pyvista_placeholder, 1)
        main_layout.addWidget(sidebar)
        main_layout.addLayout(view_layout, 1)
        self.setLayout(main_layout)

import os
import nibabel as nib
import pyvista as pv
import matplotlib as plt
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QSlider, QColorDialog, QCheckBox
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class OrgansViewer(QWidget):
    def __init__(self, selected_organ=None, return_callback=None):
        super().__init__()
        if selected_organ is None:
            selected_organ = 'kidney'
        main_layout = QHBoxLayout(self)
        # Sidebar controller
        sidebar = QFrame(self)
        sidebar.setFixedWidth(360)  
        sidebar.setStyleSheet("background: #232946; border-right: 2px solid #0078d7;")
        self.sidebar_layout = QVBoxLayout(sidebar)
        self.sidebar_layout.setAlignment(Qt.AlignTop)
        # Return button
        back_btn = QPushButton("←", sidebar)
        back_btn.setFixedSize(48, 48)
        back_btn.setStyleSheet("font-size: 28px; color: #fff; background: #0078d7; border-radius: 24px;")
        if return_callback:
            back_btn.clicked.connect(return_callback)
        self.sidebar_layout.addWidget(back_btn)
        # Organ title label
        organ_label = QLabel(selected_organ.capitalize(), sidebar)
        organ_label.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold; margin: 16px 0 8px 0;")
        organ_label.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(organ_label)
        # Models tree views
        organs = {
            'kidney': os.listdir(os.path.join(os.path.dirname(__file__), 'kidney')),
            'stomach': os.listdir(os.path.join(os.path.dirname(__file__), 'stomach')),
            'liver': os.listdir(os.path.join(os.path.dirname(__file__), 'liver')),
        }
        organ_files = {
            'kidney': {},
            'stomach': {},
            'liver': {}
        }
        # enter the files dynamicaly
        for organ in organs:
            for model in organs[organ]:
                model_path = os.path.join(os.path.dirname(__file__), organ, model)
                if os.path.isdir(model_path):
                    organ_files[organ].update({model : [f for f in os.listdir(model_path) if f.endswith('.nii') or f.endswith('.nii.gz')]})


        self.pv_widgets = {}
        self.pv_actors = {}
        if selected_organ in organs:
            for model in organs[selected_organ]:
                tree = QTreeWidget(sidebar)
                tree.setHeaderHidden(True)
                tree.setStyleSheet("QTreeWidget::item { padding-left: 0px; } QTreeWidget { border: none; }")
                model_item = QTreeWidgetItem([model])
                tree.addTopLevelItem(model_item)
                self.pv_actors[model] = {}
                for file in organ_files[selected_organ][model]:
                    file_item = QTreeWidgetItem([file])
                    model_item.addChild(file_item)
                    controls_widget = QWidget()
                    controls_layout = QHBoxLayout(controls_widget)
                    controls_layout.setContentsMargins(0,0,0,0)
                    # Part name label
                    part_label = QLabel(file[:file.find('.')])  # Strip extension for cleaner label
                    part_label.setStyleSheet("color: #fff; font-size: 12px; margin-right: 8px; margin-left: 0px;")
                    controls_layout.addWidget(part_label)
                    # View/Hide
                    view_checkbox = QCheckBox("View")
                    view_checkbox.setChecked(True)
                    view_checkbox.setStyleSheet("QCheckBox { color: #fff; } QCheckBox::indicator { width: 18px; height: 18px; } QCheckBox::indicator:checked { background-color: #0078d7; border-radius: 4px; border: 2px solid #fff; } QCheckBox::indicator:unchecked { background-color: #232946; border-radius: 4px; border: 2px solid #fff; } QCheckBox:hover { background: #3a4a6a; }")
                    controls_layout.addWidget(view_checkbox)
                    # Opacity
                    opacity_slider = QSlider(Qt.Horizontal)
                    opacity_slider.setMinimum(0)
                    opacity_slider.setMaximum(100)
                    opacity_slider.setValue(100)
                    opacity_slider.setFixedWidth(80)
                    controls_layout.addWidget(opacity_slider)
                    # Color picker
                    color_btn = QPushButton("Color")
                    color_btn.setFixedWidth(50)
                    controls_layout.addWidget(color_btn)
                    tree.setItemWidget(file_item, 0, controls_widget)
                    # Connect controls
                    view_checkbox.stateChanged.connect(lambda state, m=model, f=file, cb=view_checkbox: self.toggle_actor(m, f, cb.isChecked()))
                    opacity_slider.valueChanged.connect(lambda val, m=model, f=file: self.set_opacity(m, f, val))
                    color_btn.clicked.connect(lambda _, m=model, f=file, btn=color_btn: self.pick_color(m, f, btn))
                self.sidebar_layout.addWidget(tree)
        # Main 3D view area for selected organ
        view_layout = QVBoxLayout()
        models_area = QHBoxLayout()
        self.model_widgets = []
        for model in organs[selected_organ]:
            # Create a vertical layout for each model
            model_vbox = QVBoxLayout()
            # Add model name label above viewer
            model_label = QLabel(model)
            model_label.setStyleSheet("color: #fff; font-size: 18px; font-weight: bold; margin-bottom: 8px;")
            model_label.setAlignment(Qt.AlignCenter)
            model_vbox.addWidget(model_label)
            # Add 3D viewer
            pv_widget = QtInteractor(self)
            self.pv_widgets[model] = pv_widget
            model_vbox.addWidget(pv_widget, 1)
            # Add evaluation table below viewer
            from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
            table = QTableWidget(2, 3, self)
            table.setHorizontalHeaderLabels(["Dice", "IoU", "Hausdorff"])
            table.setVerticalHeaderLabels(["Model", "Reference"])
            table.setItem(0, 0, QTableWidgetItem("0.85"))
            table.setItem(0, 1, QTableWidgetItem("0.78"))
            table.setItem(0, 2, QTableWidgetItem("12.3"))
            table.setItem(1, 0, QTableWidgetItem("0.88"))
            table.setItem(1, 1, QTableWidgetItem("0.81"))
            table.setItem(1, 2, QTableWidgetItem("10.7"))
            table.setStyleSheet("color: #fff; background: #232946; font-size: 12px;")
            model_vbox.addWidget(table)
            # Wrap the model_vbox in a QWidget
            model_widget = QWidget(self)
            model_widget.setLayout(model_vbox)
            models_area.addWidget(model_widget, 1)
            self.model_widgets.append(model_widget)
            # Load and show all files for this model
            for file in organ_files[selected_organ][model]:
                nii_path = os.path.join(os.path.dirname(__file__), selected_organ, model, file)
                if os.path.exists(nii_path):
                    img = nib.load(nii_path)
                    data = img.get_fdata()
                    # Use ImageData for volumetric grid
                    grid = pv.ImageData()
                    grid.dimensions = data.shape
                    grid.spacing = img.header.get_zooms()
                    grid.origin = tuple(img.affine[:3, 3])
                    grid['values'] = data.flatten(order='F')
                    # Extract mesh using marching cubes (threshold: mean value)
                    try:
                        threshold = data.mean()
                        mesh = grid.contour([threshold], scalars='values')
                        mesh = mesh.smooth(n_iter=50, relaxation_factor=0.1)
                        # Assign a unique color for each actor
                        import random
                        default_color = [random.random(), random.random(), random.random()]
                        actor = pv_widget.add_mesh(mesh, name=file, color=default_color, show_scalar_bar=False)
                        self.pv_actors[model][file] = actor
                    except Exception as e:
                        print(f"Mesh extraction failed for {file}: {e}")
            # Add 'View slices' button under each model
            btn = QPushButton("View slices")
            btn.setStyleSheet("margin-top: 8px; font-size: 14px; background: #0078d7; color: #fff; border-radius: 8px; padding: 4px 12px;")
            btn.clicked.connect(lambda checked, organ=selected_organ, m=model: self.show_slices_view(organ, m))
            model_vbox.addWidget(btn)
        view_layout.addLayout(models_area, 1)
        self.models_area = models_area
        self.view_layout = view_layout
        main_layout.addWidget(sidebar)
        main_layout.addLayout(view_layout, 1)
        self.setLayout(main_layout)

        self.slice_viewer = None
        self.slice_viewer_model = None

    def toggle_actor(self, model, file, checked):
        actor = self.pv_actors.get(model, {}).get(file)
        if actor:
            actor.SetVisibility(checked)
            self.view_checkbox.stateChanged

    def set_opacity(self, model, file, value):
        actor = self.pv_actors.get(model, {}).get(file)
        if actor:
            actor.GetProperty().SetOpacity(value / 100.0)

    def pick_color(self, model, file, btn):
        actor = self.pv_actors.get(model, {}).get(file)
        if actor:
            color = QColorDialog.getColor(parent=btn)
            if color.isValid():
                rgb = color.getRgb()[:3]
                actor.GetProperty().SetColor([c/255.0 for c in rgb])

    def show_slices_view(self, organ, model):
        # Hide all model viewers
        for w in self.model_widgets:
            w.hide()
        # Remove previous slice_viewer if exists
        if self.slice_viewer is not None:
            self.view_layout.removeWidget(self.slice_viewer)
            self.slice_viewer.deleteLater()
            self.slice_viewer = None

        # Use fixed scan file
        scan_file = os.path.join(os.path.dirname(__file__), "scan.nii.gz")
        # Collect all .nii/.nii.gz files for the selected model as organs
        organ_files = {}
        model_dir = os.path.join(os.path.dirname(__file__), organ, model)
        for f in os.listdir(model_dir):
            if f.endswith('.nii') or f.endswith('.nii.gz'):
                organ_files[f] = os.path.join(model_dir, f)
        # Get color and opacity from sidebar controls (default if not set)
        color = (0, 0.5, 1, 1)
        opacity = 0.5
        if hasattr(self, 'pv_actors') and model in self.pv_actors:
            for file, actor in self.pv_actors[model].items():
                c = actor.GetProperty().GetColor()
                color = (c[0], c[1], c[2], 1)
                opacity = actor.GetProperty().GetOpacity()
                break
        colors = {f: color for f in organ_files}
        opacities = {f: opacity for f in organ_files}
        # Import SegmentationViewer from mytest.py
        from slicer import SegmentationViewer
        self.slice_viewer = SegmentationViewer(scan_file, organ_files, colors, opacities)
        # Add back button
        back_btn = QPushButton("            ← Back to models            ", self.slice_viewer)
        back_btn.setStyleSheet("font-size: 16px; color: #fff; background: #0078d7; border-radius: 8px; margin-bottom: 8px;")
        back_btn.clicked.connect(self.hide_slices_view)
        self.slice_viewer.layout().addWidget(back_btn, 2, 0, 1, 2, alignment=Qt.AlignCenter)
        self.slice_viewer_model = model
        self.view_layout.addWidget(self.slice_viewer)
        
        self.slice_viewer.show()
        # Update sidebar to show only the opened model
        for i in reversed(range(self.sidebar_layout.count())):
            widget = self.sidebar_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        model_label = QLabel(model.capitalize(), self)
        model_label.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold; margin: 16px 0 8px 0;")
        model_label.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(model_label)

    def hide_slices_view(self):
        if self.slice_viewer:
            self.slice_viewer.hide()
        # Show all model viewers
        for w in self.model_widgets:
            w.show()

import os
import nibabel as nib
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QSlider, QColorDialog, QCheckBox
from PySide6.QtCore import Qt



class OrgansViewer(QWidget):
    def __init__(self, selected_organ=None, return_callback=None):
        super().__init__()
        if selected_organ is None:
            selected_organ = 'kidney'
        main_layout = QHBoxLayout(self)
        # Sidebar controller
        sidebar = QFrame(self)
        sidebar.setFixedWidth(320)
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
        # Organ title label
        organ_label = QLabel(selected_organ.capitalize(), sidebar)
        organ_label.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold; margin: 16px 0 8px 0;")
        organ_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(organ_label)
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
                    part_label.setStyleSheet("color: #fff; font-size: 12px; margin-right: 8px;")
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
                sidebar_layout.addWidget(tree)
        # Main 3D view area for selected organ
        view_layout = QVBoxLayout()
        nav_bar = QFrame(self)
        nav_bar.setFixedHeight(60)
        nav_bar.setStyleSheet("background: #232946; border-bottom: 2px solid #0078d7;")
        view_layout.addWidget(nav_bar)
        models_area = QHBoxLayout()
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
            models_area.addLayout(model_vbox, 1)
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
                        # Assign a unique color for each actor
                        import random
                        default_color = [random.random(), random.random(), random.random()]
                        actor = pv_widget.add_mesh(mesh, name=file, color=default_color, show_scalar_bar=False)
                        self.pv_actors[model][file] = actor
                    except Exception as e:
                        print(f"Mesh extraction failed for {file}: {e}")
        view_layout.addLayout(models_area, 1)
        main_layout.addWidget(sidebar)
        main_layout.addLayout(view_layout, 1)
        self.setLayout(main_layout)

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

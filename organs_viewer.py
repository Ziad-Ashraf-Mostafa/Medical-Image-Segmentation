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
            self.selected_organ = 'kidney'
        else:
            self.selected_organ = selected_organ
        main_layout = QHBoxLayout(self)
        # Sidebar controller
        sidebar = QFrame(self)
        sidebar.setFixedWidth(360)  
        sidebar.setStyleSheet("background: #232946; border-right: 2px solid #0078d7;")
        self.sidebar_layout = QVBoxLayout(sidebar)
        self.sidebar_layout.setAlignment(Qt.AlignTop)
        # Return button
        self.return_btn = QPushButton("←", sidebar)
        self.return_btn.setFixedSize(48, 48)
        self.return_btn.setStyleSheet("font-size: 28px; color: #fff; background: #0078d7; border-radius: 24px;")
        if return_callback:
            self.return_btn.clicked.connect(return_callback)
        self.sidebar_layout.addWidget(self.return_btn)
    # Organ title label (only once at the top)
        self.organ_label_widget = QLabel(self.selected_organ.capitalize(), sidebar)
        self.organ_label_widget.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold; margin: 16px 0 8px 0;")
        self.organ_label_widget.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(self.organ_label_widget)
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
        self.sidebar_trees = {}
        self.sidebar_controls = {}
        if selected_organ in organs:
            for model in organs[self.selected_organ]:
                tree = QTreeWidget(sidebar)
                tree.setHeaderHidden(True)
                tree.setStyleSheet("QTreeWidget::item { padding-left: 0px; font-size: 14px; font-weight: bold; } QTreeWidget { border: none; }")
                model_item = QTreeWidgetItem([model])
                font = model_item.font(0)
                font.setPointSize(12)
                font.setBold(True)
                model_item.setFont(0, font)
                tree.addTopLevelItem(model_item)
                self.pv_actors[model] = {}
                controls = []
                for file in organ_files[self.selected_organ][model]:
                    file_item = QTreeWidgetItem([file])
                    model_item.addChild(file_item)
                    controls_widget = QWidget()
                    controls_layout = QHBoxLayout(controls_widget)
                    controls_layout.setContentsMargins(0,0,0,0)
                    part_label = QLabel(file[:file.find('.')])
                    part_label.setStyleSheet("color: #fff; font-size: 12px; margin-right: 8px; margin-left: 0px;")
                    controls_layout.addWidget(part_label)
                    view_checkbox = QCheckBox("View")
                    view_checkbox.setChecked(True)
                    view_checkbox.setStyleSheet("QCheckBox { color: #fff; } QCheckBox::indicator { width: 18px; height: 18px; } QCheckBox::indicator:checked { background-color: #0078d7; border-radius: 4px; border: 2px solid #fff; } QCheckBox::indicator:unchecked { background-color: #232946; border-radius: 4px; border: 2px solid #fff; } QCheckBox:hover { background: #3a4a6a; }")
                    controls_layout.addWidget(view_checkbox)
                    opacity_slider = QSlider(Qt.Horizontal)
                    opacity_slider.setMinimum(0)
                    opacity_slider.setMaximum(100)
                    opacity_slider.setValue(100)
                    opacity_slider.setFixedWidth(80)
                    controls_layout.addWidget(opacity_slider)
                    color_btn = QPushButton("Color")
                    color_btn.setFixedWidth(50)
                    controls_layout.addWidget(color_btn)
                    tree.setItemWidget(file_item, 0, controls_widget)
                    # Connect controls to actively update mesh
                    view_checkbox.stateChanged.connect(lambda state, m=model, f=file, cb=view_checkbox: self.toggle_actor(m, f, cb.isChecked()))
                    opacity_slider.valueChanged.connect(lambda val, m=model, f=file, slider=opacity_slider: self.set_opacity(m, f, slider.value()))
                    color_btn.clicked.connect(lambda _, m=model, f=file, btn=color_btn: self.pick_color(m, f, btn))
                    controls.append((part_label, view_checkbox, opacity_slider, color_btn, file))
                self.sidebar_trees[model] = tree
                self.sidebar_controls[model] = controls
    # Add all model trees (for model view)
        # Add model labels above each tree with increased font size
        self.model_tree_widgets = []
        for model in organs[self.selected_organ]:
            self.sidebar_layout.addWidget(self.sidebar_trees[model])
            self.model_tree_widgets.append((None, self.sidebar_trees[model]))
        # Main 3D view area for selected organ
        view_layout = QVBoxLayout()
        models_area = QHBoxLayout()
        self.model_widgets = []
        for model in organs[self.selected_organ]:
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
            from PySide6.QtWidgets import QTableWidget, QTableWidgetItem; import pandas as pd
            if model == "Total Segmentator": 
                model_abberviation = "ts"
            elif model == "Swin UNETR":
                model_abberviation = "swin"
            elif model == "Whole Body CT":
                model_abberviation = "ts"

            organs_col = os.listdir(os.path.dirname(__file__)+"/"+ self.selected_organ+"/"+ model)
            table = QTableWidget(len(organs_col)+1, 3, self)
            table.setHorizontalHeaderLabels(["Dice", "IoU", "Volume Similarity"])
            row_labels = [file[:file.index(".")] for file in organs_col] + ["Average"]
            table.setVerticalHeaderLabels(row_labels)
            

            # Reading csv and visualizing evaluation matrix data on the app
            df = pd.read_csv("evaluation.csv", header=0)
            df.columns = ["Model", "case", "Organ", "Dice", "IoU", "Pred_Volume", "GT_Volume"]

            i = 0
            for organ in organs_col:
                organ_name = organ.split(".")[0]  # extracting organ name from the file name

                dice = df.query(f'Model == "{model_abberviation}" and Organ == "{organ_name}"')["Dice"].values
                iou  = df.query(f'Model == "{model_abberviation}" and Organ == "{organ_name}"')["IoU"].values
                vs1  = df.query(f'Model == "{model_abberviation}" and Organ == "{organ_name}"')["Pred_Volume"].values
                vs2  = df.query(f'Model == "{model_abberviation}" and Organ == "{organ_name}"')["GT_Volume"].values

                try:
                    table.setItem(i, 0, QTableWidgetItem(f"{float(dice[0]):.2f}"))
                    table.setItem(i, 1, QTableWidgetItem(f"{float(iou[0]):.2f}"))
                    table.setItem(i, 2, QTableWidgetItem(f"{(float(abs(vs1[0] - vs2[0])/(vs1[0] + vs2[0])+1)):.2f}"))
                except:
                    print(model_abberviation, organ, dice, iou)
                i += 1

            # Average row
            avg_dice = df.query(f"Model == '{model_abberviation}'")["Dice"].mean()
            avg_iou = df.query(f"Model == '{model_abberviation}'")["IoU"].mean()
            avg_vs1 = df.query(f"Model == '{model_abberviation}'")["Pred_Volume"].mean()
            avg_vs2 = df.query(f"Model == '{model_abberviation}'")["GT_Volume"].mean()
            table.setItem(i, 0, QTableWidgetItem(f"{avg_dice:.2f}"))
            table.setItem(i, 1, QTableWidgetItem(f"{avg_iou:.2f}"))
            table.setItem(i, 2, QTableWidgetItem(f"{abs(avg_vs1 - avg_vs2)/(avg_vs1 + avg_vs2)+1:.2f}"))

            table.resizeColumnsToContents()
            table.setStyleSheet("color: #fff; background: #232946; font-size: 12px; padding")
            model_vbox.addWidget(table)
            # Wrap the model_vbox in a QWidget
            model_widget = QWidget(self)
            model_widget.setLayout(model_vbox)
            models_area.addWidget(model_widget, 1)
            self.model_widgets.append(model_widget)
            # Load and show all files for this model
            for file in organ_files[self.selected_organ][model]:
                nii_path = os.path.join(os.path.dirname(__file__), self.selected_organ, model, file)
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
            btn.clicked.connect(lambda checked, organ=self.selected_organ, m=model: self.show_slices_view(organ, m))
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

        # Gather meshes and mesh_properties from pv_actors
        meshes = {}
        mesh_properties = {}
        colors = {}
        opacities = {}
        if hasattr(self, 'pv_actors') and model in self.pv_actors:
            for file, actor in self.pv_actors[model].items():
                mesh = actor.GetMapper().GetInputAsDataSet()
                color = actor.GetProperty().GetColor()
                opacity = actor.GetProperty().GetOpacity()
                meshes[file] = mesh
                mesh_properties[file] = {
                    'color': color,
                    'opacity': opacity
                }
                colors[file] = (*color, 0.45)
                opacities[file] = opacity
        else:
            # fallback default color/opacity
            for f in organ_files:
                colors[f] = (0, 0.5, 1, 1)
                opacities[f] = 0.5

        from slicer import SegmentationViewer
        self.slice_viewer = QWidget(self)
        layout = QHBoxLayout(self.slice_viewer)
        # Slices viewer with meshes and mesh_properties
        seg_viewer = SegmentationViewer(scan_file, organ_files, colors, opacities, meshes=meshes, mesh_properties=mesh_properties)
        layout.addWidget(seg_viewer, 2)
        # Add back button
        back_btn = QPushButton("        ← Back to models        ", self.slice_viewer)
        back_btn.setStyleSheet("font-size: 16px; color: #fff; background: #0078d7; border-radius: 8px; margin-bottom: 8px;")
        back_btn.clicked.connect(self.hide_slices_view)
        layout.addWidget(back_btn, )
        self.slice_viewer_model = model
        self.view_layout.addWidget(self.slice_viewer)
        self.slice_viewer.show()
        # Update sidebar for slice view: organ label, model label, and part controls directly (no tree/dropdown)
        for i in reversed(range(self.sidebar_layout.count())):
            widget = self.sidebar_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        organ_label = QLabel(self.selected_organ.capitalize(), self)
        organ_label.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold; margin: 16px 0 8px 0;")
        organ_label.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(organ_label)
        model_label = QLabel(model.capitalize(), self)
        model_label.setStyleSheet("color: #fff; font-size: 20px; font-weight: bold; margin: 8px 0 8px 0;")
        model_label.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(model_label)
        # Add part controls directly for this model, but connect to slice view's SegmentationViewer
        controls = []
        for file in organ_files:
            part_label = QLabel(file[:file.find('.')])
            part_label.setStyleSheet("color: #fff; font-size: 12px; margin-right: 8px; margin-left: 0px;")
            view_checkbox = QCheckBox("View")
            view_checkbox.setChecked(True)
            view_checkbox.setStyleSheet("QCheckBox { color: #fff; } QCheckBox::indicator { width: 18px; height: 18px; } QCheckBox::indicator:checked { background-color: #0078d7; border-radius: 4px; border: 2px solid #fff; } QCheckBox::indicator:unchecked { background-color: #232946; border-radius: 4px; border: 2px solid #fff; } QCheckBox:hover { background: #3a4a6a; }")
            opacity_slider = QSlider(Qt.Horizontal)
            opacity_slider.setMinimum(0)
            opacity_slider.setMaximum(100)
            opacity_slider.setValue(int(opacities[file]*100))
            opacity_slider.setFixedWidth(80)
            color_btn = QPushButton("Color")
            color_btn.setFixedWidth(50)
            # Connect controls to seg_viewer.actors
            def toggle_slice_actor(checked, f=file):
                actor = seg_viewer.actors.get(f)
                if actor:
                    actor.SetVisibility(checked)
            def set_slice_opacity(val, f=file):
                actor = seg_viewer.actors.get(f)
                if actor:
                    actor.GetProperty().SetOpacity(val/100.0)
            def pick_slice_color(_, f=file, btn=color_btn):
                actor = seg_viewer.actors.get(f)
                if actor:
                    color = QColorDialog.getColor(parent=btn)
                    if color.isValid():
                        rgb = color.getRgb()[:3]
                        actor.GetProperty().SetColor([c/255.0 for c in rgb])
                        # Also update mask overlay color in slice viewers
                        rgba = tuple([c/255.0 for c in rgb] + [0.45])
                        seg_viewer.colors[f] = rgba
                        for sv in [seg_viewer.axial_view, seg_viewer.sagittal_view, seg_viewer.coronal_view]:
                            sv.mask_colors[f] = rgba
                            sv.update_slice(sv.slider.value())
            view_checkbox.stateChanged.connect(lambda checked, f=file: toggle_slice_actor(checked, f))
            opacity_slider.valueChanged.connect(lambda val, f=file: set_slice_opacity(val, f))
            color_btn.clicked.connect(lambda _, f=file, btn=color_btn: pick_slice_color(_, f, btn))
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0,0,0,0)
            row_layout.addWidget(part_label)
            row_layout.addWidget(view_checkbox)
            row_layout.addWidget(opacity_slider)
            row_layout.addWidget(color_btn)
            self.sidebar_layout.addWidget(row)

    def hide_slices_view(self):
        if self.slice_viewer:
            self.slice_viewer.hide()
            self.view_layout.removeWidget(self.slice_viewer)
            self.slice_viewer.deleteLater()
            self.slice_viewer = None
        # Restore sidebar to normal: organ label and all model trees
        for i in reversed(range(self.sidebar_layout.count())):
            widget = self.sidebar_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        # Add the return button at the top
        self.sidebar_layout.addWidget(self.return_btn)
        self.sidebar_layout.addWidget(self.organ_label_widget)
        for model_label, tree_widget in self.model_tree_widgets:
            if model_label is not None:
                self.sidebar_layout.addWidget(model_label)
            self.sidebar_layout.addWidget(tree_widget)
        # Show all model viewers
        for w in self.model_widgets:
            w.show()

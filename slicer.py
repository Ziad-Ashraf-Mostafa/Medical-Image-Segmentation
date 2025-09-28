# seg_viewer_pyside.py
import sys
import nibabel as nib
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6 import QtWidgets, QtCore
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class SliceViewer(QtWidgets.QWidget):
    """
    Widget to display one slice view (axial/sagittal/coronal) with a slider.
    Displays full slice and overlays RGBA masks.
    """
    def __init__(self, volume, masks=None, mask_colors=None, orientation="axial", parent=None):
        super().__init__(parent)
        self.volume = volume
        self.masks = masks or {}
        self.mask_colors = mask_colors or {}
        self.orientation = orientation

        self.fig = Figure(figsize=(4, 3), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.axis("off")

        if orientation == "axial":
            self.max_idx = volume.shape[2] - 1
        elif orientation == "sagittal":
            self.max_idx = volume.shape[0] - 1
        elif orientation == "coronal":
            self.max_idx = volume.shape[1] - 1
        else:
            raise ValueError("orientation must be 'axial'|'sagittal'|'coronal'")

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(self.max_idx)
        self.slider.setValue(self.max_idx // 2)
        self.slider.setFixedHeight(18)
        self.slider.setMaximumWidth(340)
        self.slider.valueChanged.connect(self.update_slice)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        layout.addWidget(self.canvas, stretch=0)
        layout.addWidget(self.slider, alignment=QtCore.Qt.AlignCenter)

        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.update_slice(self.slider.value())

    def update_slice(self, idx):
        if isinstance(idx, (QtCore.QModelIndex, object)):
            try:
                idx = int(self.slider.value())
            except Exception:
                idx = int(idx)

        self.ax.clear()

        if self.orientation == "axial":
            img = self.volume[:, :, idx]
            mask_slices = {name: mask[:, :, idx] for name, mask in self.masks.items()}
        elif self.orientation == "sagittal":
            img = self.volume[idx, :, :]
            mask_slices = {name: mask[idx, :, :] for name, mask in self.masks.items()}
        else:
            img = self.volume[:, idx, :]
            mask_slices = {name: mask[:, idx, :] for name, mask in self.masks.items()}

        img = np.rot90(img)
        self.ax.imshow(img, cmap="gray", origin="lower", aspect="auto")

        h, w = img.shape
        overlay = np.zeros((h, w, 4), dtype=float)

        for name, mask_slice in mask_slices.items():
            ms = np.rot90(mask_slice)
            if ms.shape != (h, w):
                mh, mw = ms.shape
                new_ms = np.zeros((h, w), dtype=bool)
                copy_h = min(h, mh)
                copy_w = min(w, mw)
                new_ms[:copy_h, :copy_w] = ms[:copy_h, :copy_w] > 0.5
                ms = new_ms
            else:
                ms = ms > 0.5
            if not np.any(ms):
                continue
            color = self.mask_colors.get(name, (1.0, 0.0, 0.0, 0.35))
            overlay[ms, :3] = color[:3]
            overlay[ms, 3] = np.maximum(overlay[ms, 3], color[3])

        if overlay[..., 3].sum() > 0:
            self.ax.imshow(overlay, origin="lower", aspect="auto", interpolation="none")

        self.ax.set_position([0, 0, 1, 1])
        self.ax.axis("off")
        self.canvas.draw_idle()


class SegmentationViewer(QtWidgets.QWidget):
    def __init__(self, scan_file, organ_files, colors, opacities=None, parent=None):
        super().__init__(parent)

        self.scan = nib.load(scan_file).get_fdata()
        self.organs = {organ: nib.load(path).get_fdata() for organ, path in organ_files.items()}

        self.colors = {k: (v[0], v[1], v[2], 0.45) if len(v) == 3 else v for k, v in colors.items()}
        self.opacities = opacities or {name: 0.5 for name in self.organs.keys()}

        mask_colors = {}
        for name in organ_files.keys():
            if name in self.colors:
                mask_colors[name] = self.colors[name]
            else:
                found = None
                for ck in self.colors:
                    if ck.lower() == name.lower():
                        found = self.colors[ck]
                        break
                mask_colors[name] = found if found is not None else (1.0, 0.0, 0.0, 0.35)

        # Slice viewers with reduced width for axial/sagittal
        self.axial_view = SliceViewer(self.scan, self.organs, mask_colors, orientation="axial")
        self.sagittal_view = SliceViewer(self.scan, self.organs, mask_colors, orientation="sagittal")
        self.coronal_view = SliceViewer(self.scan, self.organs, mask_colors, orientation="coronal")

        self.axial_view.canvas.setMinimumSize(250, 180)     # narrower axial
        self.sagittal_view.canvas.setMinimumSize(250, 180)  # narrower sagittal
        self.coronal_view.setMaximumWidth(360)   # keep coronal bigger (ok already)

        self.plotter = QtInteractor(self)
        self.plotter.set_background("black")
        self.plotter.interactor.setMinimumWidth(100)

        self.actors = {}
        for organ, mask in self.organs.items():
            try:
                mask_bool = (mask > 0.5).astype(np.uint8)
                grid = pv.wrap(mask_bool)
                surf = grid.contour([0.5])
                color = self.colors.get(organ, (1.0, 0.5, 0.0, 0.5))[:3]
                actor = self.plotter.add_mesh(
                    surf, color=color, opacity=self.opacities.get(organ, 0.5), name=organ
                )
                self.actors[organ] = actor
            except Exception as e:
                print(f"[warn] mesh failed for {organ}: {e}")

        grid = QtWidgets.QGridLayout(self)
        grid.setSpacing(6)
        grid.setContentsMargins(6, 6, 6, 6)

        grid.setColumnStretch(0, 2)  # left column (axial+sagittal) smaller
        grid.setColumnStretch(1, 3)  # right column (3D+coronal) slightly larger

        grid.setRowStretch(0, 2)
        grid.setRowStretch(1, 3)

        grid.addWidget(self.axial_view, 0, 0)
        grid.addWidget(self.plotter.interactor, 0, 1)
        grid.addWidget(self.sagittal_view, 1, 0)
        grid.addWidget(self.coronal_view, 1, 1)

        self.setLayout(grid)


if __name__ == "__main__":
    scan_file = "scan.nii.gz"
    organ_files = {
        "Liver": r"E:\Ziad\Anatomy tasks\task1-image segmentaton\liver\Swin UNETR\liver.nii.gz",
        "Spleen": r"E:\Ziad\Anatomy tasks\task1-image segmentaton\liver\Swin UNETR\spleen.nii.gz",
        "Stomach": r"E:\Ziad\Anatomy tasks\task1-image segmentaton\stomach\Swin UNETR\stomach.nii.gz",
    }
    colors = {
        "Liver": (1.0, 0.0, 0.0, 0.45),
        "Spleen": (0.0, 1.0, 0.0, 0.45),
        "Stomach": (0.0, 0.0, 1.0, 0.45),
    }
    opacities = {"Liver": 0.45, "Spleen": 0.6, "Stomach": 0.4}

    app = QtWidgets.QApplication(sys.argv)
    viewer = SegmentationViewer(scan_file, organ_files, colors, opacities)
    viewer.resize(1200, 900)
    viewer.show()
    sys.exit(app.exec())

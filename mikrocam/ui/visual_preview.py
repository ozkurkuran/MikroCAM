"""Display canonical, individual-group and combined interlace previews."""
import builtins
import gettext
from PyQt6 import QtCore, QtGui, QtWidgets
from mikrocam.core.visual_preview import preview_images
from mikrocam.core.interlace_job import VisualInterlaceJob

_ = getattr(builtins, '_', gettext.gettext)


class CanvasPreview(QtWidgets.QLabel):
    """Fit the entire image to the available viewport after every dock resize."""
    def __init__(self) -> None:
        super().__init__()
        self.original = None
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 140)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Expanding)

    def set_image(self, image: QtGui.QImage) -> None:
        self.original = QtGui.QPixmap.fromImage(image)
        self._fit()

    def _fit(self) -> None:
        if self.original is not None:
            self.setPixmap(self.original.scaled(self.contentsRect().size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.FastTransformation))

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._fit(); super().resizeEvent(event)


class VisualPreview(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.job = None
        self.images = None
        self.zoom_window = None
        self.tabs = QtWidgets.QTabWidget()
        self.labels = []
        for title in (_('Kaynak görünümü'), _('Ana maske'), _('Tek geçiş'), _('Birleşim')):
            label = CanvasPreview()
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.tabs.addTab(label, title); self.labels.append(label)
        self.group = QtWidgets.QSpinBox(); self.group.setRange(1, 8)
        self.group.valueChanged.connect(self.refresh)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tabs); layout.addWidget(self.group)
        zoom = QtWidgets.QPushButton(_('Önizlemeyi yakınlaştır…'))
        zoom.clicked.connect(self.open_zoom); layout.addWidget(zoom)

    def set_job(self, job: VisualInterlaceJob, images: dict | None = None) -> None:
        self.job = job
        self.images = images if images is not None else preview_images(job.mask, job.interlace.count)
        self.group.setMaximum(job.interlace.count)
        if self.images['source'] is None and self.tabs.currentIndex() == 0: self.tabs.setCurrentIndex(1)
        self.refresh()

    def refresh(self) -> None:
        if self.job is None: return
        views = (self.images['source'], self.images['master'],
                 self.images['groups'][self.group.value() - 1], self.images['combined'])
        for label, array in zip(self.labels, views):
            if array is None:
                label.original = None; label.clear()
                label.setText(_('Kaynak kaydın içinde. Görünüm için maskeyi yeniden hazırlayabilirsiniz.'))
                label.setWordWrap(True)
                continue
            label.setText('')
            height, width, _channels = array.shape
            qimage = QtGui.QImage(array.data, width, height, width * 3, QtGui.QImage.Format.Format_RGB888).copy()
            label.set_image(qimage)


    def open_zoom(self) -> None:
        original = self.labels[self.tabs.currentIndex()].original
        if original is None: return
        if self.zoom_window is not None: self.zoom_window.close()
        self.zoom_window = PreviewZoom(original, self)
        self.zoom_window.show()


class PreviewZoom(QtWidgets.QDialog):
    """Magnify the immutable preview thumbnail, never the manufacturing mask."""
    def __init__(self, original: QtGui.QPixmap, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(_('Önizleme yakınlaştırması'))
        self.resize(640, 480)
        self.original = original
        self.image = QtWidgets.QLabel()
        self.scroll = QtWidgets.QScrollArea(); self.scroll.setWidget(self.image)
        self.scale = QtWidgets.QSpinBox(); self.scale.setRange(25, 800); self.scale.setSuffix('%')
        self.scale.setValue(100); self.scale.valueChanged.connect(self.refresh)
        layout = QtWidgets.QVBoxLayout(self)
        note = QtWidgets.QLabel(_('Bu görünüm önizlemeyi büyütür. Çıktı çözünürlüğünü değiştirmez; büyük görüntülerde küçük önizleme kullanılır.'))
        note.setWordWrap(True)
        layout.addWidget(note); layout.addWidget(self.scale); layout.addWidget(self.scroll)
        self.refresh()

    def refresh(self) -> None:
        factor = self.scale.value() / 100
        size = QtCore.QSize(max(1, round(self.original.width() * factor)), max(1, round(self.original.height() * factor)))
        self.image.setPixmap(self.original.scaled(size, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                                 QtCore.Qt.TransformationMode.FastTransformation))
        self.image.resize(size)

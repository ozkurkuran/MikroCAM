"""Thin source/measurement controls and revision-aware visual job dock."""
import builtins
from dataclasses import replace
import gettext
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets
from mikrocam.core.visual import PreparationSettings
from mikrocam.core.interlace_job import InterlaceSettings
from mikrocam.core.placement import Placement
from .visual_preview import VisualPreview
from .visual_worker import VisualWorker
from .visual_errors import visual_error_text
from .laser_recipe import LaserRecipeEditor

_ = getattr(builtins, '_', gettext.gettext)


def _decimal(minimum: float, maximum: float, value: float, decimals: int = 4):
    widget = QtWidgets.QDoubleSpinBox()
    widget.setDecimals(decimals); widget.setRange(minimum, maximum); widget.setValue(value)
    return widget


def _integer(minimum: int, maximum: int, value: int):
    widget = QtWidgets.QSpinBox(); widget.setRange(minimum, maximum); widget.setValue(value)
    return widget


class VisualInterlacePanel(QtWidgets.QDockWidget):
    def __init__(self, host: object) -> None:
        super().__init__(_('Görsel satır serpiştirme'), host.parent_widget())
        self.setObjectName('mikrocam_visual_interlace')
        self.host = host
        self.source = self.job = self.plan = self.worker = None
        self.revision = 1
        self._updating = False
        self._values = {'width': 30.0, 'height': 18.0, 'dpi': 508.0, 'spot': 0.0, 'x': 0.0, 'y': 0.0}
        self._edited_numbers = set()
        self._previous_rotation = 0
        self._build()
        self._sync()
        QtWidgets.QApplication.instance().aboutToQuit.connect(self.shutdown)

    def _build(self) -> None:
        scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget(); layout = QtWidgets.QVBoxLayout(content)
        self.source_label = QtWidgets.QLabel(_('Kaynak seçilmedi.'))
        self.source_label.setWordWrap(True); layout.addWidget(self.source_label)
        self.open_button = QtWidgets.QPushButton(_('Resim / SVG / PDF aç…'))
        self.open_button.clicked.connect(self._choose_source); layout.addWidget(self.open_button)
        self.project_sources = QtWidgets.QComboBox()
        self.project_sources.addItems(self.host.source_names())
        layout.addWidget(self.project_sources)
        self.project_open_button = QtWidgets.QPushButton(_('Projedeki görsel işi aç'))
        self.project_open_button.clicked.connect(self.load_project_source)
        layout.addWidget(self.project_open_button)
        self._build_geometry_controls(layout)
        self._build_recipe_controls(layout)
        self.page = _integer(1, 1, 1)
        self.width = _decimal(.0001, 100000, 30)
        self.height = _decimal(.0001, 100000, 18)
        self.dpi = _decimal(.01, 100000, 508, 2)
        self.threshold = _integer(1, 255, 128)
        self.invert = QtWidgets.QCheckBox(_('Renkleri ters çevir'))
        self.mirror_x = QtWidgets.QCheckBox(_('Yatay ayna'))
        self.mirror_y = QtWidgets.QCheckBox(_('Dikey ayna'))
        self.rotation = QtWidgets.QComboBox(); self.rotation.addItems(['0°', '90°', '180°', '270°'])
        self.count = _integer(1, 8, 3)
        self.order = QtWidgets.QComboBox(); self.order.addItems([_('Ardışık'), _('Karışık')])
        self.rounds = _integer(1, 999, 1)
        self.vary = QtWidgets.QCheckBox(_('Her turda geçiş sırasını değiştir'))
        self.delay = _integer(0, 600000, 0)
        self.delay.setToolTip(_('Bekleme işte saklanır; LightBurn desteği doğrulanmadan uygulanmış sayılmaz.'))
        self.spot = _decimal(0, 1000, 0)
        self.spot.setSpecialValueText(_('Bilinmiyor'))
        self.x = _decimal(-100000, 100000, 0); self.y = _decimal(-100000, 100000, 0)
        form = QtWidgets.QFormLayout(); layout.addLayout(form)
        for text, widget in (( _('Sayfa / kare'), self.page), (_('Genişlik (mm)'), self.width),
                             (_('Yükseklik (mm)'), self.height), (_('Çıktı DPI'), self.dpi),
                             (_('Siyah-beyaz eşiği'), self.threshold), (_('Dönüş'), self.rotation),
                             (_('Serpiştirme sayısı (1 = kapalı)'), self.count), (_('Geçiş sırası'), self.order),
                             (_('Toplam tur'), self.rounds), (_('Geçişler arası bekleme (ms)'), self.delay),
                             (_('Spot çapı (mm)'), self.spot), (_('X (mm)'), self.x), (_('Y (mm)'), self.y)):
            form.addRow(text, widget)
        for checkbox in (self.invert, self.mirror_x, self.mirror_y, self.vary): layout.addWidget(checkbox)
        self.prepare_button = QtWidgets.QPushButton(_('Maskeyi hazırla'))
        self.cancel_button = QtWidgets.QPushButton(_('İptal'))
        self.save_button = QtWidgets.QPushButton(_('İşi JSON olarak kaydet…'))
        self.load_button = QtWidgets.QPushButton(_('JSON işi aç…'))
        self.png_button = QtWidgets.QPushButton(_('Geçiş PNG paketini kaydet…'))
        self.project_button = QtWidgets.QPushButton(_('MikroCAM projesine ekle'))
        self.lightburn_button = QtWidgets.QPushButton(_('LightBurn projesi (.lbrn2)'))
        self.lightburn_button.setToolTip(_('Doğrulanmış LightBurn sürüm/cihaz profili bekleniyor.'))
        for button in (self.prepare_button, self.cancel_button, self.save_button, self.load_button,
                       self.png_button, self.project_button, self.lightburn_button): layout.addWidget(button)
        self.prepare_button.clicked.connect(self.prepare); self.cancel_button.clicked.connect(self.cancel)
        self.save_button.clicked.connect(self._choose_save); self.load_button.clicked.connect(self._choose_load)
        self.png_button.clicked.connect(self._choose_png); self.project_button.clicked.connect(self.save_to_project)
        self.preview = VisualPreview(); layout.addWidget(self.preview)
        self.pass_list = QtWidgets.QListWidget(); self.pass_list.setMaximumHeight(150); layout.addWidget(self.pass_list)
        self.status = QtWidgets.QLabel(); self.status.setWordWrap(True); layout.addWidget(self.status)
        for widget in (self.threshold, self.count, self.rounds, self.delay):
            widget.valueChanged.connect(self._dirty)
        for widget in (self.invert, self.mirror_x, self.mirror_y, self.vary): widget.toggled.connect(self._dirty)
        self.order.currentIndexChanged.connect(self._dirty)
        self.rotation.currentIndexChanged.connect(self._rotate_changed)
        self.width.valueChanged.connect(self._width_changed); self.height.valueChanged.connect(self._height_changed)
        self.page.valueChanged.connect(self._page_changed)
        self._wire_measurements()
        scroll.setWidget(content); self.setWidget(scroll)

    def _wire_measurements(self) -> None:
        for name in self._values:
            widget = getattr(self, name)
            if name not in ('width', 'height'):
                widget.valueChanged.connect(lambda value, key=name: self._numeric_changed(key, value))
            widget.lineEdit().textEdited.connect(lambda _text, key=name: self._edited_numbers.add(key))
            widget.editingFinished.connect(lambda key=name, control=widget: self._commit_measurement(key, control))

    def _numeric_changed(self, name: str, value: float) -> None:
        if self._updating: return
        self._values[name] = value
        self._measurement_tooltips(); self._dirty()

    def _commit_measurement(self, name: str, widget) -> None:
        if name not in self._edited_numbers: return
        self._edited_numbers.discard(name)
        if self._values[name] == widget.value(): return
        if name == 'width': self._width_changed()
        elif name == 'height': self._height_changed()
        else: self._numeric_changed(name, widget.value())

    def _measurement_tooltips(self) -> None:
        for name, value in self._values.items():
            getattr(self, name).setToolTip(_('İşte kullanılacak kesin değer: ') + repr(value))

    def _build_recipe_controls(self, layout) -> None:
        direction = QtWidgets.QFormLayout()
        self.bidirectional = QtWidgets.QCheckBox(_('Çift yönlü tarama'))
        self.bidirectional.setChecked(True)
        self.direction_policy = QtWidgets.QComboBox()
        self.direction_policy.addItems([_('LightBurn yönetir'), _('Kaynak satır paritesi (profil doğrulaması gerekir)')])
        self.bidirectional.toggled.connect(self._dirty)
        self.direction_policy.currentIndexChanged.connect(self._dirty)
        direction.addRow(self.bidirectional); direction.addRow(_('Satır yönü'), self.direction_policy)
        layout.addLayout(direction)
        self.recipe_group = QtWidgets.QGroupBox(_('Lazer reçetesi (isteğe bağlı)'))
        self.recipe_group.setCheckable(True); self.recipe_group.setChecked(False)
        self.recipe_editor = LaserRecipeEditor()
        recipe_layout = QtWidgets.QVBoxLayout(self.recipe_group); recipe_layout.addWidget(self.recipe_editor)
        self.recipe_group.toggled.connect(self._dirty); self.recipe_editor.changed.connect(self._dirty)
        layout.addWidget(self.recipe_group)

    def _build_geometry_controls(self, layout) -> None:
        group = QtWidgets.QGroupBox(_('İsteğe bağlı Gerber / poligon kaynağı'))
        form = QtWidgets.QFormLayout(group)
        self.geometry_sources = QtWidgets.QComboBox()
        self.geometry_sources.addItems(getattr(self.host, 'geometry_source_names', lambda: [])())
        form.addRow(_('Kaynak'), self.geometry_sources)
        self.roi = tuple(_decimal(-100000, 100000, v) for v in (0, 0, 30, 18))
        for label, widget in zip(('ROI X min (mm)', 'ROI Y min (mm)', 'ROI X max (mm)', 'ROI Y max (mm)'), self.roi):
            form.addRow(_(label), widget)
        self.geometry_button = QtWidgets.QPushButton(_('Seçilen alanı görsele dönüştür'))
        self.geometry_button.clicked.connect(self.open_geometry_source); form.addRow(self.geometry_button)
        refresh = QtWidgets.QPushButton(_('Proje kaynaklarını yenile'))
        refresh.clicked.connect(self.refresh_sources); form.addRow(refresh)
        layout.addWidget(group)

    def refresh_sources(self) -> None:
        self.project_sources.clear(); self.project_sources.addItems(self.host.source_names())
        self.geometry_sources.clear()
        self.geometry_sources.addItems(getattr(self.host, 'geometry_source_names', lambda: [])())
        self._sync()

    def open_geometry_source(self) -> None:
        if self.worker is not None or not self.geometry_sources.currentText(): return
        try:
            name = self.geometry_sources.currentText()
            geometry, units = self.host.geometry_source_snapshot(name)
            roi = tuple(widget.value() for widget in self.roi)
            self._dirty(); self._start('geometry', (geometry, units, roi, name))
        except (ValueError, OSError) as error: self._show_error(str(error))

    def _dirty(self, *_args) -> None:
        if self._updating: return
        self.revision += 1
        self.cancel()
        self.status.setText(_('Ayarlar değişti. Maskeyi yeniden hazırlayın.'))
        self._sync()

    def _width_changed(self) -> None:
        if not self._updating:
            self._values['width'] = self.width.value()
            self._updating = True
            if self.source and self.source.info.suggested_size_mm:
                w, h = self.source.info.suggested_size_mm
                ratio = w/h if self.rotation.currentIndex() % 2 else h/w
                self._values['height'] = self._values['width'] * ratio
                self.height.setValue(self._values['height'])
            self._updating = False; self._measurement_tooltips(); self._dirty()

    def _height_changed(self) -> None:
        if not self._updating:
            self._values['height'] = self.height.value()
            self._updating = True
            if self.source and self.source.info.suggested_size_mm:
                w, h = self.source.info.suggested_size_mm
                ratio = h/w if self.rotation.currentIndex() % 2 else w/h
                self._values['width'] = self._values['height'] * ratio
                self.width.setValue(self._values['width'])
            self._updating = False; self._measurement_tooltips(); self._dirty()

    def _rotate_changed(self) -> None:
        index = self.rotation.currentIndex()
        swap = (index - self._previous_rotation) % 2
        self._previous_rotation = index
        if self._updating: return
        self._updating = True
        if swap:
            self._values['width'], self._values['height'] = self._values['height'], self._values['width']
            self.width.setValue(self._values['width']); self.height.setValue(self._values['height'])
        self._updating = False; self._measurement_tooltips(); self._dirty()

    def _page_changed(self) -> None:
        if self._updating or self.source is None: return
        self._dirty()
        if self.worker is None: self._start('page', (self.source, self.page.value() - 1))

    def _sync(self) -> None:
        busy = self.worker is not None
        current = self.job is not None and self.job.revision == self.revision
        self.open_button.setEnabled(not busy); self.load_button.setEnabled(not busy)
        self.prepare_button.setEnabled(self.source is not None and not busy)
        self.cancel_button.setEnabled(busy)
        for button in (self.save_button, self.png_button, self.project_button): button.setEnabled(current and not busy)
        self.lightburn_button.setEnabled(False)
        self.geometry_button.setEnabled(not busy and self.geometry_sources.count() > 0)
        self.project_open_button.setEnabled(not busy and self.project_sources.count() > 0)
        self.page.setEnabled(not busy and self.source is not None and self.source.info.page_count > 1)

    def _start(self, operation: str, args: tuple) -> None:
        if self.worker is not None: return
        worker = VisualWorker(operation, self.revision, args, self)
        self.worker = worker
        worker.completed.connect(self._completed); worker.failed.connect(self._failed)
        worker.cancelled.connect(self._cancelled); worker.finished.connect(self._finished)
        self.status.setText(_('İşleniyor…')); self._sync(); worker.start()

    def open_source(self, path: Path) -> None:
        self._dirty(); self._start('open', (Path(path),))

    def prepare(self) -> None:
        if self.source is None or self.worker is not None: return
        try:
            preparation = PreparationSettings(self._values['width'], self._values['height'], self._values['dpi'],
                self.threshold.value(), self.invert.isChecked(), self.mirror_x.isChecked(),
                self.mirror_y.isChecked(), self.rotation.currentIndex(),
                crop_rect=self.job.preparation.crop_rect if self.job and self.job.source == self.source else None)
            settings = InterlaceSettings(self.count.value(), 'mixed' if self.order.currentIndex() else 'sequential',
                round_count=self.rounds.value(), vary_order_each_round=self.vary.isChecked(),
                delay_ms=self.delay.value(), spot_diameter_mm=self._values['spot'] or None,
                bidirectional=self.bidirectional.isChecked(),
                direction_policy='source_row_parity' if self.direction_policy.currentIndex() else 'lightburn_managed')
            placement = replace(self.job.placement if self.job else Placement(), translation=(self._values['x'], self._values['y']))
            recipe = self.recipe_editor.get_recipe() if self.recipe_group.isChecked() else None
            self._start('prepare', (self.source, preparation, settings, placement, recipe))
        except (ValueError, OSError) as error: self._show_error(str(error))

    def _current_job(self) -> bool:
        return self.job is not None and self.job.revision == self.revision and self.worker is None

    def save_job(self, path: Path) -> None:
        if self._current_job(): self._start('save', (self.job, Path(path)))

    def load_job(self, path: Path) -> None:
        self._dirty(); self._start('load', (Path(path),))

    def load_project_source(self) -> None:
        if self.worker is not None or not self.project_sources.currentText(): return
        try:
            payload = self.host.project_payload(self.project_sources.currentText())
            self._dirty(); self._start('project_load', (payload,))
        except (ValueError, OSError) as error: self._show_error(str(error))

    def save_to_project(self) -> None:
        if self._current_job(): self._start('project', (self.job,))

    def _completed(self, revision: int, operation: str, result) -> None:
        if self.sender() is not self.worker or revision != self.revision or self.worker.is_cancelled(): return
        if operation in ('open', 'page', 'geometry'):
            if operation == 'geometry':
                result, roi = result
                self._updating = True
                self._values.update(x=roi[0], y=roi[1])
                self.x.setValue(roi[0]); self.y.setValue(roi[1]); self._updating = False
            self.source = result
            self._updating = True
            self.page.setMaximum(result.info.page_count); self.page.setValue(result.page_index + 1)
            if result.info.suggested_size_mm:
                dims = result.info.suggested_size_mm
                if operation == 'page' and self.rotation.currentIndex() % 2: dims = dims[::-1]
                self._values.update(width=dims[0], height=dims[1])
                self.width.setValue(self._values['width']); self.height.setValue(self._values['height'])
            if operation in ('open', 'geometry'):
                self.rotation.setCurrentIndex(0); self.mirror_x.setChecked(False); self.mirror_y.setChecked(False)
            self._updating = False; self._measurement_tooltips()
            self.source_label.setText(f'{result.name} — {result.info.kind} — {result.page_index + 1}/{result.info.page_count}')
            self.status.setText(_('Kaynak hazır. Ölçüyü kontrol edip maskeyi hazırlayın.'))
        elif operation in ('prepare', 'load', 'project_load'):
            self.job, self.plan = result[:2]; self.source = self.job.source
            if operation in ('load', 'project_load'): self._restore_controls()
            self.preview.set_job(self.job, result[2]); self._show_plan()
        elif operation == 'project':
            try: self.host.publish_payload(self.job, result)
            except Exception as error:
                self._show_error('PROJECT_ATTACH_FAILED: ' + str(error)); return
            self.project_sources.clear(); self.project_sources.addItems(self.host.source_names())
            self.status.setText(_('İş projenin içine eklendi. MikroCAM projesini kaydedebilirsiniz.'))
        else: self.status.setText(_('Kaydedildi: ') + str(result))

    def _restore_controls(self) -> None:
        self._updating = True
        p, s = self.job.preparation, self.job.interlace
        self._values.update(width=p.requested_width_mm, height=p.requested_height_mm, dpi=p.requested_dpi,
                            spot=s.spot_diameter_mm or 0, x=self.job.placement.translation[0], y=self.job.placement.translation[1])
        for widget, value in ((self.width, p.requested_width_mm), (self.height, p.requested_height_mm),
            (self.dpi, p.requested_dpi), (self.threshold, p.threshold), (self.count, s.count),
            (self.rounds, s.round_count), (self.delay, s.delay_ms), (self.spot, s.spot_diameter_mm or 0)):
            widget.setValue(value)
        self.rotation.setCurrentIndex(p.quarter_turns); self.order.setCurrentIndex(s.order_mode == 'mixed')
        self.invert.setChecked(p.invert); self.mirror_x.setChecked(p.mirror_x); self.mirror_y.setChecked(p.mirror_y)
        self.vary.setChecked(s.vary_order_each_round)
        self.bidirectional.setChecked(s.bidirectional)
        self.direction_policy.setCurrentIndex(s.direction_policy == 'source_row_parity')
        self.recipe_group.setChecked(self.job.laser_recipe is not None)
        if self.job.laser_recipe is not None: self.recipe_editor.set_recipe(self.job.laser_recipe)
        self.page.setMaximum(self.source.info.page_count); self.page.setValue(self.source.page_index + 1)
        self.x.setValue(self.job.placement.translation[0]); self.y.setValue(self.job.placement.translation[1])
        self._updating = False; self._measurement_tooltips()
        self.source_label.setText(self.source.name)

    def _show_plan(self) -> None:
        self.pass_list.clear()
        for p in self.plan.passes:
            label = _('etkin') if p.enabled else _('boş — atlanır')
            self.pass_list.addItem(f'{p.round_index + 1}.{p.sequence_index + 1}  '+_('Grup')+f' {p.group_index}  {p.active_row_count} '+_('satır')+f'  {label}')
        grid = self.job.mask.grid
        text = f'{grid.width_px} × {grid.height_px} px | {grid.canvas_width_mm:g} × {grid.canvas_height_mm:g} mm\n'
        text += _('Etkin geçiş: ')+str(self.plan.active_pass_count)+_(' · İstenen toplam bekleme (ms): ')+str(self.plan.total_delay_ms)
        text += '\n'+_('Toplam süre: LightBurn önizlemesinde hesaplanacak.')
        if self.plan.pitch_below_spot:
            text += '\n'+_('Satır aralığı spot çapından küçük, serpiştirmenin soğutma etkisi sınırlı olabilir.')
        self.status.setText(text)

    def _show_error(self, message: str) -> None:
        self.status.setText(visual_error_text(message)); self.status.setToolTip(message)

    def _failed(self, revision: int, message: str) -> None:
        if self.sender() is self.worker and revision == self.revision: self._show_error(message)

    def _cancelled(self, revision: int) -> None:
        if self.sender() is self.worker and revision == self.revision: self.status.setText(_('İptal edildi.'))

    def _finished(self) -> None:
        if self.sender() is not self.worker: return
        worker, self.worker = self.worker, None
        worker.deleteLater(); self._sync()

    def cancel(self) -> None:
        if self.worker is not None: self.worker.cancel()

    def shutdown(self) -> None:
        if self.worker is not None:
            self.worker.cancel(); self.worker.wait()
            self.worker.deleteLater(); self.worker = None
        self._sync()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.cancel(); super().closeEvent(event)

    def _choose_source(self) -> None:
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(self, _('Kaynak aç'), '',
            _('Görseller (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.gif *.svg *.pdf)'))
        if path: self.open_source(Path(path))

    def _choose_save(self) -> None:
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(self, _('İşi kaydet'), '', _('JSON (*.json)'))
        if path: self.save_job(Path(path))

    def _choose_load(self) -> None:
        path, _filter = QtWidgets.QFileDialog.getOpenFileName(self, _('İşi aç'), '', _('JSON (*.json)'))
        if path: self.load_job(Path(path))

    def _choose_png(self) -> None:
        if not self._current_job(): return
        path, _filter = QtWidgets.QFileDialog.getSaveFileName(self, _('Geçiş PNG paketi'), '', _('ZIP (*.zip)'))
        if path: self._start('png', (self.job, self.plan, Path(path)))


def open_visual_interlace(app: object) -> VisualInterlacePanel:
    from mikrocam.bridge.visual_host import VisualHost
    host = VisualHost(app)
    panel = host.existing_panel()
    if panel is None:
        panel = VisualInterlacePanel(host)
        host.parent_widget().addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, panel)
        host.remember_panel(panel)
    panel.show(); panel.raise_()
    return panel

"""Interfaz de escritorio (PySide6) para inspeccionar los RBH/VRAM de Cartman."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from .binfile import BinFile, RangeError, hexdump
from .glview import GLView
from .report import build_report, save_report
from .vram import FORMATS, PALETTE_FORMATS, decode_preview

# slot -> (nombre en pantalla, nombre de archivo esperado)
SLOTS = {
    "vehicle_rbh": ("Jeep · modelo", "cartman.rbh"),
    "vehicle_vram": ("Jeep · textura", "cartman.vram"),
    "character_rbh": ("Personaje · modelo", "cartman_anim.rbh"),
    "character_vram": ("Personaje · textura", "cartman_anim.vram"),
}
PROFILES = {
    "Cartman Jeep": ("vehicle_rbh", "vehicle_vram"),
    "Cartman Character": ("character_rbh", "character_vram"),
}
HEX_WINDOW = 4096


def _parse_int(text: str) -> int:
    return int(text.strip(), 0)


class _Signals(QtCore.QObject):
    done = QtCore.Signal(str, object)


class _ReportJob(QtCore.QRunnable):
    """Análisis fuera del hilo de la interfaz."""

    def __init__(self, slot: str, path: str, signals: _Signals):
        super().__init__()
        self.slot, self.path, self.signals = slot, path, signals

    def run(self):
        self.signals.done.emit(self.slot, build_report(self.path))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("South Park Rally · inspector RBH/VRAM")
        self.resize(1400, 850)
        self.paths: dict[str, str] = {}
        self.reports: dict[str, dict] = {}
        self._bins: dict[str, BinFile] = {}
        self._image = None
        self.current = "vehicle_rbh"
        self.pool = QtCore.QThreadPool.globalInstance()
        self.signals = _Signals()
        self.signals.done.connect(self._on_report)

        self._build_toolbar()
        self._build_ui()
        self.log("Listo. Abrí una carpeta con cartman.rbh/.vram y cartman_anim.rbh/.vram, "
                 "o cargá cada archivo con doble clic en la lista.")
        self.log("Aún no hay decodificador de geometría: el formato RBH se está investigando "
                 "(ver docs/RBH_NOTES.md).")

    # --- construcción de la interfaz --------------------------------------
    def _build_toolbar(self):
        tb = self.addToolBar("Principal")
        tb.setMovable(False)

        def act(text, slot, checkable=False, checked=False, tip=""):
            a = QtGui.QAction(text, self)
            a.setCheckable(checkable)
            a.setChecked(checked)
            a.setToolTip(tip or text)
            (a.toggled if checkable else a.triggered).connect(slot)
            tb.addAction(a)
            return a

        act("Abrir carpeta…", self.open_directory)
        tb.addSeparator()
        self.profile = QtWidgets.QComboBox()
        self.profile.addItems(PROFILES)
        self.profile.currentTextChanged.connect(self._on_profile)
        tb.addWidget(self.profile)
        tb.addSeparator()
        act("Reiniciar cámara", lambda: self.gl.reset_camera())
        act("Alámbrico", self._set_wire, checkable=True)
        act("Grilla", self._set_grid, checkable=True, checked=True)
        act("Ejes", self._set_axes, checkable=True, checked=True)
        act("Fondo…", self._pick_bg)
        tb.addSeparator()
        act("Exportar reporte JSON", self.export_report)
        self.obj_action = act("Exportar OBJ", lambda: None,
                              tip="Deshabilitado: todavía no se recuperó geometría")
        self.obj_action.setEnabled(False)

    def _build_ui(self):
        self.gl = GLView()

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["Archivo", "Estado"])
        self.items: dict[str, QtWidgets.QTreeWidgetItem] = {}
        for slot, (label, fname) in SLOTS.items():
            it = QtWidgets.QTreeWidgetItem([f"{label} ({fname})", "sin cargar"])
            it.setData(0, QtCore.Qt.UserRole, slot)
            self.tree.addTopLevelItem(it)
            self.items[slot] = it
        self.tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.tree.itemClicked.connect(lambda it, _c: self._select(it.data(0, QtCore.Qt.UserRole)))
        self.tree.itemDoubleClicked.connect(lambda it, _c: self._open_single(it.data(0, QtCore.Qt.UserRole)))

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self._build_hex_tab(), "Hex")
        self.tabs.addTab(self._build_tags_tab(), "Etiquetas")
        self.tabs.addTab(self._build_texture_tab(), "Textura")

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)

        top = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        top.addWidget(self.tree)
        top.addWidget(self.gl)
        top.addWidget(self.tabs)
        top.setSizes([280, 640, 480])
        main = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        main.addWidget(top)
        main.addWidget(self.log_view)
        main.setSizes([700, 150])
        self.setCentralWidget(main)

    def _mono(self, widget):
        widget.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        return widget

    def _build_hex_tab(self):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        row = QtWidgets.QHBoxLayout()
        self.hex_offset = QtWidgets.QLineEdit("0x0")
        go = QtWidgets.QPushButton("Ir")
        go.clicked.connect(self._refresh_hex)
        self.hex_offset.returnPressed.connect(self._refresh_hex)
        row.addWidget(QtWidgets.QLabel("Offset:"))
        row.addWidget(self.hex_offset)
        row.addWidget(go)
        lay.addLayout(row)
        self.hex_view = self._mono(QtWidgets.QPlainTextEdit())
        self.hex_view.setReadOnly(True)
        self.hex_view.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        lay.addWidget(self.hex_view)
        return w

    def _build_tags_tab(self):
        self.tag_table = self._mono(QtWidgets.QTableWidget(0, 4))
        self.tag_table.setHorizontalHeaderLabels(
            ["Etiqueta", "Offset", "16 bytes siguientes", "u32 LE (hipótesis)"])
        self.tag_table.horizontalHeader().setStretchLastSection(True)
        self.tag_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tag_table.cellDoubleClicked.connect(self._jump_to_tag)
        return self.tag_table

    def _build_texture_tab(self):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        warn = QtWidgets.QLabel("EXPERIMENTAL: el formato VRAM no está confirmado. "
                                "La vista previa solo interpreta bytes con los parámetros elegidos.")
        warn.setWordWrap(True)
        lay.addWidget(warn)
        form = QtWidgets.QFormLayout()
        self.tx_w = QtWidgets.QSpinBox(); self.tx_w.setRange(1, 8192); self.tx_w.setValue(256)
        self.tx_h = QtWidgets.QSpinBox(); self.tx_h.setRange(1, 8192); self.tx_h.setValue(256)
        self.tx_off = QtWidgets.QLineEdit("0x0")
        self.tx_fmt = QtWidgets.QComboBox(); self.tx_fmt.addItems(sorted(FORMATS))
        self.tx_fmt.setCurrentText("rgb565")
        self.tx_pal_off = QtWidgets.QLineEdit("0x0")
        self.tx_pal_fmt = QtWidgets.QComboBox(); self.tx_pal_fmt.addItems(PALETTE_FORMATS)
        for label, widget in (("Ancho", self.tx_w), ("Alto", self.tx_h), ("Offset", self.tx_off),
                              ("Formato", self.tx_fmt), ("Offset paleta (pal8)", self.tx_pal_off),
                              ("Formato paleta", self.tx_pal_fmt)):
            form.addRow(label, widget)
        lay.addLayout(form)
        row = QtWidgets.QHBoxLayout()
        b1 = QtWidgets.QPushButton("Vista previa (experimental)")
        b1.clicked.connect(self._preview_texture)
        self.tx_save = QtWidgets.QPushButton("Exportar PNG")
        self.tx_save.setEnabled(False)
        self.tx_save.clicked.connect(self._save_texture)
        row.addWidget(b1); row.addWidget(self.tx_save)
        lay.addLayout(row)
        self.tx_label = QtWidgets.QLabel()
        self.tx_label.setAlignment(QtCore.Qt.AlignCenter)
        scroll = QtWidgets.QScrollArea(); scroll.setWidget(self.tx_label); scroll.setWidgetResizable(True)
        lay.addWidget(scroll, 1)
        return w

    # --- utilidades -------------------------------------------------------
    def log(self, text: str):
        self.log_view.appendPlainText(text)

    def _bin(self, slot: str) -> BinFile | None:
        if slot not in self.paths:
            return None
        if slot not in self._bins:
            try:
                self._bins[slot] = BinFile.open(self.paths[slot])
            except (OSError, ValueError) as e:
                self.log(f"ERROR leyendo {self.paths[slot]}: {e}")
                return None
        return self._bins[slot]

    # --- carga de archivos ------------------------------------------------
    def load_file(self, slot: str, path: str):
        self.paths[slot] = path
        self._bins.pop(slot, None)
        self.items[slot].setText(1, "analizando…")
        self.pool.start(_ReportJob(slot, path, self.signals))

    def _open_single(self, slot: str):
        label, fname = SLOTS[slot]
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, f"Abrir {label}", "", f"{fname};;Todos (*)")
        if path:
            self.load_file(slot, path)

    def open_directory(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Carpeta del juego")
        if not d:
            return
        self.discover(d)

    def discover(self, directory: str):
        by_lower = {}
        for root, _dirs, files in os.walk(directory):
            for f in files:
                by_lower.setdefault(f.lower(), os.path.join(root, f))
        missing = []
        for slot, (_label, fname) in SLOTS.items():
            if fname in by_lower:
                self.load_file(slot, by_lower[fname])
            else:
                missing.append(fname)
        if missing:
            self.log("Faltan en la carpeta: " + ", ".join(missing))

    def _on_report(self, slot: str, report: dict):
        self.reports[slot] = report
        if report["errors"]:
            self.items[slot].setText(1, "error")
            self.log(f"{SLOTS[slot][1]}: " + "; ".join(report["errors"]))
            return
        found = sum(1 for t in report["tags"].values() if t["count"])
        self.items[slot].setText(1, f"{report['size']} bytes · {found} tags")
        self.log(f"{report['file']}: {report['size']} bytes, {found} identificadores candidatos")
        for w in report["warnings"]:
            self.log(f"  aviso: {w}")
        if slot == self.current:
            self._select(slot)

    # --- selección y paneles ----------------------------------------------
    def _on_profile(self, name: str):
        rbh, _vram = PROFILES[name]
        self._select(rbh)
        self.gl.clear_mesh()
        self.statusBar().showMessage(f"{name}: la geometría aún no está decodificada.", 8000)

    def _select(self, slot: str):
        self.current = slot
        self.tree.setCurrentItem(self.items[slot])
        self._refresh_hex()
        self._fill_tags()

    def _refresh_hex(self):
        bf = self._bin(self.current)
        if bf is None:
            self.hex_view.setPlainText("(archivo no cargado)")
            return
        try:
            off = _parse_int(self.hex_offset.text())
            size = min(HEX_WINDOW, max(0, len(bf) - off))
            self.hex_view.setPlainText(hexdump(bf.slice(off, size), off))
        except (ValueError, RangeError) as e:
            self.hex_view.setPlainText(f"Offset inválido: {e}")

    def _fill_tags(self):
        self.tag_table.setRowCount(0)
        rep = self.reports.get(self.current)
        if not rep:
            return
        for tag, info in rep["tags"].items():
            for hit in info["hits"]:
                r = self.tag_table.rowCount()
                self.tag_table.insertRow(r)
                for c, text in enumerate((tag, f"0x{hit['offset']:X}", hit["next16_hex"],
                                          ", ".join(str(v) for v in hit["u32le_after"]))):
                    self.tag_table.setItem(r, c, QtWidgets.QTableWidgetItem(text))

    def _jump_to_tag(self, row: int, _col: int):
        self.hex_offset.setText(self.tag_table.item(row, 1).text())
        self._refresh_hex()
        self.tabs.setCurrentIndex(0)

    # --- textura ----------------------------------------------------------
    def _preview_texture(self):
        bf = self._bin(self.current)
        if bf is None:
            self.log("Seleccioná y cargá un archivo primero.")
            return
        try:
            pal = _parse_int(self.tx_pal_off.text()) if self.tx_fmt.currentText() == "pal8" else None
            img = decode_preview(bf, _parse_int(self.tx_off.text()), self.tx_w.value(),
                                 self.tx_h.value(), self.tx_fmt.currentText(), pal,
                                 self.tx_pal_fmt.currentText())
        except (ValueError, RangeError) as e:
            self.log(f"Vista previa imposible: {e}")
            return
        self._image = img
        qimg = QtGui.QImage(img.tobytes("raw", "RGBA"), img.width, img.height,
                            QtGui.QImage.Format_RGBA8888).copy()
        pix = QtGui.QPixmap.fromImage(qimg)
        if max(pix.width(), pix.height()) < 256:
            pix = pix.scaled(pix.width() * 4, pix.height() * 4, QtCore.Qt.KeepAspectRatio)
        self.tx_label.setPixmap(pix)
        self.tx_save.setEnabled(True)
        self.log("Vista previa de textura generada (EXPERIMENTAL, sin verificar).")

    def _save_texture(self):
        if self._image is None:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Guardar PNG", "textura.png", "PNG (*.png)")
        if path:
            self._image.save(path)
            self.log(f"PNG guardado en {path} (interpretación experimental).")

    # --- varios -----------------------------------------------------------
    def _set_wire(self, on): self.gl.wireframe = on; self.gl.update()
    def _set_grid(self, on): self.gl.show_grid = on; self.gl.update()
    def _set_axes(self, on): self.gl.show_axes = on; self.gl.update()

    def _pick_bg(self):
        c = QtWidgets.QColorDialog.getColor(parent=self)
        if c.isValid():
            self.gl.set_background(c)

    def export_report(self):
        rep = self.reports.get(self.current)
        if not rep:
            self.log("No hay reporte para el archivo seleccionado.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Guardar reporte", f"{rep['file']}.report.json", "JSON (*.json)")
        if path:
            save_report(rep, path)
            self.log(f"Reporte guardado en {path}")


def run(argv=None) -> int:
    app = QtWidgets.QApplication(argv or sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())

"""Viewport OpenGL: órbita, pan, zoom, grilla, ejes, sólido/alámbrico.

Solo dibuja geometría real recuperada de los archivos (set_mesh). Mientras no
haya ninguna, muestra únicamente la grilla y los ejes.
"""
from __future__ import annotations

import math

import numpy as np
from OpenGL import GL as gl
from OpenGL import GLU as glu
from PySide6 import QtCore, QtGui, QtOpenGLWidgets


class GLView(QtOpenGLWidgets.QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.background = (0.12, 0.12, 0.14)
        self.wireframe = False
        self.show_grid = True
        self.show_axes = True
        self._positions: np.ndarray | None = None  # (N, 3) float32
        self._indices: np.ndarray | None = None    # (M, 3) uint32
        self._last = QtCore.QPoint()
        self.reset_camera()

    # --- cámara -----------------------------------------------------------
    def reset_camera(self):
        self.yaw, self.pitch, self.dist = 0.6, 0.45, 8.0
        self.target = np.zeros(3)
        self.update()

    def frame_mesh(self):
        if self._positions is None or len(self._positions) == 0:
            return
        lo, hi = self._positions.min(axis=0), self._positions.max(axis=0)
        self.target = ((lo + hi) / 2).astype(float)
        radius = float(np.linalg.norm(hi - lo)) / 2 or 1.0
        self.dist = radius * 2.5
        self.update()

    # --- geometría --------------------------------------------------------
    def set_mesh(self, positions: np.ndarray, indices: np.ndarray):
        positions = np.ascontiguousarray(positions, dtype=np.float32)
        indices = np.ascontiguousarray(indices, dtype=np.uint32)
        if positions.ndim != 2 or positions.shape[1] != 3:
            raise ValueError("positions debe ser (N, 3)")
        if indices.ndim != 2 or indices.shape[1] != 3:
            raise ValueError("indices debe ser (M, 3)")
        if indices.size and int(indices.max()) >= len(positions):
            raise ValueError("índices fuera de rango")
        self._positions, self._indices = positions, indices
        self.frame_mesh()

    def clear_mesh(self):
        self._positions = self._indices = None
        self.update()

    def has_mesh(self) -> bool:
        return self._positions is not None

    def set_background(self, color: QtGui.QColor):
        self.background = (color.redF(), color.greenF(), color.blueF())
        self.update()

    # --- OpenGL -----------------------------------------------------------
    def initializeGL(self):
        gl.glEnable(gl.GL_DEPTH_TEST)

    def resizeGL(self, w, h):
        gl.glViewport(0, 0, max(w, 1), max(h, 1))

    def _eye(self):
        cp = math.cos(self.pitch)
        return self.target + self.dist * np.array(
            [cp * math.sin(self.yaw), math.sin(self.pitch), cp * math.cos(self.yaw)])

    def paintGL(self):
        gl.glClearColor(*self.background, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        w, h = max(self.width(), 1), max(self.height(), 1)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(45.0, w / h, max(self.dist / 1000, 0.01), self.dist * 100 + 1000)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        e, t = self._eye(), self.target
        glu.gluLookAt(e[0], e[1], e[2], t[0], t[1], t[2], 0, 1, 0)

        if self.show_grid:
            self._draw_grid()
        if self.show_axes:
            self._draw_axes()
        if self._positions is not None and self._indices is not None:
            self._draw_mesh()

    def _draw_grid(self, n: int = 20, step: float = 1.0):
        gl.glColor3f(0.3, 0.3, 0.33)
        gl.glBegin(gl.GL_LINES)
        for i in range(-n, n + 1):
            gl.glVertex3f(i * step, 0, -n * step)
            gl.glVertex3f(i * step, 0, n * step)
            gl.glVertex3f(-n * step, 0, i * step)
            gl.glVertex3f(n * step, 0, i * step)
        gl.glEnd()

    def _draw_axes(self, length: float = 2.0):
        gl.glBegin(gl.GL_LINES)
        for color, end in (((1, 0.2, 0.2), (length, 0, 0)),
                           ((0.2, 1, 0.2), (0, length, 0)),
                           ((0.3, 0.5, 1), (0, 0, length))):
            gl.glColor3f(*color)
            gl.glVertex3f(0, 0, 0)
            gl.glVertex3f(*end)
        gl.glEnd()

    def _draw_mesh(self):
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE if self.wireframe else gl.GL_FILL)
        gl.glColor3f(0.75, 0.75, 0.8)
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glVertexPointer(3, gl.GL_FLOAT, 0, self._positions)
        gl.glDrawElements(gl.GL_TRIANGLES, self._indices.size, gl.GL_UNSIGNED_INT, self._indices)
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)

    # --- ratón ------------------------------------------------------------
    def mousePressEvent(self, ev):
        self._last = ev.position().toPoint()

    def mouseMoveEvent(self, ev):
        pos = ev.position().toPoint()
        dx, dy = pos.x() - self._last.x(), pos.y() - self._last.y()
        self._last = pos
        if ev.buttons() & QtCore.Qt.LeftButton:
            self.yaw -= dx * 0.01
            self.pitch = max(-1.5, min(1.5, self.pitch + dy * 0.01))
        elif ev.buttons() & (QtCore.Qt.RightButton | QtCore.Qt.MiddleButton):
            k = self.dist * 0.0015
            right = np.array([math.cos(self.yaw), 0.0, -math.sin(self.yaw)])
            self.target = self.target - right * dx * k + np.array([0.0, 1.0, 0.0]) * dy * k
        self.update()

    def wheelEvent(self, ev):
        self.dist = max(0.1, self.dist * (0.9 ** (ev.angleDelta().y() / 120)))
        self.update()

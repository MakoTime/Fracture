from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableView, QPushButton

from common.icons import get_icon
from tools.widgets import VisibleWidget
from .model import TableManager, TableModel


class TableView(QTableView):
    def __init__(self, parent=None, table_manager=None):
        super().__init__(parent)
        self.table_manager = table_manager or TableManager()
        self.table_model = TableModel(self.table_manager)
        self.setModel(self.table_model)
        self.table_model.rowsInserted.connect(self._refresh_visibility_widgets)
        self.table_model.rowsRemoved.connect(self._refresh_visibility_widgets)
        self.table_model.modelReset.connect(self._refresh_visibility_widgets)
        self.table_model.dataChanged.connect(self._refresh_visibility_widgets)
        self.table_model.rowsInserted.connect(self._refresh_shape_widgets)
        self.table_model.rowsRemoved.connect(self._refresh_shape_widgets)
        self.table_model.modelReset.connect(self._refresh_shape_widgets)
        self.table_model.dataChanged.connect(self._refresh_shape_widgets)
        self._refresh_visibility_widgets()
        self._refresh_shape_widgets()

    def _refresh_visibility_widgets(self, *args):
        for row in range(self.table_model.rowCount()):
            index = self.table_model.index(row, self.table_model.VISIBLE)
            widget = self.indexWidget(index)
            if widget is None:
                widget = VisibleWidget(parent=self.viewport())
                widget.toggled.connect(
                    lambda visible, row=row: self._set_row_visibility(
                        row, visible
                    )
                )
                self.setIndexWidget(index, widget)
            object_base = self.table_manager.get_data()[row].obj.obj
            block_object = getattr(object_base, "block_object", None)
            visible = getattr(
                block_object,
                "visible",
                self.table_manager.get_data()[row].visible.visible,
            )
            widget.set_visible(visible)

    def _refresh_shape_widgets(self, *args):
        for row in range(self.table_model.rowCount()):
            index = self.table_model.index(row, self.table_model.SHAPES)
            object_base = self.table_manager.get_data()[row].obj.obj
            shape = getattr(object_base, "orbit_shape", None)
            button = self.indexWidget(index)
            if shape is None:
                if button is not None:
                    button.deleteLater()
                continue
            if button is None:
                button = QPushButton(parent=self.viewport())
                button.setCheckable(True)
                button.setFixedSize(28, 28)
                button.setIcon(get_icon("orbit"))
                button.setToolTip("Show orbit")
                button.toggled.connect(
                    lambda visible, row=row: self._set_shape_visibility(
                        row, visible
                    )
                )
                self.setIndexWidget(index, button)
            button.blockSignals(True)
            button.setChecked(bool(shape.visible))
            button.setToolTip("Hide orbit" if shape.visible else "Show orbit")
            button.blockSignals(False)

    def _set_row_visibility(self, row, visible):
        index = self.table_model.index(row, self.table_model.VISIBLE)
        if index.isValid():
            self.table_model.setData(index, visible, Qt.CheckStateRole)

    def _set_shape_visibility(self, row, visible):
        if row < 0 or row >= self.table_model.rowCount():
            return
        object_base = self.table_manager.get_data()[row].obj.obj
        shape = getattr(object_base, "orbit_shape", None)
        interface = getattr(object_base, "shape_interface", None)
        if shape is not None and interface is not None:
            interface.set_visible(shape, visible)
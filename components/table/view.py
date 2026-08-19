from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableView

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
        self._refresh_visibility_widgets()

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
            widget.set_visible(
                self.table_manager.get_data()[row].visible.visible
            )

    def _set_row_visibility(self, row, visible):
        index = self.table_model.index(row, self.table_model.VISIBLE)
        if index.isValid():
            self.table_model.setData(index, visible, Qt.CheckStateRole)
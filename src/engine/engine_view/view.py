from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.engine.task import EngineTask, EngineTaskModel, TaskStatus
from src.tools.widgets import PlayPauseWidget


class EngineRunner(QWidget):
    """Controls and task monitor for background engine work."""

    def __init__(self, parent=None, task_model=None):
        super().__init__(parent)
        self.task_model = task_model or EngineTaskModel(self)
        self._rows = {}
        self._build_ui()
        self.task_model.task_added.connect(self._add_task)
        self.task_model.task_updated.connect(self._update_task)
        self.task_model.task_finished.connect(self._remove_completed_task)

    def _build_ui(self):
        self.play_pause_button = PlayPauseWidget(playing=True)
        self.state_label = QLabel("Running")
        self.play_pause_button.toggled.connect(self._set_playing)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.addWidget(self.play_pause_button)
        controls.addWidget(self.state_label)
        controls.addStretch(1)

        self.task_table = QTableWidget(0, 3)
        self.task_table.setHorizontalHeaderLabels(["Task", "Status", "Progress"])
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.setWordWrap(False)
        self.task_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.task_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controls)
        layout.addWidget(self.task_table)

    def play(self):
        self.play_pause_button.set_playing(True)

    def pause(self):
        self.play_pause_button.set_playing(False)

    def _set_playing(self, playing):
        if playing:
            self.task_model.play()
            self.state_label.setText("Running")
        else:
            self.task_model.pause()
            self.state_label.setText("Paused")

    def enqueue_task(self, name, work, on_finished=None) -> EngineTask:
        return self.task_model.enqueue(name, work, on_finished=on_finished)

    def enqueue_block_task(self, name, block_task, on_finished=None) -> EngineTask:
        return self.task_model.enqueue_block_task(
            name,
            block_task,
            on_finished=on_finished,
        )

    def remove_block_task(self, block_object):
        return self.task_model.remove_block_task(block_object)

    def clear(self):
        self.task_model.clear()
        self.task_table.setRowCount(0)
        self._rows.clear()

    def _add_task(self, task: EngineTask):
        row = self.task_table.rowCount()
        self.task_table.insertRow(row)
        self._rows[task.task_id] = row
        self._update_task(task)

    def _update_task(self, task: EngineTask):
        row = self._rows.get(task.task_id)
        if row is None:
            return
        self.task_table.setItem(row, 0, QTableWidgetItem(task.name))
        self.task_table.setItem(row, 1, QTableWidgetItem(task.status.value))
        progress = f"{task.progress:.0%}"
        if task.error:
            progress = task.error
        self.task_table.setItem(row, 2, QTableWidgetItem(progress))

    def _remove_completed_task(self, task: EngineTask):
        if task.status is not TaskStatus.COMPLETED:
            return
        row = self._rows.pop(task.task_id, None)
        if row is None:
            return
        self.task_table.removeRow(row)
        self._rows = {
            task_id: current_row - (current_row > row)
            for task_id, current_row in self._rows.items()
        }

from dataclasses import dataclass, field, replace
from enum import Enum
import inspect
from threading import Event
from typing import Callable, Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class TaskStatus(Enum):
    QUEUED = "Queued"
    RUNNING = "Running"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    FAILED = "Failed"


@dataclass
class EngineTask:
    name: str
    work: Callable[..., None]
    on_finished: Optional[Callable[["EngineTask"], None]] = None
    status: TaskStatus = TaskStatus.QUEUED
    progress: float = 0.0
    error: Optional[str] = None
    task_id: int = field(default=0)


class TaskSignals(QObject):
    finished = Signal(object)
    updated = Signal(object)


class TaskWorker(QRunnable):
    def __init__(self, task: EngineTask, resume_event: Event):
        super().__init__()
        self.task = task
        self.resume_event = resume_event
        self.signals = TaskSignals()

    def run(self):
        self.resume_event.wait()
        self.task.status = TaskStatus.RUNNING
        self.signals.updated.emit(self.task)
        try:
            parameters = inspect.signature(self.task.work).parameters.values()
            accepts_progress = any(
                parameter.kind
                in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
                for parameter in parameters
            )
            if accepts_progress:
                self.task.work(self._set_progress)
            else:
                self.task.work()
        except Exception as error:
            self.task.error = str(error)
            self.task.status = TaskStatus.FAILED
        else:
            self.task.progress = 1.0
            self.task.status = TaskStatus.COMPLETED
        self.signals.updated.emit(self.task)
        self.signals.finished.emit(self.task)

    def _set_progress(self, progress: float):
        self.task.progress = max(0.0, min(1.0, float(progress)))
        self.signals.updated.emit(replace(self.task))


class EngineTaskModel(QObject):
    task_added = Signal(object)
    task_updated = Signal(object)
    task_finished = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = []
        self._next_id = 1
        self._paused = False
        self._resume_event = Event()
        self._resume_event.set()
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)

    @property
    def paused(self):
        return self._paused

    def enqueue(
        self,
        name: str,
        work: Callable[..., None],
        on_finished: Optional[Callable[[EngineTask], None]] = None,
    ) -> EngineTask:
        task = EngineTask(
            name=name,
            work=work,
            on_finished=on_finished,
            task_id=self._next_id,
        )
        self._next_id += 1
        self.tasks.append(task)
        self.task_added.emit(task)
        self._start_next()
        return task

    def play(self):
        self._paused = False
        self._resume_event.set()
        self._start_next()

    def pause(self):
        self._paused = True
        self._resume_event.clear()
        for task in self.tasks:
            if task.status is TaskStatus.QUEUED:
                task.status = TaskStatus.PAUSED
                self.task_updated.emit(task)

    def _start_next(self):
        if self._paused or self._thread_pool.activeThreadCount():
            return
        task = next(
            (item for item in self.tasks if item.status in (TaskStatus.QUEUED, TaskStatus.PAUSED)),
            None,
        )
        if task is None:
            return
        task.status = TaskStatus.QUEUED
        self.task_updated.emit(task)
        worker = TaskWorker(task, self._resume_event)
        worker.signals.updated.connect(self.task_updated)
        worker.signals.finished.connect(self._task_finished)
        self._thread_pool.start(worker)

    def _task_finished(self, task: EngineTask):
        self.task_finished.emit(task)
        if task.on_finished is not None:
            task.on_finished(task)
        self._start_next()

    def wait_for_done(self, timeout=30000):
        return self._thread_pool.waitForDone(timeout)

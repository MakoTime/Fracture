from dataclasses import dataclass, field, replace
from enum import Enum
import inspect
from threading import Event
from typing import Callable, Optional, Protocol

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


class BlockTask(Protocol):
    block_object: object

    def prepare(self):
        ...

    def process(self, prepared, progress_callback=None):
        ...


def _call_with_optional_progress(work, progress_callback):
    parameters = inspect.signature(work).parameters.values()
    accepts_progress = any(
        parameter.kind
        in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
        for parameter in parameters
    )
    if accepts_progress:
        return work(progress_callback)
    return work()


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
            _call_with_optional_progress(self.task.work, self._set_progress)
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
        self._block_tasks = {}

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

    def enqueue_block_task(
        self,
        name: str,
        block_task: BlockTask,
        on_finished: Optional[Callable[[EngineTask], None]] = None,
    ) -> EngineTask:
        """Queue a block task and retry it when its block is invalidated."""
        self._validate_block_task_contract(block_task)
        block_object = block_task.block_object
        if block_object.is_destroyed():
            raise ValueError("Cannot enqueue a task for a destroyed block object")
        binding = self._block_tasks.get(block_object.guid)
        if binding is None:
            binding = {
                "name": name,
                "task": block_task,
                "on_finished": on_finished,
                "pending": False,
                "waiting_for_children": False,
                "engine_task": None,
                "active": True,
                "prepared": None,
            }
            self._block_tasks[block_object.guid] = binding
            block_object.add_invalidation_callback(self._block_invalidated)
        else:
            binding["name"] = name
            binding["task"] = block_task
            binding["on_finished"] = on_finished
            if self._task_is_active(binding["engine_task"]):
                binding["pending"] = True
                return binding["engine_task"]

        return self._enqueue_block_process(binding)

    @staticmethod
    def _validate_block_task_contract(block_task):
        prepare = getattr(block_task, "prepare", None)
        process = getattr(block_task, "process", None)
        if not callable(prepare) or not callable(process):
            raise TypeError(
                "Block tasks must implement prepare() and "
                "process(prepared, progress_callback=None)"
            )
        parameters = list(inspect.signature(process).parameters.values())
        positional = [
            parameter
            for parameter in parameters
            if parameter.kind
            in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
        ]
        if len(positional) != 2 or any(
            parameter.kind is parameter.VAR_POSITIONAL
            for parameter in parameters
        ):
            raise TypeError(
                "Block tasks must implement process(prepared, "
                "progress_callback=None)"
            )

    def remove_block_task(self, block_object):
        """Forget a replaced block task binding before reusing its GUID."""
        binding = self._block_tasks.pop(block_object.guid, None)
        if binding is None:
            return False
        binding["active"] = False
        block_object.remove_invalidation_callback(self._block_invalidated)
        return True

    def _enqueue_block_process(self, binding):
        if not binding["active"]:
            return None
        if self._task_is_active(binding["engine_task"]):
            return binding["engine_task"]
        if not self._enqueue_invalid_children(binding, set()):
            binding["waiting_for_children"] = True
            return binding["engine_task"]
        binding["waiting_for_children"] = False
        binding["prepared"] = binding["task"].prepare()
        engine_task = self.enqueue(
            binding["name"],
            lambda progress: self._process_block_task(binding, progress),
            on_finished=lambda task: self._block_task_finished(binding, task),
        )
        binding["engine_task"] = engine_task
        return engine_task

    def _enqueue_invalid_children(self, binding, visiting):
        block_object = binding["task"].block_object
        if block_object.guid in visiting:
            raise ValueError("Block task dependencies contain a cycle")
        visiting.add(block_object.guid)
        dependencies_ready = True
        for child in block_object.child_block_objects:
            if child.is_destroyed():
                continue
            if child.is_valid():
                continue
            child_binding = self._block_tasks.get(child.guid)
            if child_binding is None:
                raise ValueError(
                    f"No block task is registered for invalid child {child.guid}"
                )
            current_task = child_binding["engine_task"]
            if current_task is not None and current_task.status in (
                TaskStatus.QUEUED,
                TaskStatus.RUNNING,
                TaskStatus.PAUSED,
            ):
                dependencies_ready = False
                continue
            child_dependencies_ready = self._enqueue_invalid_children(
                child_binding,
                visiting,
            )
            if child_dependencies_ready:
                self._enqueue_block_process_without_dependencies(child_binding)
            else:
                self._enqueue_block_process(child_binding)
            dependencies_ready = False
        visiting.remove(block_object.guid)
        return dependencies_ready

    def _enqueue_block_process_without_dependencies(self, binding):
        binding["prepared"] = binding["task"].prepare()
        engine_task = self.enqueue(
            binding["name"],
            lambda progress: self._process_block_task(binding, progress),
            on_finished=lambda task: self._block_task_finished(binding, task),
        )
        binding["engine_task"] = engine_task
        return engine_task

    @staticmethod
    def _process_block_task(binding, progress_callback=None):
        block_object = binding["task"].block_object
        if block_object.is_destroyed():
            return
        if any(not child.is_valid() for child in block_object.child_block_objects):
            return
        binding["task"].process(binding["prepared"], progress_callback)

    @staticmethod
    def _task_is_active(task):
        return task is not None and task.status in (
            TaskStatus.QUEUED,
            TaskStatus.RUNNING,
            TaskStatus.PAUSED,
        )

    def _block_invalidated(self, block_object):
        if block_object.is_destroyed():
            return
        binding = self._block_tasks.get(block_object.guid)
        if binding is None or not binding["active"]:
            return
        current_task = binding["engine_task"]
        if self._task_is_active(current_task):
            binding["pending"] = True
            return
        self._enqueue_block_process(binding)

    def _block_task_finished(self, binding, task):
        if not binding["active"]:
            return
        if binding["on_finished"] is not None:
            binding["on_finished"](task)
        binding["engine_task"] = None
        if (
            task.status is TaskStatus.COMPLETED
            and
            not binding["task"].block_object.is_destroyed()
            and (binding["pending"] or not binding["task"].block_object.is_valid())
        ):
            binding["pending"] = False
            self._enqueue_block_process(binding)
        self._resume_waiting_parents()

    def _resume_waiting_parents(self):
        for binding in tuple(self._block_tasks.values()):
            if binding["active"] and binding["waiting_for_children"]:
                self._enqueue_block_process(binding)

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

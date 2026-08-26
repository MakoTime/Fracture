from src.common.calendar import WorldTime
from src.components.timer import TimerController


class TimedObject:
    def __init__(self):
        self.updates = []

    def update_at_time(self, elapsed_seconds, delta_seconds):
        self.updates.append((elapsed_seconds, delta_seconds))


def test_timer_interface_dispatches_elapsed_and_delta_time():
    start_time = WorldTime(0, 0, 0, 0, 0, 0)
    controller = TimerController(start_time=start_time)
    object_base = TimedObject()

    interface = controller.attach(object_base)
    assert object_base.timer_interface is interface
    
    first_advance = 1
    second_advance = -1
    
    time_first_advance = WorldTime(0, 0, 0, 0, 0, 1)
    time_second_advance = start_time
    
    assert controller.advance(first_advance) == time_first_advance
    assert controller.advance(second_advance) == time_second_advance
    
    assert object_base.updates == [(time_first_advance, first_advance), (time_second_advance, second_advance)]

    assert controller.detach(object_base) is True
    assert not hasattr(object_base, "timer_interface")
    controller.advance(1.0)
    assert len(object_base.updates) == 2


def test_timer_controller_clear_detaches_all_interfaces():
    start_time = WorldTime(0, 0, 0, 0, 0, 0)
    controller = TimerController(start_time=start_time)
    first = TimedObject()
    second = TimedObject()
    controller.attach(first)
    controller.attach(second)

    controller.advance(1.0)
    controller.clear()

    assert not hasattr(first, "timer_interface")
    assert not hasattr(second, "timer_interface")
    controller.advance(1.0)
    time_after_advance = WorldTime(0, 0, 0, 0, 0, 1)
    assert first.updates == [(time_after_advance, 1.0)]
    assert second.updates == [(time_after_advance, 1.0)]


def test_timer_controller_accumulates_fractional_seconds():
    controller = TimerController(start_time=WorldTime(0, 0, 0, 0, 0, 0))

    controller.advance(0.4)
    assert controller.time == WorldTime(0, 0, 0, 0, 0, 0, 400)

    controller.advance(0.6)
    assert controller.time == WorldTime(0, 0, 0, 0, 0, 1)


def test_timer_controller_accumulates_fractional_negative_seconds():
    controller = TimerController(start_time=WorldTime(0, 0, 0, 0, 0, 1))

    controller.advance(-0.4)
    assert controller.time == WorldTime(0, 0, 0, 0, 0, 0, 600)

    controller.advance(-0.6)
    assert controller.time == WorldTime(0, 0, 0, 0, 0, 0)


def test_timer_controller_set_time_updates_attached_objects():
    start_time = WorldTime(2026, 0, 0, 0, 0, 0)
    target_time = WorldTime(2026, 0, 1, 0, 0, 0)
    controller = TimerController(start_time=start_time)
    object_base = TimedObject()

    controller.attach(object_base)

    assert controller.set_time(target_time) == target_time
    assert controller.time == target_time
    assert object_base.updates == [(target_time, 86400.0)]

from src.components.timer import TimerController


class TimedObject:
    def __init__(self):
        self.updates = []

    def update_at_time(self, elapsed_seconds, delta_seconds):
        self.updates.append((elapsed_seconds, delta_seconds))


def test_timer_interface_dispatches_elapsed_and_delta_time():
    controller = TimerController()
    object_base = TimedObject()

    interface = controller.attach(object_base)
    assert object_base.timer_interface is interface

    assert controller.advance(0.25) == 0.25
    assert controller.advance(-0.1) == 0.15
    assert object_base.updates == [(0.25, 0.25), (0.15, -0.1)]

    assert controller.detach(object_base) is True
    assert not hasattr(object_base, "timer_interface")
    controller.advance(1.0)
    assert len(object_base.updates) == 2


def test_timer_controller_clear_detaches_all_interfaces():
    controller = TimerController()
    first = TimedObject()
    second = TimedObject()
    controller.attach(first)
    controller.attach(second)

    controller.advance(1.0)
    controller.clear()

    assert controller.elapsed_seconds == 0.0
    assert not hasattr(first, "timer_interface")
    assert not hasattr(second, "timer_interface")
    controller.advance(1.0)
    assert first.updates == [(1.0, 1.0)]
    assert second.updates == [(1.0, 1.0)]

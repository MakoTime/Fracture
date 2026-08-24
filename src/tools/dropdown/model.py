from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DropdownOption:
    """One selectable dropdown entry."""

    label: str
    value: Any = None
    enabled: bool = True
    icon: Any = None

    def __post_init__(self):
        if self.value is None:
            object.__setattr__(self, "value", self.label)


@dataclass
class DropdownModel:
    """Options and current selection for a dropdown menu."""

    options: list[DropdownOption] = field(default_factory=list)
    current_value: Any = None

    def __post_init__(self):
        self.options = [self._coerce_option(option) for option in self.options]
        if self.current_value is None and self.options:
            self.current_value = self.options[0].value

    @staticmethod
    def _coerce_option(option) -> DropdownOption:
        if isinstance(option, DropdownOption):
            return option
        if isinstance(option, tuple) and len(option) == 2:
            return DropdownOption(label=str(option[0]), value=option[1])
        return DropdownOption(label=str(option), value=option)

    @classmethod
    def from_options(cls, options: Iterable, current_value=None):
        return cls(list(options), current_value)

    def set_current(self, value: Any):
        if self.find(value) is None:
            raise ValueError(f"dropdown value is not available: {value!r}")
        self.current_value = value

    def find(self, value: Any) -> DropdownOption | None:
        return next((option for option in self.options if option.value == value), None)

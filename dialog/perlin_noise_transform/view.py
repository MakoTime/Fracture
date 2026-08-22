import json
import math

from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from tools.widgets import BezierCurveGraph
from .model import PerlinNoiseTransformModel
from tools.widgets import DynamicSpinbox
from dialog.base.popup_editor import PopupEditorView


class PerlinNoiseTransformView(PopupEditorView):
    """Editor for discrete Perlin bands and sampled continuous curves."""

    PRESETS = ("Manual", "Impulse", "Flat bar", "Sin wave", "Cos wave", "Normal distribution")

    def __init__(self, model=None, parent=None):
        PopupEditorView.__init__(
            self,
            model or PerlinNoiseTransformModel(),
            parent=parent,
        )
        self.setWindowTitle("Perlin Noise Transform")
        self.resize(820, 430)

        self.name_field = QLineEdit(self.model.name)
        curve_range = self.model.curve_mode == "bezier"
        frequency_minimum = (
            min(self.model.frequencies)
            if curve_range and len(self.model.frequencies) > 1
            else min(self.model.frequencies)
        )
        frequency_maximum = (
            max(self.model.frequencies)
            if curve_range and len(self.model.frequencies) > 1
            else (8 if len(self.model.frequencies) == 1 else max(self.model.frequencies))
        )
        self.frequency_min_field = QSpinBox()
        self.frequency_min_field.setRange(1, 100000)
        self.frequency_min_field.setValue(round(frequency_minimum))
        self.frequency_max_field = QSpinBox()
        self.frequency_max_field.setRange(1, 100000)
        self.frequency_max_field.setValue(round(frequency_maximum))
        self.frequency_count_field = QSpinBox()
        self.frequency_count_field.setRange(1, 200000)
        self.frequency_count_field.setValue(
            self.model.sample_count
            if curve_range and self.model.manual_sampling
            else (2 * round(frequency_maximum) + 1 if curve_range else len(self.model.frequencies))
        )
        self.frequency_count_label = QLabel("Frequency count")
        self.manual_sampling_field = QCheckBox("Manual sampling")
        self.manual_sampling_field.setChecked(self.model.manual_sampling)
        self.max_amplitude_field = QDoubleSpinBox()
        self.max_amplitude_field.setRange(0.0, 100000.0)
        self.max_amplitude_field.setDecimals(3)
        self.max_amplitude_field.setValue(max(self.model.amplitudes, default=1.0))
        self.amplitude_field = QLineEdit(", ".join(str(value) for value in self.model.amplitudes))
        self.amplitude_field.setVisible(False)
        self.seed_field = QSpinBox()
        self.seed_field.setRange(-2147483648, 2147483647)
        self.seed_field.setValue(self.model.seed)
        self.mode_field = QComboBox()
        self.mode_field.addItem("Discrete", "discrete")
        self.mode_field.addItem("Continuous", "continuous")
        self.mode_field.setCurrentIndex(1 if self.model.curve_mode == "bezier" else 0)
        self.preset_field = QComboBox()
        self.preset_field.addItems(self.PRESETS)
        self.preset_field.setCurrentText(self.model.preset)
        self.option_fields = {}
        self.options_layout = QFormLayout()
        self._build_preset_options()
        self.preset_field.currentTextChanged.connect(self._build_preset_options)

        self.graph = BezierCurveGraph(
            self.model.frequencies,
            self.model.amplitudes,
            self.model.curve_points,
            self.model.curve_mode,
            curve_handles=self.model.curve_handles,
            frequency_min=self.frequency_min_field.value(),
            frequency_max=self.frequency_max_field.value(),
            amplitude_max=self.max_amplitude_field.value(),
            sample_count=self.frequency_count_field.value(),
        )
        if self.model.curve_mode == "bezier" and not self.graph.curve_points:
            self.graph.curve_points = [(0.0, 0.0), (0.5, 1.0), (1.0, 0.0)]
        if curve_range:
            if len(self.model.frequencies) == 1:
                self.graph.amplitudes = list(self.model.amplitudes[:self.frequency_count_field.value()])
                self.graph.amplitudes.extend(
                    [0.0] * (self.frequency_count_field.value() - len(self.graph.amplitudes))
                )
            if len(self.model.frequencies) == 1:
                self.amplitude_field.setText(
                    ", ".join(f"{value:.3g}" for value in self.graph.amplitudes)
                )
        self.graph.values_changed.connect(self._sync_graph_fields)
        self.mode_field.currentIndexChanged.connect(self._mode_changed)
        self.frequency_count_field.valueChanged.connect(self._frequency_count_spin_changed)
        self.frequency_min_field.valueChanged.connect(self._frequency_range_changed)
        self.frequency_max_field.valueChanged.connect(self._frequency_range_changed)
        self.manual_sampling_field.toggled.connect(self._manual_sampling_changed)
        self.max_amplitude_field.valueChanged.connect(self._graph_labels_changed)
        self.max_amplitude_field.valueChanged.connect(self._update_preset_ranges)
        self.max_amplitude_field.valueChanged.connect(self._apply_preset)

        basic_form = QFormLayout()
        basic_form.addRow("Name", self.name_field)
        basic_form.addRow("Mode", self.mode_field)
        basic_form.addRow("Frequency min", self.frequency_min_field)
        basic_form.addRow("Frequency max", self.frequency_max_field)
        basic_form.addRow(self.frequency_count_label, self.frequency_count_field)
        basic_form.addRow("Sampling", self.manual_sampling_field)
        basic_form.addRow("Max amplitude", self.max_amplitude_field)
        basic_form.addRow("Seed", self.seed_field)
        basic_form.addRow("Preset", self.preset_field)
        group = QGroupBox("Perlin noise bands")
        group.setLayout(basic_form)

        graph_group = QGroupBox("Amplitude by frequency")
        graph_layout = QVBoxLayout(graph_group)
        graph_layout.addWidget(self.graph)
        self.graph_position_label = QLabel(
            "Cursor position    Frequency: 0.000    Amplitude: 0.000"
        )
        self.graph_position_label.setStyleSheet(
            "QLabel { border: 1px solid palette(mid); padding: 4px 8px; "
            "background: palette(base); }"
        )
        self.graph.mouse_position_changed.connect(self._update_graph_position)
        graph_layout.addWidget(QLabel("Drag bars or curve points vertically to set amplitude."))
        graph_layout.addWidget(self.graph_position_label)
        graph_layout.addWidget(self._options_widget())

        self.create_button_box()
        layout = QVBoxLayout(self)
        editor = QHBoxLayout()
        editor.addWidget(group, 0)
        editor.addWidget(graph_group, 1)
        layout.addLayout(editor)
        layout.addWidget(self.button_box)
        self._update_frequency_count_visibility()
        self._apply_preset()

    def _options_widget(self):
        widget = QWidget()
        widget.setLayout(self.options_layout)
        return widget

    def _build_preset_options(self):
        while self.options_layout.rowCount():
            self.options_layout.removeRow(0)
        self.option_fields = {}
        preset = self.preset_field.currentText()
        definitions = {
            "Impulse": (("position", 0.5), ("width", 0.12), ("peak", 1.0), ("offset", 0.0)),
            "Flat bar": (("value", 1.0), ("offset", 0.0)),
            "Sin wave": (("cycles", 1.0), ("phase", 0.0), ("offset", 0.5), ("amplitude", 0.5)),
            "Cos wave": (("cycles", 1.0), ("phase", 0.0), ("offset", 0.5), ("amplitude", 0.5)),
            "Normal distribution": (("center", 0.5), ("width", 0.18), ("peak", 1.0), ("offset", 0.0)),
        }
        for name, value in definitions.get(preset, ()):
            field = DynamicSpinbox()
            if name in ("position", "center"):
                field.setRange(0.0, 1.0)
            elif name == "width":
                field.setRange(0.001, 1.0)
            elif name == "phase":
                field.setRange(0.0, 360.0)
            elif name == "cycles":
                field.setRange(0.0, 100.0)
            else:
                field.setRange(0.0, self.max_amplitude_field.value())
            field.setDecimals(3)
            field.setValue(
                min(field.maximum(), max(field.minimum(), float(self.model.preset_options.get(name, value))))
            )
            field.valueChanged.connect(self._apply_preset)
            self.option_fields[name] = field
            self.options_layout.addRow(name.title(), field)
        self._apply_preset()

    def _update_preset_ranges(self):
        for name, field in self.option_fields.items():
            if name not in ("peak", "offset", "value", "amplitude"):
                continue
            value = field.value()
            field.setMaximum(self.max_amplitude_field.value())
            field.setValue(min(value, field.maximum()))

    def _frequency_count_spin_changed(self, count):
        if self.mode_field.currentData() != "discrete":
            self.graph.set_sample_count(count)
            amplitudes = list(self.graph.amplitudes[:count])
            amplitudes.extend([0.0] * (count - len(amplitudes)))
            self.graph.amplitudes = amplitudes
            self.amplitude_field.setText(", ".join(f"{value:.3g}" for value in amplitudes))
            return
        self._set_frequency_data(self._frequency_range_values(count))

    def _manual_sampling_changed(self, enabled):
        if not enabled:
            self._set_automatic_sample_count()
        self._update_frequency_count_visibility()

    def _update_frequency_count_visibility(self):
        visible = self.mode_field.currentData() == "discrete"
        continuous_manual = (
            self.mode_field.currentData() == "continuous"
            and self.manual_sampling_field.isChecked()
        )
        self.frequency_count_label.setText(
            "Frequency count" if visible else "Sample count"
        )
        self.frequency_count_label.setVisible(visible or continuous_manual)
        self.frequency_count_field.setVisible(visible or continuous_manual)
        self.manual_sampling_field.setVisible(self.mode_field.currentData() == "continuous")

    def _set_automatic_sample_count(self):
        sample_count = max(2, 2 * self.frequency_max_field.value() + 1)
        self.frequency_count_field.blockSignals(True)
        self.frequency_count_field.setValue(sample_count)
        self.frequency_count_field.blockSignals(False)
        if hasattr(self, "graph"):
            self.graph.set_sample_count(sample_count)

    def _frequency_range_changed(self, value):
        del value
        self._graph_labels_changed()
        if self.mode_field.currentData() != "discrete":
            if not self.manual_sampling_field.isChecked():
                self._set_automatic_sample_count()
            return
        minimum = self.frequency_min_field.value()
        maximum = self.frequency_max_field.value()
        if minimum > maximum:
            sender = self.sender()
            if sender is self.frequency_min_field:
                self.frequency_max_field.blockSignals(True)
                self.frequency_max_field.setValue(minimum)
                self.frequency_max_field.blockSignals(False)
            else:
                self.frequency_min_field.blockSignals(True)
                self.frequency_min_field.setValue(maximum)
                self.frequency_min_field.blockSignals(False)
        self._set_frequency_data(
            self._frequency_range_values(self.frequency_count_field.value())
        )

    def _frequency_range_values(self, count):
        minimum = self.frequency_min_field.value()
        maximum = self.frequency_max_field.value()
        if count == 1:
            return (minimum,)
        return tuple(
            round(minimum + (maximum - minimum) * index / (count - 1))
            for index in range(count)
        )

    def _set_frequency_data(self, frequencies):
        amplitudes = list(self.graph.amplitudes[:len(frequencies)])
        amplitudes.extend([0.0] * (len(frequencies) - len(amplitudes)))
        self.amplitude_field.setText(", ".join(f"{value:.3g}" for value in amplitudes))
        self.graph.set_data(
            frequencies,
            amplitudes,
            curve_mode="discrete",
            frequency_min=self.frequency_min_field.value(),
            frequency_max=self.frequency_max_field.value(),
            amplitude_max=self.max_amplitude_field.value(),
        )

    def _mode_changed(self):
        mode = self.mode_field.currentData()
        if mode == "continuous" and not self.graph.curve_points:
            self.graph.curve_points = [(0.0, 0.0), (0.5, 1.0), (1.0, 0.0)]
        self.graph.set_curve_mode(self._display_curve_mode())
        self._update_frequency_count_visibility()
        if mode == "continuous" and not self.manual_sampling_field.isChecked():
            self._set_automatic_sample_count()
        self._apply_preset()

    def _sync_graph_fields(self):
        self._graph_labels_changed()

    def _graph_labels_changed(self):
        if hasattr(self, "graph"):
            self.graph.set_axis_labels(
                self.frequency_min_field.value(),
                self.frequency_max_field.value(),
                self.max_amplitude_field.value(),
            )

    def _update_graph_position(self, x, y):
        frequency = self.frequency_min_field.value() + x * (
            self.frequency_max_field.value() - self.frequency_min_field.value()
        )
        amplitude = y * self.max_amplitude_field.value()
        self.graph_position_label.setText(
            f"Cursor position    Frequency: {frequency:.3f}    "
            f"Amplitude: {amplitude:.3f}"
        )

    def _display_curve_mode(self):
        if self.mode_field.currentData() == "discrete":
            return "discrete"
        return "bezier" if self.preset_field.currentText() == "Manual" else "line"

    def _apply_preset(self):
        preset = self.preset_field.currentText()
        if not hasattr(self, "graph"):
            return
        display_mode = self._display_curve_mode()
        self.graph.set_curve_mode(display_mode)
        if preset == "Manual":
            return
        options = {name: field.value() for name, field in self.option_fields.items()}
        count = self.frequency_count_field.value()
        amplitude_scale = max(0.0001, self.max_amplitude_field.value())
        values = []
        for index in range(count):
            x = index / max(1, count - 1)
            if preset == "Impulse":
                value = options["peak"] * math.exp(-((x - options["position"]) / max(0.001, options["width"])) ** 2) + options["offset"]
            elif preset == "Flat bar":
                value = options["value"] + options["offset"]
            elif preset in ("Sin wave", "Cos wave"):
                angle = (
                    2 * math.pi * options["cycles"] * x
                    + math.radians(options["phase"])
                )
                wave = math.sin(angle) if preset == "Sin wave" else math.cos(angle)
                value = options["offset"] + options["amplitude"] * wave
            else:
                value = options["peak"] * math.exp(-0.5 * ((x - options["center"]) / max(0.001, options["width"])) ** 2) + options["offset"]
            values.append(max(0.0, min(1.0, value / amplitude_scale)))
        if self.mode_field.currentData() == "continuous":
            self.graph.curve_points = tuple(
                (index / max(1, count - 1), value) for index, value in enumerate(values)
            )
            self.graph.curve_handles = [None] * len(self.graph.curve_points)
            self.graph.set_curve_mode(display_mode)
        else:
            self.graph.set_amplitudes(values)
        self._graph_labels_changed()

    def apply_model(self):
        try:
            mode = self.mode_field.currentData()
            if mode == "continuous":
                sample_count = self.frequency_count_field.value()
                amplitudes = self.graph.sampled_values(sample_count)
                frequencies = self._frequency_range_values(sample_count)
            else:
                frequencies = self._frequency_range_values(self.frequency_count_field.value())
                amplitudes = tuple(self.graph.amplitudes)
            amplitudes = tuple(value * self.max_amplitude_field.value() for value in amplitudes)
            self.model = PerlinNoiseTransformModel(
                name=self.name_field.text(),
                frequencies=frequencies,
                amplitudes=amplitudes,
                seed=self.seed_field.value(),
                guid=self.model.guid,
                curve_mode="bezier" if mode == "continuous" else "discrete",
                curve_points=self.graph.serialized_curve_points(),
                curve_handles=self.graph.serialized_curve_handles(),
                frequency_start=self.frequency_min_field.value(),
                frequency_end=self.frequency_max_field.value(),
                sample_count=sample_count,
                manual_sampling=self.manual_sampling_field.isChecked(),
                preset=self.preset_field.currentText(),
                preset_options={name: field.value() for name, field in self.option_fields.items()},
            )
        except (TypeError, ValueError):
            return
        return self.model

    def _accept(self):
        """Preserve the legacy direct-accept helper used by callers and tests."""
        if self.apply_model() is not None:
            self.accept()

    @staticmethod
    def load_json(path):
        with open(path, "r", encoding="utf-8") as stream:
            return PerlinNoiseTransformModel.from_json(json.load(stream))

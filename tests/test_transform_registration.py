import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from components.tree import TreeModel, TreeSearch
from components.tree.roots import colourmap_root, root_objects, transform_root
from dialog.perlin_noise_transform import (
    PerlinNoiseTransformModel,
    create_perlin_noise_transform_dialog,
)
from dialog.perlin_noise_transform.graph import FrequencyAmplitudeGraph
from objects.perlin_noise_transform import PerlinNoiseTransformObject


def test_transforms_root_is_registered_after_mesh_root():
    assert transform_root in root_objects.get_nodes()
    assert root_objects.get_nodes().index(transform_root) == 1


def test_colourmap_root_is_registered_after_transform_root():
    assert colourmap_root in root_objects.get_nodes()
    assert root_objects.get_nodes().index(colourmap_root) == 2


def test_tree_search_filters_project_objects_and_exposes_blocks():
    transform = PerlinNoiseTransformModel(name="Searchable").to_object()
    transform_root.add_child(transform.node)
    try:
        search = TreeSearch(root_objects.get_nodes())
        matches = search.find(lambda node: node.node_object is transform)

        assert matches == [transform]
        assert transform.node.block_object is transform.block_object
        assert transform.node.get_block_objects() == [transform.block_object]
    finally:
        transform.remove_from_tree()


def test_perlin_transform_dialog_factory_uses_model(qapp):
    model = PerlinNoiseTransformModel(
        frequencies=(2, 8),
        amplitudes=(1.0, 0.25),
        seed=12,
    )
    dialog = create_perlin_noise_transform_dialog(model, parent=None)

    assert dialog.model is model
    assert dialog.frequency_min_field.value() == 2
    assert dialog.frequency_max_field.value() == 8
    assert dialog.amplitude_field.text() == "1.0, 0.25"
    dialog.close()


def test_perlin_transform_model_round_trips_json():
    model = PerlinNoiseTransformModel(
        name="Terrain Bands",
        frequencies=(2, 8),
        amplitudes=(1.0, 0.25),
        seed=12,
    )

    restored = PerlinNoiseTransformModel.from_json(model.to_json())

    assert restored == model


def test_perlin_curve_data_round_trips_json():
    model = PerlinNoiseTransformModel(
        curve_mode="bezier",
        curve_points=((0.0, 0.0), (0.5, 1.0), (1.0, 0.25)),
        curve_handles=(
            None,
            ((0.35, 0.8), (0.65, 1.0)),
            None,
        ),
        frequency_start=2.0,
        frequency_end=32.0,
        sample_count=9,
    )

    assert PerlinNoiseTransformModel.from_json(model.to_json()) == model


def test_perlin_editor_schema_survives_runtime_block_round_trip():
    model = PerlinNoiseTransformModel(
        frequencies=(2, 4, 8),
        amplitudes=(1.0, 0.5, 0.25),
        curve_mode="bezier",
        curve_points=((0.0, 0.0), (0.5, 1.0), (1.0, 0.0)),
        sample_count=17,
        manual_sampling=True,
        preset="Sin wave",
        preset_options={"phase": 90.0, "amplitude": 0.75},
    )

    block = model.to_object().block_object
    restored = PerlinNoiseTransformModel(
        frequencies=block.frequencies,
        amplitudes=block.amplitudes,
        seed=block.seed,
        guid=block.guid,
        curve_mode=block.curve_mode,
        curve_points=block.curve_points,
        curve_handles=block.curve_handles,
        frequency_start=block.frequency_start,
        frequency_end=block.frequency_end,
        sample_count=block.sample_count,
        manual_sampling=block.manual_sampling,
        preset=block.preset,
        preset_options=block.preset_options,
    )

    assert restored == model


def test_perlin_dialog_resizes_bars_when_frequency_count_changes(qapp):
    dialog = create_perlin_noise_transform_dialog(parent=None)
    dialog.frequency_count_field.setValue(4)

    assert len(dialog.graph.amplitudes) == 4
    assert dialog.frequency_min_field.value() == 1
    assert dialog.frequency_max_field.value() == 8
    assert dialog.amplitude_field.text() == "1, 0, 0, 0"
    dialog.close()


def test_perlin_dialog_uses_continuous_mode_and_max_amplitude(qapp):
    dialog = create_perlin_noise_transform_dialog(parent=None)

    assert dialog.mode_field.itemText(0) == "Discrete"
    assert dialog.mode_field.itemText(1) == "Continuous"
    assert dialog.mode_field.currentData() == "continuous"
    assert dialog.max_amplitude_field.value() == pytest.approx(1.0)

    dialog.frequency_min_field.setValue(3)
    dialog.frequency_max_field.setValue(20)
    dialog.max_amplitude_field.setValue(12.5)

    assert dialog.graph.frequency_min == 3
    assert dialog.graph.frequency_max == 20
    assert dialog.graph.amplitude_max == pytest.approx(12.5)
    assert dialog.graph.curve_points[1].y() == pytest.approx(1.0 / 12.5)
    assert dialog.apply_model().amplitudes[
        dialog.frequency_count_field.value() // 2
    ] == pytest.approx(1.0)
    dialog.close()


def test_perlin_dialog_clamps_out_of_range_curve_coordinates(qapp):
    model = PerlinNoiseTransformModel(
        curve_mode="bezier",
        curve_points=((0.0, 0.0), (0.5, 4.0), (1.0, 0.0)),
        curve_handles=(None, ((0.3, 4.0), (0.7, -2.0)), None),
        max_amplitude=1.0,
    )
    dialog = create_perlin_noise_transform_dialog(model, parent=None)

    assert dialog.graph.curve_points[1].y() == pytest.approx(1.0)
    assert dialog.graph.curve_handles[1][0].y() == pytest.approx(1.0)
    assert dialog.graph.curve_handles[1][1].y() == pytest.approx(0.0)
    dialog.close()


def test_perlin_continuous_sampling_defaults_to_twice_max_frequency(qapp):
    dialog = create_perlin_noise_transform_dialog(parent=None)

    assert not dialog.manual_sampling_field.isChecked()
    assert dialog.frequency_count_field.value() == 17
    assert dialog.graph.sample_count == 17

    dialog.frequency_max_field.setValue(20)
    assert dialog.frequency_count_field.value() == 41
    assert dialog.graph.sample_count == 41
    dialog.close()


def test_perlin_preset_controls_use_amplitude_ranges_and_degree_phase(qapp):
    dialog = create_perlin_noise_transform_dialog(parent=None)
    dialog.max_amplitude_field.setValue(12.0)
    dialog.preset_field.setCurrentText("Sin wave")

    assert dialog.option_fields["amplitude"].minimum() == 0.0
    assert dialog.option_fields["amplitude"].maximum() == 12.0
    assert dialog.option_fields["phase"].minimum() == 0.0
    assert dialog.option_fields["phase"].maximum() == 360.0

    dialog.option_fields["phase"].setValue(90.0)
    dialog._apply_preset()
    assert dialog.graph.curve_points[0].y() == pytest.approx(1.0 / 12.0)
    dialog.close()


def test_perlin_continuous_manual_sampling_stays_fixed_on_range_change(qapp):
    dialog = create_perlin_noise_transform_dialog(parent=None)
    dialog.manual_sampling_field.setChecked(True)
    dialog.frequency_count_field.setValue(7)

    dialog.frequency_max_field.setValue(20)

    assert dialog.frequency_count_field.value() == 7
    assert dialog.graph.sample_count == 7
    dialog.close()


def test_perlin_continuous_preset_renders_line_graph(qapp):
    dialog = create_perlin_noise_transform_dialog(parent=None)
    dialog.preset_field.setCurrentText("Sin wave")

    assert dialog.graph.curve_mode == "line"
    assert len(dialog.graph.curve_points) >= 2
    dialog.close()


def test_graph_axis_ticks_are_interpolated_and_capped(qapp):
    ticks = FrequencyAmplitudeGraph._axis_ticks(3, 97)

    assert ticks[0] == 3
    assert ticks[-1] == 97
    assert len(ticks) <= 10
    assert all(FrequencyAmplitudeGraph._format_tick(value).isdigit() for value in ticks)


def test_graph_axis_ticks_include_even_range_midpoint(qapp):
    ticks = FrequencyAmplitudeGraph._axis_ticks(3, 97)

    assert 50 in ticks
    assert 51 not in ticks


def test_graph_emits_normalized_mouse_vector(qapp):
    graph = FrequencyAmplitudeGraph()
    graph.resize(360, 230)
    positions = []
    graph.mouse_position_changed.connect(lambda x, y: positions.append((x, y)))
    graph._emit_mouse_position(graph._to_pixel(0.25, 0.75))

    assert positions[-1][0] == pytest.approx(0.25)
    assert positions[-1][1] == pytest.approx(0.75)


def test_dialog_cursor_position_label_is_named_and_bordered(qapp):
    dialog = create_perlin_noise_transform_dialog(parent=None)

    assert "Vector2" not in dialog.graph_position_label.text()
    assert "Frequency:" in dialog.graph_position_label.text()
    assert "Amplitude:" in dialog.graph_position_label.text()
    assert "border" in dialog.graph_position_label.styleSheet()
    dialog.close()


def test_perlin_manual_continuous_switches_back_to_bezier(qapp):
    dialog = create_perlin_noise_transform_dialog(parent=None)
    dialog.preset_field.setCurrentText("Sin wave")
    assert dialog.graph.curve_mode == "line"

    dialog.preset_field.setCurrentText("Manual")

    assert dialog.mode_field.currentData() == "continuous"
    assert dialog.graph.curve_mode == "bezier"
    dialog.close()


def test_perlin_dialog_samples_bezier_curve_on_accept(qapp):
    model = PerlinNoiseTransformModel(
        curve_mode="bezier",
        curve_points=((0.0, 0.0), (0.5, 1.0), (1.0, 0.0)),
        sample_count=5,
        manual_sampling=True,
    )
    dialog = create_perlin_noise_transform_dialog(model, parent=None)
    dialog._accept()

    restored = dialog.update_model()
    assert len(restored.frequencies) == 5
    assert len(restored.amplitudes) == 5
    assert restored.curve_points == model.curve_points
    dialog.close()


def test_bezier_graph_anchors_curve_to_frequency_range(qapp):
    graph = FrequencyAmplitudeGraph(
        frequencies=(2, 8),
        amplitudes=(0.0, 1.0),
        curve_points=((0.2, 0.1), (0.5, 0.8), (0.8, 0.3)),
        curve_mode="bezier",
    )
    graph.set_curve_mode("bezier")

    assert graph.serialized_curve_points()[0][0] == 0.0
    assert graph.serialized_curve_points()[-1][0] == 1.0


def test_bezier_graph_can_add_control_points(qapp):
    graph = FrequencyAmplitudeGraph(
        frequencies=(1, 8),
        amplitudes=(0.0, 1.0),
        curve_points=((0.0, 0.0), (1.0, 1.0)),
        curve_mode="bezier",
    )

    assert graph.add_curve_point((0.5, 0.75))
    points = graph.serialized_curve_points()
    assert len(points) == 3
    assert points[1] == (0.5, 0.75)


def test_bezier_double_click_removes_interior_anchor_but_not_endpoints(qapp):
    graph = FrequencyAmplitudeGraph(
        curve_points=((0.0, 0.0), (0.5, 0.75), (1.0, 1.0)),
        curve_mode="bezier",
    )
    graph.resize(360, 230)

    graph.mouseDoubleClickEvent(
        QMouseEvent(
            QEvent.Type.MouseButtonDblClick,
            QPointF(graph._to_pixel(0.5, 0.75)),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    assert graph.serialized_curve_points() == ((0.0, 0.0), (1.0, 1.0))

    graph.mouseDoubleClickEvent(
        QMouseEvent(
            QEvent.Type.MouseButtonDblClick,
            QPointF(graph._to_pixel(0.0, 0.0)),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    assert graph.serialized_curve_points() == ((0.0, 0.0), (1.0, 1.0))


def test_bezier_interior_point_can_move_horizontally_without_overshoot(qapp):
    graph = FrequencyAmplitudeGraph(
        frequencies=(1, 8),
        amplitudes=(0.0, 1.0, 0.0),
        curve_points=((0.0, 0.0), (0.5, 1.0), (1.0, 0.0)),
        curve_mode="bezier",
    )
    graph.resize(360, 230)
    graph._drag_index = 1
    graph._update_drag(graph._to_pixel(0.25, 0.6))

    points = graph.serialized_curve_points()
    values = graph.sampled_values(65)
    assert points[1][0] == 0.25
    assert min(values) >= 0.0
    assert max(values) <= 1.0


def test_bezier_moving_anchor_translates_its_control_points(qapp):
    graph = FrequencyAmplitudeGraph(
        curve_points=((0.0, 0.0), (0.5, 0.5), (1.0, 0.0)),
        curve_mode="bezier",
        curve_handles=(
            None,
            ((0.35, 0.4), (0.65, 0.6)),
            None,
        ),
    )
    graph.resize(360, 230)
    graph._drag_index = 1
    graph._update_drag(graph._to_pixel(0.6, 0.7))

    left, right = graph.curve_handles[1]
    assert left.x() == pytest.approx(0.45)
    assert left.y() == pytest.approx(0.6)
    assert right.x() == pytest.approx(0.75)
    assert right.y() == pytest.approx(0.8)


def test_bezier_point_is_inserted_in_x_order_and_stays_in_segment_range(qapp):
    graph = FrequencyAmplitudeGraph(
        frequencies=(1, 8),
        amplitudes=(0.0, 1.0),
        curve_points=((0.0, 0.0), (1.0, 0.2)),
        curve_mode="bezier",
    )

    assert graph.add_curve_point((0.75, 1.0))
    assert graph.add_curve_point((0.25, 0.8))
    points = graph.serialized_curve_points()
    values = graph.sampled_values(101)

    assert [point[0] for point in points] == [0.0, 0.25, 0.75, 1.0]
    assert min(values) >= 0.0
    assert max(values) <= 1.0


def test_bezier_double_click_inserts_point_in_empty_graph_space(qapp):
    graph = FrequencyAmplitudeGraph(
        curve_points=((0.0, 0.0), (1.0, 1.0)),
        curve_mode="bezier",
    )
    graph.resize(360, 230)
    graph.show()
    qapp.processEvents()
    graph.mouseDoubleClickEvent(
        QMouseEvent(
            QEvent.Type.MouseButtonDblClick,
            QPointF(graph._to_pixel(0.5, 0.5)),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    qapp.processEvents()

    assert graph.serialized_curve_points() == ((0.0, 0.0), (0.5, 0.5), (1.0, 1.0))
    graph.close()


def test_bezier_right_drag_mirrors_anchor_handles(qapp):
    graph = FrequencyAmplitudeGraph(
        curve_points=((0.0, 0.0), (0.5, 0.5), (1.0, 0.0)),
        curve_mode="bezier",
    )
    graph.resize(360, 230)
    graph._handle_drag_index = 1
    graph._update_handle_drag(graph._to_pixel(0.65, 0.8))

    left, right = graph.curve_handles[1]
    anchor = graph.curve_points[1]
    assert right.x() - anchor.x() == anchor.x() - left.x()
    assert right.y() - anchor.y() == anchor.y() - left.y()


def test_bezier_right_drag_can_edit_endpoint_handles(qapp):
    graph = FrequencyAmplitudeGraph(
        curve_points=((0.0, 0.5), (1.0, 0.5)),
        curve_mode="bezier",
    )
    graph.resize(360, 230)
    graph._handle_drag_index = 0
    graph._update_handle_drag(graph._to_pixel(0.2, 0.8))

    left, right = graph.curve_handles[0]
    anchor = graph.curve_points[0]
    assert right.x() > anchor.x()
    assert right.y() > anchor.y()
    assert left.x() < anchor.x()
    assert left.y() < anchor.y()


def test_bezier_anchor_drag_preserves_other_control_points(qapp):
    graph = FrequencyAmplitudeGraph(
        curve_points=((0.0, 0.0), (0.5, 0.5), (1.0, 0.0)),
        curve_mode="bezier",
        curve_handles=(
            None,
            ((0.35, 0.4), (0.65, 0.6)),
            ((0.8, 0.2), (1.2, -0.2)),
        ),
    )
    graph.resize(360, 230)
    untouched = graph._effective_handles()[2]
    graph._drag_index = 1
    graph._update_drag(graph._to_pixel(0.6, 0.7))

    assert graph._effective_handles()[2] == untouched


def test_bezier_anchor_right_drag_direction_selects_matching_handle(qapp):
    graph = FrequencyAmplitudeGraph(
        curve_points=((0.0, 0.0), (0.5, 0.5), (1.0, 0.0)),
        curve_mode="bezier",
    )
    graph.resize(360, 230)
    graph._handle_drag_index = 1
    graph._handle_drag_side = None
    graph._update_handle_drag(graph._to_pixel(0.65, 0.8))

    assert graph._handle_drag_side == 1

    graph._handle_drag_index = 1
    graph._handle_drag_side = None
    graph._update_handle_drag(graph._to_pixel(0.35, 0.2))

    assert graph._handle_drag_side == 0


def test_bezier_anchor_press_defers_handle_selection_until_drag_direction(qapp):
    graph = FrequencyAmplitudeGraph(
        curve_points=((0.0, 0.0), (0.5, 0.5), (1.0, 0.0)),
        curve_mode="bezier",
    )
    graph.resize(360, 230)
    anchor_position = graph._to_pixel(0.5, 0.5)
    graph.mousePressEvent(
        QMouseEvent(
            QEvent.Type.MouseButtonPress,
            anchor_position,
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )

    assert graph._handle_drag_index == 1
    assert graph._handle_drag_side is None
    graph._update_handle_drag(graph._to_pixel(0.7, 0.7))
    assert graph._handle_drag_side == 1


def test_bezier_handle_side_uses_motion_from_initial_click(qapp):
    graph = FrequencyAmplitudeGraph(
        curve_points=((0.0, 0.0), (0.5, 0.5), (1.0, 0.0)),
        curve_mode="bezier",
    )
    graph.resize(360, 230)
    graph._handle_drag_index = 1
    graph._handle_drag_side = None
    graph._handle_drag_origin_x = 0.6
    graph._update_handle_drag(graph._to_pixel(0.55, 0.7))

    assert graph._handle_drag_side == 0


def test_perlin_transform_object_registers_under_transform_root(qapp):
    transform = PerlinNoiseTransformModel(name="Bands").to_object()
    transform.add_to_tree(TreeModel(root_objects.get_nodes()), parent=transform_root)

    assert isinstance(transform, PerlinNoiseTransformObject)
    assert transform.node in transform_root.children
    transform.remove_from_tree()

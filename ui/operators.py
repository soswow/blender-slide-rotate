"""Slide Rotate modal operator and development reload."""

from __future__ import annotations

import bmesh
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy_extras import view3d_utils
from mathutils import Matrix, Vector

from ..core.axis import (
    lock_axis_overlay_letter,
    lock_label,
    locked_axis_vector,
    mouse_angle_axis_sign,
    press_axis_key,
    view_toward_camera,
)
from ..core.geometry import apply_vertex_theta, build_vertex_state, transformed_world
from ..core.input import (
    apply_precision,
    format_status_text,
    mouse_delta_fallback,
    numeric_handle_key,
    numeric_value_radians,
    screen_angle,
    select_snap_increment,
    snap_angle,
    wrap_angle_delta,
)
from ..core.transforms import choose_pivot, local_from_world, world_from_local
from ..core.types import AxisLockState, NumericInput, VertexRailState
from ..core.vec import Mat3, Mat4, Vec3, identity_mat3, invert_affine_mat4, normalize
from . import overlay

# Faces whose normals align this closely are one island for borrowed rails.
_COPLANAR_DOT = 0.999


def _vec(values) -> Vec3:
    return (float(values[0]), float(values[1]), float(values[2]))


def _mat4(matrix: Matrix) -> Mat4:
    return tuple(tuple(float(matrix[row][col]) for col in range(4)) for row in range(4))


def _mat3(matrix: Matrix) -> Mat3:
    return tuple(tuple(float(matrix[row][col]) for col in range(3)) for row in range(3))


def _coplanar_face_island(start_face: bmesh.types.BMFace) -> set[bmesh.types.BMFace]:
    """Walk edge-adjacent faces that share ``start_face``'s plane."""
    ref = start_face.normal.copy()
    if ref.length_squared < 1e-16:
        return {start_face}
    ref.normalize()
    island: set[bmesh.types.BMFace] = set()
    stack = [start_face]
    while stack:
        face = stack.pop()
        if face in island:
            continue
        normal = face.normal
        if normal.length_squared < 1e-16:
            continue
        if abs(normal.normalized().dot(ref)) < _COPLANAR_DOT:
            continue
        island.add(face)
        for edge in face.edges:
            stack.extend(edge.link_faces)
    return island


def _borrowed_rail_worlds(
    vert: bmesh.types.BMVert,
    selected_ids: set[int],
    matrix_world: Mat4,
) -> list[Vec3]:
    """Copy leaving-edge offsets from the coplanar face island onto ``vert``.

    A vertex sitting inside a subdivided face has only in-face neighbors. The
    boundary of that same planar region usually has edges going through the
    volume; those directions are the rails the interior vertex is missing.
    """
    if not vert.link_faces:
        return []
    seen_faces: set[bmesh.types.BMFace] = set()
    islands: list[set[bmesh.types.BMFace]] = []
    for face in vert.link_faces:
        if face in seen_faces:
            continue
        island = _coplanar_face_island(face)
        seen_faces.update(island)
        islands.append(island)

    targets: list[Vec3] = []
    seen_offsets: set[tuple[float, float, float]] = set()
    for island in islands:
        island_vert_ids = {island_vert.index for face in island for island_vert in face.verts}
        for face in island:
            for island_vert in face.verts:
                for edge in island_vert.link_edges:
                    far = edge.other_vert(island_vert)
                    if far is None or far.index in island_vert_ids:
                        continue
                    if far.index in selected_ids:
                        continue
                    offset = far.co - island_vert.co
                    key = (round(offset.x, 6), round(offset.y, 6), round(offset.z, 6))
                    if key in seen_offsets:
                        continue
                    seen_offsets.add(key)
                    target_local = _vec(vert.co + offset)
                    targets.append(world_from_local(target_local, matrix_world))
    return targets


def _view_axis(rv3d) -> Vec3:
    if rv3d is None:
        return (0.0, 0.0, 1.0)
    axis = rv3d.view_rotation @ Vector((0.0, 0.0, 1.0))
    unit = normalize(_vec(axis))
    return unit if unit is not None else (0.0, 0.0, 1.0)


def _active_world(bm: bmesh.types.BMesh, matrix_world: Mat4) -> Vec3 | None:
    active = bm.select_history.active
    if isinstance(active, bmesh.types.BMVert):
        return world_from_local(_vec(active.co), matrix_world)
    if isinstance(active, bmesh.types.BMEdge):
        midpoint = (active.verts[0].co + active.verts[1].co) * 0.5
        return world_from_local(_vec(midpoint), matrix_world)
    if isinstance(active, bmesh.types.BMFace):
        return world_from_local(_vec(active.calc_center_median()), matrix_world)
    return None


def _orientation_matrix(context: bpy.types.Context, bm: bmesh.types.BMesh, matrix_world: Matrix) -> tuple[str, Mat3]:
    slot = context.scene.transform_orientation_slots[0]
    kind = slot.type
    rv3d = context.region_data
    if kind == "GLOBAL":
        return kind, identity_mat3()
    if kind == "LOCAL":
        return kind, _mat3(matrix_world.to_3x3())
    if kind == "VIEW" and rv3d is not None:
        return kind, _mat3(rv3d.view_rotation.to_matrix())
    if kind == "CURSOR":
        return kind, _mat3(context.scene.cursor.matrix.to_3x3())
    if kind == "NORMAL":
        total = Vector((0.0, 0.0, 0.0))
        count = 0
        rotation = matrix_world.to_3x3()
        for vert in bm.verts:
            if not vert.select:
                continue
            total += rotation @ vert.normal
            count += 1
        if count == 0 or total.length_squared < 1e-16:
            return kind, _mat3(matrix_world.to_3x3())
        normal = total.normalized()
        helper = Vector((0.0, 0.0, 1.0)) if abs(normal.z) < 0.9 else Vector((0.0, 1.0, 0.0))
        tangent = normal.cross(helper).normalized()
        bitangent = normal.cross(tangent)
        return kind, _mat3(Matrix((tangent, bitangent, normal)).transposed())
    custom = getattr(slot, "custom_orientation", None)
    if custom is not None:
        return kind, _mat3(custom.matrix)
    return kind, identity_mat3()


class MESH_OT_slide_rotate(bpy.types.Operator):
    """Rotate the selection around the pivot while vertices slide on connected rails."""

    bl_idname = "mesh.slide_rotate"
    bl_label = "Slide Rotate"
    bl_options = {"REGISTER", "UNDO", "GRAB_CURSOR", "BLOCKING"}
    bl_description = (
        "Rotate selected vertices around the transform pivot while each vertex "
        "slides along an automatically chosen connected edge"
    )

    angle: FloatProperty(
        name="Angle",
        description="Shared rotation angle",
        default=0.0,
        subtype="ANGLE",
    )
    extend_rails: BoolProperty(
        name="Extend Rails",
        description="Allow sliding past the physical guide edge (disable to clamp)",
        default=True,
    )
    lock_letter: EnumProperty(
        name="Axis",
        items=(
            ("NONE", "View", "Rotate in the view plane"),
            ("X", "X", "Lock to X"),
            ("Y", "Y", "Lock to Y"),
            ("Z", "Z", "Lock to Z"),
        ),
        default="NONE",
    )
    lock_stage: IntProperty(
        name="Axis Stage",
        description="0=view, 1=current orientation, 2=global/local flip",
        default=0,
        min=0,
        max=2,
    )

    def draw(self, _context: bpy.types.Context) -> None:
        layout = self.layout
        layout.prop(self, "angle")
        layout.prop(self, "extend_rails")
        layout.prop(self, "lock_letter")

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = context.edit_object
        return obj is not None and obj.type == "MESH" and context.mode == "EDIT_MESH"

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        space = context.space_data
        if space is None or space.type != "VIEW_3D" or context.region_data is None:
            self.report({"WARNING"}, "Slide Rotate requires a 3D Viewport")
            return {"CANCELLED"}
        self.lock_letter = "NONE"
        self.lock_stage = 0
        self.angle = 0.0
        if not self._prepare(context):
            return {"CANCELLED"}
        self._numeric = NumericInput()
        self._start_mouse_x = float(event.mouse_region_x)
        self._start_mouse_y = float(event.mouse_region_y)
        region = context.region
        rv3d = context.region_data
        projected = view3d_utils.location_3d_to_region_2d(
            region,
            rv3d,
            Vector(self._pivot),
        )
        if projected is None:
            self._pivot_2d = None
            self._initial_screen_angle = None
        else:
            self._pivot_2d = (float(projected.x), float(projected.y))
            self._initial_screen_angle = screen_angle(
                self._start_mouse_x,
                self._start_mouse_y,
                self._pivot_2d[0],
                self._pivot_2d[1],
            )
        self._sync_overlay()
        overlay.ensure_draw_handler()
        context.window.cursor_modal_set("SCROLL_XY")
        context.window_manager.modal_handler_add(self)
        self._update_header(context)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            return self._cancel(context)
        if event.type in {"LEFTMOUSE", "RET", "NUMPAD_ENTER"} and event.value == "PRESS":
            return self._confirm(context)
        if event.type == "C" and event.value == "PRESS" and not event.ctrl and not event.alt:
            self.extend_rails = not self.extend_rails
            self._sync_overlay()
            self._apply(context)
            self._update_header(context)
            return {"RUNNING_MODAL"}
        if event.type in {"X", "Y", "Z"} and event.value == "PRESS" and not event.ctrl and not event.oskey:
            state = press_axis_key(self._axis_state, event.type)
            self._axis_state = state
            self.lock_letter = state.letter if state.letter is not None else "NONE"
            self.lock_stage = state.stage
            # Rails depend on the rotational tangent, so lock must re-score
            # (face-interior through-rails only win for the matching axis).
            self._restore(context)
            if not self._prepare(context):
                return self._cancel(context)
            self._sync_overlay()
            if not self._numeric.active:
                self.angle = self._theta_from_mouse(context, event)
            self._apply(context)
            self._update_header(context)
            return {"RUNNING_MODAL"}
        if event.value == "PRESS":
            unicode_char = event.unicode or ""
            handled, numeric = numeric_handle_key(self._numeric, event.type, unicode_char)
            if handled:
                self._numeric = numeric
                typed = numeric_value_radians(numeric)
                if typed is not None:
                    self.angle = typed
                    self._apply(context)
                self._update_header(context)
                return {"RUNNING_MODAL"}
        if event.type == "MOUSEMOVE" and not self._numeric.active:
            self.angle = self._theta_from_mouse(context, event)
            self._apply(context)
            self._update_header(context)
            return {"RUNNING_MODAL"}
        return {"RUNNING_MODAL"}

    def execute(self, context: bpy.types.Context):
        if not self._prepare(context):
            return {"CANCELLED"}
        self._apply(context)
        return {"FINISHED"}

    def cancel(self, context: bpy.types.Context) -> None:
        self._restore(context)
        self._teardown_modal(context)

    def _axis_state_from_props(self) -> AxisLockState:
        if self.lock_letter == "NONE":
            return AxisLockState()
        return AxisLockState(letter=self.lock_letter, stage=int(self.lock_stage) or 1)

    def _prepare(self, context: bpy.types.Context) -> bool:
        obj = context.edit_object
        if obj is None or obj.type != "MESH":
            self.report({"ERROR"}, "Slide Rotate requires a mesh in Edit Mode")
            return False
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        bm.verts.ensure_lookup_table()
        selected = [vert for vert in bm.verts if vert.select]
        if not selected:
            self.report({"ERROR"}, "No vertices selected")
            return False
        matrix_world = obj.matrix_world.copy()
        self._matrix_world = _mat4(matrix_world)
        self._matrix_inv = invert_affine_mat4(self._matrix_world)
        self._local_matrix = _mat3(matrix_world.to_3x3())
        self._orientation_name, self._orientation_matrix = _orientation_matrix(
            context,
            bm,
            matrix_world,
        )
        self._view_axis = _view_axis(context.region_data)
        self._axis_state = self._axis_state_from_props()
        axis = locked_axis_vector(
            self._axis_state,
            self._view_axis,
            self._orientation_name,
            self._orientation_matrix,
            self._local_matrix,
        )
        worlds = [world_from_local(_vec(vert.co), self._matrix_world) for vert in selected]
        cursor = _vec(context.scene.cursor.location)
        active = _active_world(bm, self._matrix_world)
        pivot_mode = context.tool_settings.transform_pivot_point
        pivot = choose_pivot(pivot_mode, worlds, cursor, active)
        if pivot is None:
            self.report({"ERROR"}, "Could not determine transform pivot")
            return False
        self._pivot = pivot
        states: list[VertexRailState] = []
        selected_ids = {vert.index for vert in selected}
        for vert in selected:
            neighbors: list[Vec3] = []
            for edge in vert.link_edges:
                other = edge.other_vert(vert)
                if other is None or other.index in selected_ids:
                    continue
                neighbors.append(world_from_local(_vec(other.co), self._matrix_world))
            local = _vec(vert.co)
            world = world_from_local(local, self._matrix_world)
            borrowed = _borrowed_rail_worlds(vert, selected_ids, self._matrix_world)
            states.append(
                build_vertex_state(vert.index, local, world, neighbors, pivot, axis, borrowed)
            )
        self._states = states
        self._frozen_count = sum(0 if state.movable else 1 for state in states)
        self._numeric = getattr(self, "_numeric", NumericInput())
        return True

    def _current_axis(self) -> Vec3:
        return locked_axis_vector(
            self._axis_state,
            self._view_axis,
            self._orientation_name,
            self._orientation_matrix,
            self._local_matrix,
        )

    def _view_toward_camera(self, context: bpy.types.Context) -> Vec3:
        rv3d = context.region_data
        camera_location = None
        perspective = False
        if rv3d is not None:
            perspective = bool(getattr(rv3d, "is_perspective", False))
            try:
                camera_location = _vec(rv3d.view_matrix.inverted().translation)
            except ValueError:
                camera_location = None
        return view_toward_camera(
            self._view_axis,
            self._pivot,
            camera_location,
            perspective,
        )

    def _theta_from_mouse(self, context: bpy.types.Context, event: bpy.types.Event) -> float:
        # Screen CCW around the projected pivot. Axis lock may flip the sign so a
        # lock axis pointing away from the camera still follows the mouse.
        precision = bool(event.shift)
        snap = bool(event.ctrl)
        increment = select_snap_increment(
            snap,
            precision,
            float(context.tool_settings.snap_angle_increment_3d),
            float(context.tool_settings.snap_angle_increment_3d_precision),
        )
        mouse_x = float(event.mouse_region_x)
        mouse_y = float(event.mouse_region_y)
        if self._pivot_2d is None or self._initial_screen_angle is None:
            delta = mouse_delta_fallback(self._start_mouse_x, mouse_x)
            theta = apply_precision(delta, precision)
        else:
            current = screen_angle(mouse_x, mouse_y, self._pivot_2d[0], self._pivot_2d[1])
            if current is None:
                delta = mouse_delta_fallback(self._start_mouse_x, mouse_x)
                theta = apply_precision(delta, precision)
            else:
                delta = wrap_angle_delta(self._initial_screen_angle, current)
                theta = apply_precision(delta, precision)
        if self._axis_state.stage != 0 and self._axis_state.letter is not None:
            theta *= mouse_angle_axis_sign(
                self._current_axis(),
                self._view_toward_camera(context),
            )
        if increment is not None:
            theta = snap_angle(theta, increment)
        return theta

    def _apply(self, context: bpy.types.Context) -> None:
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        axis = self._current_axis()
        for state in self._states:
            apply_vertex_theta(state, self._pivot, axis, float(self.angle), bool(self.extend_rails))
            vert = bm.verts[state.index]
            local = local_from_world(
                transformed_world(state),
                self._matrix_world,
                self._matrix_inv,
            )
            vert.co = Vector(local)
        bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
        self._sync_overlay()
        if context.area is not None:
            context.area.tag_redraw()

    def _restore(self, context: bpy.types.Context) -> None:
        obj = context.edit_object
        if obj is None:
            return
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        for state in getattr(self, "_states", []):
            bm.verts[state.index].co = Vector(state.original_local)
        bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)

    def _update_header(self, context: bpy.types.Context) -> None:
        if context.area is None:
            return
        context.area.header_text_set(
            format_status_text(
                float(self.angle),
                lock_label(self._axis_state, self._orientation_name),
                bool(self.extend_rails),
                self._frozen_count,
                self._numeric,
            )
        )

    def _sync_overlay(self) -> None:
        overlay.set_rails(self._states, bool(self.extend_rails))
        overlay.set_lock_axis(
            self._pivot,
            self._current_axis(),
            lock_axis_overlay_letter(self._axis_state),
        )

    def _teardown_modal(self, context: bpy.types.Context) -> None:
        overlay.remove_draw_handler()
        if context.area is not None:
            context.area.header_text_set(None)
        if context.window is not None:
            context.window.cursor_modal_restore()
        if context.area is not None:
            context.area.tag_redraw()

    def _confirm(self, context: bpy.types.Context):
        typed = numeric_value_radians(self._numeric)
        if typed is not None:
            self.angle = typed
            self._apply(context)
        self._teardown_modal(context)
        return {"FINISHED"}

    def _cancel(self, context: bpy.types.Context):
        self._restore(context)
        self._teardown_modal(context)
        return {"CANCELLED"}


class SR_OT_reload(bpy.types.Operator):
    """Dev helper: unregister, reload modules from disk, and register again."""

    bl_idname = "slide_rotate.reload"
    bl_label = "Reload Slide Rotate"
    bl_description = (
        "Reload this extension from disk after the current UI event finishes. "
        "Only available when the extension is a linked git checkout."
    )
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, _context: bpy.types.Context) -> bool:
        from .. import is_dev_install

        return is_dev_install()

    def execute(self, _context: bpy.types.Context):
        from .. import schedule_reload

        if not schedule_reload():
            self.report({"WARNING"}, "Slide Rotate reload already queued")
            return {"CANCELLED"}
        self.report({"INFO"}, "Slide Rotate reload queued")
        return {"FINISHED"}


def _draw_mesh_menu(self, _context: bpy.types.Context) -> None:
    self.layout.operator(MESH_OT_slide_rotate.bl_idname, text="Slide Rotate")


def _draw_transform_menu(self, context: bpy.types.Context) -> None:
    # VIEW3D_MT_transform is shared with curve/lattice/etc.; only show in mesh Edit Mode.
    if getattr(context, "mode", None) != "EDIT_MESH":
        return
    _draw_mesh_menu(self, context)


CLASSES = (
    MESH_OT_slide_rotate,
    SR_OT_reload,
)


def _menu_draws() -> tuple[tuple[type, object], ...]:
    return (
        (bpy.types.VIEW3D_MT_transform, _draw_transform_menu),
        (bpy.types.VIEW3D_MT_edit_mesh_vertices, _draw_mesh_menu),
        (bpy.types.VIEW3D_MT_edit_mesh_edges, _draw_mesh_menu),
    )


def register_menus() -> None:
    for menu, draw in _menu_draws():
        menu.append(draw)


def unregister_menus() -> None:
    for menu, draw in _menu_draws():
        try:
            menu.remove(draw)
        except (ValueError, AttributeError):
            pass

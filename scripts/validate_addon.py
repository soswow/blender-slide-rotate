"""Headless Blender 5.1 registration, keymap, poll, execute, and reload smoke."""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import bmesh
import bpy


def load_extension_module():
    extension_directory = Path(__file__).resolve().parents[1]
    module_name = "slide_tools"
    spec = importlib.util.spec_from_file_location(
        module_name,
        extension_directory / "__init__.py",
        submodule_search_locations=[str(extension_directory)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _assert_keymap(extension) -> None:
    assert len(extension._addon_keymaps) == 1
    _keymap, item = extension._addon_keymaps[0]
    assert item.idname == "wm.call_menu_pie"
    assert item.type == "R"
    assert item.shift and item.alt
    assert not item.ctrl
    assert item.properties.name == "VIEW3D_MT_slide_pie"


def _assert_face_interior_through_rails() -> None:
    """Interior vert on a subdivided face slides on borrowed through-rails around X."""
    mesh = bpy.data.meshes.new("slide_tools_interior")
    obj = bpy.data.objects.new("slide_tools_interior", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    builder = bmesh.new()
    # 3x3 grid on y=1; index 4 is the interior vertex.
    face_coords = [(x, 1.0, z) for z in (-1.0, 0.0, 1.0) for x in (-1.0, 0.0, 1.0)]
    face_verts = [builder.verts.new(coord) for coord in face_coords]
    for row in range(2):
        for col in range(2):
            index = row * 3 + col
            builder.faces.new(
                (face_verts[index], face_verts[index + 1], face_verts[index + 4], face_verts[index + 3])
            )
    for index, vert in enumerate(face_verts):
        if index == 4:
            continue
        far = builder.verts.new((vert.co.x, -1.0, vert.co.z))
        builder.edges.new((vert, far))
    builder.to_mesh(mesh)
    builder.free()

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    bpy.context.tool_settings.transform_pivot_point = "CURSOR"
    bpy.context.scene.cursor.location = (1.0, 1.0, -1.0)
    edit_mesh = bmesh.from_edit_mesh(mesh)
    edit_mesh.select_mode = {"VERT"}
    edit_mesh.verts.ensure_lookup_table()
    for face in edit_mesh.faces:
        face.select = False
    for edge in edit_mesh.edges:
        edge.select = False
    for vert in edit_mesh.verts:
        vert.select = abs(vert.co.y - 1.0) < 1e-8
    bmesh.update_edit_mesh(mesh)

    bpy.ops.mesh.slide_tools(
        angle=math.radians(20.0),
        extend_rails=True,
        lock_letter="X",
        lock_stage=1,
    )
    edit_mesh = bmesh.from_edit_mesh(mesh)
    edit_mesh.verts.ensure_lookup_table()
    interior = next(vert for vert in edit_mesh.verts if abs(vert.co.x) < 1e-8 and abs(vert.co.z) < 1e-8)
    assert abs(float(interior.co.x)) < 1e-5
    assert abs(float(interior.co.z)) < 1e-5
    assert abs(float(interior.co.y) - 1.0) > 1e-4
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.tool_settings.transform_pivot_point = "MEDIAN_POINT"


def _assert_scale_along_radial_rails() -> None:
    """Opposite verts on X slide further out when scale factor is 2."""
    mesh = bpy.data.meshes.new("slide_scale_probe")
    obj = bpy.data.objects.new("slide_scale_probe", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    builder = bmesh.new()
    coords = ((-2.0, 0.0, 0.0), (-1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0))
    verts = [builder.verts.new(coord) for coord in coords]
    builder.edges.new((verts[0], verts[1]))
    builder.edges.new((verts[2], verts[3]))
    builder.to_mesh(mesh)
    builder.free()

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    bpy.context.tool_settings.transform_pivot_point = "MEDIAN_POINT"
    edit_mesh = bmesh.from_edit_mesh(mesh)
    edit_mesh.select_mode = {"VERT"}
    edit_mesh.verts.ensure_lookup_table()
    for vert in edit_mesh.verts:
        vert.select = abs(abs(vert.co.x) - 1.0) < 1e-8
    bmesh.update_edit_mesh(mesh)

    bpy.ops.mesh.slide_tools(mode="SCALE", factor=2.0, extend_rails=True)
    edit_mesh = bmesh.from_edit_mesh(mesh)
    edit_mesh.verts.ensure_lookup_table()
    xs = sorted(float(vert.co.x) for vert in edit_mesh.verts if vert.select)
    assert abs(xs[0] + 2.0) < 1e-5
    assert abs(xs[1] - 2.0) < 1e-5
    bpy.ops.object.mode_set(mode="OBJECT")


def _assert_flatten_along_normal_rails() -> None:
    """Lifted vert with a Z rail lands on Z=0 at flatten factor 1 with Z lock."""
    mesh = bpy.data.meshes.new("slide_flatten_probe")
    obj = bpy.data.objects.new("slide_flatten_probe", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    builder = bmesh.new()
    coords = ((0.0, 0.0, 0.0), (0.0, 0.0, 2.0), (2.0, 0.0, 0.0), (2.0, 2.0, 0.0))
    verts = [builder.verts.new(coord) for coord in coords]
    builder.edges.new((verts[0], verts[1]))
    builder.faces.new((verts[0], verts[2], verts[3]))
    builder.to_mesh(mesh)
    builder.free()

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    bpy.context.tool_settings.transform_pivot_point = "CURSOR"
    bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
    edit_mesh = bmesh.from_edit_mesh(mesh)
    edit_mesh.select_mode = {"VERT"}
    edit_mesh.verts.ensure_lookup_table()
    for vert in edit_mesh.verts:
        vert.select = abs(vert.co.z - 2.0) < 1e-8
    bmesh.update_edit_mesh(mesh)

    bpy.ops.mesh.slide_tools(
        mode="FLATTEN",
        factor=1.0,
        extend_rails=True,
        lock_letter="Z",
        lock_stage=1,
    )
    edit_mesh = bmesh.from_edit_mesh(mesh)
    edit_mesh.verts.ensure_lookup_table()
    lifted = next(vert for vert in edit_mesh.verts if vert.select)
    assert abs(float(lifted.co.x)) < 1e-5
    assert abs(float(lifted.co.y)) < 1e-5
    assert abs(float(lifted.co.z)) < 1e-5
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.tool_settings.transform_pivot_point = "MEDIAN_POINT"
    bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)


def _build_loop_with_rails() -> bpy.types.Object:
    mesh = bpy.data.meshes.new("slide_tools_probe")
    obj = bpy.data.objects.new("slide_tools_probe", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    builder = bmesh.new()
    coords = (
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (2.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, 1.0, 0.0),
        (2.0, 1.0, 0.0),
    )
    verts = [builder.verts.new(coord) for coord in coords]
    builder.faces.new((verts[0], verts[1], verts[4], verts[3]))
    builder.faces.new((verts[1], verts[2], verts[5], verts[4]))
    builder.to_mesh(mesh)
    builder.free()
    return obj


def main() -> None:
    extension = load_extension_module()
    registered = False
    try:
        extension.register()
        registered = True
        _assert_keymap(extension)
        from slide_tools.core.input import modal_status_hints
        from slide_tools.ui import operators as operators_module
        from slide_tools.ui.operators import MESH_OT_slide_tools, VIEW3D_MT_slide_pie

        hints = modal_status_hints(True)
        assert ("EVENT_X",) in {icons for icons, _label in hints}
        assert MESH_OT_slide_tools._set_status_bar is not None
        assert VIEW3D_MT_slide_pie.bl_idname == "VIEW3D_MT_slide_pie"
        from slide_tools.ui import overlay as overlay_module

        for menu, draw in operators_module._menu_draws():
            assert draw in menu.draw._draw_funcs

        assert not MESH_OT_slide_tools.poll(bpy.context)

        obj = _build_loop_with_rails()
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.context.tool_settings.mesh_select_mode = (True, False, False)
        mesh = obj.data
        edit_mesh = bmesh.from_edit_mesh(mesh)
        edit_mesh.select_mode = {"VERT"}
        edit_mesh.verts.ensure_lookup_table()
        for face in edit_mesh.faces:
            face.select = False
        for edge in edit_mesh.edges:
            edge.select = False
        for vert in edit_mesh.verts:
            vert.select = abs(vert.co.y) < 1e-8
        bmesh.update_edit_mesh(mesh)
        assert MESH_OT_slide_tools.poll(bpy.context)

        bpy.ops.mesh.slide_tools(angle=math.radians(20.0), extend_rails=True)
        edit_mesh = bmesh.from_edit_mesh(mesh)
        edit_mesh.verts.ensure_lookup_table()
        left_y = float(edit_mesh.verts[0].co.y)
        mid_y = float(edit_mesh.verts[1].co.y)
        right_y = float(edit_mesh.verts[2].co.y)
        assert abs(mid_y) < 1e-5
        assert abs(left_y) > 1e-4
        assert abs(right_y) > 1e-4
        assert left_y * right_y < 0.0

        overlay_module.set_lock_axis((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), "X")
        overlay_module.ensure_draw_handler()
        overlay_module.remove_draw_handler()
        overlay_module.remove_draw_handler()

        bpy.ops.object.mode_set(mode="OBJECT")
        assert not MESH_OT_slide_tools.poll(bpy.context)

        _assert_face_interior_through_rails()
        assert not MESH_OT_slide_tools.poll(bpy.context)

        _assert_scale_along_radial_rails()
        assert not MESH_OT_slide_tools.poll(bpy.context)

        _assert_flatten_along_normal_rails()
        assert not MESH_OT_slide_tools.poll(bpy.context)

        extension.unregister()
        registered = False
        assert not extension._addon_keymaps
        extension.register()
        registered = True
        _assert_keymap(extension)
        bpy.ops.object.mode_set(mode="EDIT")
        assert MESH_OT_slide_tools.poll(bpy.context)
        print("Slide Tools validate_addon: ok")
    finally:
        if registered:
            extension.unregister()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)

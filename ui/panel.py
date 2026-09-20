"""Tiny N-panel: invoke Slide Tools, plus a development reload button."""

from __future__ import annotations

import bpy


class VIEW3D_PT_slide_tools(bpy.types.Panel):
    """3D View sidebar tab with the operators and optional reload."""

    bl_label = "Slide Tools"
    bl_idname = "VIEW3D_PT_slide_tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Slide Tools"

    def draw(self, _context: bpy.types.Context) -> None:
        layout = self.layout
        layout.operator_context = "INVOKE_REGION_WIN"
        column = layout.column(align=True)
        rotate = column.operator("mesh.slide_tools", text="Slide Rotate", icon="ORIENTATION_GIMBAL")
        rotate.mode = "ROTATE"
        scale = column.operator("mesh.slide_tools", text="Slide Scale", icon="FULLSCREEN_ENTER")
        scale.mode = "SCALE"
        flatten = column.operator("mesh.slide_tools", text="Slide Flatten", icon="MESH_PLANE")
        flatten.mode = "FLATTEN"
        from .. import is_dev_install

        if is_dev_install():
            layout.separator()
            layout.operator("slide_tools.reload", icon="FILE_REFRESH")


CLASSES = (VIEW3D_PT_slide_tools,)

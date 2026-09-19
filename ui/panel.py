"""Tiny N-panel: invoke Slide Rotate, plus a development reload button."""

from __future__ import annotations

import bpy


class VIEW3D_PT_slide_rotate(bpy.types.Panel):
    """3D View sidebar tab with the operator and optional reload."""

    bl_label = "Slide Rotate"
    bl_idname = "VIEW3D_PT_slide_rotate"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Slide Rotate"

    def draw(self, _context: bpy.types.Context) -> None:
        layout = self.layout
        layout.operator_context = "INVOKE_REGION_WIN"
        column = layout.column(align=True)
        rotate = column.operator("mesh.slide_rotate", text="Slide Rotate", icon="ORIENTATION_GIMBAL")
        rotate.mode = "ROTATE"
        scale = column.operator("mesh.slide_rotate", text="Slide Scale", icon="FULLSCREEN_ENTER")
        scale.mode = "SCALE"
        from .. import is_dev_install

        if is_dev_install():
            layout.separator()
            layout.operator("slide_rotate.reload", icon="FILE_REFRESH")


CLASSES = (VIEW3D_PT_slide_rotate,)

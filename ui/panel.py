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
        layout.operator("mesh.slide_rotate", icon="ORIENTATION_GIMBAL")
        from .. import is_dev_install

        if is_dev_install():
            layout.separator()
            layout.operator("slide_rotate.reload", icon="FILE_REFRESH")


CLASSES = (VIEW3D_PT_slide_rotate,)

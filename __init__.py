"""Slide Rotate Blender extension entry point."""

from __future__ import annotations

import importlib.util
import sys
import traceback
from pathlib import Path

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

if bpy is not None:
    from .ui import operators, overlay, panel
else:
    operators = overlay = panel = None

bl_info = {
    "name": "Slide Rotate",
    "author": "Aleksandr 'Sasha' Motsjonov",
    "version": (0, 1, 0),
    "blender": (5, 1, 0),
    "location": "Mesh Edit Mode > Shift+Alt+R",
    "description": "Rotate a selection around the pivot while vertices slide on connected edges",
    "category": "Mesh",
}

CLASSES = (
    (*operators.CLASSES, *panel.CLASSES)
    if bpy is not None
    else ()
)

_reload_pending = False
_addon_keymaps: list[tuple] = []


def is_dev_install() -> bool:
    """True when this package is a git checkout (``./scripts/link-dev.sh``), not a zip."""
    root = Path(__file__).resolve().parent
    return (root / "scripts" / "link-dev.sh").is_file()


def _register_keymaps() -> None:
    _unregister_keymaps()
    window_manager = bpy.context.window_manager
    if window_manager is None:
        return
    keyconfig = window_manager.keyconfigs.addon
    if keyconfig is None:
        return
    keymap = keyconfig.keymaps.new(name="Mesh", space_type="EMPTY")
    item = keymap.keymap_items.new(
        "mesh.slide_rotate",
        "R",
        "PRESS",
        shift=True,
        alt=True,
    )
    _addon_keymaps.append((keymap, item))


def _unregister_keymaps() -> None:
    for keymap, item in _addon_keymaps:
        try:
            keymap.keymap_items.remove(item)
        except (ReferenceError, RuntimeError):
            pass
    _addon_keymaps.clear()


def _register_classes() -> None:
    for cls in CLASSES:
        if getattr(cls, "is_registered", False):
            continue
        try:
            bpy.utils.register_class(cls)
        except ValueError as error:
            if "already registered" not in str(error):
                raise


def _unregister_classes() -> None:
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass


def reload_addon() -> None:
    """Unregister, purge package modules, and register a fresh disk import."""
    package_name = __package__
    if not package_name:
        raise RuntimeError("Slide Rotate reload requires a package context")
    package_path = Path(sys.modules[package_name].__file__).resolve().parent
    overlay.remove_draw_handler()
    unregister()
    prefix = package_name + "."
    for module_name in list(sys.modules):
        if module_name == package_name or module_name.startswith(prefix):
            del sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(
        package_name,
        package_path / "__init__.py",
        submodule_search_locations=[str(package_path)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not reload Slide Rotate from {package_path}")
    package = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = package
    spec.loader.exec_module(package)
    package.register()
    window_manager = bpy.context.window_manager
    if window_manager is None:
        return
    for window in window_manager.windows:
        screen = window.screen
        if screen is None:
            continue
        for area in screen.areas:
            area.tag_redraw()


def schedule_reload() -> bool:
    """Queue reload after the current operator and panel event stack returns."""
    global _reload_pending
    if _reload_pending:
        return False
    _reload_pending = True
    package_name = __package__

    def _run_reload() -> None:
        global _reload_pending
        _reload_pending = False
        try:
            package = sys.modules.get(package_name)
            if package is None:
                print(f"Slide Rotate: reload skipped; missing {package_name}")
                return None
            package.reload_addon()
            print("Slide Rotate: reloaded from disk")
        except Exception:
            print("Slide Rotate: reload failed")
            traceback.print_exc()
        return None

    bpy.app.timers.register(_run_reload, first_interval=0.35)
    return True


def register() -> None:
    _register_classes()
    operators.register_menus()
    _register_keymaps()


def unregister() -> None:
    try:
        overlay.remove_draw_handler()
    except Exception:
        traceback.print_exc()
    try:
        _unregister_keymaps()
    except Exception:
        traceback.print_exc()
    try:
        operators.unregister_menus()
    except Exception:
        traceback.print_exc()
    _unregister_classes()


if __name__ == "__main__":
    register()

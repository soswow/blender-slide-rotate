# Development

## Link a checkout

```sh
./scripts/link-dev.sh
```

That symlinks this repo to `~/Library/Application Support/Blender/5.1/extensions/user_default/slide_tools`. Enable **Slide Tools** once. After edits, click **Reload Slide Tools** at the bottom of the 3D View **Slide Tools** sidebar (or F3). Watch the system console for `Slide Tools: reloaded from disk`. Restart Blender after RNA property schema changes.

## Tests

```sh
./scripts/run-unittests.sh
"/Applications/Blender 5.1.app/Contents/MacOS/blender" \
 --factory-startup -b --python scripts/validate_addon.py
```

See [AGENTS.md](../AGENTS.md) for changelog and unit-test rules, and [MILESTONES.md](../MILESTONES.md) for session progress.

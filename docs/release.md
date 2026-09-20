# Release

On a clean `main`, with Unreleased changelog bullets and a GitHub `origin` remote:

```sh
./scripts/release.sh 0.1.0
```

That bumps `blender_manifest.toml` if needed, moves `## [Unreleased]` into a dated section, commits, tags `v0.1.0`, and pushes. The **Release** GitHub Action builds `slide_tools-0.1.0.zip` with Blender’s extension builder and publishes it on the [GitHub Release](https://github.com/soswow/blender-slide-tools/releases). Do not attach zips by hand unless Actions failed.

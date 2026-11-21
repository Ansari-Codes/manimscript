# ManimScript examples

Run an example from the project root:

```powershell
python source.py examples\intro.manim --output intro.py
```

Generated Python can then be rendered with Manim:

```powershell
manim -pql intro.py Introduction
```

Each example uses the language documented in the [project README](../README.md).

Additional examples include:

- `intro.manim` - introductory text fades
- `shapes.manim` - shape placement and motion
- `orbit.manim` - circular motion
- `logo.manim` - SVG image rendering
- `transformation.manim` - shape morphing
- `gravity.manim` - Earth's gravity, inverse-square attraction, and moon orbit

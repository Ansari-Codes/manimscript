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
- `shapes.manim` - shape placement, motion, and simultaneous `ALL DO` movement
- `orbit.manim` - circular motion
- `logo.manim` - SVG image rendering
- `transformation.manim` - shape morphing
- `gravity.manim` - Earth's gravity, inverse-square attraction, and moon orbit
- `gradient_boosting.manim` - a narrated, numeric walkthrough of gradient boosting for regression

Render the gradient-boosting lesson from the repository root:

```powershell
python source.py examples\gradient_boosting.manim --output gradient_boosting.py
manim -pql gradient_boosting.py GradientBoosting
```

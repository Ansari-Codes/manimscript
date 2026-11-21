# ManimScript

ManimScript is a small declarative language for describing animated scenes.
Write objects and a sequence of animation commands in a `.manim` file, then
use `source.py` to transpile that file into ordinary Python code for
[Manim Community Edition](https://www.manim.community/).

For a visual introduction to the language, open [`docs/index.html`](docs/index.html)
in a browser. It includes an interactive preview and a technical walkthrough
of the compiler pipeline.

```text
ManimScript source (.manim) -> source.py -> generated Python -> Manim render
```

The transpiler does not render a video itself. The generated Python is the
input to Manim.

## Features

- Define reusable text, geometric objects, images, and SVG assets.
- Describe Manim scenes with readable, ordered statements.
- Move, fade, rotate, scale, transform, and circulate objects.
- Add gTTS narration, optionally alongside scene actions.
- Keep examples in plain-text `.manim` files.

## Requirements

- Python 3.10 or later
- Manim Community Edition and its system requirements (including FFmpeg)
- gTTS for voice-over generation
- Mutagen for reading the generated MP3 duration (an estimate is used if it is
  unavailable at runtime)
- An internet connection the first time each voice-over is generated

Install the Python dependencies from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell prevents environment activation, run the virtual environment's
Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Quick start

From the repository root, transpile the gravity example:

```powershell
python source.py examples\gravity.manim --output gravity.py
```

Render its `Introduction` scene with Manim:

```powershell
manim -pql gravity.py Introduction
```

The transpiler writes generated Python to standard output if `--output` is
omitted:

```powershell
python source.py examples\intro.manim
```

`-o` is an alias for `--output`. Scene class names are derived from scene names:
for example, `SCENE "Shape Demo":` generates a `ShapeDemo` class.

## Language guide

### File layout and comments

A `.manim` file contains an optional `OBJECTS:` section followed by one or more
scenes. Statements are executed in the order written. A semicolon at the end of
a statement is optional. Blank lines and lines whose first non-space character
is `#` are ignored.

```manim
OBJECTS:
    title: { object: { type: "text", text: "Hello, Manim!" } }

SCENE "Welcome":
    PLACE title AT (0, 1);
    FADE_IN title FOR 1;
    WAIT 1;
    FADE_OUT title FOR 0.5;
```

Object names must be valid identifiers, such as `title` or `planet`. Scene names
are quoted strings. Scene names must be unique within a file.

### Objects

Define objects once and refer to them by name in scene commands:

```manim
OBJECTS:
    heading: { object: { type: "text", text: "Orbit", font_size: 56, color: BLUE } }
    planet: { object: { type: "circle", radius: 0.5, color: GOLD, fill_opacity: 1 } }
    card: { object: { type: "rectangle", width: 4, height: 2, color: GREEN } }
    mark: { source: "assets/logo.svg" }
```

Supported built-in `type` values:

| Type | Generated Manim class | Common properties |
| --- | --- | --- |
| `text` | `Text` | `text` (or `value`), `font_size`, `color` |
| `circle` | `Circle` | `radius`, `color`, `fill_opacity` |
| `square` | `Square` | `side_length`, `color`, `fill_opacity` |
| `rectangle` | `Rectangle` | `width`, `height`, `color`, `fill_opacity` |
| `dot` | `Dot` | `radius`, `color` |
| `line` | `Line` | `start`, `end`, `color` |

Use `source` instead of `object` to load a file. A path ending in `.svg` is
loaded with Manim's `SVGMobject`; other paths are loaded with `ImageMobject`.
Paths are interpreted relative to the working directory used when running
Manim. For example, the logo example refers to `assets/logo.svg`.

Additional properties are emitted as keyword arguments to the corresponding
Manim constructor. Property values may be quoted strings, numbers, booleans
(`true`/`false`), `null`, tuples, or Manim constants such as `BLUE`, `RED`,
`WHITE`, and `GOLD`. An optional `position` property sets an object's initial
position.

### Scenes and coordinates

Each `SCENE "name":` block becomes a Manim `Scene` subclass with a `construct`
method. Coordinates are Manim scene units, not pixels. Points use `(x, y)` and
are emitted as three-dimensional Manim points with `z = 0`.

```manim
SCENE "Positioning":
    PLACE heading AT (0, 2);
    PLACE planet AT (-3, 0);
    MOVE planet TO (3, 0) FOR 2;
```

Objects are instantiated at the start of each generated scene, but are not
visible until a command such as `PLACE`, `FADE_IN`, `SHOW`, or `self.add` makes
them part of the scene. Each scene gets its own instances.

### Animation and scene commands

| Statement | Behavior |
| --- | --- |
| `PLACE object AT (x, y)` | Position an object and add it to the scene immediately. |
| `MOVE object TO point FOR seconds` | Animate the object to a point. |
| `MOVE object TOWARD target FOR seconds` | Animate the object to a point or another object's center. |
| `CIRCULATE object AROUND target RADIUS r OMEGA turns FOR seconds` | Animate a circular path around a point or object's center. |
| `FADE_IN object [FOR seconds]` | Play Manim's `FadeIn`; duration defaults to 1 second. |
| `FADE_OUT object [FOR seconds]` | Play Manim's `FadeOut`; duration defaults to 1 second. |
| `ROTATE object BY degrees [FOR seconds]` | Rotate by degrees; duration defaults to 1 second. |
| `SCALE object BY factor [FOR seconds]` | Scale by a factor; duration defaults to 1 second. |
| `TRANSFORM object TO other FOR seconds` | Morph one named object into another. |
| `WAIT seconds` | Pause the scene timeline. |
| `REMOVE object` | Remove the object immediately. |
| `HIDE object` | Set opacity to zero immediately and add it to the scene. |
| `SHOW object` | Set opacity to one immediately and add it to the scene. |

`TO` and `TOWARD` both move to the specified destination. A named target means
that target object's center. For `CIRCULATE`, `OMEGA` is the number of turns
made over the animation; for example, `OMEGA 1` makes one revolution.

`RATE` can be appended to `MOVE`:

```manim
MOVE planet TO (2, 1) FOR 2 RATE LINEAR;
MOVE planet TOWARD earth FOR 2 RATE SMOOTH;
```

The accepted rate names are `LINEAR`, `SMOOTH`, `IN_OUT`, and `EASE_IN_OUT`.
`LINEAR` uses Manim's linear rate function; the remaining accepted names use
Manim's smooth rate function.

### Parallel animation groups

Use `ALL DO:` to start several animations together rather than playing each
command sequentially:

```manim
SCENE "GroupMove":
    ALL DO:
        MOVE planet TO (2, 1) FOR 2;
        MOVE moon TO (-2, 0) FOR 2;
        ROTATE title BY 90 FOR 1;
```

The block is emitted as one Manim `self.play(AnimationGroup(..., lag_ratio=0))`
call. Each animation starts at the same time and keeps its own duration; the
group finishes when its longest animation finishes. `ALL DO` accepts
animation commands: `MOVE`, `CIRCULATE`, `FADE_IN`, `FADE_OUT`, `ROTATE`,
`SCALE`, and `TRANSFORM`. Commands that act immediately or control timing,
such as `PLACE`, `REMOVE`, and `WAIT`, must remain outside the group.

### Voice-over

`SPEAK` synthesizes English speech with gTTS:

```manim
SCENE "Narrated":
    SPEAK "Gravity pulls objects toward one another.";
```

To start scene actions at the same point in the timeline as the narration, put
them under `DO:` and indent them:

```manim
SCENE "Falling Object":
    SPEAK "Earth's gravity accelerates the falling apple." DO:
        PLACE apple AT (-3, 2);
        FADE_IN apple FOR 0.5;
        MOVE apple TOWARD earth FOR 2;
```

Use `ALL DO:` after `SPEAK` when the actions should also run at the same time
as one another:

```manim
SCENE "NarratedOrbit":
    SPEAK "The moon and title move together." ALL DO:
        MOVE moon AROUND (0, 0) RADIUS 3 OMEGA 1 FOR 4;
        MOVE title TO (0, 2) FOR 2;
```

The grouped animations begin with the voice-over. The scene waits for whichever
lasts longer: the generated narration or the longest animation in the group.
`SPEAK ... ALL DO:` accepts the same animation-only commands as a regular
`ALL DO:` block.

The narration audio is added to the Manim scene before the indented commands
are emitted, so those actions play while the audio is on the timeline. The
generated scene then waits for the narration duration. gTTS needs an internet
connection to synthesize a phrase the first time. Generated MP3 files are
cached under `voiceover/` in the working directory; this folder is runtime
output and is not required as source input.

### Transitions

`TRANSITION:` may be placed between scene blocks and accepts `NONE`, `FADE`,
`CROSS_FADE`, or `WRITE`:

```manim
SCENE "First":
    WAIT 1;

TRANSITION: FADE

SCENE "Second":
    WAIT 1;
```

The current transpiler records a transition as a comment in the generated
scene. It does not yet create a visual transition effect between scenes.

## Examples

The [`examples/`](examples/) folder contains:

- [`intro.manim`](examples/intro.manim) - text and fade animations
- [`shapes.manim`](examples/shapes.manim) - shape placement and transforms
- [`orbit.manim`](examples/orbit.manim) - circular motion
- [`logo.manim`](examples/logo.manim) - loading an SVG asset
- [`transformation.manim`](examples/transformation.manim) - morphing a square
  into a circle
- [`gravity.manim`](examples/gravity.manim) - a narrated gravity lesson

The SVG used in the logo example is in [`assets/`](assets/).

## Limitations

- The language is intentionally small and line-oriented; it does not support
  variables, expressions, loops, or arbitrary Python.
- `MOVE`, `CIRCULATE`, and `TRANSFORM` currently accept the forms documented
  above.
- Transition labels are parsed but are not rendered as effects yet.
- Voice-over currently synthesizes English text. gTTS is an online service and
  requires network access when generating uncached audio.
- A `.manim` file must be transpiled before it can be rendered by Manim.

## License

This project is distributed under the Apache License, Version 2.0. See
[`LICENSE`](LICENSE) for the full text.

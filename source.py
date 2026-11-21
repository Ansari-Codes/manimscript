from __future__ import annotations

import ast
import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
POINT_RE = re.compile(r"\(\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s*,\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s*\)")


@dataclass
class ObjectDefinition:
    name: str
    kind: str
    properties: dict


@dataclass
class Scene:
    name: str
    transition: str | None
    commands: list[str]


@dataclass
class Program:
    objects: dict[str, ObjectDefinition]
    scenes: list[Scene]


class DSLParseError(Exception):
    pass


def indented_lines(source: str) -> list[tuple[int, int, str]]:
    lines = []
    for number, raw in enumerate(source.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content = raw.strip().rstrip(";").strip()
        lines.append((number, indent, content))
    return lines


def split_top_level(text: str, separator: str = ",") -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    quote = None
    escape = False
    for index, char in enumerate(text):
        if escape:
            escape = False
            continue
        if char == "\\" and quote:
            escape = True
            continue
        if char in ("'", '"'):
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
        elif quote is None:
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            elif char == separator and depth == 0:
                parts.append(text[start:index].strip())
                start = index + 1
    parts.append(text[start:].strip())
    return [part for part in parts if part]


def parse_value(text: str):
    text = text.strip()
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    if text.lower() in ("null", "none"):
        return None
    if text.startswith("{") and text.endswith("}"):
        return parse_property_map(text[1:-1])
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        if re.fullmatch(r"-?(?:\d+(?:\.\d*)?|\.\d+)", text):
            return float(text) if "." in text else int(text)
        if NAME_RE.match(text):
            return text
        raise DSLParseError(f"Invalid value: {text}")


def parse_property_map(text: str) -> dict:
    properties = {}
    for item in split_top_level(text):
        if ":" not in item:
            raise DSLParseError(f"Expected key: value, found {item!r}")
        key, value = item.split(":", 1)
        key = key.strip()
        if not NAME_RE.match(key):
            raise DSLParseError(f"Invalid property name: {key}")
        properties[key] = parse_value(value)
    return properties


def parse_object(definition: str, line_number: int) -> ObjectDefinition:
    if ":" not in definition:
        raise DSLParseError(f"Line {line_number}: expected object_name: {{...}}")
    name, body = definition.split(":", 1)
    name = name.strip()
    if not NAME_RE.match(name):
        raise DSLParseError(f"Line {line_number}: invalid object name {name}")
    body = body.strip()
    if not (body.startswith("{") and body.endswith("}")):
        raise DSLParseError(f"Line {line_number}: object definition must be a property map")
    properties = parse_property_map(body[1:-1])
    if "source" in properties:
        if "object" in properties:
            raise DSLParseError(f"Line {line_number}: source and object are mutually exclusive")
        source = str(properties["source"])
        kind = "svg" if source.lower().endswith(".svg") else "image"
        return ObjectDefinition(name, kind, {"source": source})
    if "object" not in properties:
        raise DSLParseError(f"Line {line_number}: object definition needs source or object")
    object_map = properties["object"]
    if not isinstance(object_map, dict) or "type" not in object_map:
        raise DSLParseError(f"Line {line_number}: object needs {type: ...}")
    kind = str(object_map.pop("type")).lower()
    supported = {"text", "circle", "square", "rectangle", "dot", "line"}
    if kind not in supported:
        raise DSLParseError(f"Line {line_number}: unsupported object type {kind}")
    return ObjectDefinition(name, kind, object_map)


def clean_lines(source: str) -> list[tuple[int, str]]:
    cleaned = []
    for number, raw in enumerate(source.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cleaned.append((number, line.rstrip(";").strip()))
    return cleaned


def supported_transitions() -> set[str]:
    return {"NONE", "FADE", "CROSS_FADE", "WRITE"}


def parse(source: str) -> Program:
    objects: dict[str, ObjectDefinition] = {}
    scenes: list[Scene] = []
    section = None
    current_scene = None
    pending_transition = None
    scene_names: set[str] = set()

    lines = indented_lines(source)
    index = 0

    while index < len(lines):
        line_number, indent, line = lines[index]
        if line == "OBJECTS:":
            section = "objects"
            index += 1
            continue
        scene_match = re.fullmatch(r'SCENE\s+(["\'])(.*?)\1\s*:', line)
        if scene_match:
            name = scene_match.group(2)
            if name in scene_names:
                raise DSLParseError(f"Line {line_number}: duplicate scene {name}")
            scene_names.add(name)
            current_scene = Scene(name, pending_transition, [])
            scenes.append(current_scene)
            pending_transition = None
            section = "scene"
            index += 1
            continue
        transition_match = re.fullmatch(r'TRANSITION\s*:\s*([A-Za-z_]+)', line, re.IGNORECASE)
        if transition_match:
            transition = transition_match.group(1).upper()
            if transition not in supported_transitions():
                raise DSLParseError(f"Line {line_number}: unsupported transition {transition}")
            pending_transition = transition
            index += 1
            continue

        if section == "objects":
            definition = parse_object(line, line_number)
            if definition.name in objects:
                raise DSLParseError(f"Line {line_number}: duplicate object {definition.name}")
            objects[definition.name] = definition
        elif section == "scene":
            if current_scene is None:
                raise DSLParseError(f"Line {line_number}: command outside scene")
            speak_match = re.fullmatch(r'SPEAK\s+(["\'])(.*?)\1(?:\s+DO\s*:)?', line)
            if speak_match:
                text = speak_match.group(2)
                if re.search(r"\s+DO\s*:$", line):
                    block_indent = indent
                    block = []
                    index += 1
                    while index < len(lines):
                        next_number, next_indent, next_line = lines[index]
                        if next_indent <= block_indent:
                            break
                        validate_command(next_line, next_number, objects)
                        block.append(next_line)
                        index += 1
                    current_scene.commands.append({"speak": text, "block": block})
                    continue
                current_scene.commands.append({"speak": text, "block": []})
                index += 1
                continue
            validate_command(line, line_number, objects)
            current_scene.commands.append(line)
        else:
            raise DSLParseError(f"Line {line_number}: unexpected top-level statement {line}")
        index += 1
    if not scenes:
        raise DSLParseError("Program must contain at least one SCENE")
    return Program(objects, scenes)


def validate_command(line: str, line_number: int, objects: dict[str, ObjectDefinition]) -> None:
    command_names = ("PLACE ", "MOVE ", "CIRCULATE ", "FADE_IN ", "FADE_OUT ",
                     "ROTATE ", "SCALE ", "TRANSFORM ", "WAIT ", "REMOVE ",
                     "HIDE ", "SHOW ")
    if not line.startswith(command_names):
        raise DSLParseError(f"Line {line_number}: unknown command {line}")
    names = re.findall(r"\b[A-Za-z_][A-Za-z0-9]*\b", line)
    command_keywords = {
        "PLACE", "MOVE", "TO", "TOWARD", "FOR", "RATE", "LINEAR", "SMOOTH",
        "IN_OUT", "EASE_IN_OUT", "CIRCULATE", "AROUND", "RADIUS", "OMEGA",
        "FADE_IN", "FADE_OUT", "ROTATE", "BY", "SCALE", "TRANSFORM",
        "WAIT", "REMOVE", "HIDE", "SHOW", "AT",
    }
    for name in names:
        if name not in command_keywords and name in objects:
            continue
        if name not in command_keywords and name not in objects:
            raise DSLParseError(f"Line {line_number}: unknown object {name}")


def python_literal(value) -> str:
    if isinstance(value, str):
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
            return value
        return repr(value)
    if isinstance(value, bool):
        return "True" if value else "False"
    if value is None:
        return "None"
    return repr(value)


def scene_class_name(name: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", name)
    result = "".join(part[:1].upper() + part[1:] for part in parts)
    if not result:
        return "GeneratedScene"
    if result[0].isdigit():
        result = "Scene" + result
    return result


def object_constructor(definition: ObjectDefinition) -> str:
    properties = dict(definition.properties)
    position = properties.pop("position", None)
    args: list[str] = []
    if definition.kind == "text":
        text = properties.pop("text", properties.pop("value", ""))
        args.append(python_literal(text))
    elif definition.kind == "line":
        start = properties.pop("start", (-1, 0))
        end = properties.pop("end", (1, 0))
        args.append(f"start={python_literal(start)}")
        args.append(f"end={python_literal(end)}")

    if definition.kind == "circle" and "radius" in properties:
        args.append(f"radius={python_literal(properties.pop('radius'))}")
    elif definition.kind == "square" and "side_length" in properties:
        args.append(f"side_length={python_literal(properties.pop('side_length'))}")
    elif definition.kind == "rectangle":
        if "width" in properties:
            args.append(f"width={python_literal(properties.pop('width'))}")
        if "height" in properties:
            args.append(f"height={python_literal(properties.pop('height'))}")

    for key, value in properties.items():
        args.append(f"{key}={python_literal(value)}")

    constructors = {
        "text": "Text", "circle": "Circle", "square": "Square",
        "rectangle": "Rectangle", "dot": "Dot", "line": "Line",
        "image": "ImageMobject", "svg": "SVGMobject",
    }
    constructor = constructors[definition.kind]
    if definition.kind in {"image", "svg"}:
        expression = f"{constructor}({python_literal(definition.properties['source'])})"
    else:
        expression = f"{constructor}({', '.join(args)})"
    if position is not None:
        expression += f".move_to({python_literal(position)})"
    return expression


def parse_point(text: str) -> str:
    match = POINT_RE.fullmatch(text.strip())
    if not match:
        raise DSLParseError(f"Invalid point {text}")
    x = float(match.group(1)) if "." in match.group(1) else int(match.group(1))
    y = float(match.group(2)) if "." in match.group(2) else int(match.group(2))
    return f"({x}, {y}, 0)"


def target_expression(text: str, objects: dict[str, ObjectDefinition]) -> str:
    if text in objects:
        return f"{text}.get_center()"
    if POINT_RE.fullmatch(text.strip()):
        return parse_point(text)
    raise DSLParseError(f"Unknown target or point: {text}")


def compile_command(line: str, objects: dict[str, ObjectDefinition]) -> list[str]:
    place_match = re.fullmatch(r"PLACE\s+([A-Za-z_]\w*)\s+AT\s+(.+)", line)
    if place_match:
        name, point = place_match.groups()
        if name not in objects:
            raise DSLParseError(f"Unknown object {name}")
        return [f"{name}.move_to({parse_point(point)})", f"self.add({name})"]

    move_match = re.fullmatch(
        r"MOVE\s+([A-Za-z_]\w*)\s+(TO|TOWARD)\s+(.+?)\s+FOR\s+(\d+(?:\.\d*)?)"
        r"(?:\s+RATE\s+(LINEAR|SMOOTH|IN_OUT|EASE_IN_OUT))?",
        line,
    )
    if move_match:
        name, direction, target, duration, rate = move_match.groups()
        if name not in objects:
            raise DSLParseError(f"Unknown object {name}")
        target_text = target_expression(target.strip(), objects)
        rate_func = "linear" if rate == "LINEAR" else "smooth"
        if rate in ("IN_OUT", "EASE_IN_OUT"):
            rate_func = "smooth"
        return [f"self.play({name}.animate.move_to({target_text}), run_time={duration}, rate_func={rate_func})"]

    circulate_match = re.fullmatch(
        r"CIRCULATE\s+([A-Za-z_]\w*)\s+AROUND\s+(.+?)\s+RADIUS\s+"
        r"(\d+(?:\.\d*)?)\s+OMEGA\s+(\d+(?:\.\d*)?)\s+FOR\s+(\d+(?:\.\d*)?)",
        line,
    )
    if circulate_match:
        name, target, radius, omega, duration = circulate_match.groups()
        center = target_expression(target.strip(), objects)
        return [
            f"self.play(UpdateFromAlphaFunc({name},",
            f"    lambda mob, alpha: mob.move_to({center} +",
            f"    {radius} * np.array([np.cos({omega} * alpha * 2 * np.pi),",
            f"    np.sin({omega} * alpha * 2 * np.pi), 0]))),",
            f"    run_time={duration})",
        ]

    fade_match = re.fullmatch(r"FADE_(IN|OUT)\s+([A-Za-z_]\w*)(?:\s+FOR\s+(\d+(?:\.\d*)?))?", line)
    if fade_match:
        action, name, duration = fade_match.groups()
        if name not in objects:
            raise DSLParseError(f"Unknown object {name}")
        method = "FadeIn" if action == "IN" else "FadeOut"
        duration_arg = f", run_time={duration}" if duration else ", run_time=1"
        return [f"self.play({method}({name}{duration_arg}))"]

    rotate_match = re.fullmatch(
        r"ROTATE\s+([A-Za-z_]\w*)\s+BY\s+([-+]?\d+(?:\.\d*)?)"
        r"(?:\s+FOR\s+(\d+(?:\.\d*)?))?",
        line,
    )
    if rotate_match:
        name, angle, duration = rotate_match.groups()
        duration = duration or "1"
        return [f"self.play(Rotate({name}, angle={angle} * DEGREES), run_time={duration})"]

    scale_match = re.fullmatch(
        r"SCALE\s+([A-Za-z_]\w*)\s+BY\s+(\d+(?:\.\d*)?)"
        r"(?:\s+FOR\s+(\d+(?:\.\d*)?))?",
        line,
    )
    if scale_match:
        name, factor, duration = scale_match.groups()
        duration = duration or "1"
        return [f"self.play({name}.animate.scale({factor}), run_time={duration})"]

    transform_match = re.fullmatch(r"TRANSFORM\s+([A-Za-z_]\w*)\s+TO\s+([A-Za-z_]\w*)\s+FOR\s+(\d+(?:\.\d*)?)", line)
    if transform_match:
        name, target, duration = transform_match.groups()
        if name not in objects or target not in objects:
            raise DSLParseError(f"Unknown object in transformation: {line}")
        return [f"self.play(Transform({name}, {target}), run_time={duration})"]

    wait_match = re.fullmatch(r"WAIT\s+(\d+(?:\.\d*)?)", line)
    if wait_match:
        return [f"self.wait({wait_match.group(1)})"]
    remove_match = re.fullmatch(r"REMOVE\s+([A-Za-z_]\w*)", line)
    if remove_match:
        name = remove_match.group(1)
        return [f"self.remove({name})"]
    hide_match = re.fullmatch(r"HIDE\s+([A-Za-z_]\w*)", line)
    if hide_match:
        name = hide_match.group(1)
        return [f"{name}.set_opacity(0)", f"self.add({name})"]
    show_match = re.fullmatch(r"SHOW\s+([A-Za-z_]\w*)", line)
    if show_match:
        name = show_match.group(1)
        return [f"{name}.set_opacity(1)", f"self.add({name})"]
    raise DSLParseError(f"Could not compile command: {line}")


def transpile(program: Program) -> str:
    lines = [
        "from manim import *",
        "import hashlib",
        "import os",
        "import numpy as np",
        "from gtts import gTTS",
        "",
        "",
        "def create_voiceover(text, scene_name, index):",
        "    directory = os.path.join(os.getcwd(), \"voiceover\")",
        "    os.makedirs(directory, exist_ok=True)",
        "    digest = hashlib.sha256(text.encode(\"utf-8\")).hexdigest()[:12]",
        "    path = os.path.join(directory, f\"{scene_name}_{index}_{digest}.mp3\")",
        "    if not os.path.exists(path):",
        "        gTTS(text=text, lang=\"en\").save(path)",
        "    duration = 0.18 * max(1, len(text.split()))",
        "    try:",
        "        from mutagen.mp3 import MP3",
        "        duration = MP3(path).info.length",
        "    except Exception:",
        "        pass",
        "    return path, duration",
        "",
        "",
    ]
    voice_index = 0
    for scene in program.scenes:
        lines.append(f"class {scene_class_name(scene.name)}(Scene):")
        lines.append("    def construct(self):")
        if scene.transition:
            lines.append(f"        # Incoming transition: {scene.transition}")
        for name, definition in program.objects.items():
            lines.append(f"        {name} = {object_constructor(definition)}")
        lines.append("")
        for command in scene.commands:
            if isinstance(command, dict) and "speak" in command:
                voice_index += 1
                text = python_literal(command["speak"])
                scene_name = scene_class_name(scene.name)
                lines.append(
                    f"        voice_file, voice_duration = create_voiceover("
                    f"{text}, {scene_name!r}, {voice_index})"
                )
                lines.append("        self.add_sound(voice_file)")
                for action in command["block"]:
                    for compiled_line in compile_command(action, program.objects):
                        lines.append("        " + compiled_line)
                if not command["block"]:
                    lines.append("        self.wait(voice_duration)")
                else:
                    lines.append("        self.wait(voice_duration)")
            else:
                for compiled_line in compile_command(command, program.objects):
                    lines.append("        " + compiled_line)
        if not scene.commands:
            lines.append("        pass")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Transpile ManimScript to Manim Python")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        source = args.input.read_text(encoding="utf-8")
        generated = transpile(parse(source))
        if args.output:
            args.output.write_text(generated, encoding="utf-8")
            print(f"Wrote {args.output}")
        else:
            sys.stdout.write(generated)
        return 0
    except (OSError, DSLParseError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

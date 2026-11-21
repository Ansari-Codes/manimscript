import unittest
from pathlib import Path

import source as m


class ManimScriptTests(unittest.TestCase):
    def test_all_do_groups_animations_in_one_play_call(self):
        source = '''OBJECTS:
    first: { object: { type: "circle", radius: 1 } }
    second: { object: { type: "square", side_length: 1 } }
SCENE "Grouped":
    ALL DO:
        MOVE first TO (2, 0) FOR 2 RATE LINEAR;
        ROTATE second BY 90 FOR 1;
'''
        program = m.parse(source)
        generated = m.transpile(program)
        self.assertEqual(program.scenes[0].commands[0]["all"], [
            "MOVE first TO (2, 0) FOR 2 RATE LINEAR",
            "ROTATE second BY 90 FOR 1",
        ])
        self.assertEqual(generated.count("self.play(AnimationGroup("), 1)
        self.assertIn("first.animate(run_time=2, rate_func=linear)", generated)
        self.assertIn("Rotate(second, angle=90 * DEGREES, run_time=1)", generated)
        compile(generated, "all_do_test", "exec")

    def test_all_do_rejects_non_animation_commands(self):
        source = '''OBJECTS:
    dot: { object: { type: "dot" } }
SCENE "Invalid":
    ALL DO:
        WAIT 1;
'''
        with self.assertRaisesRegex(m.DSLParseError, "supports PLACE setup and animation"):
            m.transpile(m.parse(source))

    def test_speak_and_speak_do(self):
        source = '''OBJECTS:
    title: { object: { type: "text", text: "Gravity", color: GOLD } }
SCENE "Narration":
    SPEAK "Gravity attracts objects"
    SPEAK "Watch gravity" DO:
        PLACE title AT (0, 1)
        FADE_IN title FOR 1
'''
        program = m.parse(source)
        generated = m.transpile(program)
        self.assertEqual(len(program.scenes[0].commands), 2)
        self.assertIn("create_voiceover", generated)
        self.assertIn("self.add_sound(voice_file)", generated)
        compile(generated, "speak_test", "exec")

    def test_all_do_can_be_used_inside_speak_do(self):
        source = '''OBJECTS:
    first: { object: { type: "dot" } }
    second: { object: { type: "dot" } }
SCENE "NarratedGroup":
    SPEAK "Move together" DO:
        ALL DO:
            MOVE first TO (1, 0) FOR 2;
            MOVE second TO (-1, 0) FOR 2;
'''
        generated = m.transpile(m.parse(source))
        self.assertIn("self.add_sound(voice_file)", generated)
        self.assertEqual(generated.count("self.play(AnimationGroup("), 1)

    def test_speak_all_do_places_objects_at_group_start(self):
        source = '''OBJECTS:
    dot: { object: { type: "dot" } }
SCENE "PlacedGroup":
    SPEAK "Watch it move" ALL DO:
        PLACE dot AT (-2, 0);
        MOVE dot TO (2, 0) FOR 2;
'''
        generated = m.transpile(m.parse(source))
        sound_index = generated.index("self.add_sound(voice_file)")
        place_index = generated.index("dot.move_to((-2, 0, 0))")
        play_index = generated.index("self.play(voice_animation_1)")
        self.assertLess(sound_index, place_index)
        self.assertLess(place_index, play_index)

    def test_speak_all_do_runs_animations_together_with_narration(self):
        source = '''OBJECTS:
    first: { object: { type: "dot" } }
    second: { object: { type: "dot" } }
SCENE "NarratedGroup":
    SPEAK "Move these together" ALL DO:
        MOVE first TO (1, 0) FOR 2;
        MOVE second TO (-1, 0) FOR 3;
'''
        program = m.parse(source)
        command = program.scenes[0].commands[0]
        generated = m.transpile(program)
        self.assertTrue(command["parallel"])
        self.assertEqual(len(command["block"]), 2)
        self.assertIn("self.add_sound(voice_file)", generated)
        self.assertEqual(generated.count("self.play(voice_animation_1)"), 1)
        self.assertIn(
            "self.wait(max(0, voice_duration - voice_animation_1.run_time))",
            generated,
        )
        self.assertEqual(generated.count("self.play(AnimationGroup("), 0)
        compile(generated, "speak_all_do_test", "exec")

    def test_all_examples_parse_and_transpile(self):
        examples = Path("examples").glob("*.manim")
        for example in examples:
            with self.subTest(example=example.name):
                source = example.read_text(encoding="utf-8")
                program = m.parse(source)
                generated = m.transpile(program)
                compile(generated, str(example), "exec")

    def test_gradient_boosting_example_documents_correct_updates(self):
        source = Path("examples/gradient_boosting.manim").read_text(encoding="utf-8")
        generated = m.transpile(m.parse(source))
        compile(generated, "gradient_boosting", "exec")
        self.assertIn("175 + (0.5 x -50) = 150", source)
        self.assertIn("175 + (0.5 x +50) = 200", source)
        self.assertIn("125", source)
        self.assertIn("225", source)
        self.assertIn("Other losses use their gradients", source)
        self.assertIn('FADE_OUT title FOR 0.5;', source)

    def test_parse_and_transpile_example(self):
        with open("example.manim", "r", encoding="utf-8") as source_file:
            source = source_file.read()
        program = m.parse(source)
        self.assertEqual(set(program.objects), {"title", "planet", "logo"})
        self.assertEqual([scene.name for scene in program.scenes], ["Introduction", "Orbit"])
        generated = m.transpile(program)
        self.assertIn("from manim import *", generated)
        self.assertIn("class Introduction(Scene):", generated)
        self.assertIn("title = Text('ManimScript', color=BLUE)", generated)
        self.assertIn("planet = Circle(radius=0.45", generated)
        self.assertIn("logo = SVGMobject('assets/logo.svg')", generated)

    def test_duplicate_object_rejected(self):
        with self.assertRaises(m.DSLParseError):
            m.parse('OBJECTS:\n a: { source: "a.svg" }\n a: { source: "b.svg" }\nSCENE "Test":\n WAIT 1')

    def test_unknown_object_rejected(self):
        with self.assertRaises(m.DSLParseError):
            m.parse('OBJECTS:\n a: { object: { type: "circle", radius: 1 } }\nSCENE "Test":\n PLACE b AT (0, 0)')


if __name__ == "__main__":
    unittest.main()

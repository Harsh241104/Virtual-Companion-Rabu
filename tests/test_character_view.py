import json
import struct
import unittest
from pathlib import Path

from rabu_companion.character_view import CHARACTER_PAGE


MODEL_PATH = Path(__file__).resolve().parents[1] / "rabu_companion" / "assets" / "rabu.glb"


class CharacterViewTests(unittest.TestCase):
    def test_model_contains_the_animations_used_by_the_companion(self):
        data = MODEL_PATH.read_bytes()
        magic, version, total_length = struct.unpack_from("<4sII", data)
        self.assertEqual((magic, version, total_length), (b"glTF", 2, len(data)))

        chunk_length, chunk_type = struct.unpack_from("<I4s", data, 12)
        self.assertEqual(chunk_type, b"JSON")
        model = json.loads(data[20 : 20 + chunk_length].decode("utf-8").rstrip())

        self.assertEqual(
            {animation["name"] for animation in model["animations"]},
            {"Explain", "Idle", "Point", "Think", "Wave"},
        )

    def test_embedded_page_loads_the_packaged_model_with_transparency(self):
        self.assertIn("data:model/gltf-binary;base64,__RABU_MODEL_BASE64__", CHARACTER_PAGE)
        self.assertIn("background: transparent !important", CHARACTER_PAGE)
        self.assertIn("@google/model-viewer@1.12.0", CHARACTER_PAGE)
        self.assertIn("qrc:///qtwebchannel/qwebchannel.js", CHARACTER_PAGE)
        self.assertIn('companion.greet()', CHARACTER_PAGE)
        self.assertIn('name === "Wave"', CHARACTER_PAGE)
        self.assertNotIn("radial-gradient", CHARACTER_PAGE)


if __name__ == "__main__":
    unittest.main()

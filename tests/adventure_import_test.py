import json
import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "resources" / "core"))

from apps.adventure import AdventureManager
from commands import adventure


class AdventureImportTests(TestCase):
    def test_import_rejects_invalid_references_before_opening_the_game(self):
        rooms = {"mill": {"id": "mill", "name": "Mill", "exits": {}}}
        game = {"startingRoomId": "mill", "rooms": rooms}
        cases = [
            ({**game, "startingRoomId": "missing"}, "starting room"),
            ({**game, "rooms": {"mill": {**rooms["mill"], "exits": {"north": "missing"}}}}, "destination room ID"),
            ({**game, "rooms": {"mill": {**rooms["mill"], "exits": ["north"]}}}, "map exit names"),
            ({**game, "player": {"inventory": ["missing"]}}, "unknown item"),
        ]
        for data, detail in cases:
            with self.subTest(detail=detail), patch.object(adventure.fs_manager, "get_node", return_value={
                "type": "file", "content": json.dumps(data),
            }):
                result = adventure.run(["world.json"], {}, {})
                self.assertFalse(result["success"])
                self.assertIn(detail, result["error"]["message"])
                self.assertNotIn("effect", result)
                self.assertFalse(AdventureManager().initialize_state(json.dumps(data), None)["success"])


if __name__ == "__main__":
    main()

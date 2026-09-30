import json
import random
import re

class AdventureManager:
    """Manages the state and logic for the text adventure game."""
    def __init__(self):
        self.state = {}
        self.verbs = self._get_default_verbs()

    def _get_default_verbs(self):
        return {
            "look": {"action": "look", "aliases": ["l", "examine", "x", "look at", "look in", "look inside"]},
            "go": {"action": "go", "aliases": ["north", "south", "east", "west", "up", "down", "n", "s", "e", "w", "u", "d", "enter", "exit"]},
            "take": {"action": "take", "aliases": ["get", "grab", "pick up"]},
            "drop": {"action": "drop", "aliases": []},
            "use": {"action": "use", "aliases": []},
            "inventory": {"action": "inventory", "aliases": ["i", "inv"]},
            "help": {"action": "help", "aliases": ["?"]},
            "quit": {"action": "quit", "aliases": []},
            "talk": {"action": "talk", "aliases": ["talk to", "speak to", "speak with"]},
            "score": {"action": "score", "aliases": []},
            "wait": {"action": "wait", "aliases": ["z"]},
        }

    def initialize_state(self, adventure_data_json, scripting_context_json):
        adventure = json.loads(adventure_data_json)
        scripting_context = json.loads(scripting_context_json) if scripting_context_json else None

        starting_room = adventure.get("rooms", {}).get(adventure.get("startingRoomId"))
        initial_score = starting_room.get("points", 0) if starting_room else 0

        self.state = {
            "adventure": adventure,
            "player": {
                "currentLocation": adventure.get("startingRoomId"),
                "inventory": adventure.get("player", {}).get("inventory", []),
                "score": initial_score,
                "moves": 0,
                "dialogueWith": None,
                "dialogueNode": None
            },
            "scriptingContext": scripting_context,
            "lastPlayerCommand": "",
        }

        self.verbs.update(adventure.get("verbs", {}))

        return self.get_initial_ui_update()

    def get_initial_ui_update(self):
        """Returns the necessary data to render the initial game state."""
        room = self.state["adventure"]["rooms"].get(self.state["player"]["currentLocation"])
        if not room:
            return {"error": "You have fallen into the void."}

        outputs = []
        outputs.append({"type": "status", "roomName": room.get("name"), "score": self.state["player"]["score"], "moves": self.state["player"]["moves"]})
        outputs.append({"type": "output", "text": self._get_room_description(room), "styleClass": "room-desc"})

        return {"success": True, "updates": outputs}

    def _get_room_description(self, room):
        """Constructs the full description for a room."""
        desc = [room.get("description", "")]

        items_in_room = [item["name"] for item in self.state["adventure"].get("items", {}).values() if item.get("location") == room.get("id")]
        if items_in_room:
            desc.append("You see here: " + ", ".join(items_in_room) + ".")

        npcs_in_room = [npc["name"] for npc in self.state["adventure"].get("npcs", {}).values() if npc.get("location") == room.get("id")]
        if npcs_in_room:
            desc.append("You see " + ", ".join(npcs_in_room) + " here.")

        exits = list(room.get("exits", {}).keys())
        if exits:
            desc.append("Exits: " + ", ".join(exits) + ".")

        return "\n".join(desc)

    def process_command(self, command_text):
        """Processes a single player command."""
        self.state['player']['moves'] += 1

        if self.state['player'].get('dialogueWith'):
            handler_result = self._process_dialogue_response(command_text)
            updates = handler_result.get("updates", [])
            game_over = False
        else:
            parts = command_text.lower().strip().split()
            verb_str = parts[0] if parts else ""
            noun_str = " ".join(parts[1:]) if len(parts) > 1 else ""

            action = self._find_action(verb_str)

            updates = []
            game_over = False

            if not action:
                updates.append({"type": "output", "text": "I don't understand that verb.", "styleClass": "error"})
            else:
                handler_name = f"_handle_{action}"
                handler = getattr(self, handler_name, self._handle_unknown)
                handler_result = handler(noun_str, verb_str)

                if isinstance(handler_result, dict):
                    updates.extend(handler_result.get("updates", []))
                    game_over = handler_result.get("gameOver", False)
                else:
                    updates.extend(handler_result)

        room = self.state["adventure"]["rooms"].get(self.state["player"]["currentLocation"])
        updates.append({"type": "status", "roomName": room.get("name"), "score": self.state["player"]["score"], "moves": self.state["player"]["moves"]})

        return {"success": True, "updates": updates, "gameOver": game_over}

    def _process_dialogue_response(self, response_text):
        """Handles player input during a conversation."""
        npc_id = self.state['player']['dialogueWith']
        node_id = self.state['player']['dialogueNode']
        npc = self.state['adventure']['npcs'].get(npc_id)
        current_node = npc['dialogue']['nodes'].get(node_id)

        response_lower = response_text.lower()

        if response_lower in ["goodbye", "bye", "exit", "quit"]:
            self.state['player']['dialogueWith'] = None
            self.state['player']['dialogueNode'] = None
            return {"updates": [{"type": "output", "text": "You end the conversation.", "styleClass": "system"}]}

        for choice in current_node.get('playerChoices', []):
            if any(keyword in response_lower for keyword in choice['keywords']):
                next_node_id = choice['nextNode']
                self.state['player']['dialogueNode'] = next_node_id
                return self._present_dialogue_node(npc, next_node_id)

        return {"updates": [{"type": "output", "text": "That's not a valid response.", "styleClass": "error"}]}

    def _present_dialogue_node(self, npc, node_id):
        """Formats and returns the output for a given dialogue node."""
        node = npc['dialogue']['nodes'].get(node_id)
        if not node:
            self.state['player']['dialogueWith'] = None
            self.state['player']['dialogueNode'] = None
            return {"updates": [{"type": "output", "text": f"{npc['name']} has nothing more to say.", "styleClass": "system"}]}

        output_text = [node['npcResponse']]
        if node.get('playerChoices'):
            for i, choice in enumerate(node['playerChoices']):
                output_text.append(f"  > You could say something about: {', '.join(choice['keywords'])}")
        else:
            self.state['player']['dialogueWith'] = None
            self.state['player']['dialogueNode'] = None

        return {"updates": [{"type": "output", "text": "\n".join(output_text), "styleClass": "dialogue"}]}

    def _find_action(self, verb_str):
        for verb, data in self.verbs.items():
            if verb == verb_str or verb_str in data.get("aliases", []):
                return data.get("action")
        return None

    def _find_entity_in_scope(self, noun_str):
        current_location = self.state['player']['currentLocation']
        inventory = self.state['player']['inventory']

        for item_id in inventory:
            item = self.state['adventure']['items'].get(item_id)
            if item and item.get('noun') == noun_str:
                return item, 'item'

        for item_id, item in self.state['adventure']['items'].items():
            if item.get('location') == current_location and item.get('noun') == noun_str:
                return item, 'item'

        for npc_id, npc in self.state['adventure']['npcs'].items():
            if npc.get('location') == current_location and npc.get('noun') == noun_str:
                return npc, 'npc'

        return None, None

    def _handle_talk(self, noun_str, verb_str):
        if not noun_str:
            return [{"type": "output", "text": "Talk to whom?", "styleClass": "error"}]

        entity, entity_type = self._find_entity_in_scope(noun_str)

        if entity_type != 'npc':
            return [{"type": "output", "text": "You can't talk to that.", "styleClass": "error"}]

        npc = entity
        if not npc.get('dialogue'):
            return [{"type": "output", "text": f"{npc['name']} has nothing to say.", "styleClass": "system"}]

        start_node_id = npc['dialogue']['startNode']
        self.state['player']['dialogueWith'] = npc['id']
        self.state['player']['dialogueNode'] = start_node_id

        return self._present_dialogue_node(npc, start_node_id)

    def _handle_look(self, noun_str, verb_str):
        if not noun_str:
            room = self.state["adventure"]["rooms"].get(self.state["player"]["currentLocation"])
            return [{"type": "output", "text": self._get_room_description(room), "styleClass": "room-desc"}]
        else:
            entity, entity_type = self._find_entity_in_scope(noun_str)
            if entity:
                return [{"type": "output", "text": entity.get("description", "You see nothing special."), "styleClass": "system"}]
            return [{"type": "output", "text": "You don't see that here.", "styleClass": "error"}]

    def _handle_go(self, noun_str, verb_str):
        direction = noun_str or verb_str
        room = self.state["adventure"]["rooms"].get(self.state["player"]["currentLocation"])
        exits = room.get("exits", {})

        if direction in exits:
            new_room_id = exits[direction]
            self.state['player']['currentLocation'] = new_room_id
            new_room = self.state['adventure']['rooms'].get(new_room_id)
            return [{"type": "output", "text": self._get_room_description(new_room), "styleClass": "room-desc"}]
        return [{"type": "output", "text": "You can't go that way.", "styleClass": "error"}]

    def _handle_take(self, noun_str, verb_str):
        if not noun_str:
            return [{"type": "output", "text": "Take what?", "styleClass": "error"}]

        entity, entity_type = self._find_entity_in_scope(noun_str)

        if entity_type == 'item' and entity.get('location') == self.state['player']['currentLocation']:
            if entity.get('canTake', False):
                entity['location'] = 'inventory'
                self.state['player']['inventory'].append(entity['id'])
                if entity.get('points'):
                    self.state['player']['score'] += entity.get('points', 0)
                return [{"type": "output", "text": f"You take the {entity['name']}.", "styleClass": "system"}]
            else:
                return [{"type": "output", "text": "You can't take that.", "styleClass": "error"}]

        return [{"type": "output", "text": "You don't see that here.", "styleClass": "error"}]

    def _handle_inventory(self, noun_str, verb_str):
        inventory_ids = self.state['player']['inventory']
        if not inventory_ids:
            return [{"type": "output", "text": "You are not carrying anything.", "styleClass": "system"}]

        item_names = [self.state['adventure']['items'][item_id]['name'] for item_id in inventory_ids]
        return [{"type": "output", "text": "You are carrying:\n" + "\n".join(item_names), "styleClass": "system"}]


    def _handle_use(self, noun_str, verb_str):
        parts = noun_str.split(" on ")
        item, e_type = self._find_entity_in_scope(parts[0].strip())
        if not item or e_type != "item":
            return [{"type": "output", "text": "You don't see that here or in your inventory."}]
            
        target = None
        if len(parts) > 1:
            target, t_type = self._find_entity_in_scope(parts[1].strip())
            if not target or t_type != "item":
                return [{"type": "output", "text": f"You don't see a {parts[1]} here."}]

        if item.get("location") != "inventory":
            return [{"type": "output", "text": "You need to be holding it to use it."}]

        item_id = item["id"]

        if target:
            target_id = target["id"]
            if item.get("unlocks") == target_id:
                if target.get("isLocked"):
                    target["isLocked"] = False
                    return [{"type": "output", "text": f"You unlocked the {target['name']} with the {item['name']}."}]
                else:
                    return [{"type": "output", "text": f"The {target['name']} is already unlocked."}]
            
            if "onUse" in target and item_id in target["onUse"]:
                use_data = target["onUse"][item_id]
                if "conditions" in use_data:
                    for cond in use_data["conditions"]:
                        if cond.get("itemId") == target_id and target.get("state") != cond.get("requiredState"):
                            return [{"type": "output", "text": use_data.get("failureMessage", "Nothing happens.")}]
                
                updates = [{"type": "output", "text": use_data.get("message", "You use it.")}]
                if use_data.get("destroyItem"):
                    item["location"] = None
                    self.state['player']['inventory'].remove(item_id)
                    
                win_cond = self.state['adventure'].get("winCondition", {})
                if win_cond.get("type") == "itemUsedOn" and win_cond.get("itemId") == item_id and win_cond.get("targetId") == target_id:
                    updates.append({"type": "output", "text": self.state['adventure'].get("winMessage", "You won!"), "styleClass": "success"})
                    return {"updates": updates, "gameOver": True}
                    
                return updates

        return [{"type": "output", "text": "Nothing happens."}]

    def _handle_drop(self, noun_str, verb_str):
        item, e_type = self._find_entity_in_scope(noun_str)
        if not item or e_type != "item" or item["id"] not in self.state['player']['inventory']:
            return [{"type": "output", "text": "You don't have that."}]
        
        item['location'] = self.state['player']['currentLocation']
        self.state['player']['inventory'].remove(item["id"])
        return [{"type": "output", "text": f"Dropped the {item['name']}."}]

    def _handle_score(self, noun_str, verb_str):
        return [{"type": "output", "text": f"Your score is {self.state['player']['score']} out of {self.state['adventure'].get('maxScore', 0)}."}]

    def _handle_wait(self, noun_str, verb_str):
        return [{"type": "output", "text": "Time passes..."}]

    def _handle_quit(self, noun_str, verb_str):
        return {
            "updates": [{"type": "output", "text": "Goodbye!", "styleClass": "system"}],
            "gameOver": True
        }

    def _handle_unknown(self, noun_str, verb_str):
        return [{"type": "output", "text": "That's not a verb I recognize.", "styleClass": "error"}]

    # --- CREATOR MODE ---
    def creator_initialize(self, filename, initial_data_json, context_json):
        from filesystem import fs_manager
        import json
        self.creator_state = {
            "filename": filename,
            "data": json.loads(initial_data_json) if initial_data_json and initial_data_json != "{}" else {"rooms": {}, "items": {}, "npcs": {}},
            "user_context": json.loads(context_json) if context_json else {}
        }
        
        # Ensure minimal structure
        for key in ["rooms", "items", "npcs"]:
            if key not in self.creator_state["data"]:
                self.creator_state["data"][key] = {}
                
        return {"success": True, "message": f"Interactive Adventure Creator started.\nEditing: {filename}\nType 'help' for commands, or 'save' / 'quit'."}

    def creator_get_prompt(self):
        filename = getattr(self, 'creator_state', {}).get("filename", "unknown")
        return {"success": True, "prompt": f"(creator: {filename})> "}

    def creator_process_command(self, user_input):
        from filesystem import fs_manager
        import json
        
        if not user_input.strip():
            return {"success": True, "output": "", "shouldExit": False}
            
        parts = user_input.strip().split()
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd in ["quit", "exit"]:
            return {"success": True, "output": "Exiting creator.", "shouldExit": True}
            
        if cmd == "help":
            help_text = "Creator Commands:\n" + \
                        "  room add <id> <name> - Add a room\n" + \
                        "  room desc <id> <text> - Set room description\n" + \
                        "  room link <id> <dir> <target_id> - Add an exit (e.g. room link start north hallway)\n" + \
                        "  item add <id> <name> <room_id> - Add an item to a room\n" + \
                        "  item desc <id> <text> - Set item description\n" + \
                        "  item set <id> <prop> <value> - Set item property (e.g. item set key canTake true)\n" + \
                        "  start <room_id> - Set starting room\n" + \
                        "  save - Save to disk\n" + \
                        "  quit / exit - Exit creator\n" + \
                        "  dump - Show current JSON"
            return {"success": True, "output": help_text, "shouldExit": False}
            
        if cmd == "dump":
            return {"success": True, "output": json.dumps(self.creator_state["data"], indent=2), "shouldExit": False}
            
        if cmd == "save":
            path = self.creator_state["filename"]
            fs_manager.write_file(path, json.dumps(self.creator_state["data"], indent=2), self.creator_state["user_context"].get("user_context", {}))
            return {"success": True, "output": f"Saved to {path}", "shouldExit": False}
            
        if cmd == "start" and args:
            self.creator_state["data"]["startingRoomId"] = args[0]
            return {"success": True, "output": f"Starting room set to {args[0]}", "shouldExit": False}
            
        if cmd == "room" and len(args) >= 2:
            sub = args[0]
            rid = args[1]
            if sub == "add" and len(args) >= 3:
                name = " ".join(args[2:])
                self.creator_state["data"]["rooms"][rid] = {"id": rid, "name": name, "description": "A new room.", "exits": {}}
                return {"success": True, "output": f"Added room: {rid}", "shouldExit": False}
            elif sub == "desc" and len(args) >= 3:
                if rid in self.creator_state["data"]["rooms"]:
                    self.creator_state["data"]["rooms"][rid]["description"] = " ".join(args[2:])
                    return {"success": True, "output": f"Updated {rid} description.", "shouldExit": False}
            elif sub == "link" and len(args) >= 4:
                direction = args[2]
                target = args[3]
                if rid in self.creator_state["data"]["rooms"]:
                    self.creator_state["data"]["rooms"][rid].setdefault("exits", {})[direction] = target
                    return {"success": True, "output": f"Linked {rid} {direction} -> {target}", "shouldExit": False}
                    
        if cmd == "item" and len(args) >= 2:
            sub = args[0]
            iid = args[1]
            if sub == "add" and len(args) >= 4:
                room_id = args[-1]
                name = " ".join(args[2:-1])
                self.creator_state["data"]["items"][iid] = {"id": iid, "name": name, "description": "A new item.", "location": room_id, "canTake": False}
                return {"success": True, "output": f"Added item: {iid} in {room_id}", "shouldExit": False}
            elif sub == "desc" and len(args) >= 3:
                if iid in self.creator_state["data"]["items"]:
                    self.creator_state["data"]["items"][iid]["description"] = " ".join(args[2:])
                    return {"success": True, "output": f"Updated {iid} description.", "shouldExit": False}
            elif sub == "set" and len(args) >= 4:
                if iid in self.creator_state["data"]["items"]:
                    prop = args[2]
                    val = args[3]
                    if val.lower() == "true": val = True
                    elif val.lower() == "false": val = False
                    self.creator_state["data"]["items"][iid][prop] = val
                    return {"success": True, "output": f"Set {iid}.{prop} = {val}", "shouldExit": False}
                    
        return {"success": True, "output": f"Unknown or invalid command: {user_input}", "shouldExit": False}
        

adventure_manager = AdventureManager()
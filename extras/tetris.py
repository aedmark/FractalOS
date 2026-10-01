import json
import random

SHAPES = [
    [[1, 1, 1, 1]], # I
    [[1, 1], [1, 1]], # O
    [[0, 1, 0], [1, 1, 1]], # T
    [[1, 0, 0], [1, 1, 1]], # L
    [[0, 0, 1], [1, 1, 1]], # J
    [[0, 1, 1], [1, 1, 0]], # S
    [[1, 1, 0], [0, 1, 1]]  # Z
]

WIDTH = 10
HEIGHT = 20

def get_state(fs_manager, user_context):
    node = fs_manager.get_node("/home/" + user_context["name"] + "/.tetris.json")
    if node and node.get("type") == "file":
        try:
            return json.loads(node.get("content", "{}"))
        except:
            pass
    return None

def save_state(fs_manager, user_context, state):
    path = "/home/" + user_context["name"] + "/.tetris.json"
    fs_manager.write_file(path, json.dumps(state), user_context)

def check_collision(board, shape, offset_x, offset_y):
    for y, row in enumerate(shape):
        for x, val in enumerate(row):
            if val:
                if x + offset_x < 0 or x + offset_x >= WIDTH or y + offset_y >= HEIGHT:
                    return True
                if y + offset_y >= 0 and board[y + offset_y][x + offset_x]:
                    return True
    return False

def merge_board(board, shape, offset_x, offset_y):
    for y, row in enumerate(shape):
        for x, val in enumerate(row):
            if val and y + offset_y >= 0:
                board[y + offset_y][x + offset_x] = 1

def clear_lines(board):
    new_board = [row for row in board if not all(row)]
    lines_cleared = HEIGHT - len(new_board)
    for _ in range(lines_cleared):
        new_board.insert(0, [0] * WIDTH)
    return new_board, lines_cleared

def spawn_piece(state):
    state["piece"] = random.choice(SHAPES)
    state["x"] = WIDTH // 2 - len(state["piece"][0]) // 2
    state["y"] = 0
    if check_collision(state["board"], state["piece"], state["x"], state["y"]):
        state["game_over"] = True

def render(state):
    if state["game_over"]:
        return "GAME OVER\nScore: " + str(state["score"]) + "\nType 'tetris start' to play again."
        
    board_copy = [row[:] for row in state["board"]]
    for y, row in enumerate(state["piece"]):
        for x, val in enumerate(row):
            if val and y + state["y"] >= 0:
                board_copy[y + state["y"]][x + state["x"]] = 2

    out = []
    out.append("Score: " + str(state["score"]))
    out.append("+" + "-" * WIDTH + "+")
    for row in board_copy:
        line = "|"
        for cell in row:
            if cell == 1: line += "[]"
            elif cell == 2: line += "@@"
            else: line += " ."
        line += "|"
        out.append(line.replace("[]", "\x1b[1;32m[]\x1b[0m").replace("@@", "\x1b[1;36m[]\x1b[0m"))
    out.append("+" + "-" * WIDTH + "+")
    out.append("Commands: start | left | right | rotate | drop")
    return "\n".join(out)

def run(args, flags, user_context, **kwargs):
    fs_manager = kwargs.get("filesystem")
    # Wait, commands don't receive filesystem in kwargs by default, they import it!
    from filesystem import fs_manager
    
    cmd = args[0] if args else "show"
    
    if cmd == "start":
        state = {
            "board": [[0] * WIDTH for _ in range(HEIGHT)],
            "score": 0,
            "game_over": False
        }
        spawn_piece(state)
        save_state(fs_manager, user_context, state)
        return render(state)

    state = get_state(fs_manager, user_context)
    if not state:
        return {"success": False, "error": {"message": "No active game.", "suggestion": "Run 'tetris start'"}}
        
    if state["game_over"]:
        return render(state)
        
    if cmd == "left":
        if not check_collision(state["board"], state["piece"], state["x"] - 1, state["y"]):
            state["x"] -= 1
    elif cmd == "right":
        if not check_collision(state["board"], state["piece"], state["x"] + 1, state["y"]):
            state["x"] += 1
    elif cmd == "rotate":
        rotated = [list(row) for row in zip(*state["piece"][::-1])]
        if not check_collision(state["board"], rotated, state["x"], state["y"]):
            state["piece"] = rotated
    elif cmd == "drop":
        while not check_collision(state["board"], state["piece"], state["x"], state["y"] + 1):
            state["y"] += 1

    # Gravity step
    if cmd != "show" and cmd != "drop":
        if not check_collision(state["board"], state["piece"], state["x"], state["y"] + 1):
            state["y"] += 1
        else:
            merge_board(state["board"], state["piece"], state["x"], state["y"])
            state["board"], lines = clear_lines(state["board"])
            state["score"] += lines * 100
            spawn_piece(state)
            
    if cmd == "drop":
        merge_board(state["board"], state["piece"], state["x"], state["y"])
        state["board"], lines = clear_lines(state["board"])
        state["score"] += lines * 100
        spawn_piece(state)

    save_state(fs_manager, user_context, state)
    return render(state)

def man(args, flags, user_context, **kwargs):
    return """
NAME
    tetris - a turn-based terminal tetris

SYNOPSIS
    tetris [start|left|right|rotate|drop|show]

DESCRIPTION
    Plays a turn-based game of Tetris. State is saved in your home directory.
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: tetris [start|left|right|rotate|drop|show]"

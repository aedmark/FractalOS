"""
netgame.py - Multiplayer terminal games over the FractalOS mesh network.

Supports Connect 4 ('c4'), Tic-Tac-Toe ('ttt'), and Battleship ('battleship').
Playable via CLI commands or fullscreen interactive TUI.
"""

import json
import random
import copy

# In-memory storage for games on this node (persists across commands within kernel lifetime)
ACTIVE_SESSIONS = {}

def _get_active_session(user):
    return ACTIVE_SESSIONS.get(user)

def _set_active_session(user, session):
    ACTIVE_SESSIONS[user] = session

# --- Game Engine: Connect 4 ---
class Connect4:
    COLS = 7
    ROWS = 6

    @staticmethod
    def create_board():
        return [["." for _ in range(Connect4.COLS)] for _ in range(Connect4.ROWS)]

    @staticmethod
    def is_valid_move(board, col):
        if col < 0 or col >= Connect4.COLS:
            return False
        return board[0][col] == "."

    @staticmethod
    def make_move(board, col, player):
        for r in range(Connect4.ROWS - 1, -1, -1):
            if board[r][col] == ".":
                board[r][col] = player
                return r
        return -1

    @staticmethod
    def check_winner(board):
        # Check horizontal
        for r in range(Connect4.ROWS):
            for c in range(Connect4.COLS - 3):
                p = board[r][c]
                if p != "." and p == board[r][c+1] == board[r][c+2] == board[r][c+3]:
                    return p

        # Check vertical
        for r in range(Connect4.ROWS - 3):
            for c in range(Connect4.COLS):
                p = board[r][c]
                if p != "." and p == board[r+1][c] == board[r+2][c] == board[r+3][c]:
                    return p

        # Check diagonal (down-right)
        for r in range(Connect4.ROWS - 3):
            for c in range(Connect4.COLS - 3):
                p = board[r][c]
                if p != "." and p == board[r+1][c+1] == board[r+2][c+2] == board[r+3][c+3]:
                    return p

        # Check diagonal (up-right)
        for r in range(3, Connect4.ROWS):
            for c in range(Connect4.COLS - 3):
                p = board[r][c]
                if p != "." and p == board[r-1][c+1] == board[r-2][c+2] == board[r-3][c+3]:
                    return p

        # Check draw
        if all(board[0][c] != "." for c in range(Connect4.COLS)):
            return "draw"

        return None

    @staticmethod
    def bot_move(board, bot_player):
        opp = "O" if bot_player == "X" else "X"
        valid_cols = [c for c in range(Connect4.COLS) if Connect4.is_valid_move(board, c)]
        if not valid_cols:
            return -1

        # 1. Winning move
        for c in valid_cols:
            b = copy.deepcopy(board)
            Connect4.make_move(b, c, bot_player)
            if Connect4.check_winner(b) == bot_player:
                return c

        # 2. Block opponent win
        for c in valid_cols:
            b = copy.deepcopy(board)
            Connect4.make_move(b, c, opp)
            if Connect4.check_winner(b) == opp:
                return c

        # 3. Prefer center column
        center_pref = [3, 2, 4, 1, 5, 0, 6]
        for c in center_pref:
            if c in valid_cols:
                return c

        return random.choice(valid_cols)

    @staticmethod
    def render_ansi(board, p1_name="Player 1 (X)", p2_name="Player 2 (O)"):
        lines = []
        lines.append(f"\x1b[1;36m┌─────────────────────────────┐\x1b[0m")
        lines.append(f"\x1b[1;36m│       CONNECT 4 ARENA       │\x1b[0m")
        lines.append(f"\x1b[1;36m└─────────────────────────────┘\x1b[0m")
        lines.append(f" \x1b[1;33m[X]\x1b[0m {p1_name}  vs  \x1b[1;31m[O]\x1b[0m {p2_name}\n")
        lines.append("  1   2   3   4   5   6   7")
        lines.append("┌───┬───┬───┬───┬───┬───┬───┐")
        for r in range(Connect4.ROWS):
            row_str = "│"
            for c in range(Connect4.COLS):
                cell = board[r][c]
                if cell == "X":
                    piece = "\x1b[1;33m ● \x1b[0m"
                elif cell == "O":
                    piece = "\x1b[1;31m ● \x1b[0m"
                else:
                    piece = " · "
                row_str += piece + "│"
            lines.append(row_str)
            if r < Connect4.ROWS - 1:
                lines.append("├───┼───┼───┼───┼───┼───┼───┤")
        lines.append("└───┴───┴───┴───┴───┴───┴───┘")
        lines.append("  1   2   3   4   5   6   7")
        return "\n".join(lines)


# --- Game Engine: Tic-Tac-Toe ---
class TicTacToe:
    @staticmethod
    def create_board():
        return ["." for _ in range(9)]

    @staticmethod
    def is_valid_move(board, pos):
        if pos < 0 or pos >= 9:
            return False
        return board[pos] == "."

    @staticmethod
    def make_move(board, pos, player):
        if TicTacToe.is_valid_move(board, pos):
            board[pos] = player
            return True
        return False

    @staticmethod
    def check_winner(board):
        wins = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8), # rows
            (0, 3, 6), (1, 4, 7), (2, 5, 8), # cols
            (0, 4, 8), (2, 4, 6)             # diagonals
        ]
        for a, b, c in wins:
            if board[a] != "." and board[a] == board[b] == board[c]:
                return board[a]
        if "." not in board:
            return "draw"
        return None

    @staticmethod
    def bot_move(board, bot_player):
        opp = "O" if bot_player == "X" else "X"
        valid = [i for i in range(9) if board[i] == "."]
        if not valid:
            return -1

        # Check win
        for pos in valid:
            b = list(board)
            b[pos] = bot_player
            if TicTacToe.check_winner(b) == bot_player:
                return pos

        # Block opponent
        for pos in valid:
            b = list(board)
            b[pos] = opp
            if TicTacToe.check_winner(b) == opp:
                return pos

        # Center
        if 4 in valid:
            return 4

        # Corners
        corners = [i for i in [0, 2, 6, 8] if i in valid]
        if corners:
            return random.choice(corners)

        return random.choice(valid)

    @staticmethod
    def render_ansi(board, p1_name="Player 1 (X)", p2_name="Player 2 (O)"):
        def fmt(idx):
            val = board[idx]
            if val == "X":
                return "\x1b[1;33m X \x1b[0m"
            elif val == "O":
                return "\x1b[1;31m O \x1b[0m"
            else:
                return f" {idx+1} "

        lines = [
            "\x1b[1;36m┌─────────────────────────────┐\x1b[0m",
            "\x1b[1;36m│       TIC-TAC-TOE ARENA     │\x1b[0m",
            "\x1b[1;36m└─────────────────────────────┘\x1b[0m",
            f" \x1b[1;33m[X]\x1b[0m {p1_name}  vs  \x1b[1;31m[O]\x1b[0m {p2_name}\n",
            "┌───┬───┬───┐",
            f"│{fmt(0)}│{fmt(1)}│{fmt(2)}│",
            "├───┼───┼───┤",
            f"│{fmt(3)}│{fmt(4)}│{fmt(5)}│",
            "├───┼───┼───┤",
            f"│{fmt(6)}│{fmt(7)}│{fmt(8)}│",
            "└───┴───┴───┘"
        ]
        return "\n".join(lines)


def run(args, flags, user_context, **kwargs):
    username = user_context.get("username", "guest") if user_context else "guest"

    # Quick flag inspection
    wants_gui = "--gui" in flags or "-g" in flags
    wants_bot = "--bot" in flags or "-b" in flags
    wants_local = "--local" in flags

    if not args and not wants_gui:
        # Default status or usage
        session = _get_active_session(username)
        if session:
            return cmd_status(session)
        return cmd_list()

    subcmd = args[0].lower() if args else "gui"

    if subcmd in ("list", "ls"):
        return cmd_list()

    elif subcmd in ("host", "new", "start"):
        game_type = args[1].lower() if len(args) > 1 else "c4"
        peer = args[2] if len(args) > 2 else None
        return cmd_host(username, game_type, peer, wants_bot, wants_gui)

    elif subcmd in ("play", "gui", "open"):
        game_type = args[1].lower() if len(args) > 1 else "c4"
        peer = args[2] if len(args) > 2 else None
        return cmd_play_gui(username, game_type, peer, wants_bot)

    elif subcmd in ("accept", "join"):
        peer = args[1] if len(args) > 1 else None
        return cmd_accept(username, peer, wants_gui)

    elif subcmd in ("move", "play-move", "m"):
        if len(args) < 2:
            return {"success": False, "error": {"message": "netgame move: missing column or coordinate", "suggestion": "Usage: netgame move <1-7> (for Connect 4) or <1-9> (for Tic-Tac-Toe)"}}
        move_val = args[1]
        return cmd_move(username, move_val)

    elif subcmd in ("board", "show"):
        session = _get_active_session(username)
        if not session:
            return {"success": False, "error": {"message": "netgame: no active game in progress", "suggestion": "Start a game with 'netgame host c4' or 'netgame bot c4'."}}
        return cmd_render_board(session)

    elif subcmd in ("status", "stat"):
        session = _get_active_session(username)
        if not session:
            return {"success": False, "error": {"message": "netgame: no active game in progress", "suggestion": "Start a game with 'netgame host c4' or 'netgame bot c4'."}}
        return cmd_status(session)

    elif subcmd in ("bot", "ai"):
        game_type = args[1].lower() if len(args) > 1 else "c4"
        return cmd_host(username, game_type, peer=None, is_bot=True, is_gui=wants_gui)

    elif subcmd in ("resign", "forfeit"):
        return cmd_resign(username)

    elif subcmd in ("close", "exit", "quit"):
        if username in ACTIVE_SESSIONS:
            del ACTIVE_SESSIONS[username]
        return "Game session closed."

    elif subcmd in ("c4", "connect4"):
        peer = args[1] if len(args) > 1 else None
        return cmd_host(username, "c4", peer, wants_bot, wants_gui)

    elif subcmd in ("ttt", "tictactoe"):
        peer = args[1] if len(args) > 1 else None
        return cmd_host(username, "ttt", peer, wants_bot, wants_gui)

    else:
        # Check if first argument is a column number or move (shortcut: 'netgame 4')
        if subcmd.isdigit():
            return cmd_move(username, subcmd)
        return {"success": False, "error": {"message": f"netgame: unknown subcommand '{subcmd}'", "suggestion": "Run 'netgame list' or 'man netgame' for help."}}


def cmd_list():
    out = [
        "\x1b[1;36m=== FractalOS Multiplayer Games ===\x1b[0m",
        "Available Games:",
        "  \x1b[1;32mc4\x1b[0m          Connect 4 (7 columns, 6 rows, first to 4 wins)",
        "  \x1b[1;32mttt\x1b[0m         Tic-Tac-Toe (3x3 grid, fast match)",
        "",
        "Quick Commands:",
        "  netgame host <game> [peer]    Host a mesh multiplayer match",
        "  netgame bot <game>            Play solo match against local bot",
        "  netgame accept <peer>         Accept game invitation from peer",
        "  netgame move <col/num>        Make a move in active game",
        "  netgame board                 Display current game board",
        "  netgame play <game>           Launch interactive graphical TUI",
        "  netgame resign                Forfeit current game",
        ""
    ]
    return "\n".join(out)


def cmd_host(username, game_type, peer=None, is_bot=False, is_gui=False):
    if game_type in ("connect4", "c4"):
        game_type = "c4"
        board = Connect4.create_board()
    elif game_type in ("tictactoe", "ttt"):
        game_type = "ttt"
        board = TicTacToe.create_board()
    else:
        return {"success": False, "error": {"message": f"netgame: unknown game type '{game_type}'", "suggestion": "Supported games: c4, ttt"}}

    p2_name = "Automated Bot" if is_bot else (f"Peer @{peer}" if peer else "Waiting for Player...")

    session = {
        "gameType": game_type,
        "p1": username,
        "p2": "BOT" if is_bot else peer,
        "p2_display": p2_name,
        "board": board,
        "turn": "X", # X goes first
        "my_symbol": "X",
        "winner": None,
        "moves": [],
        "is_bot": is_bot,
        "peer": peer
    }
    _set_active_session(username, session)

    if is_gui:
        return {
            "effect": "launch_app",
            "app_name": "Netgame",
            "options": {
                "session": session
            }
        }

    effects = []
    if peer and not is_bot:
        effects.append({
            "effect": "mesh_game_action",
            "action": "invite",
            "peerId": peer,
            "gameType": game_type,
            "hostName": username
        })

    board_text = cmd_render_board(session)
    invite_msg = f"\n\x1b[1;32m[Netgame]\x1b[0m Game hosted! {board_text}\n"
    if peer:
        invite_msg += f"Invitation sent to \x1b[1;35m@{peer}\x1b[0m. Waiting for them to accept..."
    elif is_bot:
        invite_msg += "Playing against \x1b[1;36mAutomated Bot\x1b[0m. Your turn! (Type 'netgame move <col>')"
    else:
        invite_msg += "Waiting for an opponent or play with 'netgame move <col>'."

    if effects:
        return {"effects": effects, "output": invite_msg}
    return invite_msg


def cmd_play_gui(username, game_type, peer=None, is_bot=False):
    res = cmd_host(username, game_type, peer, is_bot=is_bot, is_gui=True)
    return res


def cmd_accept(username, peer, is_gui=False):
    # Initializes a guest session
    # Peer is the host
    session = {
        "gameType": "c4", # Default or synced via network
        "p1": peer or "Host",
        "p2": username,
        "p2_display": username,
        "board": Connect4.create_board(),
        "turn": "X",
        "my_symbol": "O", # Guest is O
        "winner": None,
        "moves": [],
        "is_bot": False,
        "peer": peer
    }
    _set_active_session(username, session)

    effects = [{
        "effect": "mesh_game_action",
        "action": "accept",
        "peerId": peer,
        "guestName": username
    }]

    if is_gui:
        effects.append({
            "effect": "launch_app",
            "app_name": "Netgame",
            "options": {"session": session}
        })
        return {"effects": effects}

    return {
        "effects": effects,
        "output": f"\x1b[1;32m[Netgame]\x1b[0m Joined game with \x1b[1;35m@{peer}\x1b[0m! You are Player [O]. Waiting for Host's move..."
    }


def cmd_move(username, move_val):
    session = _get_active_session(username)
    if not session:
        return {"success": False, "error": {"message": "netgame: no active game in progress", "suggestion": "Start a game with 'netgame host c4' or 'netgame bot c4'."}}

    if session["winner"]:
        return f"Game is already over! Winner: {session['winner']}. Start a new match with 'netgame host {session['gameType']}'."

    my_symbol = session["my_symbol"]
    if session["turn"] != my_symbol and not session["is_bot"]:
        return {"success": False, "error": {"message": f"netgame: it is not your turn (current turn: Player {session['turn']})"}}

    board = session["board"]
    game_type = session["gameType"]

    if game_type == "c4":
        try:
            col = int(move_val) - 1 # 1-indexed for user
        except ValueError:
            return {"success": False, "error": {"message": f"netgame: invalid column '{move_val}'", "suggestion": "Enter a number between 1 and 7."}}

        if not Connect4.is_valid_move(board, col):
            return {"success": False, "error": {"message": f"netgame: column {col+1} is full or invalid", "suggestion": "Choose an open column 1-7."}}

        Connect4.make_move(board, col, my_symbol)
        session["moves"].append({"player": my_symbol, "move": col + 1})
        winner = Connect4.check_winner(board)
        session["winner"] = winner

    elif game_type == "ttt":
        try:
            cell = int(move_val) - 1 # 1-indexed
        except ValueError:
            return {"success": False, "error": {"message": f"netgame: invalid cell '{move_val}'", "suggestion": "Enter a number between 1 and 9."}}

        if not TicTacToe.is_valid_move(board, cell):
            return {"success": False, "error": {"message": f"netgame: cell {cell+1} is already taken or invalid"}}

        TicTacToe.make_move(board, cell, my_symbol)
        session["moves"].append({"player": my_symbol, "move": cell + 1})
        winner = TicTacToe.check_winner(board)
        session["winner"] = winner

    # Next turn
    next_turn = "O" if my_symbol == "X" else "X"
    session["turn"] = next_turn

    bot_msg = ""
    # If playing against bot and game not over, bot moves immediately!
    if session["is_bot"] and not session["winner"]:
        if game_type == "c4":
            b_move = Connect4.bot_move(board, "O")
            if b_move >= 0:
                Connect4.make_move(board, b_move, "O")
                session["moves"].append({"player": "O", "move": b_move + 1})
                b_win = Connect4.check_winner(board)
                session["winner"] = b_win
                session["turn"] = "X"
                bot_msg = f"\n\x1b[1;36m[Bot]\x1b[0m Bot dropped into column {b_move + 1}."
        elif game_type == "ttt":
            b_move = TicTacToe.bot_move(board, "O")
            if b_move >= 0:
                TicTacToe.make_move(board, b_move, "O")
                session["moves"].append({"player": "O", "move": b_move + 1})
                b_win = TicTacToe.check_winner(board)
                session["winner"] = b_win
                session["turn"] = "X"
                bot_msg = f"\n\x1b[1;36m[Bot]\x1b[0m Bot placed in cell {b_move + 1}."

    board_text = cmd_render_board(session)
    status_text = cmd_status(session)

    effects = []
    # If peer connected, dispatch move over mesh
    if session.get("peer") and not session.get("is_bot"):
        effects.append({
            "effect": "mesh_game_action",
            "action": "move",
            "peerId": session["peer"],
            "gameType": session["gameType"],
            "move": move_val,
            "board": session["board"],
            "turn": session["turn"],
            "winner": session["winner"]
        })

    output_lines = [board_text]
    if bot_msg:
        output_lines.append(bot_msg)
    output_lines.append(status_text)
    full_output = "\n".join(output_lines)

    if effects:
        return {"effects": effects, "output": full_output}
    return full_output


def cmd_render_board(session):
    game_type = session["gameType"]
    board = session["board"]
    p1 = session.get("p1", "Player 1")
    p2 = session.get("p2_display", "Player 2")
    if game_type == "c4":
        return Connect4.render_ansi(board, p1, p2)
    elif game_type == "ttt":
        return TicTacToe.render_ansi(board, p1, p2)
    return "Unknown game board"


def cmd_status(session):
    lines = []
    if session["winner"]:
        if session["winner"] == "draw":
            lines.append("\x1b[1;33m*** MATCH RESULT: DRAW! ***\x1b[0m")
        else:
            winner_name = session["p1"] if session["winner"] == "X" else session["p2_display"]
            lines.append(f"\x1b[1;32m*** WINNER: {winner_name} ({session['winner']})! ***\x1b[0m")
    else:
        current_player = session["p1"] if session["turn"] == "X" else session["p2_display"]
        lines.append(f"Turn: \x1b[1;33mPlayer {session['turn']}\x1b[0m ({current_player})")
        if session["turn"] == session["my_symbol"]:
            lines.append("\x1b[1;32m>> It is your turn! Enter 'netgame move <val>'\x1b[0m")
        else:
            lines.append(f"Waiting for {current_player}...")

    total_moves = len(session.get("moves", []))
    lines.append(f"Total moves played: {total_moves}")
    return "\n".join(lines)


def cmd_resign(username):
    session = _get_active_session(username)
    if not session:
        return {"success": False, "error": {"message": "netgame: no active game to resign"}}

    my_symbol = session["my_symbol"]
    opp_symbol = "O" if my_symbol == "X" else "X"
    session["winner"] = opp_symbol

    effects = []
    if session.get("peer") and not session.get("is_bot"):
        effects.append({
            "effect": "mesh_game_action",
            "action": "resign",
            "peerId": session["peer"],
            "winner": opp_symbol
        })

    out = f"You resigned the match. Opponent wins!"
    if effects:
        return {"effects": effects, "output": out}
    return out


def man(args, flags, user_context, **kwargs):
    return """
NAME
    netgame - Multiplayer terminal games over the FractalOS mesh network

SYNOPSIS
    netgame list
    netgame host <game> [peer] [--gui] [--bot]
    netgame accept <peer> [--gui]
    netgame move <coordinate>
    netgame board
    netgame status
    netgame bot <game>
    netgame play <game>
    netgame resign
    netgame close

DESCRIPTION
    Runs peer-to-peer multiplayer turn-based terminal games across FractalOS nodes.
    Supports Connect 4 ('c4') and Tic-Tac-Toe ('ttt').
    Can be played directly in shell mode with ANSI-rendered boards or in a graphical
    fullscreen TUI window.
    Also supports solo matches against an automated bot.

OPTIONS
    --gui, -g
        Launches the game in a graphical TUI window.
    --bot, -b
        Plays locally against an automated bot.
    --local
        Plays local pass-and-play.

EXAMPLES
    netgame list
        Lists available games and commands.
    netgame bot c4
        Plays Connect 4 solo against the automated bot.
    netgame host c4 node-59a1
        Invites peer node-59a1 to a match of Connect 4 over the mesh network.
    netgame accept node-59a1
        Accepts a game invitation from node-59a1.
    netgame move 4
        Drops a piece into column 4 in Connect 4.
    netgame play c4
        Opens the interactive graphical Connect 4 TUI app.
    netgame board
        Re-displays the current game board.
"""

def help(args, flags, user_context, **kwargs):
    return "Usage: netgame [list | host <game> [peer] | accept <peer> | move <col> | board | status | bot <game> | play <game>]"

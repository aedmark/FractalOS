#!/usr/bin/env python3
"""
Unit tests for netgame.py, c4.py, and ttt.py.
"""

import sys
import os

# Add resources/core to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../resources/core")))

from commands import netgame, c4, ttt
from commands.netgame import Connect4, TicTacToe

def test_connect4_mechanics():
    board = Connect4.create_board()
    assert len(board) == 6
    assert len(board[0]) == 7

    # Drop column 3
    r = Connect4.make_move(board, 3, "X")
    assert r == 5 # bottom row
    assert board[5][3] == "X"

    # Drop another in column 3
    r2 = Connect4.make_move(board, 3, "O")
    assert r2 == 4
    assert board[4][3] == "O"

    # Test horizontal win
    h_board = Connect4.create_board()
    for col in range(4):
        Connect4.make_move(h_board, col, "X")
    assert Connect4.check_winner(h_board) == "X"

    # Test vertical win
    v_board = Connect4.create_board()
    for _ in range(4):
        Connect4.make_move(v_board, 0, "O")
    assert Connect4.check_winner(v_board) == "O"

    # Test diagonal win
    d_board = Connect4.create_board()
    # (5,0)=X, (4,1)=X, (3,2)=X, (2,3)=X
    # setup base
    Connect4.make_move(d_board, 0, "X")
    Connect4.make_move(d_board, 1, "O"); Connect4.make_move(d_board, 1, "X")
    Connect4.make_move(d_board, 2, "O"); Connect4.make_move(d_board, 2, "O"); Connect4.make_move(d_board, 2, "X")
    Connect4.make_move(d_board, 3, "O"); Connect4.make_move(d_board, 3, "O"); Connect4.make_move(d_board, 3, "O"); Connect4.make_move(d_board, 3, "X")
    assert Connect4.check_winner(d_board) == "X"

    print("PASS: Connect4 mechanics")

def test_tictactoe_mechanics():
    board = TicTacToe.create_board()
    assert len(board) == 9

    assert TicTacToe.make_move(board, 0, "X")
    assert board[0] == "X"
    assert not TicTacToe.make_move(board, 0, "O") # Taken

    # Row win
    TicTacToe.make_move(board, 1, "X")
    TicTacToe.make_move(board, 2, "X")
    assert TicTacToe.check_winner(board) == "X"

    print("PASS: TicTacToe mechanics")

def test_bot_intelligence():
    # Connect 4: bot should win if it has 3 in a row
    board = Connect4.create_board()
    Connect4.make_move(board, 0, "O")
    Connect4.make_move(board, 1, "O")
    Connect4.make_move(board, 2, "O")
    move = Connect4.bot_move(board, "O")
    assert move == 3 # Should complete the line!

    # TicTacToe: bot should block opponent
    ttt_b = TicTacToe.create_board()
    TicTacToe.make_move(ttt_b, 0, "X")
    TicTacToe.make_move(ttt_b, 1, "X")
    move_ttt = TicTacToe.bot_move(ttt_b, "O")
    assert move_ttt == 2 # Should block cell 2!

    print("PASS: Bot heuristics")

def test_commands_execution():
    ctx = {"username": "alice"}

    # 1. List
    res_list = netgame.run(["list"], {}, ctx)
    assert "Connect 4" in res_list
    assert "Tic-Tac-Toe" in res_list

    # 2. Host c4 with bot
    res_host = netgame.run(["bot", "c4"], {}, ctx)
    assert "CONNECT 4" in res_host
    session = netgame._get_active_session("alice")
    assert session is not None
    assert session["gameType"] == "c4"
    assert session["is_bot"] is True

    # 3. Move
    res_move = netgame.run(["move", "4"], {}, ctx)
    assert "CONNECT 4" in res_move

    # 4. Status
    res_stat = netgame.run(["status"], {}, ctx)
    assert "Total moves" in res_stat

    # 5. Shortcuts
    res_c4 = c4.run(["4"], {}, ctx)
    assert "CONNECT 4" in res_c4

    # 6. Resign
    res_resign = netgame.run(["resign"], {}, ctx)
    assert "resigned" in res_resign.lower()

    # 7. TTT host and move
    res_ttt = ttt.run(["bot"], {}, ctx)
    session_ttt = netgame._get_active_session("alice")
    assert session_ttt["gameType"] == "ttt"

    res_ttt_move = ttt.run(["5"], {}, ctx)
    assert "TIC-TAC-TOE" in res_ttt_move

    print("PASS: CLI commands execution")

if __name__ == "__main__":
    test_connect4_mechanics()
    test_tictactoe_mechanics()
    test_bot_intelligence()
    test_commands_execution()
    print("ALL 4 NETGAME TEST SUITES PASSED!")

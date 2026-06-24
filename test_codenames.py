"""
Codenames Test Suite
Covers: GameController logic, hint validation, login assignment, and performance.
"""

from __future__ import annotations
import sys
import os
import time
import random
import threading
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controller import (GameController, STARTING_TEAM_CARDS, OTHER_TEAM_CARDS,
                        WHITE_COUNT, BLACK_COUNT, TOTAL)
from login import assign_role_color
from ui import _normalize, _flatten, CodenamesUI


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_state(
    active_team="Red",
    starting_team="Red",
    hint=("Tier", 2),
    guesses=2,
    revealed=None,
    round_over=False,
    winner=None,
    end_reason=None,
    red_found=0,
    blue_found=0,
    red_wins=0,
    blue_wins=0,
):
    red_total  = STARTING_TEAM_CARDS if starting_team == "Red" else OTHER_TEAM_CARDS
    blue_total = STARTING_TEAM_CARDS if starting_team == "Blue" else OTHER_TEAM_CARDS
    words = [f"W{i}" for i in range(25)]
    colors = (
        ["red"]   * red_total
        + ["blue"]  * blue_total
        + ["white"] * WHITE_COUNT
        + ["black"] * BLACK_COUNT
    )
    board = dict(zip(words, colors))
    revealed_list = list(revealed or [])
    board_agents = {w: (c if w in revealed_list else None) for w, c in board.items()}
    return {
        "board_full":        board,
        "board_agents":      board_agents,
        "revealed":          revealed_list,
        "active_team":       active_team,
        "starting_team":     starting_team,
        "current_hint":      hint,
        "guesses_remaining": guesses,
        "red_found":         red_found,
        "blue_found":        blue_found,
        "red_total":         red_total,
        "blue_total":        blue_total,
        "round_over":        round_over,
        "winner":            winner,
        "end_reason":        end_reason,
        "red_wins":          red_wins,
        "blue_wins":         blue_wins,
    }


class _UIStub:
    """Minimal stand-in for calling CodenamesUI instance methods without Tk."""
    _grid_words: list[str] = []


def _find_button(widget, text: str):
    import tkinter as tk
    if isinstance(widget, tk.Button) and widget.cget("text") == text:
        return widget
    for child in widget.winfo_children():
        found = _find_button(child, text)
        if found:
            return found
    return None


# ─── GameController ───────────────────────────────────────────────────────────

class TestBoardGeneration(unittest.TestCase):

    def setUp(self):
        self.gc = GameController()

    def test_board_has_25_tiles(self):
        self.assertEqual(len(self.gc.board), TOTAL)

    def test_color_counts(self):
        colors   = list(self.gc.board.values())
        starting = self.gc.starting_team
        red_exp  = STARTING_TEAM_CARDS if starting == "Red"  else OTHER_TEAM_CARDS
        blue_exp = STARTING_TEAM_CARDS if starting == "Blue" else OTHER_TEAM_CARDS
        self.assertEqual(colors.count("red"),   red_exp)
        self.assertEqual(colors.count("blue"),  blue_exp)
        self.assertEqual(colors.count("white"), WHITE_COUNT)
        self.assertEqual(colors.count("black"), BLACK_COUNT)

    def test_starting_team_has_more_cards(self):
        starting = self.gc.starting_team
        colors   = list(self.gc.board.values())
        self.assertEqual(colors.count(starting.lower()), STARTING_TEAM_CARDS)
        other = "blue" if starting == "Red" else "red"
        self.assertEqual(colors.count(other), OTHER_TEAM_CARDS)

    def test_active_team_equals_starting_team_at_round_start(self):
        self.assertEqual(self.gc.active_team, self.gc.starting_team)

    def test_start_new_round_alternates_starting_team(self):
        first = self.gc.starting_team
        self.gc.start_new_round()
        second = self.gc.starting_team
        self.assertNotEqual(first, second)
        self.gc.start_new_round()
        self.assertEqual(self.gc.starting_team, first)

    def test_new_round_starting_team_has_more_cards(self):
        self.gc.start_new_round()
        starting = self.gc.starting_team
        colors   = list(self.gc.board.values())
        self.assertEqual(colors.count(starting.lower()), STARTING_TEAM_CARDS)

    def test_words_are_unique(self):
        words = list(self.gc.board.keys())
        self.assertEqual(len(words), len(set(words)))

    def test_active_team_is_red_or_blue(self):
        self.assertIn(self.gc.active_team, ("Red", "Blue"))

    def test_initial_state_clean(self):
        self.assertIsNone(self.gc.current_hint)
        self.assertEqual(self.gc.guesses_remaining, 0)
        self.assertFalse(self.gc.round_over)
        self.assertEqual(len(self.gc.revealed), 0)

    def test_start_new_round_resets_board(self):
        old_board = dict(self.gc.board)
        self.gc.start_new_round()
        # board is regenerated (may theoretically be the same; just check structure)
        self.assertEqual(len(self.gc.board), TOTAL)

    def test_start_new_round_preserves_wins(self):
        self.gc.red_wins  = 3
        self.gc.blue_wins = 2
        self.gc.start_new_round()
        self.assertEqual(self.gc.red_wins,  3)
        self.assertEqual(self.gc.blue_wins, 2)


class TestSubmitHint(unittest.TestCase):

    def setUp(self):
        self.gc = GameController()
        self.team = self.gc.active_team

    def test_valid_hint_accepted(self):
        res = self.gc.submit_hint(self.team, "Tier", 2)
        self.assertTrue(res["ok"])
        self.assertEqual(self.gc.current_hint, ("Tier", 2))
        self.assertEqual(self.gc.guesses_remaining, -1)

    def test_hint_contains_state(self):
        res = self.gc.submit_hint(self.team, "Tier", 2)
        self.assertIn("state", res)

    def test_wrong_team_rejected(self):
        opponent = "Blue" if self.team == "Red" else "Red"
        res = self.gc.submit_hint(opponent, "Tier", 2)
        self.assertFalse(res["ok"])
        self.assertIn("error", res)

    def test_duplicate_hint_rejected(self):
        self.gc.submit_hint(self.team, "Tier", 2)
        res = self.gc.submit_hint(self.team, "Pflanze", 1)
        self.assertFalse(res["ok"])

    def test_count_zero_rejected(self):
        res = self.gc.submit_hint(self.team, "Tier", 0)
        self.assertFalse(res["ok"])

    def test_hint_after_round_over(self):
        self.gc.round_over = True
        res = self.gc.submit_hint(self.team, "Tier", 1)
        self.assertFalse(res["ok"])


class TestRevealTile(unittest.TestCase):

    def setUp(self):
        self.gc   = GameController()
        self.team = self.gc.active_team
        self.gc.submit_hint(self.team, "Tier", 3)

    def _word_of_color(self, color: str) -> str:
        return next(w for w, c in self.gc.board.items() if c == color)

    def test_reveal_own_tile(self):
        word = self._word_of_color(self.team.lower())
        res  = self.gc.reveal_tile(self.team, word)
        self.assertTrue(res["ok"])
        self.assertTrue(res["correct"])
        self.assertIn(word, self.gc.revealed)

    def test_reveal_wrong_tile_ends_turn(self):
        opp_color = "blue" if self.team == "Red" else "red"
        word = self._word_of_color(opp_color)
        res  = self.gc.reveal_tile(self.team, word)
        self.assertTrue(res["ok"])
        self.assertTrue(res["turn_over"])

    def test_reveal_assassin_ends_round(self):
        word = self._word_of_color("black")
        res  = self.gc.reveal_tile(self.team, word)
        self.assertTrue(res["round_over"])
        self.assertEqual(res["end_reason"], "assassin")
        opponent = "Blue" if self.team == "Red" else "Red"
        self.assertEqual(res["winner"], opponent)

    def test_reveal_already_revealed_rejected(self):
        word = self._word_of_color(self.team.lower())
        self.gc.reveal_tile(self.team, word)
        res = self.gc.reveal_tile(self.team, word)
        self.assertFalse(res["ok"])

    def test_reveal_unknown_word_rejected(self):
        res = self.gc.reveal_tile(self.team, "NICHTIMSPIEL")
        self.assertFalse(res["ok"])

    def test_reveal_without_hint_rejected(self):
        gc = GameController()
        team = gc.active_team
        word = next(iter(gc.board))
        res  = gc.reveal_tile(team, word)
        self.assertFalse(res["ok"])

    def test_wrong_team_cannot_reveal(self):
        opponent = "Blue" if self.team == "Red" else "Red"
        word = next(iter(self.gc.board))
        res  = self.gc.reveal_tile(opponent, word)
        self.assertFalse(res["ok"])

    def test_reveal_after_round_over_rejected(self):
        word = self._word_of_color("black")
        self.gc.reveal_tile(self.team, word)
        word2 = next(w for w in self.gc.board if w not in self.gc.revealed)
        team2  = self.gc.active_team
        res    = self.gc.reveal_tile(team2, word2)
        self.assertFalse(res["ok"])

    def test_win_by_finding_all_own_cards(self):
        gc        = GameController()
        team      = gc.active_team
        own_words = [w for w, c in gc.board.items() if c == team.lower()]
        gc.submit_hint(team, "Tier", len(own_words))
        for word in own_words[:-1]:
            gc.reveal_tile(team, word)
        res = gc.reveal_tile(team, own_words[-1])
        self.assertTrue(res["round_over"])
        self.assertEqual(res["winner"], team)
        self.assertEqual(res["end_reason"], "all_found")


class TestEndTurn(unittest.TestCase):

    def setUp(self):
        self.gc   = GameController()
        self.team = self.gc.active_team
        self.gc.submit_hint(self.team, "Tier", 2)

    def test_end_turn_switches_active_team(self):
        opponent = "Blue" if self.team == "Red" else "Red"
        res = self.gc.end_turn(self.team)
        self.assertTrue(res["ok"])
        self.assertEqual(self.gc.active_team, opponent)

    def test_end_turn_clears_hint(self):
        self.gc.end_turn(self.team)
        self.assertIsNone(self.gc.current_hint)

    def test_end_turn_wrong_team_rejected(self):
        opponent = "Blue" if self.team == "Red" else "Red"
        res = self.gc.end_turn(opponent)
        self.assertFalse(res["ok"])

    def test_end_turn_without_hint_rejected(self):
        gc = GameController()
        res = gc.end_turn(gc.active_team)
        self.assertFalse(res["ok"])

    def test_end_turn_after_round_over_rejected(self):
        self.gc.round_over = True
        res = self.gc.end_turn(self.team)
        self.assertFalse(res["ok"])


class TestGetState(unittest.TestCase):

    def setUp(self):
        self.gc = GameController()

    def test_state_has_all_keys(self):
        required = {
            "board_full", "board_agents", "revealed",
            "active_team", "starting_team", "current_hint", "guesses_remaining",
            "red_found", "blue_found", "red_total", "blue_total",
            "round_over", "winner", "end_reason",
            "red_wins", "blue_wins",
        }
        state = self.gc.get_state()
        self.assertTrue(required.issubset(state.keys()))

    def test_board_agents_hides_unrevealed_colors(self):
        state = self.gc.get_state()
        for color in state["board_agents"].values():
            self.assertIsNone(color)

    def test_board_agents_shows_revealed(self):
        word  = next(iter(self.gc.board))
        self.gc.revealed.add(word)
        state = self.gc.get_state()
        self.assertIsNotNone(state["board_agents"][word])

    def test_state_totals(self):
        state    = self.gc.get_state()
        starting = self.gc.starting_team
        self.assertEqual(state["red_total"],
                         STARTING_TEAM_CARDS if starting == "Red" else OTHER_TEAM_CARDS)
        self.assertEqual(state["blue_total"],
                         STARTING_TEAM_CARDS if starting == "Blue" else OTHER_TEAM_CARDS)
        self.assertEqual(state["starting_team"], starting)


# ─── Login Assignment ─────────────────────────────────────────────────────────

class TestLoginAssignment(unittest.TestCase):

    def test_returns_four_slots(self):
        a = assign_role_color()
        self.assertIn("server",   a)
        self.assertIn("client_1", a)
        self.assertIn("client_2", a)
        self.assertIn("client_3", a)

    def test_each_combination_once(self):
        a = assign_role_color()
        pairs = [a["server"], a["client_1"], a["client_2"], a["client_3"]]
        from itertools import product
        expected = set(product(["instructor", "agent"], ["Red", "Blue"]))
        self.assertEqual(set(pairs), expected)

    def test_roles_are_valid(self):
        a = assign_role_color()
        for slot in ("server", "client_1", "client_2", "client_3"):
            role, color = a[slot]
            self.assertIn(role,  ("instructor", "agent"))
            self.assertIn(color, ("Red", "Blue"))

    def test_randomness(self):
        results = [assign_role_color()["server"] for _ in range(20)]
        unique  = set(results)
        self.assertGreater(len(unique), 1, "assign_role_color always returns the same slot")


# ─── Hint Validation ─────────────────────────────────────────────────────────

class TestNormalize(unittest.TestCase):

    def test_lowercase(self):
        self.assertEqual(_normalize("HUND"), "hund")

    def test_strips_digits(self):
        self.assertEqual(_normalize("abc123"), "abc")

    def test_strips_punctuation(self):
        self.assertEqual(_normalize("hund!"), "hund")

    def test_keeps_umlauts(self):
        result = _normalize("Äpfel")
        self.assertIn("ä", result)

    def test_empty_string(self):
        self.assertEqual(_normalize(""), "")


class TestFlatten(unittest.TestCase):

    def test_converts_ae(self):
        self.assertNotIn("ä", _flatten("Äpfel"))

    def test_converts_oe(self):
        self.assertNotIn("ö", _flatten("Öl"))

    def test_converts_ue(self):
        self.assertNotIn("ü", _flatten("Über"))

    def test_converts_ss(self):
        self.assertNotIn("ß", _flatten("Straße"))
        self.assertIn("ss", _flatten("Straße"))


class TestIsValidHint(unittest.TestCase):

    def _check(self, hint: str, grid: list[str] = None) -> tuple[bool, str]:
        stub = _UIStub()
        stub._grid_words = grid or []
        return CodenamesUI._is_valid_hint(stub, hint, stub._grid_words)

    def test_empty_hint_rejected(self):
        ok, err = self._check("")
        self.assertFalse(ok)
        self.assertTrue(err)

    def test_whitespace_only_rejected(self):
        ok, _ = self._check("   ")
        self.assertFalse(ok)

    def test_hint_with_digits_rejected(self):
        ok, _ = self._check("Hund2")
        self.assertFalse(ok)

    def test_single_char_rejected(self):
        ok, _ = self._check("A")
        self.assertFalse(ok)

    def test_no_vowels_rejected(self):
        ok, _ = self._check("Str")
        self.assertFalse(ok)

    def test_grid_word_exact_match_rejected(self):
        ok, err = self._check("Hund", ["Hund"])
        self.assertFalse(ok)
        self.assertIn("Spielfeld", err)

    def test_hint_containing_grid_word_rejected(self):
        ok, _ = self._check("Hundehaus", ["Hund"])
        self.assertFalse(ok)

    def test_multi_word_hint_rejected(self):
        ok, err = self._check("zwei Wörter")
        self.assertFalse(ok)
        self.assertIn("ein Wort", err)

    def test_valid_noun_no_grid_conflict(self):
        ok, err = self._check("Tempel", ["Haus", "Auto"])
        # Without HanTa installed, capitalization check applies
        if not ok:
            self.assertIn("Großbuchstaben", err)
        else:
            self.assertTrue(ok)


# ─── Performance Benchmarks ───────────────────────────────────────────────────

PERF_LIMIT_MS = {
    "board_generation":  50,    # 1 board in < 50 ms
    "state_snapshot":     5,    # 1 get_state() in < 5 ms
    "full_game_sim":    500,    # simulate an entire game in < 500 ms
    "hint_validation":    5,    # 1 _is_valid_hint call in < 5 ms
}


class TestPerformance(unittest.TestCase):

    def _ms(self, start: float) -> float:
        return (time.perf_counter() - start) * 1000

    def test_board_generation_speed(self):
        gc    = GameController()
        start = time.perf_counter()
        gc._generate_board()
        elapsed = self._ms(start)
        self.assertLess(elapsed, PERF_LIMIT_MS["board_generation"],
                        f"Board gen took {elapsed:.1f} ms (limit {PERF_LIMIT_MS['board_generation']} ms)")

    def test_get_state_speed(self):
        gc    = GameController()
        start = time.perf_counter()
        gc.get_state()
        elapsed = self._ms(start)
        self.assertLess(elapsed, PERF_LIMIT_MS["state_snapshot"],
                        f"get_state took {elapsed:.1f} ms (limit {PERF_LIMIT_MS['state_snapshot']} ms)")

    def test_full_game_simulation_speed(self):
        """Simulate a complete game (hints + reveals until round ends)."""
        gc    = GameController()
        start = time.perf_counter()

        while not gc.round_over:
            team = gc.active_team
            if gc.current_hint is None:
                gc.submit_hint(team, "Tier", 3)
            else:
                color      = team.lower()
                candidates = [w for w, c in gc.board.items()
                              if c == color and w not in gc.revealed]
                if candidates:
                    gc.reveal_tile(team, random.choice(candidates))
                else:
                    gc.end_turn(team)

        elapsed = self._ms(start)
        self.assertLess(elapsed, PERF_LIMIT_MS["full_game_sim"],
                        f"Full game sim took {elapsed:.1f} ms (limit {PERF_LIMIT_MS['full_game_sim']} ms)")

    def test_100_board_generations(self):
        gc    = GameController()
        start = time.perf_counter()
        for _ in range(100):
            gc._generate_board()
        elapsed = self._ms(start)
        per_board = elapsed / 100
        self.assertLess(per_board, PERF_LIMIT_MS["board_generation"],
                        f"Avg board gen: {per_board:.2f} ms")

    def test_hint_validation_speed(self):
        stub = _UIStub()
        stub._grid_words = ["Haus", "Auto", "Baum", "Hund", "Katze"]
        start = time.perf_counter()
        CodenamesUI._is_valid_hint(stub, "Tempel", stub._grid_words)
        elapsed = self._ms(start)
        self.assertLess(elapsed, PERF_LIMIT_MS["hint_validation"],
                        f"Hint validation took {elapsed:.1f} ms (limit {PERF_LIMIT_MS['hint_validation']} ms)")

    def test_concurrent_game_controllers(self):
        """Verify GameController is thread-safe enough for parallel instantiation."""
        errors: list[Exception] = []

        def run():
            try:
                gc   = GameController()
                team = gc.active_team
                gc.submit_hint(team, "Tier", 2)
                color    = team.lower()
                words    = [w for w, c in gc.board.items() if c == color]
                gc.reveal_tile(team, words[0])
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        self.assertEqual(errors, [], f"Concurrent errors: {errors}")


# ─── UI Widget Tests (requires display) ──────────────────────────────────────

def _has_display() -> bool:
    import subprocess
    result = subprocess.run(
        [sys.executable, "-c", "import tkinter; r=tkinter.Tk(); r.destroy()"],
        capture_output=True, timeout=5,
    )
    return result.returncode == 0


@unittest.skipUnless(_has_display(), "No display available")
class TestUIWidgets(unittest.TestCase):

    def setUp(self):
        import tkinter as tk
        self.tk_module = tk
        # Patch fullscreen so the window doesn't take over the screen
        self._fs_patch = patch("tkinter.Tk.attributes")
        self._fs_patch.start()

    def tearDown(self):
        self._fs_patch.stop()
        if hasattr(self, "ui"):
            try:
                self.ui.root.destroy()
            except Exception:
                pass

    def test_instantiation_waiting_screen(self):
        self.ui = CodenamesUI()
        self.assertIsNotNone(self.ui.root)

    def test_instantiation_with_role(self):
        self.ui = CodenamesUI(role="agent", color="Red")
        self.assertIsNotNone(self.ui.root)

    def test_show_role_red_agent(self):
        self.ui = CodenamesUI()
        self.ui.show_role("agent", "Red")
        self.assertEqual(self.ui.role,  "agent")
        self.assertEqual(self.ui.color, "Red")

    def test_show_role_blue_instructor(self):
        self.ui = CodenamesUI()
        self.ui.show_role("instructor", "Blue")
        self.assertEqual(self.ui.role,  "instructor")
        self.assertEqual(self.ui.color, "Blue")

    def test_show_game_from_state_agent(self):
        self.ui = CodenamesUI(role="agent", color="Red")
        state   = _make_state(active_team="Red", hint=("Tier", 2), guesses=2)
        self.ui.show_game_from_state(state)
        self.assertIsNotNone(self.ui._current_state)

    def test_show_game_from_state_instructor(self):
        self.ui = CodenamesUI(role="instructor", color="Blue")
        state   = _make_state(active_team="Blue", hint=None, guesses=0)
        self.ui.show_game_from_state(state)
        self.assertIsNotNone(self.ui._current_state)

    def test_tile_click_callback_wired(self):
        self.ui = CodenamesUI(role="agent", color="Red")
        received: list[str] = []
        self.ui.on_tile_click = received.append
        self.ui._tile_clicked("Hund")
        self.assertEqual(received, ["Hund"])

    def test_end_turn_callback_wired(self):
        self.ui = CodenamesUI(role="agent", color="Red")
        calls: list[int] = []
        self.ui.on_end_turn = lambda: calls.append(1)
        self.ui._end_turn_clicked()
        self.assertEqual(calls, [1])

    def test_game_grid_contains_25_words(self):
        self.ui = CodenamesUI(role="instructor", color="Red")
        state   = _make_state(active_team="Red", hint=None, guesses=0)
        self.ui.show_game_from_state(state)
        self.assertEqual(len(self.ui._grid_words), 25)

    def test_round_over_state_renders(self):
        self.ui = CodenamesUI(role="agent", color="Red")
        state   = _make_state(
            active_team="Red", hint=None, guesses=0,
            round_over=True, winner="Red", end_reason="all_found",
        )
        try:
            self.ui.show_game_from_state(state)
        except Exception as e:
            self.fail(f"show_game_from_state raised {e} on round_over state")

    def test_end_turn_button_disabled_before_tile_click(self):
        self.ui = CodenamesUI(role="agent", color="Red")
        state   = _make_state(active_team="Red", hint=("Tier", 2), guesses=-1)
        self.ui.show_game_from_state(state)
        btn = _find_button(self.ui.root, "Zug beenden")
        self.assertIsNotNone(btn, "Zug beenden button not found")
        self.assertEqual(str(btn.cget("state")), "disabled")

    def test_end_turn_button_enabled_after_tile_click(self):
        self.ui = CodenamesUI(role="agent", color="Red")
        state   = _make_state(active_team="Red", hint=("Tier", 2), guesses=-1)
        self.ui.show_game_from_state(state)
        self.ui._tile_clicked("W0")
        self.ui.show_game_from_state(state)  # simulate server state update after tile click
        btn = _find_button(self.ui.root, "Zug beenden")
        self.assertIsNotNone(btn, "Zug beenden button not found")
        self.assertEqual(str(btn.cget("state")), "normal")

    def test_ip_dialog_opens(self):
        import tkinter as tk
        self.ui = CodenamesUI()
        called_with: list[str] = []
        self.ui.show_ip_dialog(on_confirm=called_with.append)
        # Dialog muss als Toplevel-Kind des Root-Fensters existieren
        toplevels = [w for w in self.ui.root.winfo_children()
                     if isinstance(w, tk.Toplevel)]
        self.assertEqual(len(toplevels), 1, "Kein Toplevel-Dialog gefunden")

    def test_ip_dialog_standard_button_fills_default_ip(self):
        import tkinter as tk
        self.ui = CodenamesUI()
        self.ui.show_ip_dialog(on_confirm=lambda ip: None, default_ip="10.97.36.101")
        dialog = next(w for w in self.ui.root.winfo_children()
                      if isinstance(w, tk.Toplevel))
        entry = next(w for w in dialog.winfo_children()
                     if isinstance(w, tk.Entry))
        std_btn = _find_button(dialog, "Standard")
        self.assertIsNotNone(std_btn, "Standard-Button nicht gefunden")
        std_btn.invoke()
        self.assertEqual(entry.get(), "10.97.36.101")

    def test_ip_dialog_verbinden_calls_callback(self):
        import tkinter as tk
        self.ui = CodenamesUI()
        received: list[str] = []
        self.ui.show_ip_dialog(on_confirm=received.append, default_ip="10.97.36.101")
        dialog = next(w for w in self.ui.root.winfo_children()
                      if isinstance(w, tk.Toplevel))
        entry = next(w for w in dialog.winfo_children()
                     if isinstance(w, tk.Entry))
        entry.insert(0, "192.168.1.42")
        btn = _find_button(dialog, "Verbinden")
        self.assertIsNotNone(btn, "Verbinden-Button nicht gefunden")
        btn.invoke()
        self.assertEqual(received, ["192.168.1.42"])

    def test_ip_dialog_enter_key_confirms(self):
        import tkinter as tk
        self.ui = CodenamesUI()
        received: list[str] = []
        self.ui.show_ip_dialog(on_confirm=received.append)
        dialog = next(w for w in self.ui.root.winfo_children()
                      if isinstance(w, tk.Toplevel))
        entry = next(w for w in dialog.winfo_children()
                     if isinstance(w, tk.Entry))
        entry.insert(0, "10.0.0.1")
        entry.event_generate("<Return>")
        self.assertEqual(received, ["10.0.0.1"])

    def test_ip_dialog_closes_after_confirm(self):
        import tkinter as tk
        self.ui = CodenamesUI()
        self.ui.show_ip_dialog(on_confirm=lambda ip: None, default_ip="10.97.36.101")
        dialog = next(w for w in self.ui.root.winfo_children()
                      if isinstance(w, tk.Toplevel))
        entry = next(w for w in dialog.winfo_children()
                     if isinstance(w, tk.Entry))
        entry.insert(0, "10.0.0.1")
        _find_button(dialog, "Verbinden").invoke()
        # Dialog darf nach Bestätigung nicht mehr existieren
        remaining = [w for w in self.ui.root.winfo_children()
                     if isinstance(w, tk.Toplevel)]
        self.assertEqual(remaining, [])


# ─── Integration: full round via GameController ───────────────────────────────

class TestFullRoundIntegration(unittest.TestCase):

    def test_full_round_red_wins(self):
        gc             = GameController()
        gc.active_team = "Red"
        own_words      = [w for w, c in gc.board.items() if c == "red"]
        gc.submit_hint("Red", "Tier", len(own_words))

        for word in own_words[:-1]:
            res = gc.reveal_tile("Red", word)
            self.assertTrue(res["ok"])
            self.assertFalse(res.get("round_over", False))

        res = gc.reveal_tile("Red", own_words[-1])
        self.assertTrue(res["round_over"])
        self.assertEqual(res["winner"], "Red")
        self.assertEqual(gc.red_wins, 1)
        self.assertEqual(gc.blue_wins, 0)

    def test_new_round_after_win_resets_board(self):
        gc = GameController()
        gc.active_team  = "Red"
        gc.current_hint = ("Tier", gc.red_total)
        for w, c in gc.board.items():
            if c == "red":
                gc.revealed.add(w)
        gc.red_found = gc.red_total
        gc._end_round("Red", "all_found")

        gc.start_new_round()

        self.assertFalse(gc.round_over)
        self.assertEqual(len(gc.revealed), 0)
        self.assertIsNone(gc.current_hint)
        self.assertEqual(gc.red_found,  0)
        self.assertEqual(gc.blue_found, 0)

    def test_assassin_gives_win_to_opponent(self):
        gc    = GameController()
        team  = gc.active_team
        opp   = "Blue" if team == "Red" else "Red"
        gc.submit_hint(team, "Tier", 1)
        black = next(w for w, c in gc.board.items() if c == "black")
        res   = gc.reveal_tile(team, black)
        self.assertTrue(res["round_over"])
        self.assertEqual(res["winner"],     opp)
        self.assertEqual(res["end_reason"], "assassin")


# ─── Local Network Simulation ─────────────────────────────────────────────────
#
# These tests start a real TCP server on 127.0.0.1 with a random free port.
# main.py's hardcoded SERVER_IP ('10.97.36.101') is patched away for the
# duration of each test so nothing on the real network is ever contacted.

import socket as _sock_mod
import main   as _main


def _free_port() -> int:
    """Return an unused local TCP port."""
    with _sock_mod.socket(_sock_mod.AF_INET, _sock_mod.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


class LocalGameSession:
    """
    Spins up a complete 4-player Codenames game on localhost.

    Usage::

        with LocalGameSession() as s:
            ctrl = s.controller()
            s.send(s.slot_for('instructor', ctrl.active_team),
                   {"type": "submit_hint", "word": "Tier", "count": 2})

    What it does:
    - Resets all global state in main.py so tests are fully isolated.
    - Patches main.SERVER_IP → '127.0.0.1' and main.PORT → a random free port.
    - Starts the server thread and connects 3 client threads.
    - Blocks until the game-start broadcast is received before returning.
    """

    LOCAL_IP = '127.0.0.1'

    def __init__(self):
        self.port     = _free_port()
        self.players: dict[str, tuple[str, str, callable]] = {}
        self.states:  dict[str, list[dict]]                = {}
        self._ready   = threading.Event()
        self._patches: list = []

    # ── context manager ────────────────────────────────────────────────────

    def __enter__(self) -> "LocalGameSession":
        self._reset_main_globals()
        self._apply_patches()
        self._start_server()
        self._connect_clients()
        if not self._ready.wait(timeout=10):
            raise RuntimeError("Game did not start within 10 s")
        return self

    def __exit__(self, *_):
        for p in self._patches:
            try:
                p.stop()
            except RuntimeError:
                pass

    # ── setup ──────────────────────────────────────────────────────────────

    def _reset_main_globals(self):
        _main._clients                = []
        _main._clients_lock           = threading.Lock()
        _main._controller             = None
        _main._game_started           = threading.Event()
        _main._server_on_state_update = None
        _main._server_on_role_update  = None
        _main._server_role            = ""
        _main._server_color           = ""

    def _apply_patches(self):
        p1 = patch.object(_main, 'SERVER_IP', self.LOCAL_IP)
        p2 = patch.object(_main, 'PORT',      self.port)
        p1.start(); p2.start()
        self._patches = [p1, p2]

    def _start_server(self):
        ready = threading.Event()

        def _run():
            role, color, send_fn = _main.run_server(
                on_game_start=lambda s: (
                    self.states.setdefault('server', []).append(s),
                    self._ready.set(),
                ),
                on_state_update=lambda s:
                    self.states.setdefault('server', []).append(s),
            )
            self.players['server'] = (role, color, send_fn)
            ready.set()

        threading.Thread(target=_run, daemon=True).start()
        if not ready.wait(timeout=5):
            raise RuntimeError("Server thread did not start")

    def _connect_clients(self):
        for i in range(1, 4):
            slot  = f'client_{i}'
            ready = threading.Event()

            def _run(s=slot, e=ready):
                role, color, send_fn = _main.run_client(
                    self.LOCAL_IP,
                    on_game_start=lambda st, sl=s:
                        self.states.setdefault(sl, []).append(st),
                    on_state_update=lambda st, sl=s:
                        self.states.setdefault(sl, []).append(st),
                )
                self.players[s] = (role, color, send_fn)
                e.set()

            threading.Thread(target=_run, daemon=True).start()
            if not ready.wait(timeout=5):
                raise RuntimeError(f"{slot} did not connect")

    # ── public API ─────────────────────────────────────────────────────────

    def send(self, slot: str, msg: dict):
        _, _, fn = self.players[slot]
        fn(msg)

    def slot_for(self, role: str, color: str) -> str:
        for slot, (r, c, _) in self.players.items():
            if r == role and c.lower() == color.lower():
                return slot
        raise KeyError(f"No player with role={role!r} color={color!r}")

    def controller(self) -> GameController:
        return _main._controller

    def latest_state(self, slot: str) -> dict | None:
        lst = self.states.get(slot, [])
        return lst[-1] if lst else None

    def wait_for_state(self, slot: str, min_count: int, timeout: float = 2.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if len(self.states.get(slot, [])) >= min_count:
                return True
            time.sleep(0.01)
        return False


class TestNetworkSimulation(unittest.TestCase):
    """
    End-to-end tests over real local TCP sockets.
    The production SERVER_IP is never contacted — all traffic stays on 127.0.0.1.
    """

    # ── session setup ──────────────────────────────────────────────────────

    def test_four_players_connected(self):
        with LocalGameSession() as s:
            self.assertEqual(len(s.players), 4)

    def test_all_role_color_combos_unique(self):
        with LocalGameSession() as s:
            from itertools import product as _prod
            expected = set(_prod(["instructor", "agent"], ["Red", "Blue"]))
            actual   = {(r, c) for _, (r, c, _) in s.players.items()}
            self.assertEqual(actual, expected)

    def test_initial_state_delivered_to_server(self):
        with LocalGameSession() as s:
            self.assertIsNotNone(s.latest_state('server'))

    def test_initial_state_has_25_tiles(self):
        with LocalGameSession() as s:
            self.assertEqual(len(s.latest_state('server')['board_full']), 25)

    def test_clients_receive_initial_state(self):
        with LocalGameSession() as s:
            for slot in ('client_1', 'client_2', 'client_3'):
                self.assertTrue(
                    s.wait_for_state(slot, 1),
                    f"{slot} never received a game_start state",
                )

    # ── instructor actions ─────────────────────────────────────────────────

    def test_instructor_submit_hint_accepted(self):
        with LocalGameSession() as s:
            ctrl  = s.controller()
            team  = ctrl.active_team
            instr = s.slot_for('instructor', team)
            s.send(instr, {"type": "submit_hint", "word": "Tier", "count": 2})
            time.sleep(0.15)
            self.assertEqual(ctrl.current_hint, ("Tier", 2))

    def test_hint_broadcast_to_all_slots(self):
        with LocalGameSession() as s:
            ctrl   = s.controller()
            team   = ctrl.active_team
            instr  = s.slot_for('instructor', team)
            before = {slot: len(lst) for slot, lst in s.states.items()}
            s.send(instr, {"type": "submit_hint", "word": "Tier", "count": 2})
            for slot in s.players:
                self.assertTrue(
                    s.wait_for_state(slot, before.get(slot, 0) + 1),
                    f"{slot} did not receive state after hint",
                )

    def test_wrong_team_instructor_hint_ignored(self):
        with LocalGameSession() as s:
            ctrl     = s.controller()
            team     = ctrl.active_team
            opponent = "Blue" if team == "Red" else "Red"
            instr    = s.slot_for('instructor', opponent)
            s.send(instr, {"type": "submit_hint", "word": "Tier", "count": 2})
            time.sleep(0.15)
            self.assertIsNone(ctrl.current_hint)

    # ── agent actions ──────────────────────────────────────────────────────

    def test_agent_reveal_tile(self):
        with LocalGameSession() as s:
            ctrl  = s.controller()
            team  = ctrl.active_team
            instr = s.slot_for('instructor', team)
            agent = s.slot_for('agent', team)
            word  = next(w for w, c in ctrl.board.items() if c == team.lower())
            s.send(instr, {"type": "submit_hint", "word": "Tier", "count": 3})
            time.sleep(0.1)
            s.send(agent, {"type": "reveal_tile", "word": word})
            time.sleep(0.1)
            self.assertIn(word, ctrl.revealed)

    def test_reveal_propagates_to_all_slots(self):
        with LocalGameSession() as s:
            ctrl   = s.controller()
            team   = ctrl.active_team
            instr  = s.slot_for('instructor', team)
            agent  = s.slot_for('agent', team)
            word   = next(w for w, c in ctrl.board.items() if c == team.lower())
            s.send(instr, {"type": "submit_hint", "word": "Tier", "count": 3})
            time.sleep(0.1)
            before = {slot: len(lst) for slot, lst in s.states.items()}
            s.send(agent, {"type": "reveal_tile", "word": word})
            for slot in s.players:
                self.assertTrue(
                    s.wait_for_state(slot, before.get(slot, 0) + 1),
                    f"{slot} did not receive state after tile reveal",
                )

    def test_agent_end_turn_switches_active_team(self):
        with LocalGameSession() as s:
            ctrl     = s.controller()
            team     = ctrl.active_team
            opponent = "Blue" if team == "Red" else "Red"
            instr    = s.slot_for('instructor', team)
            agent    = s.slot_for('agent', team)
            s.send(instr, {"type": "submit_hint", "word": "Tier", "count": 3})
            time.sleep(0.1)
            s.send(agent, {"type": "end_turn"})
            time.sleep(0.1)
            self.assertEqual(ctrl.active_team, opponent)

    def test_wrong_team_agent_cannot_reveal(self):
        with LocalGameSession() as s:
            ctrl     = s.controller()
            team     = ctrl.active_team
            opponent = "Blue" if team == "Red" else "Red"
            instr    = s.slot_for('instructor', team)
            agent    = s.slot_for('agent', opponent)
            word     = next(w for w, c in ctrl.board.items() if c == team.lower())
            s.send(instr, {"type": "submit_hint", "word": "Tier", "count": 3})
            time.sleep(0.1)
            s.send(agent, {"type": "reveal_tile", "word": word})
            time.sleep(0.1)
            self.assertNotIn(word, ctrl.revealed)

    # ── full game ──────────────────────────────────────────────────────────

    def test_full_networked_game_completes(self):
        """Play an entire round to completion over 127.0.0.1 TCP sockets."""
        with LocalGameSession() as s:
            ctrl = s.controller()
            for _ in range(120):
                if ctrl.round_over:
                    break
                team  = ctrl.active_team
                color = team.lower()
                instr = s.slot_for('instructor', team)
                agent = s.slot_for('agent', team)
                if ctrl.current_hint is None:
                    s.send(instr, {"type": "submit_hint", "word": "Tier", "count": 9})
                    time.sleep(0.05)
                else:
                    candidates = [w for w, c in ctrl.board.items()
                                  if c == color and w not in ctrl.revealed]
                    if candidates:
                        s.send(agent, {"type": "reveal_tile", "word": candidates[0]})
                    else:
                        s.send(agent, {"type": "end_turn"})
                    time.sleep(0.05)

            self.assertTrue(ctrl.round_over, "Game did not finish within 120 steps")
            self.assertIn(ctrl.winner, ("Red", "Blue"))
            self.assertIn(ctrl.end_reason, ("all_found", "assassin"))

    def test_two_independent_sessions_do_not_interfere(self):
        """Each session gets its own port and controller — no shared state leaks."""
        with LocalGameSession() as s1:
            ctrl1 = s1.controller()
            team1 = ctrl1.active_team
            s1.send(s1.slot_for('instructor', team1),
                    {"type": "submit_hint", "word": "Alpha", "count": 1})
            time.sleep(0.1)
            hint1 = ctrl1.current_hint

        with LocalGameSession() as s2:
            ctrl2 = s2.controller()
            self.assertIsNone(ctrl2.current_hint,
                              "Second session inherited hint from first session")
            self.assertIsNotNone(hint1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

import random
from words import woerter

STARTING_TEAM_CARDS = 9    # beginnendes Team hat eine Karte mehr
OTHER_TEAM_CARDS    = 8
WHITE_COUNT         = 7
BLACK_COUNT         = 1
TOTAL               = 25
WIN_THRESHOLD       = 3    # Rundensiege für den Gesamtsieg


class GameController:
    """Zentrale Spiellogik; wird ausschließlich vom Server instanziiert."""

    def __init__(self):
        self.red_wins      = 0
        self.blue_wins     = 0
        self.game_over     = False
        self.game_winner:  str | None = None
        self.starting_team = random.choice(["Red", "Blue"])
        self._init_round()

    def _init_round(self):
        """Setzt alle rundenbezogenen Felder zurück; Gesamtpunkte bleiben erhalten."""
        self.red_total:         int                     = (STARTING_TEAM_CARDS if self.starting_team == "Red"
                                                           else OTHER_TEAM_CARDS)
        self.blue_total:        int                     = (STARTING_TEAM_CARDS if self.starting_team == "Blue"
                                                           else OTHER_TEAM_CARDS)
        self.board:             dict[str, str]          = self._generate_board()
        self.revealed:          set[str]                = set()
        self.active_team:       str                     = self.starting_team
        self.current_hint:      tuple[str, int] | None  = None
        self.guesses_remaining: int                     = 0
        self.red_found:         int                     = 0
        self.blue_found:        int                     = 0
        self.round_over:        bool                    = False
        self.winner:            str | None              = None
        self.end_reason:        str | None              = None  # "assassin" | "all_found"

    def _generate_board(self) -> dict[str, str]:
        """Wählt 25 Wörter und weist jeder Kachel zufällig eine Farbe zu."""
        words  = random.sample(woerter, TOTAL)
        colors = (["red"]   * self.red_total +
                  ["blue"]  * self.blue_total +
                  ["white"] * WHITE_COUNT +
                  ["black"] * BLACK_COUNT)
        random.shuffle(colors)
        return dict(zip(words, colors))

    def start_new_round(self):
        """Startet eine neue Runde; das beginnende Team wechselt."""
        self.starting_team = "Blue" if self.starting_team == "Red" else "Red"
        self._init_round()

    def _opponent(self) -> str: 
        """welches team"""
        return "Blue" if self.active_team == "Red" else "Red"

    def _switch_team(self):
        """Übergibt den Zug an den Gegner und setzt Hinweis/Versuche zurück."""
        self.active_team       = self._opponent()
        self.current_hint      = None
        self.guesses_remaining = 0

    def _end_round(self, winner: str, reason: str):
        """Beendet die Runde, erhöht den Siegzähler und prüft auf Gesamtsieg."""
        self.round_over = True
        self.winner     = winner
        self.end_reason = reason

        if winner == "Red":
            self.red_wins += 1
        else:
            self.blue_wins += 1

        if self.red_wins >= WIN_THRESHOLD:
            self.game_over   = True
            self.game_winner = "Red"
        elif self.blue_wins >= WIN_THRESHOLD:
            self.game_over   = True
            self.game_winner = "Blue"

    def submit_hint(self, team: str, word: str, count: int) -> dict:
        """Nimmt den Hinweis des Spymasters entgegen."""
        if self.round_over:
            return {"ok": False, "error": "Runde bereits beendet."}
        if team != self.active_team:
            return {"ok": False, "error": "Dein Team ist nicht an der Reihe."}
        if self.current_hint is not None:
            return {"ok": False, "error": "Es wurde bereits ein Hinweis gegeben."}
        if count < 1:
            return {"ok": False, "error": "Anzahl muss mindestens 1 sein."}

        self.current_hint      = (word, count)
        self.guesses_remaining = -1  # -1 = unbegrenzte Versuche
        return {"ok": True, "state": self.get_state()}

    def reveal_tile(self, team: str, word: str) -> dict:
        """Deckt eine Kachel auf und berechnet die Konsequenz."""
        if self.round_over:
            return {"ok": False, "error": "Runde bereits beendet."}
        if team != self.active_team:
            return {"ok": False, "error": "Dein Team ist nicht an der Reihe."}
        if self.current_hint is None:
            return {"ok": False, "error": "Noch kein Hinweis gegeben."}
        if self.guesses_remaining == 0:
            return {"ok": False, "error": "Keine Versuche mehr übrig."}
        if word not in self.board:
            return {"ok": False, "error": "Unbekanntes Wort."}
        if word in self.revealed:
            return {"ok": False, "error": "Kachel bereits aufgedeckt."}

        self.revealed.add(word)
        color = self.board[word]

        result = {
            "ok":         True,
            "color":      color,
            "correct":    color.lower() == self.active_team.lower(),
            "turn_over":  False,
            "round_over": False,
            "winner":     None,
            "end_reason": None,
        }

        if color == "black": #schwarze Karte -> aktives Team verliert Runde
            self._end_round(winner=self._opponent(), reason="assassin")
            result.update({"turn_over": True, "round_over": True,
                           "winner": self.winner, "end_reason": self.end_reason})

        elif color.lower() == self.active_team.lower():
            if color == "red":
                self.red_found += 1
            else:
                self.blue_found += 1

            if self.guesses_remaining != -1:
                self.guesses_remaining -= 1

            needed = self.red_total if self.active_team == "Red" else self.blue_total
            found  = self.red_found if self.active_team == "Red" else self.blue_found

            if found >= needed: #alle Kacheln aufgedeckt
                self._end_round(winner=self.active_team, reason="all_found")
                result.update({"turn_over": True, "round_over": True,
                               "winner": self.winner, "end_reason": self.end_reason})
            elif self.guesses_remaining == 0:
                self._switch_team()
                result["turn_over"] = True

        else:
            if color == "red":
                self.red_found += 1
            elif color == "blue":
                self.blue_found += 1

            opponent  = self._opponent()
            opp_color = opponent.lower()
            needed    = self.red_total if opp_color == "red" else self.blue_total
            found     = self.red_found if opp_color == "red" else self.blue_found

            if found >= needed:
                # Gegner gewinnt durch Fehlklick
                self._end_round(winner=opponent, reason="all_found")
                result.update({"turn_over": True, "round_over": True,
                               "winner": self.winner, "end_reason": self.end_reason})
            else:
                reason = "neutral" if color == "white" else "wrong_guess"
                self._switch_team()
                result.update({"turn_over": True, "end_reason": reason})

        result["state"] = self.get_state()
        return result

    def end_turn(self, team: str) -> dict:
        """Beendet den Zug freiwillig ohne alle Versuche zu nutzen."""
        if self.round_over:
            return {"ok": False, "error": "Runde bereits beendet."}
        if team != self.active_team:
            return {"ok": False, "error": "Dein Team ist nicht an der Reihe."}
        if self.current_hint is None:
            return {"ok": False, "error": "Noch kein Hinweis gegeben."}

        self._switch_team()
        return {"ok": True, "state": self.get_state()}

    def get_state(self) -> dict:
        """Snapshot des Spielzustands; wird nach jeder Aktion an alle Clients gesendet.
        board_full enthält alle Farben (Spymaster), board_agents nur aufgedeckte."""
        return {
            "board_full":        self.board,
            "board_agents":      {w: (c if w in self.revealed else None)
                                  for w, c in self.board.items()},
            "revealed":          list(self.revealed),
            "active_team":       self.active_team,
            "current_hint":      self.current_hint,
            "guesses_remaining": self.guesses_remaining,
            "red_found":         self.red_found,
            "blue_found":        self.blue_found,
            "red_total":         self.red_total,
            "blue_total":        self.blue_total,
            "starting_team":     self.starting_team,
            "round_over":        self.round_over,
            "winner":            self.winner,
            "end_reason":        self.end_reason,
            "red_wins":          self.red_wins,
            "blue_wins":         self.blue_wins,
            "game_over":         self.game_over,
            "game_winner":       self.game_winner,
            "win_threshold":     WIN_THRESHOLD,
        }

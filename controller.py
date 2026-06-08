import random
from words import woerter

RED_COUNT   = 8
BLUE_COUNT  = 8
WHITE_COUNT = 8
BLACK_COUNT = 1
TOTAL       = 25


class GameController:
    """
    Zentrale Spiellogik – wird ausschließlich vom Server instanziiert.
    Alle Zustandsänderungen laufen über diese Klasse; Clients erhalten
    per get_state() einen Snapshot, der über das Netzwerk gesendet wird.
    """

    def __init__(self):
        self.red_wins  = 0
        self.blue_wins = 0
        self._init_round()

    # ── Runde initialisieren ──────────────────────────────────────────────────

    def _init_round(self):
        self.board:             dict[str, str]          = self._generate_board()
        self.revealed:          set[str]                = set()
        self.active_team:       str                     = random.choice(["Red", "Blue"])
        self.current_hint:      tuple[str, int] | None  = None
        self.guesses_remaining: int                     = 0
        self.red_found:         int                     = 0
        self.blue_found:        int                     = 0
        self.round_over:        bool                    = False
        self.winner:            str | None              = None
        self.end_reason:        str | None              = None

    def _generate_board(self) -> dict[str, str]:
        """Wählt 25 zufällige Wörter und weist jeder Kachel eine Farbe zu."""
        words  = random.sample(woerter, TOTAL)
        colors = (["red"]   * RED_COUNT +
                  ["blue"]  * BLUE_COUNT +
                  ["white"] * WHITE_COUNT +
                  ["black"] * BLACK_COUNT)
        random.shuffle(colors)
        return dict(zip(words, colors))

    def start_new_round(self):
        """Setzt das Spielfeld für eine neue Runde zurück; Gesamtpunkte bleiben erhalten."""
        self._init_round()

    # ── Hilfsmethoden ─────────────────────────────────────────────────────────

    def _opponent(self) -> str:
        return "Blue" if self.active_team == "Red" else "Red"

    def _switch_team(self):
        self.active_team       = self._opponent()
        self.current_hint      = None
        self.guesses_remaining = 0

    def _end_round(self, winner: str, reason: str):
        self.round_over = True
        self.winner     = winner
        self.end_reason = reason
        if winner == "Red":
            self.red_wins += 1
        else:
            self.blue_wins += 1

    # ── Instruktor-Aktion: Hinweis geben ─────────────────────────────────────

    def submit_hint(self, team: str, word: str, count: int) -> dict:
        """
        Wird aufgerufen, wenn der Instruktor des aktiven Teams einen Hinweis gibt.

        UI-Anbindung:
          - Das Hinweis-Eingabefeld nur dem Instruktor des aktiven Teams anzeigen
            (role == 'instructor' AND color == active_team).
          - Bei Absenden (word, count) an den Server schicken; Server ruft diese
            Methode auf.
          - Den zurückgegebenen State an alle Clients broadcasten, damit Agenten
            den Hinweis sehen und die Kacheln klickbar werden.

        Rückgabe-Dict:
          'ok'    – True wenn Hinweis akzeptiert
          'error' – Fehlermeldung falls abgelehnt
          'state' – aktueller Spielzustand (immer vorhanden wenn ok=True)
        """
        if self.round_over:
            return {"ok": False, "error": "Runde bereits beendet."}
        if team != self.active_team:
            return {"ok": False, "error": "Dein Team ist nicht an der Reihe."}
        if self.current_hint is not None:
            return {"ok": False, "error": "Es wurde bereits ein Hinweis gegeben."}
        if count < 1:
            return {"ok": False, "error": "Anzahl muss mindestens 1 sein."}

        self.current_hint      = (word, count)
        self.guesses_remaining = -1  # -1 = unbegrenzt
        return {"ok": True, "state": self.get_state()}

    # ── Agenten-Aktion: Kachel aufdecken ─────────────────────────────────────

    def reveal_tile(self, team: str, word: str) -> dict:
        """
        Wird aufgerufen, wenn ein Agent des aktiven Teams eine Kachel anklickt.

        UI-Anbindung:
          - Kacheln nur für den Agenten des aktiven Teams klickbar machen,
            sobald current_hint gesetzt und guesses_remaining > 0.
          - Bei Klick (team, word) an den Server schicken; Server ruft diese
            Methode auf.
          - Den zurückgegebenen State an alle Clients broadcasten, um das Brett
            zu aktualisieren.
          - Falls result['round_over'] True ist: Gewinner-Bildschirm anzeigen.
          - Falls result['turn_over'] True (aber round_over False): UI auf die
            Hinweis-Eingabe des gegnerischen Teams umschalten.

        Rückgabe-Dict:
          'ok'           – True wenn Aktion akzeptiert
          'error'        – Fehlermeldung falls abgelehnt
          'color'        – Farbe der aufgedeckten Kachel
          'correct'      – True wenn Kachel zum aktiven Team gehört
          'turn_over'    – True wenn der Zug dieses Teams endet
          'round_over'   – True wenn die Runde beendet ist
          'winner'       – gewinnendes Team (nur wenn round_over=True)
          'end_reason'   – 'assassin' | 'all_found' | 'wrong_guess' | 'neutral'
          'state'        – aktueller Spielzustand
        """
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
        color  = self.board[word]
        result = {
            "ok":        True,
            "color":     color,
            "correct":   color.lower() == self.active_team.lower(),
            "turn_over": False,
            "round_over":False,
            "winner":    None,
            "end_reason":None,
        }

        if color == "black":
            # Schwarze Kachel: aktives Team verliert sofort
            self._end_round(winner=self._opponent(), reason="assassin")
            result.update({"turn_over": True, "round_over": True,
                           "winner": self.winner, "end_reason": self.end_reason})

        elif color.lower() == self.active_team.lower():
            # Eigene Kachel: Treffer, Rundenstand aktualisieren
            if color == "red":
                self.red_found += 1
            else:
                self.blue_found += 1

            if self.guesses_remaining != -1:
                self.guesses_remaining -= 1

            needed = RED_COUNT if self.active_team == "Red" else BLUE_COUNT
            found  = self.red_found if self.active_team == "Red" else self.blue_found

            if found >= needed:
                # Alle eigenen Kacheln gefunden: aktives Team gewinnt
                self._end_round(winner=self.active_team, reason="all_found")
                result.update({"turn_over": True, "round_over": True,
                               "winner": self.winner, "end_reason": self.end_reason})
            elif self.guesses_remaining == 0:
                self._switch_team()
                result["turn_over"] = True

        else:
            # Falsche Kachel (Gegner oder Neutral): Zug endet
            if color == "red":
                self.red_found += 1
            elif color == "blue":
                self.blue_found += 1

            # Prüfen ob der Gegner durch diesen Klick zufällig gewonnen hat
            opponent  = self._opponent()
            opp_color = opponent.lower()
            needed    = RED_COUNT  if opp_color == "red"  else BLUE_COUNT
            found     = self.red_found if opp_color == "red" else self.blue_found

            if found >= needed:
                self._end_round(winner=opponent, reason="all_found")
                result.update({"turn_over": True, "round_over": True,
                               "winner": self.winner, "end_reason": self.end_reason})
            else:
                reason = "neutral" if color == "white" else "wrong_guess"
                self._switch_team()
                result.update({"turn_over": True, "end_reason": reason})

        result["state"] = self.get_state()
        return result

    # ── Agenten-Aktion: Zug freiwillig beenden ───────────────────────────────

    def end_turn(self, team: str) -> dict:
        """
        Wird aufgerufen, wenn ein Agent seinen Zug freiwillig beendet.

        UI-Anbindung:
          - Einen "Zug beenden"-Button dem aktiven Agenten anzeigen, solange
            guesses_remaining > 0 und ein Hinweis vorliegt.
          - Bei Klick (team) an den Server schicken; Server ruft diese Methode auf.
          - Den zurückgegebenen State broadcasten, um zur Hinweis-Eingabe des
            gegnerischen Teams zu wechseln.

        Rückgabe-Dict:
          'ok'    – True wenn akzeptiert
          'error' – Fehlermeldung falls abgelehnt
          'state' – aktueller Spielzustand
        """
        if self.round_over:
            return {"ok": False, "error": "Runde bereits beendet."}
        if team != self.active_team:
            return {"ok": False, "error": "Dein Team ist nicht an der Reihe."}
        if self.current_hint is None:
            return {"ok": False, "error": "Noch kein Hinweis gegeben."}

        self._switch_team()
        return {"ok": True, "state": self.get_state()}

    # ── Spielzustand abfragen ─────────────────────────────────────────────────

    def get_state(self) -> dict:
        """
        Liefert einen vollständigen Spielzustand-Snapshot.

        UI-Anbindung:
          - 'board_full'   an Instruktoren senden (alle Farben sichtbar).
          - 'board_agents' an Agenten senden (Farben nur für aufgedeckte Kacheln).
          - Der Server filtert je nach Client-Rolle vor dem Senden.
        """
        return {
            # Brett-Daten
            "board_full":        self.board,
            "board_agents":      {w: (c if w in self.revealed else None)
                                  for w, c in self.board.items()},
            "revealed":          list(self.revealed),

            # Zustand des laufenden Zugs
            "active_team":       self.active_team,
            "current_hint":      self.current_hint,
            "guesses_remaining": self.guesses_remaining,

            # Rundenstand (angeklickte Kacheln dieser Runde)
            "red_found":         self.red_found,
            "blue_found":        self.blue_found,
            "red_total":         RED_COUNT,
            "blue_total":        BLUE_COUNT,

            # Rundenende
            "round_over":        self.round_over,
            "winner":            self.winner,
            "end_reason":        self.end_reason,

            # Gesamtstand (Rundensiege)
            "red_wins":          self.red_wins,
            "blue_wins":         self.blue_wins,
        }

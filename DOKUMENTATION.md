# Codenames – Technische Dokumentation

## Inhaltsverzeichnis

1. [Projektübersicht](#1-projektübersicht)
2. [Spielregeln](#2-spielregeln)
3. [Voraussetzungen & Installation](#3-voraussetzungen--installation)
4. [Spiel starten](#4-spiel-starten)
5. [Architektur](#5-architektur)
6. [Modulbeschreibungen](#6-modulbeschreibungen)
7. [Netzwerkprotokoll](#7-netzwerkprotokoll)
8. [Spielzustand (State-Objekt)](#8-spielzustand-state-objekt)
9. [Hinweis-Validierung](#9-hinweis-validierung)
10. [Tests](#10-tests)
11. [Dateiübersicht](#11-dateiübersicht)

---

## 1. Projektübersicht

Dieses Projekt ist eine netzwerkfähige Python-Implementierung des Brettspiels **Codenames** für genau **4 Spieler**. Ein Spieler hostet das Spiel als Server; die anderen drei verbinden sich als Clients. Die gesamte Benutzeroberfläche ist in **Tkinter** umgesetzt und läuft im Vollbildmodus.

| Eigenschaft | Wert |
|---|---|
| Sprache | Python 3.x |
| UI-Framework | Tkinter (Standard-Bibliothek) |
| Netzwerk | TCP-Sockets, zeilenbasiertes JSON |
| Spieleranzahl | 4 (fest) |
| Wortliste | 4 138 deutsche Substantive |

---

## 2. Spielregeln

### Grundprinzip

Das Spielfeld besteht aus einem **5×5-Raster** mit 25 zufällig gewählten Wörtern. Jedes Wort gehört verdeckt zu einer Farbe:

| Farbe | Bedeutung | Anzahl |
|---|---|---|
| Rot | Wörter des roten Teams | 8 oder 9 |
| Blau | Wörter des blauen Teams | 8 oder 9 |
| Weiß | Neutrale Wörter | 7 |
| Schwarz | Assassin-Karte (sofort verloren) | 1 |

Das Team, das **beginnt**, erhält **9 eigene Karten**; das andere Team **8**. Welches Team anfängt, wird zufällig bestimmt und rotiert nach jeder Runde.

### Rollen

Jedes Team hat zwei Spieler:

- **Spymaster (Instructor):** Kennt alle Farben auf dem Feld. Gibt pro Zug **einen Hinweis** (ein deutsches Substantiv + eine Zahl) und darf keine Karten anklicken.
- **Agent:** Sieht das Feld ohne Farben (außer bereits aufgedeckten). Klickt Kacheln basierend auf dem Hinweis an.

### Spielablauf

1. Der Spymaster des aktiven Teams gibt einen Hinweis (Wort + Zahl).
2. Der Agent des aktiven Teams klickt Kacheln an (so viele wie angegeben, plus optional eine extra).
3. Deckt der Agent eine **eigene Karte** auf → Zug läuft weiter (falls noch Versuche übrig).
4. Deckt der Agent eine **gegnerische oder neutrale Karte** auf → Zug endet, Gegner ist dran.
5. Deckt der Agent die **schwarze Karte** auf → das aktive Team **verliert sofort**.
6. Ein Team gewinnt die Runde, wenn alle seine Karten gefunden wurden.
7. Das erste Team, das **3 Runden** gewinnt, gewinnt das **Gesamtspiel**. Danach wird keine neue Runde mehr gestartet.

---

## 3. Voraussetzungen & Installation

### Python-Version

Python **3.10 oder neuer** wird empfohlen (wegen `match`-Syntax in neueren Ergänzungen und `X | Y`-Union-Typen).

### Pflichtabhängigkeiten

Alle folgenden Pakete gehören zur Python-Standardbibliothek und müssen nicht installiert werden:

- `tkinter`
- `socket`
- `threading`
- `json`
- `re`
- `random`
- `itertools`

### Optionale Abhängigkeit: HanTa

```bash
pip install HanTa
```

**HanTa** ist ein deutscher Morphologie-Tagger. Er wird in der Hinweis-Validierung eingesetzt, um sicherzustellen, dass nur echte deutsche Substantive als Hinweise zugelassen werden.

- **Mit HanTa:** POS-Tagging (Part-of-Speech) prüft exakt, ob das Wort ein Substantiv ist.
- **Ohne HanTa:** Fallback auf einfache Großschreibungsprüfung (weniger präzise).

Das Modell `morphmodel_ger.pgz` muss sich im Arbeitsverzeichnis befinden oder wird automatisch vom Paket mitgeliefert.

### Netzwerkkonfiguration

In `main.py` sind folgende Konstanten zu setzen:

```python
SERVER_IP = '10.97.36.101'   # IP-Adresse des Server-Computers
PORT      = 50001            # TCP-Port (muss auf dem Server frei sein)
```

Alle vier Rechner müssen sich im selben Netzwerk befinden und der Port darf nicht durch eine Firewall blockiert werden.

---

## 4. Spiel starten

### Server (1 Spieler)

```bash
python main.py server
```

Das Fenster zeigt zunächst „Warte auf Spieler…" und wechselt automatisch zur Rollenanzeige, sobald alle vier Spieler verbunden sind.

### Clients (3 Spieler)

```bash
python main.py
```

(kein Argument = Client-Modus)

### Startreihenfolge

1. Server starten
2. Drei Clients starten (Reihenfolge unter den Clients egal)
3. Sobald der dritte Client verbunden ist, startet das Spiel automatisch für alle

---

## 5. Architektur

### Überblick

```
┌─────────────────────────────────────────────────────┐
│                   main.py (Entry Point)             │
│  ┌──────────────────────┐  ┌──────────────────────┐ │
│  │    Server-Modus      │  │    Client-Modus      │ │
│  │  run_server(...)     │  │  run_client(...)     │ │
│  └──────────┬───────────┘  └──────────┬───────────┘ │
│             │                         │             │
│  ┌──────────▼─────────────────────────▼───────────┐ │
│  │              CodenamesUI (ui.py)               │ │
│  │  Tkinter-Vollbild, Callbacks: on_tile_click,   │ │
│  │  on_end_turn, on_submit_hint                   │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘

Server-Seite:
┌────────────────────────────────────────────────────┐
│  main.py (_handle_action, _broadcast)              │
│  ┌─────────────────────────────────────────────┐   │
│  │         GameController (controller.py)      │   │
│  │  submit_hint / reveal_tile / end_turn        │   │
│  │  get_state → State-Snapshot                 │   │
│  └─────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────┘
```

### Datenfluss (Beispiel: Agent klickt Kachel)

```
Agent-UI                 main.py               GameController
   │                        │                       │
   │── on_tile_click(word) ─►│                       │
   │                        │── reveal_tile(color, word) ──►│
   │                        │◄─────────── result + state ───│
   │                        │── _broadcast(state_update) ──►│ alle 4 Clients
   │◄── show_game_from_state(state) ──────────────────────────
```

### Rollenverteilung

`login.py` erstellt beim Serverstart alle vier Rollen-Farben-Kombinationen (Spymaster Rot, Spymaster Blau, Agent Rot, Agent Blau), mischt sie zufällig und verteilt sie:

- `server` → erster Eintrag (Spieler, der den Server hostet)
- `client_1`, `client_2`, `client_3` → nach Verbindungsreihenfolge

---

## 6. Modulbeschreibungen

### `main.py` – Entry Point & Netzwerkschicht

Enthält sowohl Server- als auch Client-Logik in einer Datei.

**Globale Variablen (Server-Seite):**

| Variable | Typ | Bedeutung |
|---|---|---|
| `_clients` | `list` | Alle verbundenen Sockets mit (conn, role, color) |
| `_clients_lock` | `Lock` | Thread-Sicherheit beim Zugriff auf `_clients` |
| `_controller` | `GameController` | Instanz der Spiellogik (wird bei Spielstart erzeugt) |
| `_game_started` | `Event` | Wird gesetzt, sobald alle 3 Clients verbunden sind |

**Wichtige Funktionen:**

| Funktion | Beschreibung |
|---|---|
| `run_server(...)` | Startet TCP-Server, nimmt 3 Clients an, gibt `(role, color, send_fn)` zurück |
| `run_client(...)` | Verbindet mit Server, gibt `(role, color, send_fn)` zurück |
| `_handle_action(color, msg)` | Leitet Spielaktion an `GameController` weiter, broadcasted den neuen State |
| `_broadcast(msg)` | Sendet JSON-Nachricht an alle verbundenen Clients |
| `_start_new_round()` | Startet neue Runde, tauscht Rollen, sendet State |
| `_client_thread(conn, role, color)` | Thread pro Client: empfängt Nachrichten in Endlosschleife |

---

### `controller.py` – Spiellogik

**Klasse `GameController`**

Verwaltet den gesamten Spielzustand. Wird ausschließlich auf der Server-Seite instanziiert.

**Konstanten:**

| Konstante | Wert | Bedeutung |
|---|---|---|
| `STARTING_TEAM_CARDS` | 9 | Karten des beginnenden Teams |
| `OTHER_TEAM_CARDS` | 8 | Karten des anderen Teams |
| `WHITE_COUNT` | 7 | Neutrale Karten |
| `BLACK_COUNT` | 1 | Assassin-Karte |
| `TOTAL` | 25 | Gesamtanzahl Kacheln |
| `WIN_THRESHOLD` | 3 | Rundensiege für den Gesamtsieg |

**Methoden:**

| Methode | Parameter | Rückgabe | Beschreibung |
|---|---|---|---|
| `submit_hint(team, word, count)` | Team-Farbe, Hinweiswort, Anzahl | `dict` | Instructor gibt Hinweis |
| `reveal_tile(team, word)` | Team-Farbe, Wort | `dict` | Agent deckt Kachel auf |
| `end_turn(team)` | Team-Farbe | `dict` | Agent beendet Zug freiwillig |
| `get_state()` | – | `dict` | Vollständiger Spielzustand-Snapshot |
| `start_new_round()` | – | – | Neue Runde (Punkte bleiben) |

**Rückgabe-Keys von `submit_hint`:**

```python
{"ok": bool, "error": str, "state": dict}
```

**Rückgabe-Keys von `reveal_tile`:**

```python
{
    "ok":          bool,
    "color":       str,          # Farbe der aufgedeckten Kachel
    "correct":     bool,         # True wenn eigene Kachel
    "turn_over":   bool,         # True wenn Zug wechselt
    "round_over":  bool,         # True wenn Runde endet
    "winner":      str | None,   # "Red" oder "Blue" bei round_over
    "end_reason":  str | None,   # "assassin", "all_found", "neutral", "wrong_guess"
    "state":       dict,
}
```

---

### `ui.py` – Benutzeroberfläche

**Klasse `CodenamesUI`**

Tkinter-Vollbild-UI. Kommuniziert mit `main.py` ausschließlich über drei Callbacks:

| Callback | Signatur | Wann ausgelöst |
|---|---|---|
| `on_tile_click` | `fn(word: str)` | Agent klickt eine Kachel |
| `on_end_turn` | `fn()` | Agent klickt „Zug beenden" |
| `on_submit_hint` | `fn(word: str, count: int)` | Instructor sendet Hinweis |

**Bildschirme:**

| Methode | Bildschirm |
|---|---|
| `_show_waiting()` | Wartebildschirm (noch nicht alle Spieler verbunden) |
| `show_role(role, color)` | Rollenanzeige (wartet auf Spielstart) |
| `show_game_from_state(state)` | Spielfeld (Hauptansicht) |

**Hilfsfunktionen (Modul-Ebene):**

| Funktion | Beschreibung |
|---|---|
| `_normalize(w)` | Kleinbuchstaben, nur deutsche Buchstaben |
| `_flatten(w)` | Wie `_normalize`, zusätzlich Umlaute → Basisvokale |
| `_get_stem(w)` | Grober Wortstamm (Präfix/Suffix-Stripping) |
| `_get_tagger()` | Lädt HanTa-Tagger (Singleton, lazy) |

---

### `login.py` – Rollenvergabe

```python
assign_role_color() -> dict
```

Erstellt alle vier Rollen-Farben-Kombinationen und mischt sie zufällig:

```python
{
    "server":   ("instructor", "Red"),
    "client_1": ("agent",      "Red"),
    "client_2": ("instructor", "Blue"),
    "client_3": ("agent",      "Blue"),
}
```

Jede Kombination kommt genau einmal vor. Die Zuweisung ist bei jedem Spielstart neu zufällig.

---

### `words.py` – Wortliste

Enthält die Liste `woerter` mit **4 138 deutschen Substantiven**. Pro Runde werden daraus 25 zufällig ausgewählt (`random.sample`).

---

### `test_codenames.py` – Testsuite

Vollständige Unit- und Integrationstests (siehe [Abschnitt 10](#10-tests)).

---

### `server.py` / `client.py` – Prototyp-Dateien

Diese Dateien sind **nicht aktiv** und stammen aus der frühen Entwicklungsphase. Die produktive Netzwerklogik befindet sich vollständig in `main.py`.

---

## 7. Netzwerkprotokoll

Die Kommunikation erfolgt über **TCP-Sockets** mit **zeilenbasiertem JSON** (jede Nachricht endet mit `\n`).

### Server → Client (Broadcast)

| `type` | Payload | Bedeutung |
|---|---|---|
| `login` | `{role, color}` | Rollenverteilung beim Verbindungsaufbau |
| `game_start` | `{state}` | Spielfeld bereit, alle 4 Spieler verbunden |
| `state_update` | `{state}` | Spielzustand hat sich geändert |
| `role_update` | `{role, color}` | Neue Runde, Rollen gewechselt |

### Client → Server

| `type` | Payload | Wer sendet |
|---|---|---|
| `submit_hint` | `{word, count}` | Aktiver Instructor |
| `reveal_tile` | `{word}` | Aktiver Agent |
| `end_turn` | `{}` | Aktiver Agent |

### Nachrichtenformat (Beispiel)

```json
{"type": "submit_hint", "word": "Tier", "count": 2}\n
```

```json
{"type": "state_update", "state": { ... }}\n
```

---

## 8. Spielzustand (State-Objekt)

`GameController.get_state()` liefert folgenden Snapshot:

```python
{
    # Brett
    "board_full":        dict[str, str],   # {wort: farbe} – für Instructor
    "board_agents":      dict[str, None | str], # {wort: farbe_oder_None} – für Agent
    "revealed":          list[str],        # Liste aufgedeckter Wörter

    # Aktueller Zug
    "active_team":       str,              # "Red" oder "Blue"
    "current_hint":      tuple | None,     # ("Wort", 2) oder None
    "guesses_remaining": int,              # -1 = unbegrenzt

    # Rundenstand
    "red_found":         int,
    "blue_found":        int,
    "red_total":         int,              # 8 oder 9
    "blue_total":        int,              # 8 oder 9
    "starting_team":     str,             # Team das diese Runde begann

    # Rundenende
    "round_over":        bool,
    "winner":            str | None,
    "end_reason":        str | None,       # "assassin" | "all_found"

    # Gesamtstand (über alle Runden)
    "red_wins":          int,
    "blue_wins":         int,

    # Gesamtspiel-Ende
    "game_over":         bool,        # True wenn ein Team WIN_THRESHOLD Runden gewonnen hat
    "game_winner":       str | None,  # "Red" oder "Blue"
    "win_threshold":     int,         # Aktuell: 3
}
```

**Wichtig:** `board_full` und `board_agents` unterscheiden sich:
- `board_full` enthält für jede Kachel die echte Farbe → wird nur an Instructors gesendet
- `board_agents` enthält `None` für noch nicht aufgedeckte Kacheln → für Agents

In der aktuellen Implementierung sendet der Server **denselben State** an alle; die UI selbst wählt je nach Rolle die richtige Ansicht (`board_full` vs. `board_agents`).

---

## 9. Hinweis-Validierung

Die Methode `_is_valid_hint()` in `ui.py` prüft Hinweise in folgender Reihenfolge:

| Stufe | Prüfung | Beispiel-Fehler |
|---|---|---|
| 1 | Nicht leer | `""` |
| 2 | Nur ein Wort (kein Leerzeichen) | `"zwei Wörter"` |
| 3 | Nur Buchstaben (inkl. Umlaute/ß) | `"Hund2"` |
| 4 | Mindestlänge 2 Zeichen | `"A"` |
| 5 | Mindestens ein Vokal | `"Str"` |
| 6 | Vokal-Anteil ≥ 10 % | Buchstabenketten |
| 7 | Keine 4+ gleichen Zeichen hintereinander | `"Haaaar"` |
| 8 | POS-Check (HanTa): muss Substantiv sein | `"laufen"` |
| 9 | Kein direkter Match mit Gitterwort | `"Hund"` wenn im Grid |
| 10 | Hinweis enthält kein Gitterwort als Teilstring | `"Hundehaus"` |
| 11 | Hinweis ist kein Teilstring eines Gitterworts | `"Hund"` in `"Hundehaus"` |
| 12 | Kein gleicher Wortstamm (via `_get_stem`) | `"Verarbeitung"` / `"Arbeit"` |
| 13 | Konsonantenskelett unterscheidet sich (≥ 3 Kons.) | klanglich ähnliche Wörter |

---

## 10. Tests

### Testsuite starten

```bash
python -m pytest test_codenames.py -v
# oder
python test_codenames.py
```

### Testklassen

| Klasse | Bereich | Tests |
|---|---|---|
| `TestBoardGeneration` | Spielfeld-Erzeugung | Kachelanzahl, Farbverteilung, Eindeutigkeit |
| `TestSubmitHint` | Hinweis geben | Gültige/ungültige Hints, Duplikate, falsche Teams |
| `TestRevealTile` | Kachel aufdecken | Eigene/fremde/schwarze Kacheln, Rundenende |
| `TestEndTurn` | Zug beenden | Teamwechsel, falsches Team, fehlender Hinweis |
| `TestGetState` | State-Snapshot | Pflichtschlüssel, board_agents-Maskierung |
| `TestLoginAssignment` | Rollenvergabe | 4 Slots, alle Kombinationen eindeutig |
| `TestNormalize` | `_normalize()` | Kleinbuchstaben, Sonderzeichen, Umlaute |
| `TestFlatten` | `_flatten()` | Umlaut-Konvertierung |
| `TestIsValidHint` | Hinweis-Validierung | Alle Fehlerfälle |
| `TestPerformance` | Performance | Board-Gen < 50 ms, State < 5 ms, Vollspiel < 500 ms |
| `TestUIWidgets` | Tkinter-Widgets | Bildschirmaufbau, Callbacks, Button-Zustände |
| `TestFullRoundIntegration` | Vollrunde | Rot gewinnt, Assassin, neue Runde |
| `TestNetworkSimulation` | Netzwerk (lokal) | TCP-Simulation auf 127.0.0.1, vollständiges Spiel |

### Performance-Grenzwerte

| Test | Limit |
|---|---|
| Board-Erzeugung | < 50 ms |
| `get_state()` | < 5 ms |
| Vollständiges Spiel (simuliert) | < 500 ms |
| Hinweis-Validierung | < 5 ms |

### Netzwerk-Tests (`TestNetworkSimulation`)

Diese Tests starten einen echten lokalen TCP-Server auf einem freien Port (`127.0.0.1`). Die produktive `SERVER_IP` wird für die Testdauer mit `unittest.mock.patch` überschrieben, sodass kein echter Netzwerkverkehr entsteht. Die `LocalGameSession`-Klasse verwaltet Server- und Client-Threads automatisch als Context Manager.

---

## 11. Dateiübersicht

```
codenames/
├── main.py              Entry Point: Server-/Client-Modus, TCP-Netzwerklogik
├── controller.py        Spiellogik: GameController (nur Server)
├── ui.py                Tkinter-UI: CodenamesUI + Hinweis-Validierung
├── login.py             Rollenvergabe: assign_role_color()
├── words.py             Wortliste: 4 138 deutsche Substantive
├── test_codenames.py    Vollständige Testsuite (Unit + Integration + Netzwerk)
├── server.py            Prototyp (nicht aktiv)
├── client.py            Prototyp (nicht aktiv)
└── DOKUMENTATION.md     Diese Datei
```

---

*Dokumentation erstellt für das Schulprojekt Codenames – Python-Netzwerkspiel.*

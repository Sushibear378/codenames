from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
import re

# Die UI ist mithilfe von künstlicher Intelligenz generiert worden. Dies gilt besonders für das Design

# ── Farbpalette ────────────────────────────────────────────────────────────────
# Alle Farben sind als Hex-Strings definiert, damit sie zentral geändert werden können.

BG         = "#090b0f"   # Allgemeiner Fensterhintergrund (fast Schwarz, leicht blau)
FG_LIGHT   = "#c0b8a8"   # Helle Vordergrundfarbe für Texte und KachelbeschriftungenDie UI 
FG_MUTED   = "#5a5248"   # Gedämpfte Farbe für inaktive Texte und Trennlinien
RED_CLR    = "#882020"   # Teamfarbe Rot
BLUE_CLR   = "#183870"   # Teamfarbe Blau
HIDDEN_CLR = "#161e28"   # Hintergrund noch nicht aufgedeckter Kacheln (dunkelblaugrau)
BAR_BG     = "#060810"   # Hintergrund der Punkte-Leiste oben (noch dunkler als BG)
GOLD       = "#a88838"   # Goldfarbe für die schwarze (Assassin-)Karte

# Farben für bereits aufgedeckte Kacheln in der Spymaster-Ansicht (abgedunkelt).
# Tupel: (Hintergrundfarbe, Textfarbe) je Team-Farbe
DIM_MAP = {
    "red":   ("#350808", "#704040"),   # aufgedeckte Rot-Karte
    "blue":  ("#060f20", "#304868"),   # aufgedeckte Blau-Karte
    "white": ("#303030", "#606060"),   # aufgedeckte neutrale Karte
    "black": ("#0d0d10", "#404045"),   # aufgedeckte Assassin-Karte
}

# ── HanTa-Tagger (lazy singleton) ─────────────────────────────────────────────

_tagger = None  # Wird beim ersten Aufruf von _get_tagger() initialisiert


def _get_tagger():
    """Lädt den deutschen Morphologie-Tagger (HanTa) beim ersten Aufruf einmalig.

    Der Tagger ist ein Singleton: Er wird nur einmal instanziiert und dann
    in _tagger gecacht, um die teure Initialisierung nicht mehrfach auszuführen.
    Fehlt das Paket, wird None zurückgegeben und die Validierung fällt auf eine
    einfache Großschreibungsprüfung zurück.
    """
    global _tagger
    if _tagger is None:
        try:
            from HanTa import HanoverTagger as ht
            _tagger = ht.HanoverTagger('morphmodel_ger.pgz')
        except ImportError:
            print("[HanTa] nicht installiert – bitte: pip install HanTa")
        except Exception as e:
            print(f"[HanTa] Fehler beim Laden: {e}")
    return _tagger


# ── Normalisierungshilfsfunktionen ─────────────────────────────────────────────

def _normalize(w: str) -> str:
    """Wandelt ein Wort in Kleinbuchstaben um und behält nur deutsche Buchstaben.

    Entfernt Sonderzeichen, Zahlen und Leerzeichen; Umlaute und ß bleiben erhalten.
    Wird für exakte Zeichenkettenvergleiche (z. B. Hinweis == Gitterwort) verwendet.
    """
    return re.sub(r'[^a-zäöüß]', '', w.lower())


def _flatten(w: str) -> str:
    """Wie _normalize, wandelt aber zusätzlich Umlaute in Basisvokale um.

    ä→a, ö→o, ü→u, ß→ss
    Wird für unscharfe Vergleiche verwendet, damit z. B. „Öl" und „Ol" als
    gleich erkannt werden, wenn ein Compound-Wort überprüft wird.
    """
    s = _normalize(w)
    return s.replace('ä', 'a').replace('ö', 'o').replace('ü', 'u').replace('ß', 'ss')


def _get_stem(w: str) -> str:
    """Entfernt gängige deutsche Präfixe und Suffixe für einen groben Wortfamilien-Abgleich.

    Wendet Präfix- und Suffixstripping in je zwei Durchläufen an, damit auch
    kombinierte Affixe (z. B. „Verarbeitung" → „arbeit") erkannt werden.
    Das Ergebnis ist kein linguistisch korrekter Stamm, sondern eine kurze
    Zeichenkette, anhand derer Wörter derselben Wortfamilie identifiziert werden.
    """
    w = _flatten(w)

    # Häufige Verbpräfixe, Ableitungspräfixe und trennbare Vorsilben
    prefixes = ['ge', 'be', 'ver', 'zer', 'ent', 'emp', 'er', 'ur', 'miss',
                'auf', 'ab', 'an', 'zu', 'ein', 'aus', 'vor', 'nach', 'mit', 'um', 'durch', 'uber', 'unter']

    # Zwei Durchläufe, damit verschachtelte Präfixe (z. B. „ver+ent-") entfernt werden
    for _ in range(2):
        for pref in prefixes:
            if w.startswith(pref) and len(w) > len(pref) + 2:
                w = w[len(pref):]
                break

    # Suffixliste: längere zuerst, damit spezifischere Endungen Vorrang haben
    suffixes = ['innen', 'ium', 'ung', 'heit', 'keit', 'schaft', 'lein', 'chen',
                'lich', 'isch', 'haft', 'itat', 'ismus', 'enz', 'anz', 'nis',
                'ent', 'ant', 'ist', 'ial', 'sam', 'bar', 'tum',
                'en', 'er', 'ig', 'al', 'ie', 'ik', 'ion', 'or', 'ur', 'in', 'um',
                'es', 'st', 'nd', 'e', 's', 'n', 't']

    # Sortierung nach Länge (absteigend) sicherstellt, dass längere Suffixe zuerst geprüft werden
    suffixes.sort(key=len, reverse=True)

    # Zwei Durchläufe für verschachtelte Suffixe (z. B. „-ungen" → „-ung" → Stamm)
    for _ in range(2):
        for suff in suffixes:
            if w.endswith(suff) and len(w) > len(suff) + 2:
                w = w[:-len(suff)]
                break

    return w


# ── Haupt-UI-Klasse ────────────────────────────────────────────────────────────

class CodenamesUI:
    """Tkinter-basierte Benutzeroberfläche für das Codenames-Spiel.

    Verwaltet alle Bildschirme (Warten, Rollenanzeige, Spielfeld) und stellt
    Callbacks bereit, über die main.py auf Spieleraktionen reagieren kann.
    """

    def __init__(self, role: str = None, color: str = None, server_ip: str = None):
        """Erstellt das Hauptfenster und initialisiert alle Zustände.

        Parameters
        ----------
        role:      Rolle des Spielers ('instructor' oder 'agent'), oder None wenn noch nicht bekannt
        color:     Teamfarbe des Spielers ('red' oder 'blue'), oder None wenn noch nicht bekannt
        server_ip: Eigene LAN-IP (nur Server-Modus); wird im Wartebildschirm angezeigt
        """
        self.root = tk.Tk()
        self.root.title("Codenames")
        self.root.configure(bg=BG)
        self.root.attributes('-fullscreen', True)                           # Vollbild aktivieren
        self.root.bind('<Escape>', lambda _: self.root.attributes('-fullscreen', False))  # Esc beendet Vollbild

        self.role  = role    # Spielerrolle: 'instructor' (Spymaster) oder 'agent' (Ratender)
        self.color = color   # Teamfarbe: 'red' oder 'blue'
        self._server_ip = server_ip  # Eigene LAN-IP (nur Server-Modus), für Wartebildschirm

        # Callbacks – werden von main.py gesetzt, sobald die Netzwerkverbindung steht
        self.on_tile_click:   callable | None = None   # fn(word)  → Kachel angeklickt
        self.on_end_turn:     callable | None = None   # fn()       → „Zug beenden" geklickt
        self.on_submit_hint:  callable | None = None   # fn(word, count) → Hinweis abgesendet

        self._grid_words: list[str] = []         # Alle 25 Wörter des aktuellen Spielfelds
        self._current_state: dict | None = None  # Letzter bekannter Spielzustand (für Neuzeichnen)
        self._resize_after = None                # Handle für das debounced Neuzeichnen bei Fenstergröße
        self._tile_clicked_this_turn: bool = False  # True sobald der Agent in diesem Zug eine Kachel geklickt hat
        self._last_seen_hint = None              # Letzter Hinweis, um _tile_clicked_this_turn zurückzusetzen

        # Fenstergröße überwachen, damit das Spielfeld bei Größenänderung neu gezeichnet wird
        self.root.bind('<Configure>', self._on_configure)

        # Sofort Rolle anzeigen, wenn vorhanden – sonst Wartebild
        if role and color:
            self.show_role(role, color)
        else:
            self._show_waiting()

    def update_role(self, role: str):
        """Aktualisiert die Rolle (z. B. nach einem Rundenwechsel) und zeichnet das UI neu.

        Wird von main.py nach einem 'role_update'-Netzwerkereignis aufgerufen.
        Hat nur einen sichtbaren Effekt, wenn das Spiel bereits läuft (_current_state gesetzt).
        """
        self.role = role
        if self._current_state is not None:
            self._build_game_ui(self._current_state)

    def show_ip_dialog(self, on_confirm: callable, default_ip: str = "10.97.36.101"):
        """Zeigt ein modales Popup, in dem der Spieler die Server-IP eingeben kann.

        Parameters
        ----------
        on_confirm: Callback fn(ip: str) – wird nach Bestätigung mit der eingegebenen IP aufgerufen
        default_ip: IP, die der „Standard"-Button einsetzt (aktuelle Schul-Server-IP)
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Server-IP")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.grab_set()  # modal – blockiert das Hauptfenster

        w, h = 380, 190
        sx = self.root.winfo_screenwidth()
        sy = self.root.winfo_screenheight()
        dialog.geometry(f"{w}x{h}+{(sx - w) // 2}+{(sy - h) // 2}")

        tk.Label(dialog, text="Server-IP eingeben", bg=BG, fg=FG_LIGHT,
                 font=("Helvetica", 16, "bold")).pack(pady=(22, 8))

        entry = tk.Entry(dialog, bg=HIDDEN_CLR, fg=FG_LIGHT,
                         insertbackground=FG_LIGHT, font=("Helvetica", 14),
                         width=22, justify="center", relief="flat", bd=6)
        entry.pack(pady=4)
        entry.focus_set()

        btn_frame = tk.Frame(dialog, bg=BG)
        btn_frame.pack(pady=14)

        def _confirm():
            ip = entry.get().strip()
            if ip:
                dialog.destroy()
                on_confirm(ip)

        def _set_default():
            entry.delete(0, tk.END)
            entry.insert(0, default_ip)

        tk.Button(btn_frame, text="Standard", bg=HIDDEN_CLR, fg=FG_MUTED,
                  font=("Helvetica", 12), relief="flat", bd=0,
                  padx=14, pady=6, cursor="hand2",
                  command=_set_default).pack(side="left", padx=8)

        tk.Button(btn_frame, text="Verbinden", bg=BLUE_CLR, fg=FG_LIGHT,
                  font=("Helvetica", 12, "bold"), relief="flat", bd=0,
                  padx=14, pady=6, cursor="hand2",
                  command=_confirm).pack(side="left", padx=8)

        entry.bind("<Return>", lambda _: _confirm())

    # ── interne Hilfsmethoden ─────────────────────────────────────────────────

    def _clear(self):
        """Entfernt alle Widgets aus dem Hauptfenster, um den Bildschirm für einen neuen Aufbau freizugeben."""
        for w in self.root.winfo_children():
            w.destroy()

    def _center_frame(self) -> tk.Frame:
        """Erstellt ein Canvas mit Punktmuster und gibt einen zentrierten Frame zurück.

        Das Canvas füllt das gesamte Fenster; der Frame wird per create_window
        exakt in der Mitte platziert. Alle Wartebildschirme und Rollenanzeigen
        legen ihre Widgets in diesem Frame ab.
        """
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        cv = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        cv.pack(fill=tk.BOTH, expand=True)
        self._paint_dots(cv, sw, sh)                              # Dekoratives Punktmuster
        frame = tk.Frame(cv, bg=BG)
        cv.create_window(sw // 2, sh // 2, window=frame, anchor="center")
        return frame

    def _paint_dots(self, cv: tk.Canvas, w: int, h: int):
        """Zeichnet ein gleichmäßiges Punktraster auf das Canvas als dekorativen Hintergrund.

        Punkte haben einen Abstand von 30 Pixeln und erscheinen als 2×2-Pixel-Ovale.
        """
        dot_clr = "#1c2840"   # Farbe der Hintergrundpunkte (dunkelblau)
        for x in range(30, w + 30, 30):
            for y in range(30, h + 30, 30):
                cv.create_oval(x - 1, y - 1, x + 1, y + 1, fill=dot_clr, outline="")

    def _team_color(self, team: str) -> str:
        """Gibt die UI-Farbe für das angegebene Team zurück (RED_CLR oder BLUE_CLR)."""
        return RED_CLR if team.lower() == "red" else BLUE_CLR

    # ── Hinweis-Validierung ───────────────────────────────────────────────────

    def _is_valid_hint(self, hint: str, grid_words: list) -> tuple[bool, str]:
        """Prüft, ob ein Hinweis nach den Codenames-Regeln zulässig ist.

        Führt folgende Prüfungen in Reihenfolge durch:
        1. Leerstring / Mehrwort-Hinweis
        2. Zeichensatz und Mindestlänge
        3. Vokal-Ratio (Plausibilitätsprüfung)
        4. Übermäßige Zeichenwiederholung
        5. POS-Tag via HanTa (nur Substantive erlaubt)
        6. Direkte Übereinstimmung mit Gitterwörtern (Oberfläche + Lemma)
        7. Teilwortprüfung (Hinweis enthält/ist-Teil-von Gitterwort)
        8. Wortfamilien-Abgleich via _get_stem()
        9. Konsonantenskelett-Vergleich

        Returns
        -------
        (True, "")             wenn der Hinweis gültig ist
        (False, Fehlermeldung) wenn er ungültig ist
        """
        hint = hint.strip()
        if not hint:
            return False, "Hinweis darf nicht leer sein"

        if ' ' in hint:
            return False, "Hinweis darf nur ein Wort sein"

        hint_words = hint.split()
        tagger     = _get_tagger()
        _vowels    = set('aeiouäöüAEIOUÄÖÜ')

        for word in hint_words:
            # ── Basis-Plausibilitätsprüfung ────────────────────────────────

            # Nur Buchstaben (inklusive Umlaute und ß) erlaubt
            if not re.match(r'^[a-zA-ZäöüÄÖÜß]+$', word):
                return False, f"'{word}' enthält ungültige Zeichen"

            # Mindestlänge 2 Zeichen
            if len(word) < 2:
                return False, f"'{word}' ist zu kurz"

            # Muss mindestens einen Vokal enthalten (filtert z. B. Tippfehler)
            if not any(c in _vowels for c in word):
                return False, f"'{word}' enthält keine Vokale"

            # Vokal-Anteil muss mindestens 10 % betragen (filtert Buchstabenketten wie „brrr")
            if sum(1 for c in word if c in _vowels) / len(word) < 0.10:
                return False, f"'{word}' sieht nicht wie ein deutsches Wort aus"

            # Mehr als 3 direkt aufeinanderfolgende gleiche Zeichen sind unwahrscheinlich
            if re.search(r'(.)\1{3,}', word, re.IGNORECASE):
                return False, f"'{word}' enthält zu viele gleiche Zeichen"

            # ── POS-Check via HanTa ────────────────────────────────────────
            # Nur Substantive (NN) und Eigennamen (NE) sind als Codenames-Hinweise erlaubt.
            norm_lemma = _normalize(word)  # Fallback-Lemma falls HanTa nicht verfügbar
            if tagger:
                try:
                    result = tagger.tag_word(word, taglevel=1)
                    if result:
                        norm_lemma = _normalize(result[0][1])   # Lemma des Taggers übernehmen
                        pos        = result[0][2]               # Part-of-Speech-Tag
                        if pos not in ("NN", "NE"):
                            return False, f"'{word}' ist kein deutsches Substantiv"
                except Exception:
                    pass  # Bei Tagger-Fehler stillschweigend fallback
            else:
                # Ohne Tagger: Großschreibung als minimales Substantiv-Kriterium
                if not word[0].isupper():
                    return False, "Alle Wörter müssen mit Großbuchstaben beginnen"

            # ── Spielfeld-Abgleich ─────────────────────────────────────────
            # Der Hinweis darf kein Gitterwort sein, es nicht enthalten und kein Teil davon sein.
            norm_hint  = _normalize(word)
            flat_hint  = _flatten(word)
            flat_lemma = _flatten(norm_lemma)

            for gw in grid_words:
                norm_gw = _normalize(gw)
                flat_gw = _flatten(gw)

                # Direkte Gleichheit: Hinweis == Gitterwort (Oberfläche oder Lemma)
                if norm_hint == norm_gw or norm_lemma == norm_gw:
                    return False, f"'{word}' ist ein Wort aus dem Spielfeld!"

                # Teilwortprüfung: Hinweis enthält ein Gitterwort als Substring
                for h in (norm_hint, flat_hint, norm_lemma, flat_lemma):
                    for g in (norm_gw, flat_gw):
                        if g and g in h:
                            return False, f"'{word}' enthält das Spielfeldwort '{gw}'"

                # Umgekehrte Teilwortprüfung: Hinweis ist Teil eines Gitterworts
                for h in (norm_hint, flat_hint, norm_lemma, flat_lemma):
                    for g in (norm_gw, flat_gw):
                        if h and h in g:
                            return False, f"'{word}' ist Teil des Spielfeldworts '{gw}'"

                # Wortfamilien-Abgleich: gleicher Stamm → selbe Wortfamilie
                hint_stem = _get_stem(word)
                gw_stem = _get_stem(gw)
                if hint_stem and gw_stem:
                    if hint_stem == gw_stem or hint_stem in gw_stem or gw_stem in hint_stem:
                        return False, f"'{word}' gehört zur selben Wortfamilie wie '{gw}'"

                    # Konsonantenskelett-Vergleich: Wörter mit gleichen Konsonanten (≥ 3)
                    # sind klanglich zu ähnlich (z. B. „Birne" vs. „Birn")
                    hint_cons = re.sub(r'[aeiou]', '', hint_stem)
                    gw_cons = re.sub(r'[aeiou]', '', gw_stem)
                    if hint_cons == gw_cons and len(hint_cons) >= 3:
                        return False, f"'{word}' ähnelt '{gw}' zu stark (gleiche Konsonanten)"

        return True, ""

    def _send_hint(self, number_var, text_var, number_input, text_input):
        """Liest Hinweis-Wort und -Zahl aus den Eingabefeldern, validiert sie und leitet sie weiter.

        Wird durch den „Hinweis senden"-Button im Instructor-Panel ausgelöst.
        Bei Erfolg werden die Eingabefelder geleert; bei Fehler erscheint ein Dialogfenster.
        """
        # Zahl validieren: muss ein Integer ≥ 1 sein
        try:
            count = int(number_var.get())
            if count < 1:
                messagebox.showerror("Fehler", "Die Zahl muss mindestens 1 sein")
                return
        except ValueError:
            messagebox.showerror("Fehler", "Bitte eine gültige Zahl eingeben")
            return

        # Hinweiswort gegen Spielfeldregeln prüfen
        word = text_var.get().strip()
        valid, err = self._is_valid_hint(word, self._grid_words)
        if not valid:
            messagebox.showerror("Ungültiger Hinweis", err)
            return

        # Hinweis über den Netzwerk-Callback weiterleiten (gesetzt von main.py)
        if self.on_submit_hint:
            self.on_submit_hint(word, count)
        else:
            # Fallback für den Standalone-Betrieb ohne Netzwerkverbindung
            print(f"Hinweis: {word} ({count})")

        # Eingabefelder nach erfolgreichem Absenden zurücksetzen
        number_input.delete(0, tk.END)
        text_input.delete(0, tk.END)

    def _tile_clicked(self, word: str):
        """Wird aufgerufen, wenn ein Agent auf eine Kachel klickt.

        Setzt _tile_clicked_this_turn auf True, damit der „Zug beenden"-Button
        nach dem ersten Klick aktiviert wird, und ruft den Netzwerk-Callback auf.
        """
        self._tile_clicked_this_turn = True
        if self.on_tile_click:
            self.on_tile_click(word)

    def _end_turn_clicked(self):
        """Leitet den „Zug beenden"-Klick an main.py weiter (über on_end_turn)."""
        if self.on_end_turn:
            self.on_end_turn()

    def _on_configure(self, event):
        """Reagiert auf Fenstergrößenänderungen und zeichnet das Spielfeld verzögert neu.

        Debounce-Mechanismus: Jede neue Configure-Ereignis löscht den vorherigen
        after()-Timer und setzt einen neuen (120 ms). So wird das kostspielige
        Neuzeichnen erst ausgelöst, wenn die Größenänderung abgeschlossen ist.
        """
        if event.widget is self.root and self._current_state is not None:
            if self._resize_after is not None:
                self.root.after_cancel(self._resize_after)
            self._resize_after = self.root.after(
                120, lambda: self._build_game_ui(self._current_state)
            )

    # ── Bildschirmaufbauten ───────────────────────────────────────────────────

    def _show_waiting(self):
        """Zeigt den Wartebildschirm an, bevor alle Spieler verbunden sind.
        Im Server-Modus wird die eigene LAN-IP gross angezeigt, damit Mitspieler sie ablesen können."""
        self._clear()
        f = self._center_frame()
        tk.Label(f, text="CODENAMES",
                 font=("Segoe UI", 52, "bold"),
                 fg=FG_LIGHT, bg=BG).pack(pady=(0, 8))
        tk.Frame(f, height=3, width=320, bg=FG_MUTED).pack()
        tk.Label(f, text="Warte auf Spieler…",
                 font=("Segoe UI", 20), fg=FG_MUTED, bg=BG).pack(pady=(32, 0))
        if self._server_ip:
            tk.Label(f, text="Server-IP",
                     font=("Segoe UI", 13), fg=FG_MUTED, bg=BG).pack(pady=(28, 2))
            tk.Label(f, text=self._server_ip,
                     font=("Courier New", 28, "bold"), fg=FG_LIGHT, bg=BG).pack()

    def show_role(self, role: str, color: str):
        """Zeigt die Rollen- und Teamzuweisung an, während auf die übrigen Spieler gewartet wird.

        Wird von main.py aufgerufen, sobald der Server die Zuweisung abgeschlossen hat.
        Die Anzeige bleibt so lange, bis show_game_from_state() aufgerufen wird.
        """
        self.role  = role
        self.color = color
        self._clear()

        team_clr  = self._team_color(color)
        team_name = "Rot"       if color.lower() == "red"        else "Blau"
        role_name = "Spymaster" if role.lower()  == "instructor" else "Agent"

        f = self._center_frame()
        tk.Label(f, text="CODENAMES",
                 font=("Segoe UI", 52, "bold"),
                 fg=FG_LIGHT, bg=BG).pack(pady=(0, 8))
        tk.Frame(f, height=3, width=320, bg=team_clr).pack()     # Teamfarbiger Trennstrich
        tk.Label(f, text=f"Team {team_name}",
                 font=("Segoe UI", 18), fg=team_clr, bg=BG).pack(pady=(24, 4))
        tk.Label(f, text=role_name,
                 font=("Segoe UI", 36, "bold"),
                 fg=FG_LIGHT, bg=BG).pack(pady=(0, 8))
        tk.Label(f, text="Viel Erfolg!",
                 font=("Segoe UI", 14), fg=FG_MUTED, bg=BG).pack(pady=(0, 24))
        # Kein „Weiter"-Button – das Spiel startet automatisch, wenn alle 4 Spieler verbunden sind
        tk.Label(f, text="Warte auf andere Spieler…",
                 font=("Segoe UI", 14), fg=FG_MUTED, bg=BG).pack()

    def show_game_from_state(self, state: dict):
        """Speichert den aktuellen Spielzustand und baut das Spielfeld neu auf.

        Einstiegspunkt für alle State-Updates aus main.py. Durch das Speichern
        in _current_state kann _on_configure bei Fenstergrößenänderung
        das Spielfeld ohne erneuten Netzwerkaufruf wiederherstellen.
        """
        self._current_state = state
        self._build_game_ui(state)

    def _build_game_ui(self, state: dict):
        """Baut die vollständige Spielansicht auf Basis des übergebenen Spielzustands auf.

        Reihenfolge:
        1. Punkte-Leiste oben
        2. Optionales Rundenende-Banner
        3. Hauptbereich: 5×5-Kachelgitter (links) + ggf. Instructor-Panel (rechts)
        4. Agent-Steuerelemente unterhalb des Gitters (Hinweisanzeige + „Zug beenden")

        Die Kachelgröße wird dynamisch aus der aktuellen Fenstergröße berechnet,
        damit das Layout auf beliebigen Bildschirmen skaliert.
        """
        self._clear()

        # Spielzustand entpacken
        active_team  = state["active_team"]           # Welches Team ist gerade am Zug
        hint         = state["current_hint"]           # Aktueller Hinweis (word, count) oder None
        guesses      = state["guesses_remaining"]      # Noch verbleibende Rateversuche (-1 = unbegrenzt)
        revealed_set = set(state.get("revealed", []))  # Menge der bereits aufgedeckten Wörter
        round_over   = state.get("round_over", False)  # True wenn die Runde beendet ist

        # Rollenflags für diesen Spieler
        is_agent        = self.role and self.role.lower() == "agent"
        is_instructor   = self.role and self.role.lower() == "instructor"

        # True wenn dieser Agent an der Reihe ist UND die Runde noch läuft
        is_active_agent = (is_agent and
                           self.color and
                           self.color.lower() == active_team.lower() and
                           not round_over)

        # Agenten dürfen raten, wenn sie aktiv sind, ein Hinweis vorliegt und noch Versuche übrig sind
        can_guess       = is_active_agent and hint is not None and (guesses > 0 or guesses == -1)

        # Instructor ist zur Eingabe bereit, wenn er aktiv ist und noch kein Hinweis gegeben wurde
        is_active_instructor = (
            is_instructor and
            self.color and self.color.lower() == active_team.lower() and
            hint is None and not round_over
        )

        # ── Punkte-Leiste am oberen Rand ──────────────────────────────────
        self._build_score_bar(state, active_team)

        # ── Rundenende-Banner direkt unter der Punkte-Leiste ──────────────
        if round_over:
            self._build_round_over_banner(state)

        # ── Kachelgröße dynamisch berechnen ───────────────────────────────
        self.root.update_idletasks()   # Aktuelle Fenstermaße abrufen
        win_w = self.root.winfo_width()
        win_h = self.root.winfo_height()
        if win_w < 100:   # Fenster wurde noch nicht gezeichnet (erster Aufruf)
            win_w = self.root.winfo_screenwidth()
            win_h = self.root.winfo_screenheight()

        bar_h      = 54    # Höhe der Punkte-Leiste in Pixeln
        ctrl_h     = 60 if is_agent else 0        # Höhe der Agenten-Steuerelemente (0 für Instructor)
        panel_w    = 280 if is_instructor else 0  # Breite des Instructor-Panels
        gap        = 48 if is_instructor else 0   # Abstand zwischen Gitter und Panel
        h_padding  = 48    # Horizontaler Gesamtrand
        v_padding  = 40    # Vertikaler Gesamtrand

        avail_w = win_w - panel_w - gap - h_padding   # Verfügbare Breite für das 5×5-Gitter
        avail_h = win_h - bar_h - ctrl_h - v_padding  # Verfügbare Höhe für das 5×5-Gitter

        # Kachelmaße: 91 % bzw. 75 % des theoretischen Platzanteils, damit Abstände entstehen
        tile_w   = max(120, int(avail_w / 5 * 0.91))
        tile_h   = max(55,  int(avail_h / 5 * 0.75))
        tile_pad = max(3, tile_h // 20)   # Abstand zwischen Kacheln
        font_sz  = max(8, tile_h // 7)    # Schriftgröße skaliert mit Kachelhöhe

        # ── Hauptbereich (Canvas + zentrierter Content-Frame) ─────────────
        main = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        main.pack(fill=tk.BOTH, expand=True)
        self._paint_dots(main, win_w, win_h)

        content = tk.Frame(main, bg=BG)
        cx = win_w // 2
        # Vertikale Mitte: Rundenende-Banner reduziert den verfügbaren Raum
        cy = (win_h - bar_h - (60 if state.get("round_over") else 0)) // 2
        main.create_window(cx, cy, window=content, anchor="center")

        # Linke Spalte: Kachelgitter + Agent-Steuerelemente
        grid_side = tk.Frame(content, bg=BG)
        grid_side.pack(side=tk.LEFT)

        # Farbiger Rahmen um das Gitter zeigt dem aktiven Agenten seinen Zug an
        border_clr = self._team_color(self.color) if is_active_agent else BG
        border = tk.Frame(grid_side, bg=border_clr, padx=5, pady=5)
        border.pack()

        grid_inner = tk.Frame(border, bg=BG)
        grid_inner.pack()

        # Instructor sieht board_full (mit Farben), Agent sieht board_agents (aufgedeckt/unbekannt)
        board = state["board_full"] if is_instructor else state["board_agents"]
        self._grid_words = list(board.keys())

        # Farb-Mapping: Teamfarbe → (Hintergrundfarbe, Textfarbe) für aufgedeckte Kacheln
        color_map = {
            "red":   ("#4a0c0c",  "#b89090"),
            "blue":  ("#091428",  "#7898b8"),
            "white": ("#383535",  "#909090"),
            "black": ("#0d0d10",  GOLD),
            None:    (HIDDEN_CLR, FG_MUTED),   # None = noch nicht aufgedeckt (Agent-Ansicht)
        }

        words  = list(board.keys())
        colors = list(board.values())

        # ── 5×5-Kachelgitter aufbauen ──────────────────────────────────────
        for i in range(5):
            for j in range(5):
                idx          = i * 5 + j
                word         = words[idx]
                col          = colors[idx]            # Teamfarbe oder None (unbekannt)
                bg, fg       = color_map.get(col, color_map[None])
                is_unrevealed = col is None           # Nur für Agenten: Kachel noch nicht aufgedeckt

                # Rahmenfarbe je nach Kachelfarbe für subtile visuelle Trennung
                _border_clr = {
                    "red":   "#6e1414",
                    "blue":  "#112240",
                    "white": "#4a4848",
                    "black": GOLD,
                    None:    "#242e3a",
                }
                tile_border = _border_clr.get(col, "#242e3a")

                # Container in fester Pixelgröße (pack_propagate=False verhindert Schrumpfen)
                cell = tk.Frame(grid_inner, width=tile_w, height=tile_h, bg=bg,
                                highlightbackground=tile_border, highlightthickness=2)
                cell.grid(row=i, column=j, padx=tile_pad, pady=tile_pad)
                cell.pack_propagate(False)

                if is_instructor and word in revealed_set:
                    # Instructor: Aufgedeckte Kachel abgedunkelt mit Häkchen anzeigen
                    dim_bg, dim_fg = DIM_MAP.get(col, (bg, FG_MUTED))
                    tk.Label(
                        cell, text=f"{word}  ✓",
                        font=("Segoe UI", font_sz, "bold"),
                        bg=dim_bg, fg=dim_fg, relief="flat",
                    ).pack(fill=tk.BOTH, expand=True)
                elif can_guess and is_unrevealed:
                    # Aktiver Agent: Noch nicht aufgedeckte Kachel als klickbarer Button
                    tk.Button(
                        cell, text=word,
                        font=("Segoe UI", font_sz, "bold"),
                        bg=HIDDEN_CLR, fg=FG_LIGHT,
                        activebackground="#2a3d52",
                        activeforeground=FG_LIGHT,
                        relief="flat", cursor="hand2",
                        command=lambda w=word: self._tile_clicked(w),
                    ).pack(fill=tk.BOTH, expand=True)
                else:
                    # Inaktiver Spieler oder bereits aufgedeckte Kachel: nur Label (nicht klickbar)
                    tk.Label(
                        cell, text=word,
                        font=("Segoe UI", font_sz, "bold"),
                        bg=bg, fg=fg, relief="flat",
                    ).pack(fill=tk.BOTH, expand=True)

        # ── Hinweisanzeige + „Zug beenden"-Button (nur für Agenten) ───────
        if is_agent:
            self._build_agent_controls(grid_side, state, active_team, can_guess)

        # ── Hinweis-Eingabeformular (nur für Instructor, rechte Spalte) ───
        if is_instructor:
            panel_frame = tk.Frame(content, bg=BG)
            panel_frame.pack(side=tk.LEFT, anchor=tk.N, padx=(40, 0))
            self._build_instructor_panel(panel_frame, is_active_instructor)

    # ── Teilbereich-Builder ───────────────────────────────────────────────────

    def _build_round_over_banner(self, state: dict):
        """Baut das Banner am oberen Rand an, das Rundensieger und Abschlussgrund anzeigt.

        Wird direkt nach der Punkte-Leiste in den Fensterinhalt eingehängt
        und erscheint bei round_over == True.
        Bei game_over == True wird statt „Neue Runde…" der Gesamtsieger angezeigt.
        """
        winner       = state.get("winner", "")
        reason       = state.get("end_reason", "")
        game_over    = state.get("game_over", False)
        game_winner  = state.get("game_winner", "")
        threshold    = state.get("win_threshold", 3)
        team_clr     = self._team_color(winner) if winner else FG_MUTED
        team_name    = "Rot" if winner and winner.lower() == "red" else "Blau"

        # Abschlusstext je nach Gewinnbedingung
        if reason == "assassin":
            detail = "Die schwarze Karte wurde aufgedeckt!"
        else:
            detail = "Alle eigenen Karten gefunden!"

        banner = tk.Frame(self.root, bg=team_clr, pady=10)
        banner.pack(fill=tk.X)
        tk.Label(banner,
                 text=f"Team {team_name} gewinnt die Runde!  —  {detail}",
                 font=("Segoe UI", 15, "bold"),
                 fg=FG_LIGHT, bg=team_clr).pack()

        if game_over:
            # Gesamtspiel ist entschieden
            gw_name = "Rot" if game_winner and game_winner.lower() == "red" else "Blau"
            tk.Label(banner,
                     text=f"🏆  Team {gw_name} gewinnt das Spiel mit {threshold} Rundensiegen!  🏆",
                     font=("Segoe UI", 13, "bold"),
                     fg=GOLD, bg=team_clr).pack()
        else:
            tk.Label(banner,
                     text="Neue Runde startet in 5 Sekunden…",
                     font=("Segoe UI", 11),
                     fg=FG_LIGHT, bg=team_clr).pack()

    def _build_score_bar(self, state: dict, active_team: str):
        """Baut die Punkte-Leiste am oberen Fensterrand auf.

        Zeigt für beide Teams: Teamname, Rundensiege und gefundene/gesamt Karten.
        Das aktive Team wird durch einen Pfeil (▶) und eine hellere Farbe hervorgehoben.
        Das Team, das die aktuelle Runde begonnen hat, wird mit „angefangen" markiert.
        """
        bar = tk.Frame(self.root, bg=BAR_BG, pady=10)
        bar.pack(side=tk.TOP, fill=tk.X)

        starting_team = state.get("starting_team", "")   # Team, das in dieser Runde begann

        for team, clr in (("Red", RED_CLR), ("Blue", BLUE_CLR)):
            is_active  = team.lower() == active_team.lower()  # Ist dieses Team gerade dran?
            is_starter = team == starting_team                 # Hat dieses Team die Runde gestartet?
            name       = "ROT" if team == "Red" else "BLAU"
            wins       = state["red_wins"]   if team == "Red" else state["blue_wins"]    # Rundensiege
            found      = state["red_found"]  if team == "Red" else state["blue_found"]   # Gefundene Karten
            total      = state["red_total"]  if team == "Red" else state["blue_total"]   # Gesamtkarten
            label_fg   = clr if is_active else FG_MUTED     # Aktiv: Teamfarbe, sonst gedämpft
            indicator  = "▶ " if is_active else "   "       # Pfeil bei aktivem Team

            panel = tk.Frame(bar, bg=BAR_BG)
            panel.pack(side=tk.LEFT, expand=True)

            tk.Label(panel, text=f"{indicator}{name}",
                     font=("Segoe UI", 15, "bold"),
                     fg=label_fg, bg=BAR_BG).pack(side=tk.LEFT, padx=(12, 6))
            if is_starter:
                tk.Label(panel, text="angefangen",
                         font=("Segoe UI", 9), fg=clr, bg=BAR_BG).pack(side=tk.LEFT, padx=(0, 6))
            threshold = state.get("win_threshold", 3)
            tk.Label(panel, text=f"Runden: {wins}/{threshold}",
                     font=("Segoe UI", 13),
                     fg=label_fg, bg=BAR_BG).pack(side=tk.LEFT, padx=6)
            tk.Label(panel, text=f"Karten: {found}/{total}",
                     font=("Segoe UI", 13),
                     fg=label_fg, bg=BAR_BG).pack(side=tk.LEFT, padx=6)

    def _build_agent_controls(self, parent, state: dict, active_team: str, can_guess: bool):
        """Baut die Steuerelemente für Agenten unterhalb des Kachelgitters auf.

        Enthält:
        - Hinweisanzeige (Wort und Anzahl) oder „Warte auf Hinweis…"-Meldung
        - „Zug beenden"-Button (nur aktiv, nachdem mindestens eine Kachel geklickt wurde)

        Der Button ist erst aktiv, wenn _tile_clicked_this_turn True ist –
        so wird verhindert, dass der Zug übersprungen wird, ohne eine Kachel gewählt zu haben.
        """
        hint = state["current_hint"]   # (word, count) oder None

        ctrl = tk.Frame(parent, bg=BG)
        ctrl.pack(pady=(12, 0))

        if hint is not None:
            word, count = hint
            tk.Label(ctrl,
                     text=f'Hinweis: "{word}"  ({count})',
                     font=("Segoe UI", 16, "bold"),
                     fg=self._team_color(active_team), bg=BG).pack(side=tk.LEFT, padx=(0, 24))
        else:
            tk.Label(ctrl,
                     text="Warte auf Hinweis…",
                     font=("Segoe UI", 14), fg=FG_MUTED, bg=BG).pack(side=tk.LEFT, padx=(0, 24))

        if can_guess:
            # Neuer Hinweis: Klick-Status für diesen Zug zurücksetzen
            if hint != self._last_seen_hint:
                self._tile_clicked_this_turn = False
                self._last_seen_hint = hint

            can_end  = self._tile_clicked_this_turn   # Mindestens eine Kachel wurde geklickt
            btn_bg   = FG_MUTED if can_end else HIDDEN_CLR
            tk.Button(ctrl, text="Zug beenden",
                      font=("Segoe UI", 12, "bold"),
                      fg=FG_LIGHT, bg=btn_bg,
                      activeforeground=FG_LIGHT, activebackground=FG_MUTED,
                      relief="flat", padx=16, pady=6,
                      cursor="hand2" if can_end else "arrow",
                      state=tk.NORMAL if can_end else tk.DISABLED,
                      command=self._end_turn_clicked).pack(side=tk.LEFT)

    def _build_instructor_panel(self, parent, is_active: bool):
        """Baut das Hinweis-Eingabeformular für den Instructor (Spymaster) auf.

        Enthält:
        - Textfeld für das Hinweiswort (nur Substantive)
        - Zahlenfeld für die Anzahl zugehöriger Karten (nur Ziffern erlaubt)
        - „Hinweis senden"-Button
        - Hinweistext über die Regeln

        Alle Eingabefelder und der Button sind deaktiviert, wenn der Instructor
        gerade nicht an der Reihe ist (is_active == False).
        """
        panel = parent

        tk.Label(panel, text="Hinweis geben",
                 font=("Segoe UI", 18, "bold"),
                 fg=FG_LIGHT, bg=BG).pack(pady=(0, 16))

        # ── Hinweiswort-Eingabe ────────────────────────────────────────────
        tk.Label(panel, text="Hinweis (Substantive):",
                 font=("Segoe UI", 12), fg=FG_LIGHT, bg=BG).pack(anchor=tk.W, pady=(0, 4))
        text_var   = tk.StringVar()
        text_input = tk.Entry(panel, textvariable=text_var,
                              font=("Segoe UI", 12), width=20,
                              bg="#0f1420", fg=FG_LIGHT, insertbackground=FG_LIGHT,
                              state=tk.NORMAL if is_active else tk.DISABLED)
        text_input.pack(anchor=tk.W, pady=(0, 16))

        # ── Anzahl-Eingabe ─────────────────────────────────────────────────
        tk.Label(panel, text="Anzahl:",
                 font=("Segoe UI", 12), fg=FG_LIGHT, bg=BG).pack(anchor=tk.W, pady=(0, 4))
        number_var   = tk.StringVar()
        # validatecommand verhindert, dass Nicht-Ziffern eingetippt werden können
        only_digits  = (self.root.register(lambda P: P == "" or P.isdigit()), "%P")
        number_input = tk.Entry(panel, textvariable=number_var,
                                font=("Segoe UI", 12), width=20,
                                bg="#0f1420", fg=FG_LIGHT, insertbackground=FG_LIGHT,
                                validate="key", validatecommand=only_digits,
                                state=tk.NORMAL if is_active else tk.DISABLED)
        number_input.pack(anchor=tk.W, pady=(0, 16))

        # ── Senden-Button ──────────────────────────────────────────────────
        team_clr = self._team_color(self.color) if self.color else FG_MUTED
        tk.Button(panel, text="Hinweis senden",
                  font=("Segoe UI", 12, "bold"),
                  fg=FG_LIGHT, bg=team_clr if is_active else FG_MUTED,
                  activeforeground=FG_LIGHT, activebackground=team_clr,
                  relief="flat", padx=16, pady=8, cursor="hand2" if is_active else "arrow",
                  state=tk.NORMAL if is_active else tk.DISABLED,
                  command=lambda: self._send_hint(number_var, text_var, number_input, text_input),
                  ).pack(pady=(0, 12))

        # Regelhinweis als kleiner Text unter dem Button
        tk.Label(panel,
                 text="Nur großgeschriebene Substantive.\nKeine Teile der Gitterwörter.",
                 font=("Segoe UI", 9), fg=FG_MUTED, bg=BG, justify=tk.LEFT).pack(anchor=tk.W)

        # Wartebotschaft, wenn dieser Instructor gerade nicht dran ist
        if not is_active:
            tk.Label(panel, text="Warte auf deinen Zug…",
                     font=("Segoe UI", 12), fg=FG_MUTED, bg=BG).pack(pady=(16, 0))

    # ── Startpunkt ────────────────────────────────────────────────────────────

    def run(self):
        """Startet die Tkinter-Ereignisschleife. Blockiert bis das Fenster geschlossen wird."""
        self.root.mainloop()

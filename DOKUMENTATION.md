# Codenames – Dokumentation

Kartenspiel Codenames online für 4 Spieler, auf Python gecoded mit library Tkinter.
Das Spiel läuft via LAN auf einem Rechner als Server und die anderen 3 verbinden sich per TCP und JSON mit dem Server.


## Installation & Start

Es ist nicht benötogt, Pakete zu installieren, es werden nur Standard-Libraries genutzt
(tkinter, socket, threading, json, re, random, itertools, time).

Optional kann HanTa installiert werden, um die Hinweis-Validierung zu verbessern:

pip install HanTa  

### Wie starte ich dieses Programm?

Server starten (1 Spieler):

python main.py server

Clients starten (3 Spieler, kein Argument):

python main.py
Beim Client-Start öffnet sich ein IP-Dialog: Server-IP eintippen oder per Standard-Button die Schul-IP (`10.97.36.101`) setzen, dann Verbinden.

Sobald der dritte Client verbunden ist, startet das Spiel automatisch für alle.

Es ist vorgesehen, dass am Agent-PC auch mehrere Spieler sitzen und zusammen spielen, der Spymaster soll aber alleine sein. 

---

## Spielregeln (Kurzfassung)

5×5-Raster mit 25 Wörtern. Verdeckte Farbverteilung: 8/9 rot, 8/9 blau, 7 weiß (neutral), 1 schwarz (Terrorist). Das beginnende Team hat 9 eigene Karten, das andere 8; der Startvorteil rotiert jede Runde.

Pro Team gibt es einen Spymaster(kennt alle Farben, gibt pro Zug ein Substantiv und eine  Zahl) und einen Agent (deckt Kacheln auf).

- Eigene Karte aufgedeckt → Zug geht weiter
- Gegnerische/neutrale Karte → Zug endet
- Schwarze Karte → Team veliert sofort die Runde
- Alle eigenen Karten gefunden → Runde gewonnen

Nach jeder Runde werden die Rollen neu verteilt (in den dementsprechenden Teams)

Das Team, das zuerst 3 Runden gewinnt, gewinnt das Spiel.

### Hinweis-Validierung

_is_valid_hint() in ui.py lehnt ungültige Hinweise ab. Die wichtigsten Regeln für die Hinweise vom Spymaster sind: 

- Genau ein Wort, nur Buchstaben (inkl. Umlaute/ß), min. 2 Zeichen, plausibler Vokalanteil
- Muss großgeschrieben sein
- Darf kein Wort vom Spielfeld sein – auch nicht als Teilstring oder mit gleichem Wortstamm/Konsonantenskelett (verhindert z. B. "Hundehaus" bei "Hund" auf dem Brett)


## Architektur


main.py:          Entry Point + TCP-Netzwerk (Server- & Client-Logik)
controller.py:    GameController – die gesamte Spiellogik (nur Server)
ui.py:            CodenamesUI (Tkinter) + Hinweis-Validierung
login.py:         assign_role_color() – zufällige Rollenvergabe
words.py:         Wortliste
(test_codenames.py: Testsuite)


Die Spiellogik liegt ausschließlich serverseitig im GameController, also auf dem Server werden die tatsächlichen Rechenoperationen durchgeführt. Clients sind reine UI-Schicht, sie schicken also Aktionen, empfangen State-Updates und rendern nur. 

login.py erzeugt beim Serverstart die vier Rollen-Farb-Kombinationen (Spymaster/Agent × Rot/Blau), mischt sie und verteilt sie zufällig auf den Server und die 3 Clients.


## Netzwerkprotokoll

Das Netzwerk ist ein Client-Server System, das über TCP funktioniert und JSON-Nachrichten als Python Dictionaries versendet und empfängt.

Server -> Client

login{role, color}:         Rolle beim Verbinden wird zugeteilt
game_start{state}:          Alle 4 verbunden, Spiel startet 
state_update{state}:        Zustand hat sich geändert 
role_update{role, color}:   Neue Runde, Rollen gewechselt 

CLient -> Server

submit_hint{word, count}:   Spymaster schickt Hinweis an seinen verbündteten Agenten
reveal_tile{word}:          Agent deckt karte auf
end_turn{}:                 Agent beendet den Zug

## KI Nutzung
Die Scripts wurden alle mithilfe von KI (Claude Code Opus 4.8 High) erstellt, da wir beide noch relativ wenig Erfahrung hatten mit TCP und JSON. Dazu war die UI auch sehr aufwendig (fast 1000 Zeilen). Dafür konnten wir besser uns auf das Spiel an sich und die Prozesse beim Entwickeln von anspruchsvollerer Software konzentrieren, wie z. B. Server-Client mit TCP und JSON, saubere Software-Architektur und Implementierung von Git. 





# Codenames — Projekt

Dieses Repository enthält ein Softwareprojekt für den Informatikunterricht, das das Gesellschaftsspiel „Codenames" als Netzwerk‑Multiplayer‑Anwendung umsetzt.

Kurzbeschreibung
- Implementierung des Spiels Codenames als Mehrspieler‑Spiel.
- Spielbar von mehreren Computern aus: Spieler verbinden sich über das Netzwerk (z. B. Web‑Clients oder dedizierte Clients).
- Unterstützt mindestens 4 Spieler (zwei Teams), optional mehr.

Ziel und Anforderungen
- Unterrichtsprojekt / Demonstrationsprojekt für Informatik.
- Multiplayer‑fähig: Spielrunden mit mehreren Teilnehmenden, mindestens 4 Spieler.
- Rollen: Spymaster und Feldagenten (wie im Originalspiel).
- Lobby / Spielraumverwaltung: Räume erstellen, beitreten, Sitzungsverwaltung.
- Echtzeit‑Kommunikation: z. B. über WebSockets (Spielzustand, Chat).
- Spielzustand verwalten: Karten, Teams, Punkte, Rundenverlauf, Siegbedingungen.

Technischer Überblick (Beispiel‑Stack)
- Backend: Node.js (Express/Fastify), Python (FastAPI) oder Go
- Echtzeit: WebSockets (z. B. socket.io, ws) oder WebRTC
- Frontend: Web‑Client (React, Vue) oder einfache HTML/JS Oberfläche
- Datenhaltung: In‑Memory für laufende Runden; optionale DB (SQLite/Postgres) für Persistenz
- Deployment: lokal, Server oder Docker

Schnelleinrichtung (Beispiel)
1. Repository klonen:
   git clone https://github.com/Sushibear378/codenames.git
2. Ins Verzeichnis wechseln und Abhängigkeiten installieren (Beispiel Node.js):
   cd codenames
   npm install
3. Server starten (Beispiel):
   npm run start
4. Web‑Client öffnen und Raum erstellen oder beitreten (auf mehreren Geräten/Browsern testen).

Spielablauf (Kurz)
- Zwei Teams treten gegeneinander an. Jedes Team hat einen Spymaster und mindestens einen Feldagenten.
- Der Spymaster gibt Hinweise (ein Wort + Zahl), damit die Teammitglieder Karten auf dem Feld erraten.
- Ziel ist es, alle eigenen Agentenkarten zu identifizieren, ohne die gegnerischen oder die Todeskarte zu treffen.
- Spielregeln orientieren sich am Originalspiel, können aber für das Projekt angepasst werden.

Mitwirken
- Issues anlegen für Funktionen, Bugs oder Verbesserungsvorschläge.
- Pull Requests mit aussagekräftigen Beschreibungen sind willkommen.

Lizenz
- Keine Lizenz angegeben. Wenn eine Lizenz gewünscht ist, bitte eine LICENSE‑Datei (z. B. MIT) hinzufügen.

Kontakt
- Repository: https://github.com/Sushibear378/codenames
- Bei Fragen: Issue erstellen oder Pull Request kommentieren.

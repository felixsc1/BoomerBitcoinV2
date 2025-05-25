# Boomer Bitcoin

Ziel dieses Projekts ist es, die einfachst mögliche Lösung zu bieten, wie jemand ohne jegliches Vorwissen seine Bitcoin-Gewinne verfolgen kann. 

## Funktionsweise für Nutzer

Käufe können unter "MeineBitcoin" eingetragen werden.
Die Seite "Gewinn" zeigt dann den Gewinn/Verlust inkl. Grafiken. Ebenfalls zeigt es den Gewinn/Verlust wenn die selben Käufe (Betrag und Zeitpunkt) stattdessen in den S&P 500 investiert worden wären.


## Hintergrund für Administratoren
Die Käufe werden auf MongoDB gespeichert. (Initial muss ein cluster erstellt werden, und die Verbindungsdaten in eine streamlit/secrets.toml Datei eingefügt werden. mongodb liefert die Anleitung dazu.)
Für die Bitcoin-Preise wird die CoinGecko API verwendet.
Für die S&P 500-Preise wird die Yahoo Finance API verwendet.

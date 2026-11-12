# Odstępstwa od zasady „standard ponad własne”

| Co | Dlaczego gotowiec nie wystarcza | Warunek powrotu |
|---|---|---|
| Headless runner (`tools/runner/`) zamiast emulatora z oknem | oficjalny emulator nie ma trybu bez okna, skryptu pada ani zapisu klatek i dźwięku; testy muszą działać autonomicznie i w CI | oficjalny emulator dostanie tryb headless ze skryptem wejścia |
| Tracker muzyki w `src/sound.h` | konsola gra tylko próbki; gotowe utwory jako nagrania zajęłyby setki MB | — |
| Punkt wejścia emulatora webowego (`tools/web/main.cpp`) zamiast `Main.cpp`, `GUI.cpp`, `Settings.cpp` z WebEmulatora | WebEmulator (commit 9714fe4) się nie buduje: dołącza usunięte Dear ImGui i glad, pętla `while` zamraża kartę przeglądarki, kartridż tylko z linii poleceń; nie ma pada ani karty pamięci w przeglądarce. Wideo, dźwięk i klawiatura z WebEmulatora zostają bez zmian (plus łatka literówki w `VideoOutput.cpp`), konsola to ta sama `ConsoleLogic`, co w testach | WebEmulator zbuduje się z Emscriptenem i dostanie pad oraz kartę pamięci |

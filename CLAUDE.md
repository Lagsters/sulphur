# Sulphur — gra na Vircon32 (C)

Fork BlasTIC (TIC-80) na konsolę Vircon32: Bitwa dla czterech graczy i Opowieść „Legenda o siarce”
(Dratewka, siarka, owca i smok wawelski). Grafika z Blendera w stylu Amigi, muzyka z syntezy.
Plan całości: `PLAN.md`; kto za co odpowiada i jakie są API: `docs/CONTRACTS.md`; fabuła: `docs/STORY.md`.

## Zasady nadrzędne

Rozstrzygają każdy spór, w tej kolejności.

1. **Prostota.** Płaskie funkcje, bez abstrakcji na zapas. Działająca rozgrywka ważniejsza niż efekty.
2. **Standard ponad własne.** Biblioteka standardowa Vircon32 (`video.h`, `audio.h`, `input.h`…),
   oficjalne narzędzia i emulator tak, jak są. Własne rozwiązanie tylko z wpisem w `DEVIATIONS.md`
   (co, dlaczego gotowiec nie wystarcza, warunek powrotu).
3. **Kod tłumaczy się sam.** Nazwy mówią prawdę, domyślnie bez komentarza; zostaje zdanie, które
   zmieni decyzję kogoś zmieniającego kod. Komentarz opisuje stan, nie historię.
4. **Grę pisze i testuje Claude, autonomicznie.** Szczegóły niżej.

## Autonomia i weryfikacja

- Bramka „gotowe”: `python tools/check.py` (kod wyjścia 0): build gry i testów, testy logiki na
  prawdziwym kodzie konsoli (runner headless), krótka symulacja botów, wydajność bez spóźnionych
  klatek. `--sim` dokłada długą symulację. Kodu wyjścia nie maskuj potokiem.
- Zmiana funkcji nie jest skończona bez testu w `tests/`, który ją pokrywa. Błąd: najpierw test,
  który go odtwarza (czerwony), potem poprawka.
- Ocena mierzalna: symulacje (wygrane, remisy, długość rund, przejścia etapów), liczniki cykli,
  metryki dźwięku. Obraz oceniasz na klatkach z runnera (`tools/frames.py`), nie na wyobrażeniu.
- Granice: zabawę, sterowanie i brzmienie ocenia człowiek.

## Dialekt Vircon32 C (pułapki)

- Tablice: `int[ N ] nazwa;`, wskaźniki do tablic `int*[ N ]`; struktury bez słowa `struct` przy użyciu.
- Brak `?:` — jest `pick(warunek, a, b)` w `src/state.h` (liczy obie wartości).
- Własny nagłówek nie może nazywać się jak systemowy (`input.h`, `audio.h`, `time.h`…): zasłoni go.
- Zagnieżdżone przeszukiwania potrzebują osobnych tablic (`escape_dir` ma swoje): wspólne psują
  zewnętrzną kolejkę i pętla się nie kończy.
- 250 000 cykli na klatkę; boty planują w budżecie (`BOT_THINK_CYCLES`), rysowanie bez skalowania.

## Narzędzia

| Polecenie | Opis |
|---|---|
| `python tools/check.py` | bramka |
| `python tools/build.py [program.c nazwa]` | ROM `build/<nazwa>.v32` |
| `python tools/toolchain.py` | ścieżki DevTools, BIOS-u i runnera (pobiera i buduje brakujące) |
| `python tools/frames.py <katalog> [--sheet plik.png]` | klatki z runnera do PNG |
| `python tools/strings.py` | teksty interfejsu EN/PL → `src/gen/strings.h` |
| `python tools/art/game/make.py`, `tools/art/story/make.py`, `tools/scenes/make.py` | grafika (Blender) |
| `python tools/font/make.py` | czcionki |
| `python tools/audio/make.py` | muzyka i efekty z modułu `assets/music/songs/sulphur.xm` (źródło prawdy, edytowalne w OpenMPT); `--compose` generuje moduł od nowa i **nadpisuje ręczne zmiany w trackerze** |
| `python tools/web/build.py` | wersja webowa → `build/web/` |

Windows: kompilator runnera to WinLibs (`winget install BrechtSanders.WinLibs.POSIX.UCRT`).
Blender 5.2 tylko do grafiki; CI jej nie renderuje (atlasy są w repo).

## Proces

- Praca na gałęziach, PR, scalanie tylko przez squash (gałąź znika po scaleniu).
- Commit: `<typ>(<zakres>): <temat>` po polsku.
- Push, merge i zmiany ustawień repo tylko za zgodą właściciela.

### Gdzie zapisujemy wiedzę

| Miejsce | Co |
|---|---|
| komentarz w kodzie | dlaczego kod jest taki (stan obecny) |
| `DEVIATIONS.md` | własne rozwiązanie zamiast gotowca |
| `HISTORY.md` | FAKT / DECYZJA / ŚLEPA ULICZKA |
| `TODO.md` | stan prac i następny krok |
| `docs/` | kontrakty, fabuła |

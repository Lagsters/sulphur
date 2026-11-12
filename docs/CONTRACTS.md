# Kontrakty między częściami gry

Grę robi kilka osób (agentów) naraz. Każda część ma właściciela, swoje pliki i API, którego
pozostali używają. Nie zmieniasz cudzych plików: brakującą rzecz zgłaszasz właścicielowi.

## Właściciele plików

| Część | Pliki | Właściciel |
|---|---|---|
| Silnik, kampania, boty, UI, renderer areny | `src/*.h` poza wymienionymi niżej, `src/main.c`, `tools/build.py`, `tools/toolchain.py`, `tools/assetlib.py`, `tools/catalog.py`, `tools/strings.py` | główny |
| Grafika rozgrywki | `tools/art/game/`, `assets/game/`, `src/gen/game.h` | art-game |
| Bossowie, tytuł, mapa | `tools/art/story/`, `assets/story/`, `src/gen/story.h` | art-story |
| Scenki fabularne | `tools/scenes/`, `assets/scenes/`, `src/gen/scenes.h`, `src/scenes.h` | scenes |
| Czcionka i rysowanie tekstu | `tools/font/`, `assets/font/`, `src/gen/font.h`, `src/text.h` | font |
| Muzyka i efekty | `tools/audio/`, `assets/music/`, `assets/sfx/`, `src/gen/music.h`, `src/gen/sfx.h`, `src/sound.h` | audio |
| Testy, bramka, CI | `tests/`, `tools/check.py`, `.github/workflows/build.yml` | tests |
| Wersja webowa | `web/`, `tools/web/`, `.github/workflows/pages.yml` | web |

Nikt poza głównym nie robi commitów, nie pushuje i nie zmienia gałęzi.

## Zasoby (tools/assetlib.py)

- Grupa zasobów = `assets/<grupa>/rom.txt` + `src/gen/<grupa>.h`, pisane przez
  `assetlib.pack_group(grupa, sprite'y, dźwięki)`. Kolejność grup w ROM-ie jest stała
  (`assetlib.GROUPS`); identyfikatory w C liczą się od `TEX_BASE_<GRUPA>` / `SND_BASE_<GRUPA>`
  z `src/gen/rom.h`, więc grupy nie przenumerowują się nawzajem.
- Sprite `NAZWA` grupy `g`: w C `G_NAZWA` (indeks), `G_NAZWA_N` (klatki), `_W`, `_H`;
  `g_tex[G_NAZWA]` to tekstura, `g_reg[G_NAZWA] + klatka` to region. `define_g_regions()`
  definiuje regiony raz, na starcie.
- Hotspot: kafle i ikony lewy górny róg; postacie między stopami (`w/2`, `h-1`); efekty środek.
- Lista sprite'ów grup `game` i `story` jest w `tools/catalog.py`. Grafika musi dać dokładnie
  te nazwy, liczby klatek i rozmiary (zastępcza: `tools/placeholder_art.py`).
- Wygląd Amigi: `assetlib.amiga(obraz)` — kolory 12-bitowe z ditheringiem Bayera, alfa 0/255.
- Tekstura ma najwyżej 1024×1024; ROM trzyma tekstury w ich własnym rozmiarze. Budżet ROM-u:
  do 40 MB razem (gra idzie też do przeglądarki).
- Tekst w C to tablice int; polskie litery mają kody 128..145 (`assetlib.POLISH`,
  `assetlib.c_string`).

## API w C (nazwy zostają, implementację zmienia właściciel)

- `src/text.h`: `text_init()`, `text_width(s)`, `text_draw(x,y,s,kolor)`,
  `text_draw_n(x,y,s,n,kolor)`, `text_draw_centered(cx,y,s,kolor)`,
  `text_draw_big(cx,y,s,kolor,skala)`, `text_number(x,y,v,kolor)`, `TEXT_H_PX`.
- `src/sound.h`: `sound_init()`, `music_play(SONG_*)`, `music_stop()`, `sound_frame()` (co
  klatkę: efekty z `events[]` w `state.h` i muzyka), `ui_sound(UI_*)`.
- `src/scenes.h`: `scene_start(SCENE_*)`, `scene_frame()` → `true` po końcu scenki.
- Język: globalne `lang` (0 angielski, 1 polski) w `src/state.h`.
- Pady: A — bomba / dalej, B — owca / wstecz, Start — pauza / pominięcie scenki.

## Budowanie i uruchamianie

- `python tools/build.py [program.c nazwa]` → `build/<nazwa>.v32`. Używaj własnej nazwy, gdy
  budujesz warianty testowe, żeby nie nadpisać cudzego builda.
- Runner (`python tools/toolchain.py` podaje ścieżki): `runner bios.v32 rom.v32 katalog klatek
  co_ile` + zmienne `INPUT_SCRIPT`, `GAMEPADS`, `AUDIO_OUT`, `MEMCARD`, `SKIPLOG`, `FRAME_FROM`,
  `FRAME_TO` (opis w `tools/runner/runner.cpp`). BIOS pokazuje logo przez ok. 250 klatek.
- `python tools/frames.py katalog [--sheet plik.png]` zamienia klatki PPM na PNG.
- Dialekt Vircon32 C: tablice `int[ N ] nazwa;`, struktury bez słowa `struct` przy użyciu,
  brak `?:` (jest `pick(warunek,a,b)` w `state.h`), brak `static`, łańcuchy to `int*`.
- Procesor: 250 000 cykli na klatkę (`get_cycle_counter()`); rysowanie ma być tanie:
  `select_texture` / `select_region` / `draw_region_at`, bez skalowania tam, gdzie się da.

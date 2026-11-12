# Sulphur — plan całości

Kompletny fork BlasTIC (TIC-80) na konsolę Vircon32: ta sama gra (Bitwa dla czterech graczy
i Opowieść), ale z grafiką renderowaną w Blenderze w stylu Amigi i z muzyką z bogatych,
syntezowanych próbek. Opowieść skrócona: szewc Dratewka, bomby z siarki i smok wawelski,
którego da się pokonać tylko owcą naszpikowaną siarką.

## Co już wiemy (sprawdzone)

- Narzędzia Vircon32 26.11.05 (kompilator C, asembler, packrom, png2vircon, wav2vircon) działają
  na tej maszynie; przebudowany Rockfield jest bajt w bajt równy oryginałowi.
- Headless runner (Rockfield, MIT) zbudowany na oficjalnym kodzie konsoli: uruchamia ROM bez
  okna, przyjmuje skrypt wejścia, zapisuje klatki (PPM), dźwięk (16 bit, 44,1 kHz) i kartę
  pamięci, zgłasza klatki, których program nie zdążył policzyć.
- Blender 5.2 renderuje z linii poleceń (`blender -b -P skrypt.py`, EEVEE), bez dodatku MCP.
- Sprzęt: ekran 640×360 przy 60 kl./s, CPU 15 MHz (250 000 cykli na klatkę), 256 tekstur
  1024×1024, 16 kanałów dźwięku 44,1 kHz, 16 MB RAM, karta pamięci 1 MB, 4 pady.
- Core libretro Vircon32 (BSD-3) jest na buildbocie dla wszystkich ABI Androida.
- Organizacja Lagsters ma plan darmowy: GitHub Pages wymaga publicznego repo.

## Gra

### Bitwa (bez zmian w zasadach)

Arena 30×16, czterech graczy (P1, P2 ludzie; P3, P4 boty), bomby z siarki, łańcuchy wybuchów,
bonusy (+bomba, +zasięg, osłona), zamykająca się arena, mecz do 3 wygranych. Boty z BlasTIC
(BFS, mapa zagrożeń, planista ucieczki z czasem, pułapki) przeniesione 1:1.

### Opowieść (skrócona)

Trzy rozdziały po 10 etapów, co piąty etap to boss:

1. **Wrocław** — smok porywa owce, król Krak ogłasza nagrodę. Dratewka próbuje z siarką
   (wybuch w warsztacie). Boss: utopiec.
2. **Ślęża** — Baba Jaga i czarownice; dołącza królewna Wanda (P2 albo bot). Boss: Baba Jaga.
3. **Kraków** — smok. Boss końcowy: smok wawelski.

Bez Twardowskiego i bez diabła. Każda scenka ma 3–5 ujęć i pokazuje jedno: kto jest wrogiem
i po co idziemy dalej. Zakończenie: smok pęka, nagroda u Kraka, fajerwerki.

### Siarka i owca

- Podstawowa broń to **bomba z siarki** (zasady jak w BlasTIC).
- **Owca** pojawia się dopiero w późnych etapach (rozdział 3). Biega po arenie: ucieka przed
  bohaterem i przed ogniem, jest szybsza od niego, więc trzeba ją osaczyć.
- Złapana owca to **dodatkowa „bomba”** w ekwipunku (osobny licznik w HUD).
- Wypuszczona owca z zapalonym lontem biegnie do smoka, a smok ją zjada i pęka od środka.
- **Smoka rani tylko owca**: zwykła siarka go nie bierze. Gdy na arenie brakuje owiec, pojawia
  się nowa, żeby walki nie dało się zablokować.

## Grafika (styl Amigi, z Blendera)

- Kafel 20×20, cała arena widoczna, HUD u góry; plansze kampanii przewijane w jednej osi.
- Wszystko modelowane w Blenderze skryptami (`tools/art/*.py`, `blender -b`): kafle (bruk,
  mury, skrzynie), postacie w rzucie 3/4 (4 kierunki, chód w 8 klatkach), owca, potwory,
  bossowie, smok, efekty wybuchu i ognia, tła scenek i ekranu tytułowego.
- Po renderze kwantyzacja do 12-bitowych kolorów Amigi (4096) z ditheringiem i ograniczoną
  paletą na scenę: głębia i gradienty nieba jak w grach z Amigi, bez płaskich kolorów.
- Czcionka bitmapowa z polskimi literami (font na licencji OFL), gra w języku EN i PL.

## Muzyka i dźwięk

- Tracker w C na 16 kanałach, jak moduł z Amigi: instrumenty to próbki 44,1 kHz renderowane
  offline w Pythonie (numpy): przesterowana gitara rytmiczna i prowadząca, czysta gitara,
  bas, pady z chorusem, perkusja z przestrzenią; pogłos wbudowany w próbki, echo nutami.
- Utwory: tytuł, trzy rozdziały, walka z bossem, smok, nastroje scenek (spokój, groza,
  radość) i zakończenie.
- Ocena bez słuchu, mierzalnie: głośność (LUFS), energia pasm (bas 60–250 Hz), szerokość
  stereo, brak przesterowania cyfrowego, płynne pętle. Do odsłuchu dla człowieka: WAV i MP4.

## Testy (autonomiczne; kod wyjścia to wynik)

- `python check.py` — bramka „gotowe”:
  - build ROM z czystego stanu,
  - testy logiki: osobny ROM testowy z tego samego kodu, uruchamiany headless; wyniki zapisuje
    na karcie pamięci, którą czyta Python,
  - symulacja botów z niezmiennikami (gracz w ścianie, bomba na bloku, licznik bomb),
  - kampania grana przez boty: każdy etap da się przejść, smok ginie tylko od owcy,
  - wydajność: zero spóźnionych klatek w Bitwie z czterema botami i w walce ze smokiem.
- Zrzuty klatek z kluczowych momentów: oglądam je sam, zanim cokolwiek nazwę gotowym.
- CI (GitHub Actions, Ubuntu): ta sama bramka na narzędziach Vircon32 dla Linuksa.

## Publikacja

- GitHub Pages: gra w przeglądarce w emulatorze webowym Vircon32 (BSD-3, budowany
  Emscriptenem). Emulator webowy obsługuje tylko klawiaturę.
- Release z plikiem `sulphur.v32` i jego SHA-256 (CI, tag `v*`).
- Praca na gałęziach i PR, scalanie przez squash.

## Kolejność prac

0. Fundament repo: `CLAUDE.md`, `README.md`, licencja MIT, `check.py`, CI, przypięte wersje
   narzędzi.
1. Silnik w C: arena, ruch, bomby, łańcuchy, bonusy, boty, zamykanie areny, Bitwa; testy
   i symulacja.
2. Kampania: etapy, potwory, bossowie, smok i owca, zapis na karcie pamięci.
3. Grafika z Blendera: kafle, postacie, potwory, bossowie, owca, efekty, HUD, czcionka, tytuł.
4. Muzyka i efekty dźwiękowe.
5. Scenki fabularne.
6. Wersja webowa, Pages, release.
7. Audyt i raport końcowy: zrzuty, filmy z dźwiękiem, wyniki bramki.

## Granice autonomii

- Zabawę, sterowanie i brzmienie ocenia tylko człowiek; ja oceniam mierzalnie i na zrzutach.
- ROM-y i BIOS-y cudzych gier nigdy nie trafiają do repo; wszystkie zasoby powstają w repo.

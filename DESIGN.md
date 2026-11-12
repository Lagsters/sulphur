# Sulphur — specyfikacja

Fork BlasTIC (TIC-80) przeniesiony na Vircon32. Legenda o Dratewce i smoku, siarka jako bomby,
owca jako broń na smoka. Grafika renderowana w Blenderze, muzyka syntezowana w kodzie.

## Platforma

- Vircon32 (C, 640×360, 16 kanałów dźwięku, 16 MB RAM).
- Testy i zrzuty przez headless runner (`tools/headless` z projektu Rockfield na oficjalnym kodzie konsoli).

## Historia (skrócona)

- Dratewka, szewc z Wrocławia, z bombami z siarki, idzie zabić smoka krakowskiego.
- Bez Twardowskiego.
- Sceny krótkie, każda pokazuje jeden cel: kto jest wrogiem, po co idziemy dalej.

## Mechaniki

- **Siarka** to podstawowa bomba Dratewki (zamiast „blast” z BlasTIC).
- **Owca** naszpikowana siarką: nie jest bronią od początku. Najpierw trzeba ją zdobyć, a dopiero potem używać przeciw smokowi.
- Owca **biega** (AI ucieka przed zagrożeniem i szuka drogi).
- **Dodatkowa bomba** z owcy: owca da się zebrać jak bonus „+1 bomba”, ale tylko na późnych etapach gry.
- Smok: boss z atakiem ogniem w rzędzie/kolumnie, ostrzeżenie na sekundę wcześniej (jak w obecnym BlasTIC).

## Muzyka i dźwięk

- Synteza w kodzie na 16 kanałach Vircon32 (SPU).
- Styl: tracker w duchu Amigi, bas, bębny, gitara jako syntetyczny lead.
- Bez zewnętrznych sampli, więc nie ma problemu z licencją.

## Grafika

- Modele 3D w Blenderze, renderowane do sprite'ów 2D.
- Paleta klimatyczna, cienie i oświetlenie zamiast płaskiego pixel-art z BlasTIC.

## Testy (autonomiczne)

- Logika gry: testy jednostkowe w C (lub skrypty testowe w Pythonie na wyjściu runnera).
- Przebiegi: headless runner z `INPUT_SCRIPT` (wejście) i `AUDIO_OUT` (dźwięk).
- Kryteria mierzalne: zrzut klatki w wybranym momencie, liczba niezerowych próbek, peak audio, brak zawieszenia.

## Publikacja

- Repo: `Lagsters/sulphur` (do utworzenia po zgodzie).
- Strona: GitHub Pages z osadzonym WebEmulatorem Vircon32 (BSD-3), bez gamepada i zapisów (ograniczenia WebEmulatora).
- Push i tworzenie repo: osobna zgoda za każdym razem.

## Status

- [x] Repo lokalne, `git init`.
- [ ] Narzędzia: kompilator C Vircon32 (DevelopmentTools), szablon projektu.
- [ ] Minimalny build „hello” + test runnera.
- [ ] Blender: pierwszy render sprite'a owcy.
- [ ] Synteza: pierwszy utwór.
- [ ] Mechaniki i sceny.
- [ ] Repo zdalne i Pages (po zgodzie).

# Stan prac

## Sesja 2026-11-12 (gałąź `gra`, pierwsza wersja całej gry)

- Zrobione: silnik (port BlasTIC), Bitwa z botami, Opowieść w trzech rozdziałach (30 etapów,
  utopiec, Baba Jaga, smok i owce), menu, mapa świata, HUD, pauza, zapis na karcie, EN/PL,
  grafika z Blendera (rozgrywka, bossowie, tytuł, mapy, scenki), czcionki OFL, muzyka z modułu
  XM i efekty z syntezy, wersja webowa (60 kl./s), testy i bramka (`tools/check.py`), CI.
- Pomiary: 88/88 testów logiki; 400 rund Bitwy bez przewagi rogów (p = 0,68), remisy 12,5%;
  0 klatek ponad budżet (najgorsza 94% przy smoku); boty-bohaterowie przechodzą 11/30 etapów
  w symulacji (to miara sprytu botów, nie dowód, że reszta jest nie do przejścia).
- Do oceny przez człowieka: zabawa i trudność etapów, sterowanie, brzmienie muzyki i efektów
  (podglądy w `build/audio/preview/` po `python tools/audio/make.py`), czy owce dają się łapać.
- Znane słabości: postacie scenek wyglądają jak proste kukiełki 3D; owca od przodu to głównie
  biała kula; remisy w Bitwie wzrosły po ostrożniejszych ucieczkach botów.
- NASTĘPNY KROK: zagranie przez człowieka; strojenie trudności etapów po jego uwagach.

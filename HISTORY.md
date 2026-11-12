# Historia ustaleń

Format wpisu: **FAKT** / **DECYZJA** / **ŚLEPA ULICZKA**, data, jedno–dwa zdania.

- **DECYZJA** 2026-11-12: fork BlasTIC na Vircon32 (TIC-80 dawał płytki dźwięk i płaską grafikę);
  repo `Lagsters/sulphur`, MIT, scalanie tylko przez squash.
- **DECYZJA** 2026-11-12: fabuła skrócona do trzech rozdziałów (Wrocław, Ślęża, Kraków), bez
  Twardowskiego i diabła; smoka rani tylko wypuszczona owca, owce tylko w rozdziale 3.
- **FAKT** 2026-11-12: dialekt Vircon32 C nie ma `?:`, tablice to `int[ N ] nazwa`, a własny
  `input.h` zasłonił systemowy. Pomocnik `pick()` liczy obie wartości.
- **FAKT** 2026-11-12: zagnieżdżone przeszukiwania na wspólnych tablicach kolejki zapętlały grę
  (escape_dir w testach celu path_dir); escape ma własne tablice.
- **FAKT** 2026-11-12: przeszukanie całej planszy z wywołaniem funkcji na każde pole i listą bomb
  kosztowało ~170 tys. cykli z 250 tys. na klatkę; liczniki bomb na polach i kroki przez indeks
  zmieściły je w budżecie (owca z lontem stała w miejscu przy budżecie 105 tys.).
- **FAKT** 2026-11-12: rysowanie przez `select_texture` + `select_region` + `draw_region_at`
  osobno kosztowało ~150 tys. cykli na ~650 kafli; jedno wywołanie z wstawką asm (`put_sprite`)
  zeszło do 56–86 tys. na klatkę.
- **FAKT** 2026-11-12: dwa boty w środkowym pasie 4×2 krążyły bez końca; po zatrzymaniu strefy
  kładą bomby bez drogi ucieczki (600 klatek), a po 2400 runda kończy się remisem.
- **DECYZJA** 2026-11-12: modele ML do muzyki odrzucone (właściciel, wcześniej MusicGen); utwory
  jako moduł XM z syntezowanymi instrumentami, odtwarzane trackerem w `src/sound.h`.
- **ŚLEPA ULICZKA** 2026-11-12: lokalne modele (ACE-Step, TripoSG) nie były pobrane, a na C: było
  ~4–5 GB wolnego miejsca; PyTorch i modele się nie zmieszczą.
- **FAKT** 2026-11-12: kilka procesów Blendera naraz psuło kompilator shaderów EEVEE; renderuj w
  jednym procesie.
- **FAKT** 2026-11-12: WebEmulator (9714fe4) nie buduje się z Emscriptenem bez własnego punktu
  wejścia (`tools/web/main.cpp`, `DEVIATIONS.md`); w przeglądarce 60 kl./s.

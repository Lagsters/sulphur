# Legenda o siarce — skrócona fabuła

Szewc Dratewka z Wrocławia, bomby z siarki i smok wawelski. Bez Twardowskiego i bez diabła.
Każda scenka ma 3–6 ujęć po 3–6 s i pokazuje jedną rzecz jasno: kto jest wrogiem i po co idziemy dalej.
Linie dialogu w obu językach (EN / PL), krótkie, pisane na ekranie jak na maszynie.

## Scenka 1: Wrocław (przed rozdziałem I)

1. Noc nad Wawelem. Smok przelatuje nad zamkiem i porywa owcę z pastwiska. Podpis: KRAKÓW.
2. Rynek we Wrocławiu, ranek. Herold przybija plakat: smok, „NAGRODA: PÓŁ KRÓLESTWA” (zbliżenie).
3. Dratewka czyta plakat; nad głową błyska pomysł.
4. Warsztat szewca: Dratewka szyje owczą skórę i sypie siarkę. BUM. Okopcona twarz:
   „...następnym razem mniej siarki.” / “...less sulphur next time.”
5. Z Odry wynurza się utopiec: „Nikt nie przejdzie przez Odrę!” / “No one crosses the Oder!”
6. Karta rozdziału I: WROCŁAW.

## Scenka 2: Ślęża (przed rozdziałem II)

1. Droga na południe, Ślęża w nocy, ognisko Kupały. Podpis: ŚLĘŻA.
2. Baba Jaga w moździerzu i czarownice krążą wokół królewny Wandy, zielone czary ją wiążą.
3. Dratewka rzuca bombę z siarki; czarownice się rozpierzchają, Jaga ucieka:
   „Smok o was usłyszy!” / “The dragon will hear of you!”
4. Wanda: „Dałabym sobie radę.” / “I had them.” — i idzie z Dratewką (od teraz P2 albo bot).
5. Karta rozdziału II: ŚLĘŻA.

## Scenka 3: Kraków (przed rozdziałem III)

1. Kraków o zmierzchu, hejnał z Mariackiej, smok nad miastem. Podpis: KRAKÓW.
2. Przed jamą smoka: bomby z siarki odbijają się od łusek. Wanda: „Siarka go nie bierze!” /
   “Sulphur won't hurt it!”
3. Dratewka patrzy na pasące się owce: „Ale owca z siarką — tak.” / “But a sheep full of it will.”
   (Tu gracz rozumie mechanikę: łapiesz owcę, B wypuszcza ją do smoka.)
4. Karta rozdziału III: KRAKÓW.

## Scenka 4: Zakończenie (po smoku)

1. Smok połyka owcę, pali go w środku, pije z Wisły, puchnie... BUM.
2. Sala Kraka. Krak: „Twoja nagroda!” / “Your reward!” Wanda: „Pół królestwa, ojcze.” /
   “Half the kingdom, father.” Krak: „Pół sera?” / “Half the cheese?”
3. Fajerwerki nad Wawelem. KONIEC / THE END.

## Rozdziały i etapy (src/campaign.h)

- I Wrocław (etapy 1–10): krasnale; boss: utopiec (etap 5 słabszy, etap 10).
- II Ślęża (11–20): krasnale, nietoperze; dołącza Wanda; bossowie: utopiec (15), Baba Jaga (20).
- III Kraków (21–30): krasnale, nietoperze, kościotrupy z bombami; owce na każdym etapie;
  bossowie: Baba Jaga (25), smok (30). Smoka rani tylko wypuszczona owca.

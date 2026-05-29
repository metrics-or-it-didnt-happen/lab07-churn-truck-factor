# Odp, zadanie 1 - Ollama

1. Najczesciej zmieniajace sie pliki w projekcie ollama:
   - README.md (545 zmian)
   - server/routes.go (440 zmian)
   - cmd/cmd.go (333 zmian)
   - server/images.go (291 zmian)
   - llm/server.go (200 zmian)

2. Nie. Pliki z najwiekszym churnem to u nich glowne zaleznosci, wylgenerowany kod albo zbiory testowe:
   - model/testdata/llama3.2/vocab.bpe
   - model/testdata/llama3.2/encoder.json
   - integration/testdata/shakespeare.txt
   Tego typu pliki dodaje sie raz, maja ogromnie duzo linii, ale na codzien sie ich nie zmienia. Z kolei pliki z top 5 z poprzedniego punktu (jak README.md) sa edytowane barodz czesto, ale o pojedyncze linijki.
   Samotnych wysp jest bardzo duzo i 2575 z 4422 plików (58.2%) ma tylko jednego autora

3. Plik `README.md`, czyli ten zmieniajacy sie najczesciej, byl dotykany przez 313 unikalnych autorow.

# Wnioski o truck factor

Truck factor dla calego projektu wynosi 2. Czyli dwoch developerow (Jeffrey Morgan i Daniel Hiltgen) jest "wlascicielami" ponad polowy wszystkich plikow w repozytorium (odpowiednio 1178 i 1113 plikow). 
Jest to ryzyko, bo jak oni zrezygnuja z projektu, to wiekszosc bazy kodu straci swoje glowne osoby decyzyjne, ktore znaja ten kod najlepiej.
Ponad 58 procent plikow ma tutaj zreszta zaledwie jednego autora. W tak duzym projekcie open source, nie kazda z tysiecy osob nad nim czynnie pracuje, tylko prawdopodobnie wiele ludzi z zewnatrz dopisuje sie do kodu z z malym fixem czy dodaje jakis plik testowy i potem juz go nikt z nich nie zmienia.

Jest to niby lepsze niz Truck Factor = 1, o ktorym wspominamy w FAQ, ale wciaz stanowi znaczne ryzyko

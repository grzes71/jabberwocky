---
description: Stage, commit with descriptive message, and push changes to remote repository
---

Wykonaj procedurę zatwierdzenia i wysłania zmian do zdalnego repozytorium:

1. Sprawdź zmodyfikowane pliki za pomocą `git status` oraz odczytaj najnowszy wpis z pliku `HISTORY.md`, aby sformułować zwięzły, jednoznaczny komentarz do commita.
2. Dodaj wszystkie zmiany do indeksu:
   ```bash
   git add .
   ```
3. Wykonaj commit z przygotowanym opisem:
   ```bash
   git commit -m "<zwięzły opis zmian>"
   ```
4. Wyślij zmiany na zdalną gałąź:
   ```bash
   git push
   ```
5. Potwierdź użytkownikowi pomyślne wykonanie operacji, podając identyfikator commita oraz treść komunikatu.

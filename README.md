# **Integracja Home Assistant ZTM Tracker**

**Uwaga: Cała ta integracja została stworzona przez Gemini AI, z ograniczonymi ręcznymi inspekcjami kodu i testami w celu uniknięcia halucynacji AI.**

## **Logika Integracji**

Podstawą tej integracji jest jej zdolność do tworzenia „zdarzeń”, gdy pojazd transportu publicznego znajdzie się w określonym promieniu od monitorowanego urządzenia śledzącego. Działa ona w następujący sposób:

1. **Pobieranie danych ZTM:** Komponent regularnie pobiera w czasie rzeczywistym dane o lokalizacji pojazdów z oficjalnego API ZTM.
2. **Znajdowanie bliskości:** Następnie porównuje lokalizację każdego skonfigurowanego urządzenia śledzącego (np. Twojego telefonu) z lokalizacją wszystkich dostępnych pojazdów ZTM.
3. **Ustanawianie zdarzenia:** Aby uniknąć fałszywych alarmów wynikających z krótkich zakłóceń sygnału, „zdarzenie” jest ustanawiane dopiero, gdy pojazd zostanie wykryty w promieniu przez określoną liczbę kolejnych cykli pobierania danych z API, zdefiniowaną przez parametr shots\_in.
4. **Podtrzymywanie zdarzenia:** Zdarzenie pozostaje aktywne tak długo, jak pojazd jest stale wykrywany. Jeśli pojazd opuści promień, komponent zezwala na pewną liczbę „shots out” zanim zdarzenie zostanie uznane za zakończone. Zapobiega to przedwczesnemu zakończeniu zdarzenia.
5. **Śledzenie ostatniej trasy:** Oddzielny, bardziej responsywny sensor śledzi „ostatnią widzianą trasę”. Wartość ta aktualizuje się natychmiast po wykryciu prawidłowego pojazdu w promieniu, zapewniając natychmiastową informację zwrotną o tym, która linia transportu publicznego jest aktualnie w pobliżu, nawet jeśli próg shots\_in dla pełnego zdarzenia nie został jeszcze osiągnięty.

## **Parametry Konfiguracji**

Integrację można skonfigurować za pomocą interfejsu użytkownika Home Assistant. Następujące parametry kontrolują jej działanie:

| Parametr | Wartość domyślna | Opis |
| :---- | :---- | :---- |
| Urządzenia śledzące | device\_tracker.your\_device | Lista identyfikatorów encji Home Assistant, które reprezentują urządzenia, których chcesz używać do śledzenia bliskości (np. device\_tracker.waldek). |
| Promień | 50 | Odległość w metrach, w jakiej pojazd ZTM musi znajdować się od urządzenia śledzącego, aby zostać uznany za „w pobliżu”. |
| Plik danych | <https://ckan2.multimediagdansk.pl/gpsPositions?v=2> | Adres URL kanału danych API ZTM. Zaleca się pozostawienie tej wartości jako domyślnej, chyba że API ulegnie zmianie. |
| Shots In | 2 | Liczba kolejnych wykryć pojazdu w promieniu, zanim zostanie zarejestrowane „zdarzenie”. |
| Shots Out | 3 | Liczba kolejnych wykryć, gdy pojazd jest poza promieniem (lub nie został wykryty), zanim aktywne zdarzenie zostanie uznane za zakończone. |
| Automatyczny interwał | 3 | Interwał w minutach, w którym integracja będzie automatycznie pobierać nowe dane z API ZTM. |
| Przesunięcie czasu GPS | 120 | Maksymalny wiek, w sekundach, danych GPS pojazdu, aby były uważane za prawidłowe. Pojazdy ze starszymi danymi będą ignorowane. |
| Biała lista linii | 2,5,12,169,171,179 | Lista numerów konkretnych linii transportu publicznego (np. 12, 169), oddzielonych przecinkami, które mają być śledzone. Jeśli to pole jest puste, śledzone będą wszystkie linie. |

## **Sensory**

Ta integracja udostępnia dwa główne sensory:

* **ztm\_tracker\_events**: Stan tego sensora wskazuje, czy trwa aktywne zdarzenie. Jego atrybuty będą zawierać szczegółową listę wszystkich bieżących zdarzeń, w tym ID pojazdu, liczby shots\_in i shots\_out oraz event\_summary, który zawiera nazwę urządzenia śledzącego i numer trasy.
* **ztm\_tracker\_last\_route**: Stan tego sensora to ciąg znaków, który pokazuje ostatnią trasę transportu publicznego wykrytą w pobliżu odpowiedniego urządzenia śledzącego. Format to \[Nazwa urządzenia śledzącego\] \- \[Numer trasy\]. Ten sensor aktualizuje się natychmiast, gdy tylko zostanie wykryta nowa trasa.

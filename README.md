# **ZTM Tracker Home Assistant Integration**

Integracja do Home Assistant, która śledzi autobusy ZTM w Gdańsku i powiadamia o ich zbliżaniu się do wybranej lokalizacji.

## **Opis**

Ta integracja pozwala na monitorowanie lokalizacji autobusów ZTM w Trójmieście. Wykorzystuje dane GPS udostępniane przez ZTM Gdańsk, aby określić, czy jakiś autobus znajduje się w zdefiniowanej strefie wokół jednego z Twoich **device\_trackers**.
Integracja używa logiki opartej na shots\_in i shots\_out, aby uniknąć fałszywych alarmów spowodowanych chwilową utratą sygnału:

* **shots\_in**: Autobus musi być wykryty w Twojej strefie przez określoną liczbę kolejnych cykli odświeżania, zanim zostanie uznane, że "wszedł" w strefę.
* **shots\_out**: Autobus musi zniknąć z Twojej strefy przez określoną liczbę kolejnych cykli odświeżania, zanim zostanie uznane, że "opuścił" strefę.

Gdy autobus spełni kryteria shots\_in, integracja aktywuje sensora, którego możesz użyć w automatyzacjach, aby na przykład wysłać powiadomienie.

## **Instalacja**

Integracja jest przeznaczona do instalacji za pomocą **HACS** (Home Assistant Community Store).

1. Upewnij się, że masz zainstalowany HACS.
2. Przejdź do HACS, a następnie do sekcji **Integracje**.
3. Kliknij przycisk z trzema kropkami w prawym górnym rogu, a następnie wybierz **Własne repozytoria**.
4. Wklej adres URL tego repozytorium i wybierz kategorię **Integracja**.
5. Repozytorium pojawi się na liście. Kliknij **Zainstaluj**.
6. Po zakończeniu instalacji, uruchom ponownie Home Assistant.

## **Konfiguracja**

Po ponownym uruchomieniu Home Assistant, dodaj integrację **ZTM Tracker** poprzez interfejs użytkownika.
Możesz skonfigurować następujące parametry:

* CONF\_DEVICE\_TRACKERS: Wymagany. Lista **device\_trackers** do monitorowania. Integracja będzie śledzić lokalizację każdego z tych urządzeń.
* CONF\_RADIUS: Opcjonalny. Promień strefy, w metrach, wokół **device\_trackers**. Wartość domyślna to 50 metrów.
* CONF\_DATA\_FILE: Opcjonalny. Adres URL pliku danych GPS z ZTM. Domyślny URL jest już poprawny.
* CONF\_SHOTS\_IN: Opcjonalny. Liczba kolejnych cykli odświeżania, w których autobus musi być wykryty w strefie, aby zdarzenie zostało uznane za aktywne. Wartość domyślna to 2\.
* CONF\_SHOTS\_OUT: Opcjonalny. Liczba kolejnych cykli odświeżania, w których autobus musi zniknąć ze strefy, aby zdarzenie zostało zakończone. Wartość domyślna to 3\.
* CONF\_AUTOMATIC\_INTERVAL: Opcjonalny. Interwał odświeżania danych GPS z ZTM w minutach. Wartość domyślna to 3 minuty.
* CONF\_GPS\_TIME\_OFFSET: Opcjonalny. Maksymalny wiek danych GPS autobusu w sekundach. Starsze dane zostaną zignorowane. Wartość domyślna to 120 sekund.
* CONF\_LINES\_WHITELIST: Opcjonalny. Lista numerów linii autobusowych, oddzielona przecinkami, które mają być śledzone. Jeśli pusta, śledzone są wszystkie linie. Domyślna wartość to 2,5,12,169,171,179.

## **Sensory**

Integracja tworzy dwa sensory w Home Assistant:

* **ZTM Tracker Events**
  * **state**: Zmienia się na active, gdy wykryty zostanie aktywny autobus w strefie, w przeciwnym razie jest inactive.
  * **attributes**: Lista aktualnych, aktywnych zdarzeń. Każde zdarzenie zawiera informacje o urządzeniu użytkownika (device\_id), numerze linii (route\_name) oraz identyfikatorze pojazdu (bus\_id).
* **ZTM Tracker Last Route**
  * **state**: Zawiera numer ostatniej linii autobusowej, która została wykryta w pobliżu.

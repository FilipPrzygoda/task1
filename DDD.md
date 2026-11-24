# Modelowanie bezpiecznej aplikacji bankowej (DDD)

## Opis zadania

Celem zadania jest zamodelowanie wybranego fragmentu bezpiecznej aplikacji bankowej zgodnie z podejściem Domain-Driven Design (DDD). Przyjęty wycinek domeny obejmuje uwierzytelnianie użytkownika, obsługę profilu klienta i rachunku bankowego oraz proces autoryzacji i realizacji przelewu wychodzącego. Całość podzielono na trzy konteksty ograniczone (*Bounded Contexts*): `Identity & Access`, `Account Management` oraz `Transfers`, komunikujące się wyłącznie za pośrednictwem identyfikatorów oraz zdarzeń domenowych. Dla wszystkich encji i obiektów wartości zdefiniowano inwarianty oraz ograniczenia formatów danych wymuszane już na etapie konstrukcji obiektów, co eliminuje ryzyko powstania niespójnego stanu w systemie.

## Model

![Model DDD](./tbo1_model.jpg)

## Konteksty ograniczone (Bounded Contexts)

| Kontekst | Odpowiedzialność | Korzenie agregatów |
| :--- | :--- | :--- |
| `Identity & Access` | Uwierzytelnianie hasłem, weryfikacja drugiego składnika (2FA) oraz blokowanie konta po nieudanych próbach dostępu. | `User` |
| `Account Management` | Przechowywanie danych osobowych i statusu KYC klienta, obsługa rachunków, pilnowanie limitów dziennych oraz księgowanie historii operacji. | `Client`, `BankAccount` |
| `Transfers` | Tworzenie zleceń przelewów, obsługa ich autoryzacji oraz zmiana statusu po rozliczeniu lub odrzuceniu przez rachunek. | `Transfer` |

## Agregaty, encje i obiekty wartości

| Agregat | Korzeń agregatu | Encje wewnętrzne | Obiekty wartości |
| :--- | :--- | :--- | :--- |
| `User` | `User` | – | – |
| `Client` | `Client` | – | `Address` |
| `BankAccount` | `BankAccount` | `Transaction` | `IBAN`, `Money` |
| `Transfer` | `Transfer` | – | `IBAN`, `Money` |

Założenia strukturalne modelu:
- Encja `Transaction` należy bezpośrednio do agregatu `BankAccount` (`0..*`) i nie posiada własnego repozytorium. Tworzona jest wyłącznie wewnątrz metod `debit()` oraz `credit()`, dzięki czemu historia księgowań jest zawsze spójna z aktualnym saldem (`balance`).
- `Client` oraz `BankAccount` są osobnymi agregatami – aktualizacja adresu zamieszkania czy statusu weryfikacji tożsamości klienta nie blokuje transakcyjnie operacji wykonywanych na rachunku.
- Powiązania pomiędzy agregatami oraz kontekstami realizowane są wyłącznie przez identyfikatory `UUID` (`clientId`, `ownerId`, `sourceAccountId`, `transferId`), bez bezpośrednich referencji obiektowych.
- Obiekty wartości (`Address`, `IBAN`, `Money`) są niemutowalne (*immutable*) i porównywane przez wartość swoich atrybutów. Zmiana adresu w agregacie `Client` (`updateAddress()`) polega na podmianie całej instancji `Address`.
- Obiekty wartości `IBAN` oraz `Money` stanowią współdzielone jądro (*Shared Kernel*) pomiędzy kontekstami `Account Management` oraz `Transfers` – mimo umieszczenia ich na diagramie przy głównych kontekstach właścicielskich, oba typy są wykorzystywane w obu tych obszarach bez powielania logiki walidacji.

## Przyjęte założenia i formaty danych

### Reguły ogólne i typy wyliczeniowe

- **Identyfikatory (`UUID`):** Generowane wyłącznie po stronie serwera w wersji UUID v4, co zapobiega podatnościom typu IDOR (enumeracji zasobów).
- **Znaczniki czasu (`DateTime`):** Zapisywane w standardzie ISO 8601 w strefie UTC (np. `2026-11-24T15:30:00Z`), nadawane przez system.
- **Sanityzacja tekstu:** Wszystkie ciągi znaków przechodzą operację `trim()`, odrzucają znaki sterujące ASCII oraz znaki specjalne wykorzystywane przy atakach typu injection (`<`, `>`, `"`, `'`, `;`).
- **Typy wyliczeniowe (Enums):**
  - `AuthMethod`: `SMS_CODE`, `MOBILE_PUSH`, `TOTP`
  - `KycStatus`: `PENDING`, `VERIFIED`, `REJECTED`
  - `AccountStatus`: `ACTIVE`, `FROZEN`, `CLOSED`
  - `TransactionType`: `DEBIT`, `CREDIT`
  - `TransferStatus`: `CREATED`, `AUTHORIZED`, `EXECUTED`, `REJECTED`
  - `Currency`: `PLN`, `EUR`, `USD` (ISO 4217)

### Kontekst: `Identity & Access`

| Element | Pole / Metoda | Typ | Ograniczenia i format |
| :--- | :--- | :--- | :--- |
| `User` *(Aggregate Root)* | `id` | `UUID` | UUID v4. |
| | `login` | `String` | 6–24 znaki, wzorzec `^[a-zA-Z0-9._-]+$`, unikalny w systemie. |
| | `passwordHash` | `String` | Skrót kryptograficzny (Argon2id lub bcrypt). Jawne hasło (min. 12 znaków, mała i wielka litera, cyfra, znak specjalny) jest walidowane tylko przy ustawianiu i nigdy nie jest utrwalane. |
| | `authMethod` | `AuthMethod` | Skonfigurowany kanał weryfikacji drugiego składnika. |
| | `failedAttempts` | `Int` | Licznik kolejnych nieudanych prób logowania lub weryfikacji 2FA (zakres `0–3`, domyślnie `0`; zerowany po poprawnym uwierzytelnieniu). |
| | `isBlocked` | `Boolean` | Domyślnie `false`; ustawiane automatycznie na `true` przez `block()` po osiągnięciu `failedAttempts == 3`. |
| | `clientId` | `UUID` | Identyfikator powiązanego klienta z kontekstu `Account Management`. |
| | `login(password: String)` | `Boolean` | Weryfikuje hash hasła; gdy `isBlocked == true`, natychmiast zwraca `false`. Przy błędnym haśle inkrementuje `failedAttempts` i wywołuje `block()` przy 3. próbie. |
| | `verify2FA(code: String)` | `Boolean` | Sprawdza jednorazowy kod (`^\d{6}$`) w oknie czasowym ważności. Przy błędnym kodzie inkrementuje `failedAttempts` i blokuje konto po 3 nieudanych próbach; przy sukcesie zeruje licznik. |
| | `block()` | `void` | Blokuje dostęp do konta użytkownika (`isBlocked = true`). |

### Kontekst: `Account Management`

| Element | Pole / Metoda | Typ | Ograniczenia i format |
| :--- | :--- | :--- | :--- |
| `Client` *(Aggregate Root)* | `id` | `UUID` | UUID v4. |
| | `firstName` | `String` | 2–50 znaków, `^[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż\-]+$`. |
| | `lastName` | `String` | 2–60 znaków, `^[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż \-]+$`. |
| | `pesel` | `String` | Dokładnie 11 cyfr (`^\d{11}$`), poprawna suma kontrolna oraz zakodowana data urodzenia. |
| | `kycStatus` | `KycStatus` | Status weryfikacji tożsamości; zmiana na `VERIFIED` jest wymagana do aktywacji rachunku. |
| | `address` | `Address` | Adres zamieszkania klienta (powiązanie `1` z obiektem wartości `Address`). |
| | `updateAddress(address: Address)` | `void` | Podmienia dotychczasowy adres na nową, zwalidowaną instancję obiektu `Address`. |
| | `verifyKyc()` | `void` | Zmienia status `kycStatus` na `VERIFIED` po pozytywnym przejściu weryfikacji tożsamości. |
| `Address` *(Value Object)* | `street` | `String` | 2–100 znaków (ulica wraz z numerem domu/lokalu), `^[A-Za-z0-9ĄĆĘŁŃÓŚŹŻąćęłńóśźż .\-/]+$`. |
| | `postalCode` | `String` | Polski kod pocztowy `^\d{2}-\d{3}$` (np. `00-661`). |
| | `city` | `String` | 2–60 znaków, `^[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż \-]+$`. |
| `BankAccount` *(Aggregate Root)* | `id` | `UUID` | UUID v4. |
| | `ownerId` | `UUID` | Identyfikator właściciela (`Client.id`). |
| | `iban` | `IBAN` | Unikalny numer rachunku bankowego. |
| | `balance` | `Money` | Bieżące saldo rachunku; nie może być ujemne (`amount >= 0.00`). |
| | `dailyLimit` | `Money` | Dzienny limit przelewów wychodzących (`amount > 0.00`, waluta zgodna z `balance`). |
| | `status` | `AccountStatus` | Zmiany salda są dozwolone wyłącznie dla statusu `ACTIVE`. |
| | `debit(amount: Money, transferId: UUID)` | `void` | Obciąża rachunek i dopisuje `Transaction` (`DEBIT`), jeśli konto jest `ACTIVE`, waluty są zgodne, `balance >= amount` oraz nie przekroczono `dailyLimit`. |
| | `credit(amount: Money, transferId: UUID)` | `void` | Uznaje rachunek i dopisuje `Transaction` (`CREDIT`) dla konta `ACTIVE` i zgodnej waluty. |
| `Transaction` *(Entity)* | `id` | `UUID` | UUID v4. |
| | `type` | `TransactionType` | `DEBIT` lub `CREDIT`. |
| | `amount` | `Money` | Kwota operacji (`amount > 0.00`), waluta zgodna z walutą rachunku. |
| | `bookedAt` | `DateTime` | Czas zaksięgowania operacji w UTC. |
| | `transferId` | `UUID` | Identyfikator powiązanego przelewu z kontekstu `Transfers`. |
| `IBAN` *(Value Object)* | `countryCode` | `String` | Dwuliterowy kod kraju ISO 3166-1 alpha-2 (`^[A-Z]{2}$`, np. `PL`). |
| | `number` | `String` | Ciąg cyfr bez spacji (dla `PL` dokładnie 26 cyfr), poprawna suma kontrolna ISO 7064 (MOD 97-10). |

### Kontekst: `Transfers`

| Element | Pole / Metoda | Typ | Ograniczenia i format |
| :--- | :--- | :--- | :--- |
| `Transfer` *(Aggregate Root)* | `id` | `UUID` | UUID v4. |
| | `sourceAccountId` | `UUID` | Identyfikator rachunku źródłowego (`BankAccount.id`) należącego do zalogowanego klienta. |
| | `targetIban` | `IBAN` | Numer rachunku odbiorcy; musi być różny od numeru `IBAN` rachunku źródłowego. |
| | `amount` | `Money` | Kwota przelewu (`amount > 0.00`), maksymalnie `100 000.00` dla pojedynczego zlecenia. |
| | `title` | `String` | 1–140 znaków, `^[A-Za-z0-9ĄĆĘŁŃÓŚŹŻąćęłńóśźż .,\-/()]+$`. |
| | `status` | `TransferStatus` | Dozwolone przejścia stanów: `CREATED` -> `AUTHORIZED` -> `EXECUTED` lub `CREATED` / `AUTHORIZED` -> `REJECTED`. |
| | `rejectionReason` | `String?` | Opcjonalny powód odrzucenia przelewu (1–200 znaków, `null` dopóki status jest inny niż `REJECTED`). |
| | `createdAt` | `DateTime` | Czas utworzenia zlecenia w UTC. |
| | `authorize()` | `void` | Zmienia status z `CREATED` na `AUTHORIZED` po pozytywnej weryfikacji 2FA. |
| | `execute()` | `void` | Zmienia status z `AUTHORIZED` na `EXECUTED` po zaksięgowaniu obciążenia na rachunku. |
| | `reject(reason: String)` | `void` | Ustawia status `REJECTED` oraz zapisuje w `rejectionReason` przyczynę odrzucenia (np. po błędzie 2FA lub odrzuceniu obciążenia przez `BankAccount`). |
| `Money` *(Value Object)* | `amount` | `Decimal` | Typ stałoprzecinkowy z dokładnością do 2 miejsc po przecinku (`scale = 2`), wykluczający błędy zaokrągleń `float`/`double`. |
| | `currency` | `Currency` | Kod waluty zgodny z ISO 4217 (`PLN`, `EUR`, `USD`). |

## Operacje i integracja między kontekstami

| Etap | Konteksty | Przebieg i reguły biznesowe |
| :--- | :--- | :--- |
| Uwierzytelnienie | `Identity & Access` -> `Account Management` | Użytkownik loguje się przez `User.login(password)`. Po poprawnej weryfikacji system zeruje `failedAttempts` i pobiera rachunki powiązane z `User.clientId` (`BankAccount.ownerId == User.clientId`), co blokuje dostęp do cudzych kont. |
| Utworzenie zlecenia | `Transfers` | Powstaje agregat `Transfer` ze statusem `CREATED`. Konstruktory obiektów `IBAN` i `Money` weryfikują poprawność formatu oraz sumy kontrolnej przed zapisem. |
| 1. Verify 2FA | `Transfers` -> `Identity & Access` | Kontekst `Transfers` zleca potwierdzenie dyspozycji przez `User.verify2FA(code)`. Poprawna weryfikacja pozwala wywołać `Transfer.authorize()`. W przypadku niepowodzenia `User` podbija `failedAttempts` (przy 3. błędzie blokuje konto), a przelew dostaje `Transfer.reject(reason)`. |
| 2. TransferAuthorized | `Transfers` -> `Account Management` | Po zmianie statusu na `AUTHORIZED` publikowane jest zdarzenie `TransferAuthorized`. Kontekst `Account Management` wywołuje `BankAccount.debit(amount, transferId)`, weryfikując aktywność rachunku, zgodność walut, dostępność salda oraz limit dzienny. |
| Księgowanie i finalizacja | `Account Management` -> `Transfers` | Jeśli `debit()` zakończy się sukcesem i zapisze encję `Transaction` (`DEBIT`), wywoływana jest metoda `Transfer.execute()` (dla przelewu wewnętrznego następuje również `credit()` na koncie odbiorcy). W razie naruszenia reguł rachunku wywoływane jest `Transfer.reject(reason)`. |
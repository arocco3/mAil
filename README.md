# mAil

Client email desktop per Windows, basato solo su protocolli standard (IMAP e SMTP), senza API proprietarie.

## Cosa fa

- Legge la posta da un account via IMAP
- Risponde e invia messaggi con allegati via SMTP
- Ordina, etichetta, sposta e cerca i messaggi
- In futuro: etichettatura automatica con un modello di IA eseguito in locale

## Requisiti

- Windows
- Python 3.10 o superiore
- Un account Gmail con la verifica in due passaggi attiva e una "password per le app"

## Avvio

Fai doppio clic sul file Python del progetto. Al primo avvio vengono chieste le credenziali.

## Sicurezza

Indirizzo email e password non vengono mai scritti nel codice né salvati in questa cartella. Il file `.gitignore` esclude anche database locali, allegati scaricati e file di configurazione, così i dati personali non finiscono su GitHub.

## Stato del progetto

Le tappe e le cose da fare sono nella sezione Issues della repo.
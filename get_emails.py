"""
Passo 1 - Login IMAP a Gmail e lettura delle ultime email (sola lettura).

Cosa impari qui:
- connessione sicura (SSL) a un server IMAP
- login con password per le app
- elenco delle cartelle (che per Gmail sono anche le "etichette")
- ricerca dei messaggi e lettura di intestazioni e testo
"""

import imaplib
import email
from email.header import decode_header, make_header
from getpass import getpass

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993          # porta standard per IMAP su SSL
NUMERO_EMAIL = 10        # quante email recenti mostrare


def decodifica(valore):
    """Le intestazioni possono essere codificate (es. =?UTF-8?B?...?=): le rendiamo leggibili."""
    if valore is None:
        return ""
    return str(make_header(decode_header(valore)))


def estrai_testo(messaggio):
    """Restituisce il corpo in testo semplice, ignorando gli allegati."""
    if messaggio.is_multipart():
        for parte in messaggio.walk():
            tipo = parte.get_content_type()
            disposizione = str(parte.get("Content-Disposition", ""))
            if tipo == "text/plain" and "attachment" not in disposizione:
                return decodifica_parte(parte)
        return "(nessuna parte di testo semplice)"
    return decodifica_parte(messaggio)


def decodifica_parte(parte):
    contenuto = parte.get_payload(decode=True)   # decodifica base64 / quoted-printable
    if contenuto is None:
        return ""
    charset = parte.get_content_charset() or "utf-8"
    return contenuto.decode(charset, errors="replace")


def main():
    indirizzo = input("Indirizzo Gmail: ").strip()
    password_app = getpass("Password per le app (16 caratteri, non viene mostrata): ").replace(" ", "")

    # 1. Connessione e login
    conn = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    conn.login(indirizzo, password_app)
    print("\nLogin riuscito.\n")

    # 2. Elenco cartelle
    stato, cartelle = conn.list()
    print("Cartelle disponibili:")
    for riga in cartelle:
        print("  ", riga.decode())

    # 3. Apro la posta in arrivo in sola lettura (readonly=True: nulla viene segnato come letto)
    conn.select("INBOX", readonly=True)

    # 4. Cerco tutti i messaggi e prendo gli ultimi
    stato, dati = conn.search(None, "ALL")
    id_messaggi = dati[0].split()
    ultimi = id_messaggi[-NUMERO_EMAIL:]
    print(f"\nTotale in INBOX: {len(id_messaggi)}. Mostro gli ultimi {len(ultimi)}.\n")

    # 5. Scarico e leggo ogni messaggio (dal più recente)
    for num in reversed(ultimi):
        stato, dati = conn.fetch(num, "(RFC822)")
        grezzo = dati[0][1]                     # il messaggio completo in bytes
        msg = email.message_from_bytes(grezzo)

        print("-" * 60)
        print("Da:     ", decodifica(msg["From"]))
        print("Oggetto:", decodifica(msg["Subject"]))
        print("Data:   ", msg["Date"])
        anteprima = estrai_testo(msg).strip().replace("\n", " ")[:200]
        print("Testo:  ", anteprima)

    conn.logout()


if __name__ == "__main__":
    # Il try/except e l'input finale servono per avviare lo script con doppio clic:
    # senza, la finestra si chiuderebbe subito e non vedresti risultato o errore.
    try:
        main()
    except Exception as errore:
        print(f"\nErrore: {errore}")
    input("\nPremi Invio per chiudere...")

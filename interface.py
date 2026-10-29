"""
Passo 2 - Interfaccia grafica di mAil (sola lettura).

Cosa impari qui:
- finestra di login (la password si scrive con i pallini, non nel terminale)
- lista dei messaggi a sinistra, testo del messaggio a destra
- scaricare dal server SOLO le intestazioni per la lista, e il messaggio intero solo
  quando lo apri (cosi' resta veloce anche con migliaia di email)

Richiede PySide6:  pip install PySide6
"""

import email
import imaplib
import re
import sys
from email.header import decode_header, make_header

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QFormLayout, QDialogButtonBox, QLineEdit, QLabel,
    QMainWindow, QMessageBox, QPushButton, QListWidget, QListWidgetItem,
    QPlainTextEdit, QSplitter, QVBoxLayout, QWidget,
)

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
QUANTE_EMAIL = 50        # quante email recenti mostrare nella lista


# ---------------------------------------------------------------------------
# Funzioni di supporto (le stesse del passo 1, piu' una per le email solo-HTML)
# ---------------------------------------------------------------------------

def decodifica(valore):
    if valore is None:
        return ""
    return str(make_header(decode_header(valore)))


def decodifica_parte(parte):
    contenuto = parte.get_payload(decode=True)
    if contenuto is None:
        return ""
    charset = parte.get_content_charset() or "utf-8"
    try:
        return contenuto.decode(charset, errors="replace")
    except LookupError:                      # charset sconosciuto
        return contenuto.decode("utf-8", errors="replace")


def html_a_testo(html):
    """Conversione grezza HTML -> testo: va bene per leggere, non e' perfetta."""
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", html)
    html = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", html)
    testo = re.sub(r"<[^>]+>", "", html)
    testo = re.sub(r"\n\s*\n+", "\n\n", testo)
    return testo.strip()


def estrai_testo(messaggio):
    """Cerca prima il testo semplice, altrimenti ripiega sull'HTML."""
    testo, html = None, None
    for parte in messaggio.walk():
        if parte.is_multipart():
            continue
        if "attachment" in str(parte.get("Content-Disposition", "")):
            continue
        tipo = parte.get_content_type()
        if tipo == "text/plain" and testo is None:
            testo = decodifica_parte(parte)
        elif tipo == "text/html" and html is None:
            html = decodifica_parte(parte)
    if testo:
        return testo
    if html:
        return html_a_testo(html)
    return "(questo messaggio non contiene testo leggibile)"


def nomi_allegati(messaggio):
    nomi = []
    for parte in messaggio.walk():
        nome = parte.get_filename()
        if nome:
            nomi.append(decodifica(nome))
    return nomi


# ---------------------------------------------------------------------------
# Finestra di login
# ---------------------------------------------------------------------------

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("mAil - Accedi")
        self.campo_email = QLineEdit()
        self.campo_password = QLineEdit()
        self.campo_password.setEchoMode(QLineEdit.Password)   # mostra i pallini

        form = QFormLayout()
        form.addRow("Indirizzo Gmail:", self.campo_email)
        form.addRow("Password per le app:", self.campo_password)

        pulsanti = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        pulsanti.accepted.connect(self.accept)
        pulsanti.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(pulsanti)
        self.setMinimumWidth(380)

    def credenziali(self):
        # la password per le app si puo' incollare anche con gli spazi
        return self.campo_email.text().strip(), self.campo_password.text().replace(" ", "")


# ---------------------------------------------------------------------------
# Finestra principale
# ---------------------------------------------------------------------------

class FinestraPrincipale(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.setWindowTitle("mAil")
        self.resize(1000, 600)

        # sinistra: lista messaggi
        self.lista = QListWidget()
        self.lista.currentItemChanged.connect(self.apri_messaggio)

        self.pulsante_aggiorna = QPushButton("Aggiorna")
        self.pulsante_aggiorna.clicked.connect(self.carica_lista)

        sinistra = QWidget()
        lay_sx = QVBoxLayout(sinistra)
        lay_sx.setContentsMargins(0, 0, 0, 0)
        lay_sx.addWidget(self.pulsante_aggiorna)
        lay_sx.addWidget(self.lista)

        # destra: intestazione + testo
        self.intestazione = QLabel("Seleziona un messaggio")
        self.intestazione.setWordWrap(True)
        self.intestazione.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.testo = QPlainTextEdit()
        self.testo.setReadOnly(True)

        destra = QWidget()
        lay_dx = QVBoxLayout(destra)
        lay_dx.setContentsMargins(0, 0, 0, 0)
        lay_dx.addWidget(self.intestazione)
        lay_dx.addWidget(self.testo)

        divisore = QSplitter()
        divisore.addWidget(sinistra)
        divisore.addWidget(destra)
        divisore.setSizes([350, 650])
        self.setCentralWidget(divisore)

        self.carica_lista()

    def carica_lista(self):
        """Scarica SOLO le intestazioni degli ultimi messaggi."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.lista.clear()
            self.conn.select("INBOX", readonly=True)
            stato, dati = self.conn.uid("search", None, "ALL")
            uids = dati[0].split()[-QUANTE_EMAIL:]
            if not uids:
                self.statusBar().showMessage("Nessun messaggio in INBOX")
                return

            # UID = identificativo stabile del messaggio (meglio del numero progressivo)
            stato, dati = self.conn.uid(
                "fetch", b",".join(uids),
                "(UID BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])",
            )

            elementi = []
            for i, parte in enumerate(dati):
                if not isinstance(parte, tuple):
                    continue
                trovato = re.search(rb"UID (\d+)", parte[0])
                if not trovato and i + 1 < len(dati) and isinstance(dati[i + 1], bytes):
                    trovato = re.search(rb"UID (\d+)", dati[i + 1])   # a volte arriva dopo
                if not trovato:
                    continue
                intest = email.message_from_bytes(parte[1])
                elementi.append((
                    int(trovato.group(1)),
                    decodifica(intest["From"]),
                    decodifica(intest["Subject"]) or "(senza oggetto)",
                ))

            # dal piu' recente al meno recente
            for uid, mittente, oggetto in sorted(elementi, reverse=True):
                voce = QListWidgetItem(f"{oggetto}\n{mittente}")
                voce.setData(Qt.UserRole, uid)
                self.lista.addItem(voce)
            self.statusBar().showMessage(f"{len(elementi)} messaggi caricati")
        except Exception as errore:
            QMessageBox.warning(self, "Errore", f"Impossibile caricare la lista:\n{errore}")
        finally:
            QApplication.restoreOverrideCursor()

    def apri_messaggio(self, voce):
        """Scarica il messaggio intero solo quando lo selezioni."""
        if voce is None:
            return
        uid = voce.data(Qt.UserRole)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            stato, dati = self.conn.uid("fetch", str(uid), "(BODY.PEEK[])")
            msg = email.message_from_bytes(dati[0][1])
            righe = [
                f"Da: {decodifica(msg['From'])}",
                f"Oggetto: {decodifica(msg['Subject'])}",
                f"Data: {msg['Date']}",
            ]
            allegati = nomi_allegati(msg)
            if allegati:
                righe.append("Allegati: " + ", ".join(allegati))
            self.intestazione.setText("\n".join(righe))
            self.testo.setPlainText(estrai_testo(msg))
        except Exception as errore:
            QMessageBox.warning(self, "Errore", f"Impossibile aprire il messaggio:\n{errore}")
        finally:
            QApplication.restoreOverrideCursor()

    def closeEvent(self, evento):
        try:
            self.conn.logout()
        except Exception:
            pass
        evento.accept()


# ---------------------------------------------------------------------------
# Avvio
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)

    while True:
        dialogo = LoginDialog()
        if dialogo.exec() != QDialog.Accepted:
            return
        indirizzo, password = dialogo.credenziali()
        try:
            conn = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
            conn.login(indirizzo, password)
            break
        except Exception as errore:
            QMessageBox.warning(None, "Accesso non riuscito", f"{errore}\n\nControlla indirizzo e password per le app.")

    finestra = FinestraPrincipale(conn)
    finestra.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

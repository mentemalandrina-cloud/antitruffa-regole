# Regole AntiTruffa — istruzioni per l'aggiornamento settimanale

`regole.json` viene scaricato ogni giorno dall'app Android AntiTruffa da
https://raw.githubusercontent.com/mentemalandrina-cloud/antitruffa-regole/main/regole.json
e serve a riconoscere le truffe via SMS, WhatsApp e telefono diffuse in Italia. Un errore qui arriva sui telefoni:
pubblica solo se `verifica.py` passa.

## Ogni esecuzione
1. Leggi le novità degli ultimi 7 giorni da queste fonti, e dalle pagine a cui rimandano:
   - CERT-AgID: https://cert-agid.gov.it/feed/ (sintesi settimanale delle campagne, il venerdì)
   - Polizia Postale: https://www.commissariatodips.it/rss-alert.xml
   - Consob, siti oscurati: https://www.consob.it/web/area-pubblica/oscuramenti
2. Per ogni truffa nuova (o variante nuova) che arriva in Italia via SMS, WhatsApp o telefono:
   - **Truffa nuova:** aggiungi una voce in `truffe` con `id`, `nome`, `canali`, `come_riconoscerla`, `cosa_fare` e `fonti`
     (solo URL che hai aperto davvero). Aggiungi anche almeno 2 `esempi` di truffa realistici, scritti con parole tue.
   - **Regole nuove:** in `frasi`, `domini_sospetti` e `prefissi_chiamate` aggiungi solo voci specifiche e documentate.
     Parole e frasi vanno in minuscolo e senza accenti.
   - **Falsi allarmi:** per ogni regola nuova aggiungi almeno 1 esempio legittimo simile, che NON deve scattare.
3. Non togliere voci esistenti. Non cambiare `schema`, `soglia`, `punteggi`, `regex_link`: l'app li implementa così.
4. Metti in `aggiornato` la data di oggi (AAAA-MM-GG).
5. `python verifica.py regole.json` deve stampare `OK: ...`. Se fallisce, correggi; dopo 3 tentativi falliti NON
   pubblicare: `git checkout -- regole.json` e termina riportando l'errore.
6. Commit su `main` con il messaggio `regole: aggiornamento AAAA-MM-GG — <truffe aggiunte>` e push.
   Se non c'è niente di nuovo, nessun commit.

## Vincoli
- Mai dati personali: niente nomi né numeri reali di vittime o di privati.
- Solo fonti ufficiali o testate serie. Mai inventare: se una cosa non è documentata, non va nel file.

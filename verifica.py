"""Verifica regole.json: struttura + classificazione degli esempi.

Uso: python verifica.py regole.json
Stampa solo gli errori, poi "OK: N esempi, M truffe" oppure "FALLITO: K errori".
Exit code 1 se c'e' almeno un errore. Solo libreria standard (Python 3.11).
L'algoritmo di punteggio e' lo stesso che deve usare l'app (Kotlin).
"""
import json
import re
import sys
import unicodedata

TOP = {
    "schema": int, "aggiornato": str, "soglia": int, "punteggi": dict,
    "regex_link": str, "accorciatori": list, "domini_ufficiali": list,
    "gruppi": list, "frasi": list, "domini_sospetti": list,
    "prefissi_chiamate": list, "truffe": list, "esempi": list,
}
PUNTEGGI = ("link", "link_accorciato", "mittente_estero", "whatsapp_sconosciuto")
CANALI = {"sms", "whatsapp", "chiamata"}
CANALI_TESTO = {"sms", "whatsapp"}
MIN_ESEMPI_TRUFFA = 2
MIN_LEGITTIMI = 25


# ---------- algoritmo (identico nell'app) ----------

def normalizza(t):
    """minuscolo -> NFD -> via i segni combinanti (\\p{Mn}) -> spazi multipli in uno -> trim"""
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip()


def host_di(link):
    """togli http(s)://, taglia a / ? #, tieni cio' che segue l'ultima @,
    tieni solo [a-z0-9.-] iniziali (via porta e punteggiatura), togli i punti finali"""
    h = link
    for p in ("https://", "http://"):
        if h.startswith(p):
            h = h[len(p):]
            break
    h = re.split(r"[/?#]", h, maxsplit=1)[0]
    h = h.rsplit("@", 1)[-1]
    h = re.match(r"[a-z0-9.-]*", h).group(0)
    return h.rstrip(".")


def ufficiale(host, domini):
    return any(host == d or host.endswith("." + d) for d in domini)


def punteggio(r, canale, mittente, testo):
    t = normalizza(testo)
    p = r["punteggi"]
    tot, voci = 0, []

    hosts = [host_di(m.group(0)) for m in re.finditer(r["regex_link"], t)]
    if hosts and not all(ufficiale(h, r["domini_ufficiali"]) for h in hosts):
        tot += p["link"]
        voci.append("link")
        if any(h in r["accorciatori"] for h in hosts):
            tot += p["link_accorciato"]
            voci.append("accorciato")

    for g in r["gruppi"]:
        if any(re.search("(^|[^a-z0-9])" + re.escape(w), t) for w in g["parole"]):
            tot += g["peso"]
            voci.append(g["id"])

    for f in r["frasi"]:
        if f["testo"] in t:
            tot += f["peso"]
            voci.append("frase:" + f["testo"])

    for d in r["domini_sospetti"]:
        if d["testo"] in t:
            tot += d["peso"]
            voci.append("dominio:" + d["testo"])

    m = mittente.replace(" ", "")
    pref = m[1:] if m.startswith("+") else m[2:] if m.startswith("00") else None
    if pref is not None and not pref.startswith("39"):
        tot += p["mittente_estero"]
        voci.append("estero")

    if canale == "whatsapp" and re.fullmatch(r"[0-9 +]+", mittente):
        tot += p["whatsapp_sconosciuto"]
        voci.append("wa_sconosciuto")

    return tot, voci


# ---------- validazione ----------

def intero_pos(v):
    return type(v) is int and v > 0


def stringa(v):
    return isinstance(v, str) and v.strip() != ""


def normalizzata(v):
    return stringa(v) and normalizza(v) == v


def url(v):
    return isinstance(v, str) and re.fullmatch(r"https?://\S+", v) is not None


def controlla(r):
    e = []
    if not isinstance(r, dict):
        return ["il file non contiene un oggetto JSON"]
    for k, tipo in TOP.items():
        if k not in r:
            e.append(f"manca la chiave '{k}'")
        elif type(r[k]) is not tipo:
            e.append(f"'{k}' deve essere {tipo.__name__}")
    if e:
        return e

    if r["schema"] != 1:
        e.append("schema deve essere 1")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["aggiornato"]):
        e.append("aggiornato deve essere AAAA-MM-GG")
    if not intero_pos(r["soglia"]):
        e.append("soglia deve essere intero > 0")
    for k in PUNTEGGI:
        if not intero_pos(r["punteggi"].get(k)):
            e.append(f"punteggi.{k} deve essere intero > 0")
    try:
        re.compile(r["regex_link"])
    except re.error as x:
        e.append(f"regex_link non compila: {x}")
    if re.search(r"\(\?(?![:=!])", r["regex_link"]):
        e.append("regex_link: ammessi solo (?: (?= (?! (niente gruppi con nome, lookbehind, flag inline)")
    for k in ("accorciatori", "domini_ufficiali"):
        for i, s in enumerate(r[k]):
            if not normalizzata(s):
                e.append(f"{k}[{i}] deve essere stringa non vuota, minuscola, senza accenti")

    def campi(o, spec, dove):
        if not isinstance(o, dict):
            e.append(f"{dove}: deve essere un oggetto")
            return False
        ok = True
        for k, tipo in spec.items():
            if k not in o:
                e.append(f"{dove}: manca '{k}'")
                ok = False
            elif type(o[k]) is not tipo:
                e.append(f"{dove}.{k} deve essere {tipo.__name__}")
                ok = False
        return ok

    truffe_ok = []
    for i, t in enumerate(r["truffe"]):
        dove = f"truffe[{i}]"
        if not campi(t, {"id": str, "nome": str, "canali": list, "come_riconoscerla": str,
                         "cosa_fare": str, "fonti": list}, dove):
            continue
        for k in ("id", "nome", "come_riconoscerla", "cosa_fare"):
            if not stringa(t[k]):
                e.append(f"{dove}.{k} vuoto")
        if not t["canali"] or not set(t["canali"]) <= CANALI or len(set(t["canali"])) != len(t["canali"]):
            e.append(f"{dove}.canali: valori ammessi {sorted(CANALI)}, senza doppioni")
        if not t["fonti"] or not all(url(u) for u in t["fonti"]):
            e.append(f"{dove}.fonti: almeno un URL http(s)")
        truffe_ok.append(t)
    ids = [t["id"] for t in truffe_ok]
    for d in sorted({x for x in ids if ids.count(x) > 1}):
        e.append(f"id truffa duplicato: {d}")
    ids = set(ids)

    gid = []
    for i, g in enumerate(r["gruppi"]):
        dove = f"gruppi[{i}]"
        if not campi(g, {"id": str, "nome": str, "peso": int, "parole": list}, dove):
            continue
        gid.append(g["id"])
        if not stringa(g["id"]) or not stringa(g["nome"]):
            e.append(f"{dove}: id e nome non vuoti")
        if not intero_pos(g["peso"]):
            e.append(f"{dove}.peso deve essere intero > 0")
        if not g["parole"]:
            e.append(f"{dove}.parole vuoto")
        for j, w in enumerate(g["parole"]):
            if not normalizzata(w):
                e.append(f"{dove}.parole[{j}] deve essere stringa minuscola, senza accenti: {w!r}")
    for d in sorted({x for x in gid if gid.count(x) > 1}):
        e.append(f"id gruppo duplicato: {d}")

    for k in ("frasi", "domini_sospetti"):
        for i, f in enumerate(r[k]):
            dove = f"{k}[{i}]"
            if not campi(f, {"testo": str, "peso": int, "truffa": str}, dove):
                continue
            if not normalizzata(f["testo"]):
                e.append(f"{dove}.testo deve essere minuscolo, senza accenti: {f['testo']!r}")
            if not intero_pos(f["peso"]):
                e.append(f"{dove}.peso deve essere intero > 0")
            if f["truffa"] not in ids:
                e.append(f"{dove}.truffa inesistente: {f['truffa']}")

    for i, p in enumerate(r["prefissi_chiamate"]):
        dove = f"prefissi_chiamate[{i}]"
        if not campi(p, {"prefisso": str, "azione": str, "motivo": str, "fonte": str}, dove):
            continue
        if not re.fullmatch(r"\+\d+", p["prefisso"]):
            e.append(f"{dove}.prefisso deve essere +<cifre>: {p['prefisso']!r}")
        if p["azione"] not in ("avvisa", "blocca"):
            e.append(f"{dove}.azione deve essere 'avvisa' o 'blocca'")
        if not stringa(p["motivo"]):
            e.append(f"{dove}.motivo vuoto")
        if not url(p["fonte"]):
            e.append(f"{dove}.fonte deve essere un URL http(s)")

    esempi_ok = []
    for i, x in enumerate(r["esempi"]):
        dove = f"esempi[{i}]"
        if not campi(x, {"canale": str, "mittente": str, "testo": str, "truffa": bool}, dove):
            continue
        if x["canale"] not in CANALI_TESTO:
            e.append(f"{dove}.canale deve essere sms o whatsapp")
            continue
        if not stringa(x["testo"]):
            e.append(f"{dove}.testo vuoto")
        if x["truffa"]:
            if x.get("id_truffa") not in ids:
                e.append(f"{dove}.id_truffa mancante o inesistente: {x.get('id_truffa')}")
        elif "id_truffa" in x:
            e.append(f"{dove}: id_truffa solo se truffa e' true")
        esempi_ok.append(x)

    for t in truffe_ok:
        if CANALI_TESTO & set(t["canali"]):
            n = sum(1 for x in esempi_ok if x["truffa"] and x.get("id_truffa") == t["id"])
            if n < MIN_ESEMPI_TRUFFA:
                e.append(f"truffa {t['id']}: {n} esempi, ne servono almeno {MIN_ESEMPI_TRUFFA}")
    n = sum(1 for x in esempi_ok if not x["truffa"])
    if n < MIN_LEGITTIMI:
        e.append(f"esempi legittimi: {n}, ne servono almeno {MIN_LEGITTIMI}")

    if e:
        return e

    s = r["soglia"]
    for i, x in enumerate(r["esempi"]):
        tot, voci = punteggio(r, x["canale"], x["mittente"], x["testo"])
        if (tot >= s) != x["truffa"]:
            atteso = "truffa " + x["id_truffa"] if x["truffa"] else "legittimo"
            e.append(f"esempi[{i}] atteso {atteso}, punteggio {tot} (soglia {s}) "
                     f"[{', '.join(voci) or '-'}]: {x['testo'][:90]}")
    return e


def main():
    sys.stdout.reconfigure(errors="replace")
    if len(sys.argv) != 2:
        print("uso: python verifica.py regole.json")
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            r = json.load(f)
    except (OSError, json.JSONDecodeError) as x:
        print(f"errore lettura: {x}")
        print("FALLITO: 1 errori")
        return 1
    errori = controlla(r)
    for x in errori:
        print(x)
    if errori:
        print(f"FALLITO: {len(errori)} errori")
        return 1
    print(f"OK: {len(r['esempi'])} esempi, {len(r['truffe'])} truffe")
    return 0


if __name__ == "__main__":
    sys.exit(main())

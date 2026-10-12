#!/usr/bin/env python3
"""fiyatlar.db'yi CSV'lerden sıfırdan kurar. Kaynak CSV'lerdir; .db elle düzenlenmez.

    python3 db_kur.py            # yerler.csv + fiyatlar.csv + piyasa.csv -> fiyatlar.db

ozel/gozlem_ozel.csv varsa (depoya girmez) çekim saati ve fotoğraf adı gözleme eklenir; yoksa boş kalır.
"""
import csv
import os
import sqlite3
import sys

KOK = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(KOK, "fiyatlar.db")

SEMA = """
CREATE TABLE yer (
    kod     TEXT PRIMARY KEY,           -- IATA kodu ya da şehir mağazası kısaltması
    ad      TEXT NOT NULL,
    ulke    TEXT NOT NULL,
    tur     TEXT NOT NULL CHECK (tur IN ('duty-free', 'şehir mağazası')),
    magaza  TEXT,
    lat     REAL,
    lon     REAL
);
CREATE TABLE gozlem (
    id              INTEGER PRIMARY KEY,
    tarih           TEXT NOT NULL,      -- YYYY-AA-GG, çekildiği yerin saatiyle
    saat_yerel      TEXT,
    yer_kod         TEXT NOT NULL REFERENCES yer(kod),
    kategori        TEXT NOT NULL,
    marka           TEXT NOT NULL,
    urun            TEXT NOT NULL,
    yas             INTEGER,            -- boş = yaş beyansız
    hacim_ml        INTEGER,
    abv             REAL,
    para            TEXT NOT NULL,
    fiyat           REAL,               -- o gün tek şişe için ödenecek fiyat (indirim uygulanmış)
    fiyat_vergisiz  REAL,               -- yalnız Japonya şehir mağazası (本体)
    fiyat_ab_ici    REAL,               -- çift fiyatlı etikette AB içi varış fiyatı; fiyat = AB dışı
    liste_fiyat     REAL,               -- indirim öncesi / üretici önerilen fiyat
    indirim_yuzde   REAL,               -- o anki indirim: etikette yazan ya da liste fiyatından hesaplanan
    coklu_teklif    TEXT,               -- "2 şişe ..." türü kampanya
    kur_eur         REAL,
    fiyat_eur       REAL,
    eur_litre       REAL,
    kaynak          TEXT,               -- raf etiketi / fiş
    guven           TEXT NOT NULL CHECK (guven IN ('kesin', 'kısmi')),
    aciklama        TEXT,
    foto            TEXT
);
CREATE INDEX gozlem_urun ON gozlem (marka, urun);
CREATE INDEX gozlem_yer_tarih ON gozlem (yer_kod, tarih);
CREATE TABLE piyasa (
    id         INTEGER PRIMARY KEY,
    tarih      TEXT NOT NULL,
    urun       TEXT NOT NULL,
    pazar      TEXT NOT NULL,
    para       TEXT NOT NULL,
    fiyat_alt  REAL,
    fiyat_ust  REAL,
    aciklama   TEXT,
    kaynak     TEXT
);
"""

GOZLEM = ["id", "tarih", "saat_yerel", "yer_kod", "kategori", "marka", "urun", "yas", "hacim_ml", "abv", "para", "fiyat",
          "fiyat_vergisiz", "fiyat_ab_ici", "liste_fiyat", "indirim_yuzde", "coklu_teklif", "kur_eur", "fiyat_eur",
          "eur_litre", "kaynak", "guven", "not", "foto"]
OZEL = os.path.join("ozel", "gozlem_ozel.csv")


def oku(ad):
    with open(os.path.join(KOK, ad), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def bos(v):
    return None if v == "" else v


def main():
    if os.path.exists(DB):
        os.remove(DB)
    db = sqlite3.connect(DB)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SEMA)
    yerler, gozlemler, piyasa = oku("yerler.csv"), oku("fiyatlar.csv"), oku("piyasa.csv")
    ozel = {o["id"]: o for o in oku(OZEL)} if os.path.exists(os.path.join(KOK, OZEL)) else {}
    for g in gozlemler:
        o = ozel.get(g["id"], {})
        g["saat_yerel"], g["foto"] = o.get("saat_yerel", ""), o.get("foto", "")
        g["not"] = o.get("not_ozel") or g["not"]
    db.executemany("INSERT INTO yer VALUES (?,?,?,?,?,?,?)",
                   [[bos(y[k]) for k in ("kod", "ad", "ulke", "tur", "magaza", "lat", "lon")] for y in yerler])
    db.executemany(f"INSERT INTO gozlem VALUES ({','.join('?' * len(GOZLEM))})",
                   [[bos(g[k]) for k in GOZLEM] for g in gozlemler])
    db.executemany("INSERT INTO piyasa (tarih, urun, pazar, para, fiyat_alt, fiyat_ust, aciklama, kaynak) VALUES (?,?,?,?,?,?,?,?)",
                   [[bos(p[k]) for k in ("tarih", "urun", "pazar", "para", "fiyat_alt", "fiyat_ust", "not", "kaynak")] for p in piyasa])
    db.commit()
    sayim = {t: db.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("yer", "gozlem", "piyasa")}
    db.close()
    # "0 satır" başarı değildir: CSV'deki her satır tabloya girmiş olmalı
    beklenen = {"yer": len(yerler), "gozlem": len(gozlemler), "piyasa": len(piyasa)}
    if sayim != beklenen or not sayim["gozlem"]:
        sys.exit(f"HATA: tablo sayıları tutmuyor — beklenen {beklenen}, bulunan {sayim}")
    print(f"fiyatlar.db kuruldu: {sayim['gozlem']} gözlem · {sayim['yer']} yer · {sayim['piyasa']} piyasa referansı")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""fiyatlar.db'yi CSV'lerden sıfırdan kurar. Kaynak CSV'lerdir; .db elle düzenlenmez.

    python3 db_kur.py    # yerler + urunler + fiyatlar + piyasa + limitler + havalimanlari -> fiyatlar.db

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
    kod          TEXT PRIMARY KEY,      -- IATA kodu ya da şehir mağazası kısaltması
    ad           TEXT NOT NULL,
    ad_en        TEXT,
    ulke         TEXT NOT NULL,
    tur          TEXT NOT NULL CHECK (tur IN ('duty-free', 'şehir mağazası')),
    magaza       TEXT,
    katalog_url  TEXT,                  -- operatörün resmî çevrim içi kataloğu (açılıp doğrulanmış)
    lat          REAL,
    lon          REAL,
    arama        TEXT                   -- arama sözcükleri (şehir adı, yazım çeşitleri)
);
CREATE TABLE urun (
    urun_id          TEXT PRIMARY KEY,  -- gözlemler ürüne ada değil bu kimliğe bağlanır
    marka            TEXT NOT NULL,
    ad               TEXT NOT NULL,
    kategori         TEXT,
    yas              INTEGER,
    yalniz_dutyfree  TEXT,              -- 'evet' = yalnız duty-free'de satılan sürüm
    es_urun_id       TEXT,              -- varsa normal perakende karşılığı
    barkod           TEXT
);
CREATE TABLE gozlem (
    id              INTEGER PRIMARY KEY,
    tarih           TEXT NOT NULL,      -- YYYY-AA-GG, çekildiği yerin saatiyle
    saat_yerel      TEXT,
    yer_kod         TEXT NOT NULL REFERENCES yer(kod),
    magaza_yonu     TEXT CHECK (magaza_yonu IN ('kalkış', 'varış') OR magaza_yonu IS NULL),
    kategori        TEXT NOT NULL,
    urun_id         TEXT NOT NULL REFERENCES urun(urun_id),
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
    kur_try         REAL,               -- o gün 1 EUR kaç TL (ECB)
    fiyat_try       REAL,
    kaynak          TEXT,               -- raf etiketi / fiş
    guven           TEXT NOT NULL CHECK (guven IN ('kesin', 'kısmi')),
    aciklama        TEXT,
    foto            TEXT
);
CREATE INDEX gozlem_urun ON gozlem (urun_id);
CREATE INDEX gozlem_yer_tarih ON gozlem (yer_kod, tarih);
CREATE TABLE piyasa (
    id           INTEGER PRIMARY KEY,
    tarih        TEXT NOT NULL,
    ulke         TEXT,                  -- JP, EU, GB, FR ya da GLOBAL
    tur          TEXT,                  -- yerel (perakende) · öneri (liste fiyatı) · duty-free · müzayede
    urun_id      TEXT REFERENCES urun(urun_id),
    marka        TEXT,
    urun_anahtar TEXT,
    hacim_ml     INTEGER,
    urun         TEXT NOT NULL,
    pazar        TEXT NOT NULL,
    pazar_en     TEXT,
    para         TEXT NOT NULL,
    fiyat_alt    REAL,
    fiyat_ust    REAL,
    kur_eur      REAL,
    aciklama     TEXT,
    kaynak       TEXT
);
CREATE TABLE limitler (
    ulke           TEXT PRIMARY KEY,    -- ISO kodu ya da EU
    ozet_tr        TEXT NOT NULL,
    ozet_en        TEXT NOT NULL,
    kaynak         TEXT NOT NULL,       -- resmî sayfa
    kaynak_tarihi  TEXT,
    okunma_tarihi  TEXT NOT NULL
);
CREATE TABLE havalimani (
    iata   TEXT PRIMARY KEY,
    ad     TEXT NOT NULL,
    sehir  TEXT,
    ulke   TEXT,
    lat    REAL,
    lon    REAL
);
"""

YER = ["kod", "ad", "ad_en", "ulke", "tur", "magaza", "katalog_url", "lat", "lon", "arama"]
URUN = ["urun_id", "marka", "ad", "kategori", "yas", "yalniz_dutyfree", "es_urun_id", "barkod"]
GOZLEM = ["id", "tarih", "saat_yerel", "yer_kod", "magaza_yonu", "kategori", "urun_id", "marka", "urun", "yas", "hacim_ml", "abv",
          "para", "fiyat", "fiyat_vergisiz", "fiyat_ab_ici", "liste_fiyat", "indirim_yuzde", "coklu_teklif", "kur_eur", "fiyat_eur",
          "eur_litre", "kur_try", "fiyat_try", "kaynak", "guven", "not", "foto"]
PIYASA = ["tarih", "ulke", "tur", "urun_id", "marka", "urun_anahtar", "hacim_ml", "urun", "pazar", "pazar_en", "para", "fiyat_alt",
          "fiyat_ust", "kur_eur", "not", "kaynak"]
LIMIT = ["ulke", "ozet_tr", "ozet_en", "kaynak", "kaynak_tarihi", "okunma_tarihi"]
HAVALIMANI = ["iata", "ad", "sehir", "ulke", "lat", "lon"]
OZEL = os.path.join("ozel", "gozlem_ozel.csv")


def oku(ad):
    with open(os.path.join(KOK, ad), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def bos(v):
    return None if v == "" else v


def yaz(db, tablo, sutunlar, satirlar, kimlikli=False):
    yer = ",".join("?" * len(sutunlar))
    db.executemany(f"INSERT INTO {tablo} VALUES ({'NULL,' if kimlikli else ''}{yer})", [[bos(s[k]) for k in sutunlar] for s in satirlar])


def main():
    if os.path.exists(DB):
        os.remove(DB)
    db = sqlite3.connect(DB)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SEMA)
    veri = {"yer": oku("yerler.csv"), "urun": oku("urunler.csv"), "gozlem": oku("fiyatlar.csv"), "piyasa": oku("piyasa.csv"),
            "limitler": oku("limitler.csv"), "havalimani": oku("havalimanlari.csv")}
    ozel = {o["id"]: o for o in oku(OZEL)} if os.path.exists(os.path.join(KOK, OZEL)) else {}
    for g in veri["gozlem"]:
        o = ozel.get(g["id"], {})
        g["saat_yerel"], g["foto"] = o.get("saat_yerel", ""), o.get("foto", "")
        g["not"] = o.get("not_ozel") or g["not"]
    try:
        yaz(db, "yer", YER, veri["yer"])
        yaz(db, "urun", URUN, veri["urun"])
        yaz(db, "gozlem", GOZLEM, veri["gozlem"])
        yaz(db, "piyasa", PIYASA, veri["piyasa"], kimlikli=True)
        yaz(db, "limitler", LIMIT, veri["limitler"])
        yaz(db, "havalimani", HAVALIMANI, veri["havalimani"])
        db.commit()
    except sqlite3.IntegrityError as e:   # bilinmeyen yer_kod / urun_id, geçersiz yön ya da güven değeri
        sys.exit(f"HATA: veri tutarsız — {e}")
    sayim = {t: db.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in veri}
    kullanilmayan = db.execute("SELECT count(*) FROM urun WHERE urun_id NOT IN (SELECT urun_id FROM gozlem) "
                               "AND urun_id NOT IN (SELECT urun_id FROM piyasa WHERE urun_id IS NOT NULL)").fetchone()[0]
    db.close()
    # "0 satır" başarı değildir: CSV'deki her satır tabloya girmiş olmalı
    beklenen = {t: len(s) for t, s in veri.items()}
    if sayim != beklenen or not sayim["gozlem"]:
        sys.exit(f"HATA: tablo sayıları tutmuyor — beklenen {beklenen}, bulunan {sayim}")
    if kullanilmayan:
        sys.exit(f"HATA: urunler.csv'de hiçbir gözlem ya da piyasa satırına bağlı olmayan {kullanilmayan} ürün var")
    print(f"fiyatlar.db kuruldu: {sayim['gozlem']} gözlem · {sayim['urun']} ürün · {sayim['yer']} yer · {sayim['piyasa']} piyasa referansı · "
          f"{sayim['limitler']} limit · {sayim['havalimani']} havalimanı")


if __name__ == "__main__":
    main()

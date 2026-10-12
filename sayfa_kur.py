#!/usr/bin/env python3
"""Kişisel kıyas sayfasını üretir: sayfa_sablon.html + CSV'ler -> sayfa.html (veri içine gömülü, tek dosya).

    python3 sayfa_kur.py
"""
import csv
import json
import os
import sys
from datetime import date

KOK = os.path.dirname(os.path.abspath(__file__))
SAYI = {"yas", "hacim_ml", "abv", "fiyat", "fiyat_ab_ici", "liste_fiyat", "indirim_yuzde", "fiyat_eur", "eur_litre",
        "fiyat_alt", "fiyat_ust", "lat", "lon"}
# Sayfaya giren sütunlar. `foto` bilerek dışarıda: dosya adı sayfada işe yaramıyor.
GOZLEM = ["id", "tarih", "yer_kod", "kategori", "marka", "urun", "yas", "hacim_ml", "abv", "para", "fiyat", "fiyat_ab_ici",
          "liste_fiyat", "indirim_yuzde", "coklu_teklif", "fiyat_eur", "eur_litre", "kaynak", "guven", "not"]


def oku(ad, sutunlar=None):
    with open(os.path.join(KOK, ad), encoding="utf-8", newline="") as f:
        satirlar = list(csv.DictReader(f))
    return [{k: (float(v) if k in SAYI and v != "" else (None if v == "" else v))
             for k, v in s.items() if sutunlar is None or k in sutunlar} for s in satirlar]


def main():
    veri = {"uretim": date.today().isoformat(), "yerler": oku("yerler.csv"),
            "gozlem": oku("fiyatlar.csv", GOZLEM), "piyasa": oku("piyasa.csv")}
    if not veri["gozlem"]:
        sys.exit("HATA: fiyatlar.csv boş — sayfa üretilmedi")
    with open(os.path.join(KOK, "sayfa_sablon.html"), encoding="utf-8") as f:
        sablon = f.read()
    if "/*VERI*/" not in sablon:
        sys.exit("HATA: şablonda /*VERI*/ yer tutucusu yok")
    gomulu = json.dumps(veri, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    with open(os.path.join(KOK, "sayfa.html"), "w", encoding="utf-8") as f:
        f.write(sablon.replace("/*VERI*/", gomulu))
    print(f"sayfa.html üretildi: {len(veri['gozlem'])} gözlem · {len(veri['yerler'])} yer · {len(veri['piyasa'])} piyasa")


if __name__ == "__main__":
    main()

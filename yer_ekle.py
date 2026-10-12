#!/usr/bin/env python3
"""Yeni bir havalimanını yerler.csv'ye ekler; ad, ülke ve konum havalimanlari.csv'den gelir.

    python3 yer_ekle.py LHR                    # İngilizce adıyla ekler
    python3 yer_ekle.py LHR "Londra Heathrow"  # Türkçe adı da verilir
    python3 yer_ekle.py LHR --kuru             # yalnız gösterir, yazmaz
"""
import csv
import os
import sys

KOK = os.path.dirname(os.path.abspath(__file__))


def main():
    arg = [a for a in sys.argv[1:] if a != "--kuru"]
    if not arg:
        sys.exit(__doc__)
    kod = arg[0].upper()
    with open(os.path.join(KOK, "havalimanlari.csv"), encoding="utf-8", newline="") as f:
        h = next((x for x in csv.DictReader(f) if x["iata"] == kod), None)
    if not h:
        sys.exit(f"HATA: {kod} havalimanlari.csv'de yok")
    yol = os.path.join(KOK, "yerler.csv")
    with open(yol, encoding="utf-8", newline="") as f:
        okuyucu = csv.DictReader(f)
        sutunlar, yerler = okuyucu.fieldnames, list(okuyucu)
    if any(y["kod"] == kod for y in yerler):
        sys.exit(f"HATA: {kod} zaten yerler.csv'de")
    satir = dict.fromkeys(sutunlar, "")
    satir.update(kod=kod, ad=arg[1] if len(arg) > 1 else h["ad"], ad_en=h["ad"], ulke=h["ulke"], tur="duty-free",
                 lat=h["lat"], lon=h["lon"], arama=h["sehir"].lower())
    print(",".join(satir[s] for s in sutunlar))
    if "--kuru" in sys.argv:
        return
    with open(yol, "a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=sutunlar).writerow(satir)
    print(f"{kod} eklendi")


if __name__ == "__main__":
    main()

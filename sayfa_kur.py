#!/usr/bin/env python3
"""Kıyas sayfasını üretir: sayfa_sablon.html + CSV'ler -> veri içine gömülü tek dosya.

    python3 sayfa_kur.py      # sayfa.html (gövde parçası) + site/index.html (tam belge, yayın için)

CSV'lerdeki açıklamalar Türkçedir; sayfa çok dilli olduğu için ürün açıklaması ve kampanya metni
burada İngilizceye çevrilir (DE/ES arayüzü veri metninde İngilizceyi kullanır).
"""
import csv
import json
import os
import re
import sys
from datetime import date

KOK = os.path.dirname(os.path.abspath(__file__))
SAYI = {"yas", "hacim_ml", "abv", "fiyat", "fiyat_ab_ici", "liste_fiyat", "indirim_yuzde", "fiyat_eur", "eur_litre",
        "fiyat_try", "fiyat_alt", "fiyat_ust", "kur_eur"}
BELGE_BASI = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="Liquor prices read from duty-free shelf tags, compared between your departure and arrival airport.">
<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
"""
# Sayfaya giren sütunlar. `not` bilerek dışarıda: serbest Türkçe metin, çok dilli sayfada gösterilmiyor.
GOZLEM = ["id", "tarih", "yer_kod", "kategori", "marka", "urun", "yas", "hacim_ml", "abv", "para", "fiyat", "fiyat_ab_ici",
          "liste_fiyat", "indirim_yuzde", "coklu_teklif", "fiyat_eur", "eur_litre", "fiyat_try", "kaynak", "guven"]
YER = ["kod", "ad", "ad_en", "ulke", "tur", "arama"]
PIYASA = ["tarih", "ulke", "tur", "marka", "urun_anahtar", "hacim_ml", "pazar", "pazar_en", "para", "fiyat_alt", "fiyat_ust",
          "kur_eur", "kaynak"]

# Ürün adındaki Türkçe açıklamalar -> İngilizce (sıra önemli: uzun kalıp önce)
URUN_EN = [
    ("Bordeaux kırmızı 2023 / beyaz 2025", "Bordeaux red 2023 / white 2025"),
    ("(ürün adı kadrajda yok; Ballantine's rafı)", "(product name outside the frame; Ballantine's shelf)"),
    ("(olası; etiket adı kesik)", "(probable; name cut off on the tag)"),
    ("(ürün adı etikette okunmuyor; raftaki şişeler Teacher's)", "(name unreadable on the tag; bottles on the shelf are Teacher's)"),
    ("Giz ya da Pus (etiket hangi ürüne ait belirsiz)", "Giz or Pus (unclear which one the tag belongs to)"),
    ("çoklu paket (içerik önizlemede okunmuyor)", "multipack (contents unreadable)"),
    ("(yaş beyansız, 100th Anniversary etiketi)", "(no age statement, 100th Anniversary label)"),
    ("(yeşil etiket, yaş beyansız)", "(green label, no age statement)"),
    ("(teneke kutu, travel exclusive)", "(tin, travel exclusive)"),
    ("(şişede 'Aged 8' görünüyor)", "(bottle shows 'Aged 8')"),
    ("(duty-free'ye özel)", "(duty-free exclusive)"),
    ("(damıtımevine özel)", "(distillery exclusive)"),
    ("(yaş beyansız)", "(no age statement)"),
    ("(ikinci şişe)", "(second bottle)"),
    ("(pembe etiket)", "(pink label)"),
    ("(mini şişe)", "(mini bottle)"),
    ("(köpüklü)", "(sparkling)"),
    ("(kutulu)", "(boxed)"),
    ("(karton)", "(carton)"),
    ("(kutuda: ", "(on the box: "),
    ("(etiket: ", "(label: "),
    ("2 kadehli set", "gift set with 2 glasses"),
    ("(etiket adı kesik: ", "(name cut off on the tag: "),
    ("(etikette yalnız ", "(tag says only "),
    ("(ürün adı kesik: ", "(product name cut off: "),
    ("(kırmızı etiket; seri adı okunmuyor)", "(red label; series name unreadable)"),
    ("(bölge serisi; alt adı okunmuyor)", "(regional series; sub-name unreadable)"),
    ("(siyah etiket; alt adı okunmuyor)", "(black label; sub-name unreadable)"),
    ("(yeşil etiket; üzüm adı okunmuyor)", "(green label; grape unreadable)"),
    ("(kırmızı şeritli etiket; üzüm adı okunmuyor)", "(red-striped label; grape unreadable)"),
    ("(mor-mavi şeritli etiket; üzüm adı okunmuyor)", "(purple-blue striped label; grape unreadable)"),
    ("(üzüm adı okunmuyor)", "(grape unreadable)"),
    ("(kupaj adı okunmuyor)", "(blend name unreadable)"),
    ("; armut likörü; üretici okunmuyor)", "; pear liqueur; producer unreadable)"),
    ("Spritz hazır kokteyl (3×20 cl paket)", "Spritz ready-to-drink cocktail (3×20 cl pack)"),
    ("(İrlanda)", "(Ireland)"),
    ("(şeffaf)", "(clear)"),
    ("(siyah)", "(black)"),
    ("(şişe)", "(bottle)"),
]
TR_HARF = re.compile(r"[çğışöüÇĞİŞÖÜ]")
SERBEST = ("Rakı", "Kavaklıdere", "Gökçen", "Shōsetsu", "Vişne", "Buzbağ", "Şahsına", "Münhasır", "Boğazkere", "Karası",
           "Öküzgözü", "Sır", "Tuğra", "Tütsü")   # Türkçe harf taşıyan özel adlar


def urun_en(s):
    for tr, en in URUN_EN:
        s = s.replace(tr, en)
    return s


def teklif_en(s):
    if not s:
        return s
    if s == "2. ürüne %15, 3. ürüne %25 indirim":
        return "15% off the 2nd item, 25% off the 3rd"
    if s.startswith("bardak hediyeli (şişe boynunda "):
        return s.replace("bardak hediyeli (şişe boynunda ", "free glass included (neck tag: ")
    s = re.sub(r"\d[\d.,]*\d", lambda m: m.group().translate(str.maketrans(".,", ",.")), s)   # 17.920 -> 17,920 · 6,50 -> 6.50
    s = re.sub(r"\(şişesi ([\d.,]+)\)", r"(\1 each)", s)
    return s.replace("şişe", "bottles")


def oku(ad, sutunlar):
    with open(os.path.join(KOK, ad), encoding="utf-8", newline="") as f:
        satirlar = list(csv.DictReader(f))
    return [{k: (float(s[k]) if k in SAYI and s[k] != "" else (None if s[k] == "" else s[k])) for k in sutunlar} for s in satirlar]


def main():
    gozlem, yerler, piyasa = oku("fiyatlar.csv", GOZLEM), oku("yerler.csv", YER), oku("piyasa.csv", PIYASA)
    if not gozlem:
        sys.exit("HATA: fiyatlar.csv boş — sayfa üretilmedi")
    cevrilmemis = []
    for g in gozlem:
        g["urun_en"], g["teklif"], g["teklif_en"] = urun_en(g["urun"]), g.pop("coklu_teklif"), None
        g["teklif_en"] = teklif_en(g["teklif"])
        if g["marka"].startswith("("):
            cevrilmemis.append(f"id {g['id']} marka açıklama içeriyor (açıklama ürün adına yazılır): {g['marka']}")
        for alan in ("urun_en", "teklif_en"):
            kalan = g[alan] or ""
            for ad in SERBEST:
                kalan = kalan.replace(ad, "")
            if TR_HARF.search(kalan):
                cevrilmemis.append(f"id {g['id']} {alan}: {g[alan]}")
    if cevrilmemis:   # İngilizce sayfaya Türkçe açıklama sızmasın: yeni kalıp URUN_EN'e eklenir
        sys.exit("HATA: İngilizceye çevrilmemiş metin var:\n  " + "\n  ".join(cevrilmemis))
    for p in piyasa:
        k = p.pop("kur_eur")
        p["eur_alt"] = round(p["fiyat_alt"] / k, 2) if p["fiyat_alt"] is not None else None
        p["eur_ust"] = round(p["fiyat_ust"] / k, 2) if p["fiyat_ust"] is not None else None
        p["kaynak"] = (p["kaynak"] or "").split(" ; ")[0] or None
    veri = {"uretim": date.today().isoformat(), "yerler": yerler, "gozlem": gozlem, "piyasa": piyasa}
    with open(os.path.join(KOK, "sayfa_sablon.html"), encoding="utf-8") as f:
        sablon = f.read()
    if "/*VERI*/" not in sablon:
        sys.exit("HATA: şablonda /*VERI*/ yer tutucusu yok")
    sayfa = sablon.replace("/*VERI*/", json.dumps(veri, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
    with open(os.path.join(KOK, "sayfa.html"), "w", encoding="utf-8") as f:
        f.write(sayfa)
    # Yayın sürümü: şablonun <title>…</style> kısmı <head>'e, kalanı <body>'ye girer
    bas, ayrac, govde = sayfa.partition("</style>")
    if not ayrac:
        sys.exit("HATA: şablonda </style> yok — site/index.html üretilmedi")
    os.makedirs(os.path.join(KOK, "site"), exist_ok=True)
    with open(os.path.join(KOK, "site", "index.html"), "w", encoding="utf-8") as f:
        f.write(BELGE_BASI + bas + ayrac + "\n</head>\n<body>" + govde + "</body>\n</html>\n")
    print(f"sayfa.html + site/index.html üretildi: {len(gozlem)} gözlem · {len(yerler)} yer · {len(piyasa)} piyasa")


if __name__ == "__main__":
    main()

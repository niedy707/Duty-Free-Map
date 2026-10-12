#!/usr/bin/env python3
"""Siteye yüklenen fotoğrafların inceleme kuyruğu (Vercel Blob, özel depo).

    python3 yukleme.py liste                 # bekleyenleri göster
    python3 yukleme.py indir                 # bekleyenleri ozel/yuklenen/ altına indir (yayımlanmaz, depoya girmez)
    python3 yukleme.py isaretle <ad> [...]   # incelendi olarak işaretle (ad: 20261012T035109-ab12cd34ef56)
    python3 yukleme.py say                   # bekleyen sayısını depodan yeniden hesapla, durum.json'u yaz

Depo düzeni: bekleyen/<ad>.jpg + bekleyen/<ad>.json (yer, tarih, not) · islenen/<ad>.json (işaret) · durum.json (sayaç).
Hiçbir şey silinmez: bir yükleme, islenen/ altında işareti olunca kuyruktan düşer.

Vercel CLI gerekir (`vercel` oturumu açık). Depo anahtarı site/.env.local'dan okunur ve yalnız alt sürecin
ortamına verilir; ekrana, komut satırına ya da günlüğe yazılmaz. Dosya yoksa: `cd site && vercel env pull`.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

KOK = os.path.dirname(os.path.abspath(__file__))
ORTAM = os.path.join(KOK, "site", ".env.local")
HEDEF = os.path.join(KOK, "ozel", "yuklenen")
AD = re.compile(r"^\d{8}T\d{6}-[0-9a-f]{12}$")


def ortam():
    if not os.path.exists(ORTAM):
        sys.exit("HATA: site/.env.local yok — `cd site && vercel env pull` çalıştır")
    for satir in open(ORTAM, encoding="utf-8"):
        if satir.startswith("BLOB_READ_WRITE_TOKEN="):
            # Yalnız okuma-yazma anahtarı aktarılır; OIDC değişkeni aktarılırsa CLI ikisini birden görüp durur
            e = {k: v for k, v in os.environ.items() if k != "VERCEL_OIDC_TOKEN"}
            e["BLOB_READ_WRITE_TOKEN"] = satir.split("=", 1)[1].strip().strip('"')
            return e
    sys.exit("HATA: site/.env.local içinde BLOB_READ_WRITE_TOKEN yok — `cd site && vercel env pull` çalıştır")


def blob(*arg, girdi=None):
    # Boş bir klasörden çalıştırılır: CLI oradaki .env.local'ı okuyup OIDC ile karıştırmasın
    with tempfile.TemporaryDirectory() as bos:
        r = subprocess.run(["vercel", "blob", *arg], cwd=bos, env=ortam(), capture_output=True, text=True, input=girdi)
    if r.returncode != 0:
        sys.exit(f"HATA: vercel blob {arg[0]} başarısız (çıkış {r.returncode}): {(r.stderr or r.stdout).strip()[-300:]}")
    return r.stdout + r.stderr


def yollar(on_ek):
    cikti = blob("list", "--prefix", on_ek, "--limit", "1000")
    return sorted(set(re.findall(re.escape(on_ek) + r"[0-9T]+-[0-9a-f]{12}\.(?:jpg|json)", cikti)))


def bekleyenler():
    islenen = {os.path.basename(y)[:-5] for y in yollar("islenen/")}
    return [os.path.basename(y)[:-4] for y in yollar("bekleyen/") if y.endswith(".jpg") and os.path.basename(y)[:-4] not in islenen]


def koy(yol, icerik):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(icerik)
    try:
        blob("put", f.name, "--access", "private", "--pathname", yol, "--allow-overwrite", "true", "--content-type", "application/json",
             "--cache-control-max-age", "60")
    finally:
        os.unlink(f.name)


def say():
    n = len(bekleyenler())
    koy("durum.json", json.dumps({"bekleyen": n, "guncelleme": datetime.now(timezone.utc).isoformat()}))
    print(f"bekleyen: {n} (durum.json yazıldı)")


def bilgi(ad):
    with tempfile.TemporaryDirectory() as g:
        yol = os.path.join(g, "b.json")
        blob("get", f"bekleyen/{ad}.json", "--access", "private", "--output", yol)
        return json.load(open(yol, encoding="utf-8"))


def main():
    komut = sys.argv[1] if len(sys.argv) > 1 else ""
    if komut == "liste":
        b = bekleyenler()
        print(f"{len(b)} fotoğraf inceleme bekliyor")
        for ad in b:
            d = bilgi(ad)
            print(f"  {ad} · {d.get('tarih')} · {d.get('yer')} · {d.get('bayt')} bayt" + (f" · not: {d['not']}" if d.get("not") else ""))
    elif komut == "indir":
        os.makedirs(HEDEF, exist_ok=True)
        for ad in bekleyenler():
            for uz in ("jpg", "json"):
                hedef = os.path.join(HEDEF, f"{ad}.{uz}")
                if not os.path.exists(hedef):
                    blob("get", f"bekleyen/{ad}.{uz}", "--access", "private", "--output", hedef)
            print(f"  indirildi: ozel/yuklenen/{ad}.jpg")
    elif komut == "isaretle" and len(sys.argv) > 2:
        b = set(bekleyenler())
        for ad in sys.argv[2:]:
            if not AD.match(ad) or ad not in b:
                sys.exit(f"HATA: bekleyenler arasında böyle bir yükleme yok: {ad}")
            koy(f"islenen/{ad}.json", json.dumps({"islendi": datetime.now(timezone.utc).isoformat()}))
            print(f"  işaretlendi: {ad}")
        say()
    elif komut == "say":
        say()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()

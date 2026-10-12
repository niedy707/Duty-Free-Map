// POST /api/yukle?yer=…&tarih=YYYY-AA-GG&not=…   gövde: JPEG (tarayıcıda küçültülmüş)
// Fotoğraf yayımlanmaz; özel depoda "bekleyen/" altına düşer ve elle incelendikten sonra veriye işlenir.
import { randomBytes } from "node:crypto";
import { put } from "@vercel/blob";
import { BOYUT_SINIRI, GUNLUK_SINIR, KUYRUK_SINIRI, durumOku, durumYaz, sayacOku, sayacYaz, sayacYolu, yanit } from "./_ortak.js";

const temiz = (s, enCok) => String(s ?? "").replace(/[\u0000-\u001f\u007f<>]/g, " ").replace(/\s+/g, " ").trim().slice(0, enCok);

async function govdeOku(req) {
  const parcalar = [];
  let toplam = 0;
  for await (const p of req) {
    toplam += p.length;
    if (toplam > BOYUT_SINIRI) return null;
    parcalar.push(p);
  }
  return Buffer.concat(parcalar);
}

export default async function handler(req, res) {
  if (req.method !== "POST") { res.setHeader("Allow", "POST"); return yanit(res, 405, { hata: "method" }); }
  // Yalnız sitenin kendi sayfasından gelen istek: başka sitelerin bu ucu ziyaretçi adına çağırmasını engeller
  let kaynakHost = null;
  try { kaynakHost = new URL(req.headers.origin).host; } catch {}
  if (!kaynakHost || kaynakHost !== req.headers.host) return yanit(res, 403, { hata: "origin" });
  if (!String(req.headers["content-type"] || "").startsWith("image/jpeg")) return yanit(res, 415, { hata: "type" });
  if (Number(req.headers["content-length"] || 0) > BOYUT_SINIRI) return yanit(res, 413, { hata: "size" });

  const q = new URL(req.url, "http://x").searchParams;
  if (q.get("web")) return yanit(res, 200, { tamam: true });            // bal küpü: gizli alanı dolduran bot
  const yer = temiz(q.get("yer"), 60), tarih = String(q.get("tarih") || ""), not = temiz(q.get("not"), 300);
  const gun = /^\d{4}-\d{2}-\d{2}$/.test(tarih) ? Date.parse(tarih + "T00:00:00Z") : NaN;
  if (yer.length < 2 || Number.isNaN(gun) || gun < Date.parse("2015-01-01") || gun > Date.now() + 2 * 864e5) return yanit(res, 400, { hata: "fields" });

  const sayac = sayacYolu(req), bugun = await sayacOku(sayac);
  if (bugun >= GUNLUK_SINIR) return yanit(res, 429, { hata: "rate" });

  const govde = await govdeOku(req);
  if (!govde) return yanit(res, 413, { hata: "size" });
  if (govde.length < 2000 || govde[0] !== 0xff || govde[1] !== 0xd8 || govde[2] !== 0xff) return yanit(res, 415, { hata: "type" });

  const durum = await durumOku();
  if (durum.bekleyen >= KUYRUK_SINIRI) return yanit(res, 429, { hata: "full" });

  const ad = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) + "-" + randomBytes(6).toString("hex");
  const secenek = { access: "private", addRandomSuffix: false, allowOverwrite: false };
  await put(`bekleyen/${ad}.jpg`, govde, { ...secenek, contentType: "image/jpeg" });
  await put(`bekleyen/${ad}.json`, JSON.stringify({ yer, tarih, not, alindi: new Date().toISOString(), bayt: govde.length }), { ...secenek, contentType: "application/json" });
  await durumYaz(durum.bekleyen + 1);
  await sayacYaz(sayac, bugun + 1);
  return yanit(res, 200, { tamam: true });
}

// Yükleme kuyruğunun ortak parçaları. Depo özel erişimlidir: hiçbir blob adresi dışarı verilmez.
import { createHash } from "node:crypto";
import { get, put } from "@vercel/blob";

export const DURUM = "durum.json";
export const KUYRUK_SINIRI = 100;          // bekleyen fotoğraf bu sayıya ulaşınca yeni yükleme alınmaz (en kötü durumda ~400 MB)
export const BOYUT_SINIRI = 4_000_000;     // bayt; Vercel işlev gövdesi sınırı 4,5 MB
export const GUNLUK_SINIR = 10;            // aynı kaynaktan bir günde kabul edilen yükleme

export async function durumOku() {
  const r = await get(DURUM, { access: "private", useCache: false });
  if (!r || r.statusCode !== 200) return { bekleyen: 0, guncelleme: null };
  const d = JSON.parse(await new Response(r.stream).text());
  return { bekleyen: Number.isInteger(d.bekleyen) && d.bekleyen >= 0 ? d.bekleyen : 0, guncelleme: d.guncelleme ?? null };
}

// Kaynağın günlük sayaç yolu. IP saklanmaz: gün ve depo anahtarıyla tuzlanmış özeti tutulur, ertesi gün eşleştirilemez.
export function sayacYolu(req) {
  const ip = String(req.headers["x-real-ip"] || req.headers["x-forwarded-for"] || "").split(",")[0].trim() || "bilinmiyor";
  const gun = new Date().toISOString().slice(0, 10), tuz = (process.env.BLOB_READ_WRITE_TOKEN || "").slice(-24);
  return `sinir/${gun}/${createHash("sha256").update(`${ip}|${gun}|${tuz}`).digest("hex").slice(0, 20)}.json`;
}

export async function sayacOku(yol) {
  const r = await get(yol, { access: "private", useCache: false });
  if (!r || r.statusCode !== 200) return 0;
  const n = JSON.parse(await new Response(r.stream).text()).n;
  return Number.isInteger(n) && n > 0 ? n : 0;
}

export async function sayacYaz(yol, n) {
  await put(yol, JSON.stringify({ n }), { access: "private", addRandomSuffix: false, allowOverwrite: true, contentType: "application/json" });
}

export async function durumYaz(bekleyen) {
  await put(DURUM, JSON.stringify({ bekleyen, guncelleme: new Date().toISOString() }),
    { access: "private", addRandomSuffix: false, allowOverwrite: true, contentType: "application/json", cacheControlMaxAge: 60 });
}

export function yanit(res, kod, govde) {
  res.statusCode = kod;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.end(JSON.stringify(govde));
}

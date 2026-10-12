// Yükleme kuyruğunun ortak parçaları. Depo özel erişimlidir: hiçbir blob adresi dışarı verilmez.
import { get, put } from "@vercel/blob";

export const DURUM = "durum.json";
export const KUYRUK_SINIRI = 100;          // bekleyen fotoğraf bu sayıya ulaşınca yeni yükleme alınmaz (en kötü durumda ~400 MB)
export const BOYUT_SINIRI = 4_000_000;     // bayt; Vercel işlev gövdesi sınırı 4,5 MB

export async function durumOku() {
  const r = await get(DURUM, { access: "private", useCache: false });
  if (!r || r.statusCode !== 200) return { bekleyen: 0, guncelleme: null };
  const d = JSON.parse(await new Response(r.stream).text());
  return { bekleyen: Number.isInteger(d.bekleyen) && d.bekleyen >= 0 ? d.bekleyen : 0, guncelleme: d.guncelleme ?? null };
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

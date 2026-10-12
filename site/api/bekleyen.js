// GET /api/bekleyen → {"bekleyen": n}   İncelenmeyi bekleyen yükleme sayısı (yalnız sayı; dosya adı ya da adres yok).
import { durumOku, yanit } from "./_ortak.js";

export default async function handler(req, res) {
  if (req.method !== "GET") { res.setHeader("Allow", "GET"); return yanit(res, 405, { hata: "method" }); }
  const d = await durumOku();
  return yanit(res, 200, { bekleyen: d.bekleyen, guncelleme: d.guncelleme });
}

# Duty-Free-Map

Havalimanı duty-free mağazalarında **raf etiketinden okunmuş** içki fiyatları ve bunları
havalimanları arasında kıyaslamak için küçük bir araç.

**Site:** https://duty-free-map.vercel.app — arayüz İngilizce (varsayılan), Almanca, İspanyolca, Türkçe.

Asıl soru: *kalkış havalimanında mı almalı, varışta mı?* Aynı şişe iki havalimanında farklı
fiyata satılıyor; varışta ucuz olan ürünü kalkışta almak mantıksız. Bu depo o kıyasın verisini
ve tek dosyalık bir kıyas sayfasını üretir.

Sitede:

- **Rota:** uçuş kodu (ör. `TK199`) ya da havalimanı adı yazılır, kalkış ve varış otomatik seçilir.
  İki havalimanında da görülen ürünler kıyaslanır; yalnız birinde görülenler ayrı listelenir.
  Bir yerde aynı ürünün birden çok kaydı varsa hepsi tarihiyle gösterilir.
- **Yerel piyasa:** kalkış ve varış ülkesi için varsa mağaza dışı perakende fiyatı ve şehir
  mağazası gözlemleri, duty-free fiyatının yanında.
- **Bir ürün, tüm yerler:** bir ürünün hangi havalimanında hangi tarihte kaça görüldüğü.
- Her fiyat avro karşılığıyla, varsa yerel para birimiyle ve o günkü kurla TL karşılığıyla gösterilir.

Uçuş kodundan rota bulmak için ziyaretçinin tarayıcısı `api.adsbdb.com`'a yalnız uçuş kodunu gönderir.

Veriler raf fotoğraflarıyla büyür. Ne kadar güncel fotoğraf eklenirse o kadar çok kişi
faydalanabilir. Sitedeki formdan herkes raf etiketi fotoğrafı yükleyebilir.

## Fotoğraf yükleme ve inceleme

Yüklenen fotoğraf **hiçbir zaman yayımlanmaz**; yalnız fiyatları okunup veriye eklenir.

1. Tarayıcı fotoğrafı JPEG'e çevirip en çok 3000 piksele küçültür (konum dahil EXIF bilgisi bu sırada
   düşer) ve `POST /api/yukle`'ye gönderir. Yükleyen, havalimanını/mağazayı ve tarihi formda yazar.
2. Uç yalnız sitenin kendi sayfasından gelen JPEG'i kabul eder (4 MB sınırı, alan denetimi, bekleyen
   100'e ulaşınca yeni yükleme almaz) ve dosyayı **özel erişimli** Vercel Blob deposunda `bekleyen/`
   altına koyar. Depo adresleri dışarıdan açılmaz, hiçbir yanıtta dönmez.
3. `GET /api/bekleyen` yalnız bekleyen sayısını verir; bakımcıya bildirim bu sayıdan üretilir.
4. Bakımcı `python3 yukleme.py liste | indir | isaretle <ad>` ile kuyruğu inceler, fiyatları
   `fiyatlar.csv`'ye işler, siteyi yeniden dağıtır. İncelenen yükleme silinmez, `islenen/` altına
   işaret konur.

Bilinen eksik: IP başına hız sınırı yok; kötüye kullanıma karşı tek fren kuyruk sınırıdır.

## Dosyalar

| Dosya | İçerik |
|---|---|
| `fiyatlar.csv` | **Kaynak.** Okunan her fiyat bir satır |
| `yerler.csv` | **Kaynak.** Havalimanı / mağaza listesi (IATA kodu, Türkçe ve İngilizce ad, ülke, mağaza, konum, arama sözcükleri) |
| `piyasa.csv` | **Kaynak.** Mağaza dışı referans fiyatlar: ülke, tür (`yerel` · `öneri` · `duty-free` · `müzayede`), `fiyatlar.csv` ile eşleşen marka + ürün anahtarı, fiyat aralığı, kur, kaynak adresi |
| `db_kur.py` | Üç CSV'den SQLite `fiyatlar.db`'yi kurar (`yer`, `gozlem`, `piyasa` tabloları) |
| `site/api/` | Vercel işlevleri: `yukle.js` (fotoğraf kabul), `bekleyen.js` (sayaç), `_ortak.js` |
| `yukleme.py` | Yükleme kuyruğunu inceleme aracı (Vercel CLI üzerinden) |
| `sayfa_kur.py`, `sayfa_sablon.html` | Tek dosyalık kıyas sayfasını üretir (veri içine gömülü): `site/index.html` yayın sürümü. CSV'deki Türkçe açıklamaları İngilizceye çevirir; çevrilmemiş metin kalırsa durur |

```bash
python3 db_kur.py      # fiyatlar.db
python3 sayfa_kur.py   # site/index.html — tarayıcıda açılır, sunucu gerekmez
```

Yalnız Python 3 standart kitaplığı kullanılır. `fiyatlar.db`, `sayfa.html` ve `site/` türetilmiştir, depoya girmez.

## `fiyatlar.csv` sütunları

| Sütun | Anlamı |
|---|---|
| `id` | Artan sıra numarası |
| `tarih` | Fiyatın görüldüğü gün (çekildiği yerin tarihiyle) |
| `yer_kod`, `yer`, `ulke`, `magaza`, `magaza_turu` | `yerler.csv`'deki kayıt; `duty-free` ya da `şehir mağazası` |
| `kategori` | viski · konyak · rom · rakı · likör · şarap · şampanya · bira · sigara |
| `marka`, `urun`, `yas` | `yas` boşsa yaş beyansız |
| `hacim_ml`, `abv` | Etikette ya da şişede okunabiliyorsa; okunamıyorsa **boş** |
| `para`, `fiyat` | O gün tek şişe için kasada ödenecek fiyat (indirim uygulanmış). Şehir mağazasında vergi dahil |
| `fiyat_vergisiz` | Yalnız Japonya şehir mağazası: etiketteki `本体` (vergisiz) fiyat |
| `fiyat_ab_ici` | Çift fiyatlı etikette AB içi varış fiyatı; `fiyat` o durumda AB dışı varış fiyatıdır |
| `liste_fiyat` | Üstü çizili eski fiyat ya da üretici önerilen fiyatı |
| `indirim_yuzde` | O anki indirim: etikette yazan ("Save 15%") ya da liste fiyatından hesaplanan |
| `coklu_teklif` | "2 şişe …", "2. ürüne %15" türü kampanya |
| `kur_eur`, `fiyat_eur`, `eur_litre` | O günkü ECB kuruyla avro karşılığı ve litre fiyatı |
| `kur_try`, `fiyat_try` | O gün 1 avronun TL karşılığı (ECB) ve fiyatın TL karşılığı |
| `kaynak` | `raf etiketi` · `fiş` · `raf etiketi + fiş` |
| `guven` | `kesin` ya da `kısmi` (etiket kesik/örtülü, düşük çözünürlükten okundu, ürün adı görünmüyor) |
| `not` | Açıklama |

Okuma kuralı: kesik etiket tahminle tamamlanmaz. Ürün adı ya da fiyatın bir hanesi görünmüyorsa
satır `kısmi` yazılır ve neyin eksik olduğu `not`'a girer.

## Kapsam (12.10.2026 itibarıyla 147 gözlem)

| Kod | Yer | Gözlem | Tarihler |
|---|---|---|---|
| ECN | Ercan Havalimanı — Kaner Duty Free | 36 | 18.06.2022 · 03.06.2023 · 13.06.2024 |
| IST | İstanbul Havalimanı | 28 | 18.06.2022 · 05.10.2026 |
| SAW | Sabiha Gökçen Havalimanı | 20 | 05.09.2022 · 13.06.2024 |
| HND | Tokyo Haneda Havalimanı | 14 | 12.10.2026 |
| CPH | Kopenhag — Heinemann Tax Free | 3 | 18.09.2024 |
| STR | Stuttgart | 3 | 29.11.2024 |
| CRL | Brüksel Güney Charleroi | 2 | 09.09.2022 |
| FCO | Roma Fiumicino | 2 | 25.10.2023 |
| ARN | Stockholm Arlanda | 2 | 19.09.2024 |
| TYO-GNZ1 | Tokyo Ginza — içki mağazası (şehir, kıyas için) | 13 | 11.10.2026 |
| TYO-GNZ2 | Tokyo Ginza — koleksiyon viski mağazası (şehir, kıyas için) | 24 | 11.10.2026 |

Fiyatlar görüldüğü günün raf fiyatıdır; bugün farklı olabilir. Bu depo bir satış ya da tanıtım
kanalı değildir, yalnız fiyat kaydıdır.

## Ön tarama (12.10.2026)

Yalnız web tarandı, üç site açılıp okundu; GitHub'da benzer depo aranmadı.

| Site | Ne yapıyor | Fark |
|---|---|---|
| dutyfreeradar.com | 10 havalimanı (Haneda dahil), İngilizce; fiyatları mağazaların çevrim içi listelerinden haftalık topluyor | Raf fotoğrafı yok, İstanbul yok |
| dutyfreecheck.com | Türkçe, ~37 lokasyon (İstanbul, Sabiha Gökçen dahil); ana sayfada yalnız kozmetik/parfüm | İçki görünmüyor |
| dutyfreecompare.com | Kore'deki üç duty-free zincirini kıyaslayan uygulamanın destek sayfası | Farklı pazar |

**Karar:** sıfırdan, bağımlılıksız yazıldı. Fark: veri raftaki etiketten (çevrim içi listeden
değil) ve kalkış ↔ varış kıyası birinci sınıf özellik.

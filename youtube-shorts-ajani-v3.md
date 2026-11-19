# Haber Videosundan YouTube Shorts Üretim Ajanı (v3)

Serbest Atış tarzı yatay haber programlarından (sunucu solda, haber görseli sağda) 9:16 Shorts üretir. v2'nin yerine geçer. v3, v2 incelemesinde bulunan hataları ve doküman tutarsızlıklarını giderir; yerleşim kuralları (720×1280, üstte sunucu, altta haber paneli) değişmedi.

## 1. v2'den v3'e neler değişti

| Konu | v2 | v3 |
|---|---|---|
| İndirme | Hep `ham_video.mp4`; dosya varsa yt-dlp atlıyor, ikinci linkte eski video kullanılıyordu | Dosya adı video kimliğinden (`<id>.mp4`), `--force-overwrites` |
| Argümanlar | Yalnızca `--baslangic` verilince çöküyor, yalnızca `--bitis` sessizce yok sayılıyordu | İkisi birlikte zorunlu, bitiş > başlangıç, dosya/anahtar kontrolü |
| Kesim oturtma | En yakın sessizlik (±5 sn); 0,25 sn'lik duraklar çoğu zaman cümle ortası | Önce Whisper cümle sınırı, sessizlik yalnızca ±0,6 sn ince ayar. Elle aralıkta ±2 sn |
| Sessizlik yoksa | `min()` boş listede çöküyordu | Çökmez; cümle sınırında bırakır |
| `silencedetect` ayrıştırma | Negatif `silence_start` kaçıyordu, pencere sonunda süren sessizlik düşüyordu | İkisi de işleniyor |
| Gemini çıktısı | Doğrulanmıyordu | Süre 115–145 sn ve transkript aralığı kontrolü, 3 denemeye kadar yeniden sorma. Model `--gemini-model` ile değişir |
| Boş / Türkçe kelime | Boş kelimede IndexError; `lower()` "Iıı"yı kaçırıyordu | Boş kelimeler atılıyor, Türkçe küçük harf dönüşümü |
| Duvar rengi | 3 tek piksel; biri sağ kenarda (koyu, mikrofonlu) | Yalnızca sol duvardan küçük bölgenin ortalaması; isteğe bağlı bulanık arka plan |
| Font yolu | Çalışma dizinine göre `fonts` | Betiğin yanındaki `fonts`; Windows yolu için kaçış |
| Kaynak çözünürlüğü | 1920×1080 varsayılıyordu | Kırpma koordinatları gerçek çözünürlüğe orantılanıyor; indirme ≤1080p tercih ediyor |
| Kadraj kontrolü | Yok | Kesit boyunca sunucu bölgesi örnekleniyor, farklı görünen saniyeler uyarı olarak yazılıyor |
| Süre kontrolü | Yok | Oturtmadan sonra 120–140 sn dışındaysa uyarı |
| Whisper | Sabit `large-v3`, CPU | `--whisper-model`, `--cihaz cuda` |

Korunanlar: `yt-dlp`, `faster-whisper`, Gemini ile kesit seçimi, tek FFmpeg komutu, sese dokunmama kuralı.

## 2. Standart yerleşim (720×1280)

Kaynak 1920×1080. Sol panel sunucu, sağ panel haber.

- **Üst alan, 760 px:** Sunucu paneli (`x 0–676`, `y 39–1001`, 676×962) kırpılmadan 760 px yüksekliğe **küçültülür** (×0,79, genişlik 534 px) ve ortalanır. Alttaki koyu şerit (sosyal medya ikonları) atılır. Yanlarda yaklaşık 93 px boşluk kalır; varsayılan olarak sol duvardan örneklenen düz renkle, `--arka-plan bulanik` ile sunucunun bulanık kopyasıyla dolar.
- **Alt alan, 520 px:** Haber paneli (`x 682–1920`, 1238×1080) 720 px genişliğe küçültülür (×0,58, yükseklik 628 px), üstten hizalanır ve **alttan 108 px (çıktı pikseli, panelin yaklaşık %17'si; kaynakta ~186 px) kırpılır**. Sağda ve solda siyah boşluk kalmaz.
- **Yazı:** Varsayılan olarak yeni yazı yok. Kaynaktaki logo ve haber görsellerinin içindeki yazılar olduğu gibi kalır.
- **Çıktı:** MP4, H.264, AAC, 30 fps, 720×1280, yaklaşık 2:10.

Altyazı açıkken: haber alanının üstündeki koyu gri bandın ortasında (`y = 800`), beyaz kalın Inter 32, siyah kenarlık, en fazla iki satır. "eee, ııı" gibi dolgular altyazıdan çıkarılır, sesten çıkarılmaz.

Denge ayarı: `UST_H` küçülürse haber alanı büyür, alttan daha az kırpılır; ama sunucunun yanlarındaki boşluk artar. Örneğin `UST_H=700, ALT_H=580` alttan kırpmayı 48 px'e indirir, yan boşluğu ~114 px'e çıkarır.

## 3. Akış

1. **İndir:** `yt-dlp`, ≤1080p MP4, dosya adı `<video id>.mp4`.
2. **Transkript:** Önce klasörde o yayına ait hazır YouTube transkripti (`levent-GG-AA-YYYY-YT.txt`) aranır; varsa `--transkript` ile verilir ve Whisper hiç çalışmaz (render ~10 sn). Yoksa `faster-whisper` (varsayılan `large-v3`, CPU'da `medium` önerilir), Türkçe, kelime zamanlı, VAD açık; `--transkript-yaz` ile cümle listesi dosyaya yazılır. Elle aralık verildi ve altyazı istenmediyse transkript hiç gerekmez.
3. **Kesit seçimi (Claude yapar, API anahtarı gerekmez):** Ajan transkripti kendisi okur ve aralığı seçer, sonra betiği `--baslangic`/`--bitis` ile çalıştırır. Ölçütler bölüm 3.1'de. Gemini yolu (`GEMINI_API_KEY` ile otomatik seçim) betikte yedek olarak duruyor ama varsayılan değil.

### 3.1 Kesit seçimi ölçütleri (Claude)

Kullanıcı aralık verdiyse seçim yapılmaz, o aralık kullanılır. Vermediyse:

- **Süre:** Hedef 125–135 sn. 115–145 sn dışı kabul edilmez.
- **Bütünlük:** Kesit bir cümlenin başında başlar, bir cümlenin sonunda biter. Bir konu açılıp kapanmalı; "bu arada", "şimdi şuna geçelim" gibi geçişlerde başlamaz, konuyu yarıda bırakmaz.
- **Kendi içinde anlaşılır:** Programın başını izlemeyen biri anlamalı. "Dediğim gibi", "o konu" gibi önceki kısma gönderme yapan cümleyle başlamaz.
- **Çarpıcılık:** Türkiye gündemi için en paylaşılabilir kısım: somut iddia, isim, rakam, net bir yorum ya da sert bir cümle. Selamlama, reklam, kanal duyurusu, yayın sonu kapanışı ve canlı yayın sorularını okuma kısımları seçilmez.
- **Görüntü:** Haber paneli sağda olan, sunucu-solda düzenindeki kısım. Tam ekran video oynatılan bölümlerden kaçınılır (betiğin kadraj uyarısı bunu yakalar).
- **Zaman damgaları:** YouTube transkriptinde zaman yalnızca satır başında var. Başlangıç olarak cümlenin başladığı satırın zamanı, bitiş olarak cümlenin bittiği satırdan bir sonraki satırın zamanı alınır. Betik ±2 sn içinde sessizliğe oturtur.
- **Rapor:** Seçilen aralık (dk:sn ve saniye), tek cümlelik gerekçe ve varsa 1–2 alternatif aralık kullanıcıya yazılır.
4. **Kesim noktalarını oturtma:** Transkript varsa önce en yakın cümle sınırına çekilir; FFmpeg `silencedetect` (−32 dB, 0,25 sn) yalnızca ±0,6 sn içinde ince ayar yapar: başlangıç konuşmadan 0,12 sn önce, bitiş konuşmadan 0,35 sn sonra. Elle aralıkta (transkript yok) ±2 sn içindeki en yakın sessizlik kullanılır. Sessizlik bulunamazsa zaman olduğu gibi kalır.
5. **Kontroller:** Süre 120–140 sn dışındaysa ve sunucu kadrajı kesit boyunca farklı görünüyorsa (tam ekran video, farklı plan) uyarı yazılır; üretim durmaz.
6. **Altyazı (isteğe bağlı):** Whisper kelime zamanlarından ya da `--transkript` dosyasından ASS dosyası. Hazır transkriptte kelime zamanı olmadığı için satır içindeki kelimeler harf sayısına göre dağıtılır; zamanlama yaklaşıktır.
7. **Render:** Tek FFmpeg komutu, sesin başında ve sonunda çok kısa fade.

## 4. Kurulum ve kullanım (Windows)

```bash
pip install yt-dlp faster-whisper google-genai pillow
```

FFmpeg ve ffprobe PATH'te olmalı; altyazı için FFmpeg'in `libass` destekli (ör. "full" build) olması gerekir. yt-dlp YouTube tarafında sık değişir, güncel tut (`pip install -U yt-dlp`). Altyazı için Inter fontunu betiğin yanındaki `fonts` klasörüne koy (`fonts\Inter-Bold.otf`).

```bash
# Önerilen (API'siz): hazır transkriptle, Claude'un seçtiği aralık, altyazılı — Whisper çalışmaz
python shorts_ajani.py ham_video.mp4 --baslangic 275.4 --bitis 405.4 --altyazi --transkript levent-19-11-2026-YT.txt

# Hazır transkript yoksa: önce Whisper transkriptini yaz, Claude okuyup aralığı seçsin
python shorts_ajani.py ham_video.mp4 --transkript-yaz ham_video.txt --whisper-model medium

# Elle aralık ver (saniye, ikisi birlikte), altyazılı (Whisper ile)
python shorts_ajani.py ham_video.mp4 --baslangic 275.4 --bitis 405.4 --altyazi

# Yedek: Gemini kesiti seçsin (API anahtarı gerekir)
set GEMINI_API_KEY=...
python shorts_ajani.py "https://youtube.com/watch?v=..." --cikti shorts.mp4

# Yan boşluk bulanık sunucuyla dolsun
python shorts_ajani.py ham_video.mp4 --baslangic 275.4 --bitis 405.4 --arka-plan bulanik

# NVIDIA GPU varsa / CPU'da hızlı model
python shorts_ajani.py "https://..." --cihaz cuda
python shorts_ajani.py "https://..." --whisper-model medium
```

## 5. Kod (`shorts_ajani.py`)

Sentetik 1920×1080 ve 1280×720 videolarla denendi: kesim oturtma (elle aralık, cümle sınırlı, sessizliksiz kaynak), `silencedetect` ayrıştırma, kadraj kontrolü (tam ekran farklı plan 20–25 sn arası doğru işaretlendi), duvar rengi örnekleme, ASS üretimi ve 720×1280 render (renk ve bulanık mod, altyazılı). **Çalıştırılmayanlar:** yt-dlp indirme, Whisper ve Gemini adımları (ortamda ağ/model yok) ve Windows yol kaçışı (`ff_kac`) Linux'ta denendi, Windows'ta ilk çalıştırmada kontrol et.

```python
#!/usr/bin/env python3
"""Serbest Atış tarzı yatay haber videosundan 9:16 YouTube Shorts üretir (v3).

Kullanım:
  python shorts_ajani.py "https://youtube.com/watch?v=..."                 # indir + Gemini kesit + render (API anahtarı gerekir)
  python shorts_ajani.py ham.mp4 --transkript-yaz ham.txt                   # sadece Whisper transkripti; kesiti Claude seçer
  python shorts_ajani.py ham.mp4 --baslangic 275.4 --bitis 405.4 --altyazi --transkript levent-GG-AA-YYYY-YT.txt  # Whisper'sız
  python shorts_ajani.py ham.mp4 --baslangic 275.4 --bitis 405.4            # elle aralık (Whisper gerekmez)
  python shorts_ajani.py ham.mp4 --baslangic 275.4 --bitis 405.4 --altyazi   # altyazı bandı da ekle
  python shorts_ajani.py ham.mp4 --arka-plan bulanik                         # yan boşluk: düz renk yerine bulanık sunucu
"""
import argparse, json, os, re, subprocess, sys, tempfile, statistics

# ---------- AYARLAR (yerleşim kuralları; koordinatlar 1920x1080 kaynağa göre) ----------
BASE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE, "fonts")     # Inter-Bold.otf buraya konur (betiğin yanında)
REF_W, REF_H = 1920, 1080                  # koordinatların ait olduğu kaynak çözünürlüğü
CIKTI_W, CIKTI_H = 720, 1280
UST_H, ALT_H = 760, 520                    # sunucu alanı + haber alanı = 1280
SUNUCU_KIRP = (0, 39, 676, 962)            # x, y, w, h  (alttaki koyu şerit atılır)
HABER_KIRP = (682, 0, 1238, 1080)          # sağdaki haber paneli
DUVAR_ORNEK = (10, 180, 80, 420)           # duvar rengi örneklenen sol bölge: x1, y1, x2, y2
SESSIZLIK_DB, SESSIZLIK_SN = "-32dB", 0.25
HEDEF_SURE = 130                           # saniye, ±5
SURE_MIN, SURE_MAX = 115, 145              # Gemini yanıtı için kabul aralığı; dışı reddedilir
UYARI_MIN, UYARI_MAX = 120, 140            # oturtmadan sonra bunun dışındaysa uyarı verilir
ALTYAZI_Y = 800                            # haber alanının üstündeki koyu bandın ortası
ALTYAZI_FONT, ALTYAZI_PUNTO = "Inter", 32
DOLGU = {"ıı", "ııı", "ıııı", "ee", "eee", "eeee", "hmm", "mm"}   # sadece altyazıdan çıkarılır, sesten değil
VARSAYILAN_RENK = "0xF1F0DE"


def calistir(cmd):
    # Windows'ta varsayılan cp1254; ffmpeg çıktısındaki UTF-8 dosya adları çökmesin
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)


def tr_kucuk(s):
    """Türkçe küçük harf: Python'un lower()'ı 'I' -> 'i' yapar, burada 'I' -> 'ı'."""
    return s.replace("I", "ı").replace("İ", "i").lower()


def ff_kac(p):
    """ffmpeg filtre argümanı için yol: ters eğik çizgi -> /, iki nokta -> \\: (Windows sürücü harfi)."""
    return os.path.abspath(p).replace("\\", "/").replace(":", r"\:")


# ---------- KAYNAK ÖLÇÜSÜ ----------
def video_boyut(video):
    p = calistir(["ffprobe", "-v", "error", "-select_streams", "v:0",
                  "-show_entries", "stream=width,height", "-of", "csv=p=0", video])
    w, h = p.stdout.strip().split(",")[:2]
    return int(w), int(h)


def olcekle(kirp, w, h):
    """Koordinatlar 1920x1080'e göre; kaynak farklı çözünürlükteyse orantıla."""
    x, y, cw, ch = kirp
    sx, sy = w / REF_W, h / REF_H
    return tuple(int(round(v)) for v in (x * sx, y * sy, cw * sx, ch * sy))


# ---------- 1. İNDİR ----------
def indir(url):
    """Dosya adı video kimliğinden gelir; her linke ayrı dosya, eski dosya yeniden kullanılmaz."""
    p = subprocess.run(["yt-dlp", "-f", "bv*+ba/b", "-S", "res:1080,ext:mp4:m4a",
                        "--merge-output-format", "mp4", "--force-overwrites",
                        "-o", "%(id)s.%(ext)s", "--print", "after_move:filepath", url],
                       stdout=subprocess.PIPE, text=True, check=True)
    return p.stdout.strip().splitlines()[-1]


# ---------- 2. TRANSKRİPT (kelime zamanlı) ----------
def transkript(video, model="large-v3", cihaz="cpu"):
    from faster_whisper import WhisperModel
    tur = "float16" if cihaz == "cuda" else "int8"
    m = WhisperModel(model, device=cihaz, compute_type=tur)
    segs, _ = m.transcribe(video, language="tr", word_timestamps=True, vad_filter=True)
    kelimeler = []
    for s in segs:
        for w in (s.words or []):
            t = w.word.strip()
            if t:                                   # boş kelimeler atılır
                kelimeler.append({"w": t, "s": w.start, "e": w.end})
    return kelimeler


def transkript_dosyadan(yol):
    """YouTube'dan kopyalanan transkript (ör. '8:228 dakika 22 saniyeKusura bakmayın...').
    Yalnızca satır başı zamanı var; kelime zamanları satır içinde harf sayısına göre dağıtılır (yaklaşık)."""
    desen = re.compile(r"^(?:(\d+):)?(\d+):(\d{2})(?:\d+ saat ?)?(?:\d+ dakika ?)?(?:\d+ saniye)?(.*)$")
    satirlar = []
    with open(yol, encoding="utf-8-sig") as f:
        for l in f:
            m = desen.match(l.strip())
            if not m or not m.group(4).strip():
                continue
            sa, dk, sn = int(m.group(1) or 0), int(m.group(2)), int(m.group(3))
            satirlar.append((sa * 3600 + dk * 60 + sn, m.group(4).strip()))
    if not satirlar:
        raise ValueError(f"Transkriptte zaman damgalı satır bulunamadı: {yol}")
    kelimeler = []
    for i, (s, metin) in enumerate(satirlar):
        e = satirlar[i + 1][0] if i + 1 < len(satirlar) else s + 6
        ws = metin.split()
        toplam = sum(len(w) + 1 for w in ws)
        t = float(s)
        for w in ws:
            d = (e - s) * (len(w) + 1) / toplam
            kelimeler.append({"w": w, "s": t, "e": t + d * 0.9})
            t += d
    return kelimeler


def cumlelere_bol(kelimeler):
    """Noktalama / uzun duraktan cümle listesi: [{s, e, t}]"""
    cumleler, cur = [], []
    for i, k in enumerate(kelimeler):
        cur.append(k)
        son = k["w"][-1] in ".?!"
        durak = i + 1 < len(kelimeler) and kelimeler[i + 1]["s"] - k["e"] > 0.6
        if son or durak:
            cumleler.append({"s": cur[0]["s"], "e": cur[-1]["e"], "t": " ".join(x["w"] for x in cur)})
            cur = []
    if cur:
        cumleler.append({"s": cur[0]["s"], "e": cur[-1]["e"], "t": " ".join(x["w"] for x in cur)})
    return cumleler


# ---------- 3. KESİT SEÇİMİ (Gemini, doğrulamalı) ----------
def kesit_sec(cumleler, api_key, model="gemini-2.5-flash", deneme=3):
    from google import genai
    from google.genai import types
    metin = "\n".join(f"[{c['s']:.1f}-{c['e']:.1f}] {c['t']}" for c in cumleler)
    prompt = f"""Aşağıda bir Türkçe haber/yorum programının cümle bazlı transkripti var.
Türkiye gündemi için en çarpıcı, paylaşılabilir, kendi içinde anlaşılır ve bütün olan
yaklaşık {HEDEF_SURE} saniyelik ({HEDEF_SURE-5}-{HEDEF_SURE+5} sn) TEK bir kesit seç.
Kesit bir cümlenin başında başlasın, bir cümlenin sonunda bitsin; konuyu yarıda bırakma.
Sadece JSON dön: {{"baslangic": 275.4, "bitis": 405.4, "gerekce": "tek cümle"}}

{metin}"""
    t0, t1 = cumleler[0]["s"], cumleler[-1]["e"]
    istemci = genai.Client(api_key=api_key)
    ek = ""
    for _ in range(deneme):
        r = istemci.models.generate_content(
            model=model, contents=prompt + ek,
            config=types.GenerateContentConfig(response_mime_type="application/json"))
        try:
            sec = json.loads(r.text)
            b, e = float(sec["baslangic"]), float(sec["bitis"])
        except Exception:
            ek = "\n\nÖnceki yanıt geçerli JSON değildi. Yalnızca istenen JSON'u dön."
            continue
        if t0 - 1 <= b < e <= t1 + 1 and SURE_MIN <= e - b <= SURE_MAX:
            sec["baslangic"], sec["bitis"] = b, e
            return sec
        ek = (f"\n\nÖnceki yanıt ({b}-{e}) kurala uymadı: süre {HEDEF_SURE-5}-{HEDEF_SURE+5} sn olmalı "
              f"ve zamanlar transkript aralığında ({t0:.0f}-{t1:.0f}) kalmalı.")
    raise RuntimeError(f"Gemini {deneme} denemede geçerli kesit döndürmedi; --baslangic/--bitis ile elle ver.")


# ---------- 4. KESİM NOKTALARINI KONUŞMAYA OTURT ----------
def sessizlikler(video, bas, sure):
    """[(baslangic, bitis)] kaynak videonun saniyesiyle. Pencere sonunda süren sessizlik de listeye girer."""
    cmd = ["ffmpeg", "-v", "info", "-ss", f"{bas:.3f}", "-t", f"{sure:.3f}", "-i", video, "-vn",
           "-af", f"silencedetect=n={SESSIZLIK_DB}:d={SESSIZLIK_SN}", "-f", "null", "-"]
    p = calistir(cmd)
    sil, cur = [], None
    for l in p.stderr.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", l)       # ffmpeg bazen küçük negatif yazar
        if m:
            cur = max(float(m.group(1)), 0.0) + bas
            continue
        m = re.search(r"silence_end: (-?[\d.]+)", l)
        if m and cur is not None:
            sil.append((cur, float(m.group(1)) + bas))
            cur = None
    if cur is not None:
        sil.append((cur, bas + sure))
    return sil


def oturt(video, bas, bit, cumleler=None):
    """Kesim noktalarını konuşmaya oturtur.
    Transkript varsa: önce en yakın CÜMLE sınırına çeker, sessizliği yalnızca ±0,6 sn'lik ince ayar için kullanır
    (0,25 sn'lik duraklar sık sık virgül/nefes olduğu için tek başına cümle sınırı garantisi vermez).
    Transkript yoksa (elle aralık): kişinin verdiği zamanın ±2 sn'sindeki en yakın sessizliğe çeker.
    Sessizlik bulunamazsa çökmez, zamanı olduğu gibi (cümle sınırıyla) bırakır."""
    pencere = 0.6 if cumleler else 2.0
    if cumleler:
        bas = min(cumleler, key=lambda c: abs(c["s"] - bas))["s"]
        bit = min(cumleler, key=lambda c: abs(c["e"] - bit))["e"]
    sil = sessizlikler(video, max(bas - 3, 0), (bit - bas) + 6)

    ad = [s for s in sil if abs(s[1] - bas) <= pencere]          # başlangıç: sessizliğin SONU konuşma başlangıcı
    if ad:
        s0, s1 = min(ad, key=lambda x: abs(x[1] - bas))
        yeni_bas = max(s0 + 0.05, s1 - 0.12)
    else:
        yeni_bas = max(bas - 0.12, 0) if cumleler else bas

    bd = [s for s in sil if abs(s[0] - bit) <= pencere]          # bitiş: sessizliğin BAŞI konuşma bitişi
    if bd:
        b0, b1 = min(bd, key=lambda x: abs(x[0] - bit))
        yeni_bit = b0 + min(0.35, (b1 - b0) * 0.8)
    else:
        yeni_bit = bit + 0.2 if cumleler else bit

    if yeni_bit - yeni_bas < 10:
        raise ValueError(f"Kesim aralığı çok kısa: {yeni_bas:.2f} -> {yeni_bit:.2f}")
    return round(yeni_bas, 2), round(yeni_bit, 2)


# ---------- 5. ALTYAZI (ASS) ----------
def dolgu_mu(w):
    return tr_kucuk(w).strip(".,!?…") in DOLGU


def ass_yaz(kelimeler, bas, bit, yol):
    ws = [k for k in kelimeler if k["s"] >= bas - 0.05 and k["e"] <= bit + 0.05 and not dolgu_mu(k["w"])]
    parcalar, cur = [], []
    for k in ws:
        cur.append(k)
        uz = sum(len(x["w"]) + 1 for x in cur)
        if (k["w"][-1] in ".?!" and len(cur) >= 3) or uz >= 48 or (k["w"][-1] == "," and uz >= 34):
            parcalar.append(cur); cur = []
    if cur: parcalar.append(cur)

    def sar(c):
        t = [x["w"] for x in c]; d = " ".join(t)
        if len(d) <= 30 or len(t) < 2: return d
        en = min(range(1, len(t)), key=lambda i: max(len(" ".join(t[:i])), len(" ".join(t[i:]))))
        return " ".join(t[:en]) + "\\N" + " ".join(t[en:])

    def zt(t):
        t = max(t, 0); return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"

    sure = bit - bas
    ev = []
    for i, c in enumerate(parcalar):
        s, e = c[0]["s"] - bas, c[-1]["e"] - bas
        nxt = parcalar[i + 1][0]["s"] - bas if i + 1 < len(parcalar) else sure
        e = nxt if nxt - e < 0.5 else e + 0.15
        ev.append(f"Dialogue: 0,{zt(s)},{zt(min(e, sure))},Cap,,0,0,0,,{{\\an5\\pos({CIKTI_W//2},{ALTYAZI_Y})}}{sar(c)}")
    baslik = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {CIKTI_W}
PlayResY: {CIKTI_H}
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Cap,{ALTYAZI_FONT},{ALTYAZI_PUNTO},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2.5,0,5,20,20,10,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    with open(yol, "w", encoding="utf-8") as f:
        f.write(baslik + "\n".join(ev) + "\n")


# ---------- 6. ARKA PLAN RENGİ + KADRAJ KONTROLÜ + RENDER ----------
def arka_plan_rengi(video, an, w, h):
    """Duvar rengi: yalnızca sol duvardan küçük bir bölgenin ortalaması (sağ kenar koyu/mikrofonlu, örneklenmez)."""
    from PIL import Image
    try:
        with tempfile.TemporaryDirectory() as d:
            png = os.path.join(d, "kare.png")
            calistir(["ffmpeg", "-v", "error", "-y", "-ss", str(an), "-i", video, "-frames:v", "1", png])
            with Image.open(png) as im0:
                im = im0.convert("RGB")
        sx, sy = im.width / REF_W, im.height / REF_H
        x1, y1, x2, y2 = DUVAR_ORNEK
        kutu = (int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy))
        r, g, b = im.crop(kutu).resize((1, 1), Image.BOX).getpixel((0, 0))
        return f"0x{r:02X}{g:02X}{b:02X}"
    except Exception as ex:
        print(f"Uyarı: duvar rengi örneklenemedi ({ex}); varsayılan renk kullanılıyor.", file=sys.stderr)
        return VARSAYILAN_RENK


def kadraj_kontrol(video, bas, bit, w, h, n=10, esik=45):
    """Kesit boyunca n kare örnekler; sunucu bölgesi medyandan çok farklıysa (tam ekran video, farklı plan)
    o saniyeleri döndürür. Yalnızca uyarı için; üretimi durdurmaz."""
    sx, sy, sw, sh = olcekle(SUNUCU_KIRP, w, h)
    sure = bit - bas
    vf = f"fps={n}/{sure:.3f},crop={sw}:{sh}:{sx}:{sy},scale=32:18,format=gray"
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{bas:.3f}", "-t", f"{sure:.3f}", "-i", video,
                        "-vf", vf, "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    ham, boy = p.stdout, 32 * 18
    kareler = [ham[i:i + boy] for i in range(0, len(ham) - boy + 1, boy)]
    if len(kareler) < 3:
        return []
    med = [statistics.median(k[j] for k in kareler) for j in range(boy)]
    sonuc = []
    for i, k in enumerate(kareler):
        fark = sum(abs(k[j] - med[j]) for j in range(boy)) / boy
        if fark > esik:
            sonuc.append(round(bas + i * sure / n, 1))
    return sonuc


def render(video, bas, bit, cikti, ass=None, renk=VARSAYILAN_RENK, mod="renk"):
    w, h = video_boyut(video)
    sx, sy, sw, sh = olcekle(SUNUCU_KIRP, w, h)
    hx, hy, hw, hh = olcekle(HABER_KIRP, w, h)
    sunucu = f"[a]crop={sw}:{sh}:{sx}:{sy},"
    if mod == "bulanik":
        sunucu += (f"split=2[s1][s2];"
                   f"[s2]scale={CIKTI_W}:{UST_H}:force_original_aspect_ratio=increase,crop={CIKTI_W}:{UST_H},boxblur=25:3[bg];"
                   f"[s1]scale=-2:{UST_H}:flags=lanczos[fg];"
                   f"[bg][fg]overlay=(W-w)/2:0[top];")
    else:
        sunucu += (f"scale=-2:{UST_H}:flags=lanczos,"
                   f"pad={CIKTI_W}:{UST_H}:(ow-iw)/2:0:color={renk}[top];")
    f = (f"[0:v]split=2[a][b];{sunucu}"
         f"[b]crop={hw}:{hh}:{hx}:{hy},scale={CIKTI_W}:-2:flags=lanczos,crop={CIKTI_W}:{ALT_H}:0:0[bot];"
         f"[top][bot]vstack,setsar=1,fps=30")
    if ass:
        f += f",ass='{ff_kac(ass)}'"
        if os.path.isdir(FONT_DIR):
            f += f":fontsdir='{ff_kac(FONT_DIR)}'"
        else:
            print(f"Uyarı: {FONT_DIR} yok; altyazı sistem fontuyla çizilecek (Inter-Bold.otf'yi oraya koy).",
                  file=sys.stderr)
    sure = bit - bas
    f += f"[v];[0:a]afade=t=in:d=0.03,afade=t=out:st={sure-0.05:.2f}:d=0.05[aa]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{bas:.3f}", "-t", f"{sure:.2f}", "-i", video,
                    "-filter_complex", f, "-map", "[v]", "-map", "[aa]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", cikti],
                   check=True)


def main():
    ap = argparse.ArgumentParser(description="Yatay haber videosundan 9:16 Shorts üretir")
    ap.add_argument("kaynak", help="YouTube linki veya yerel mp4")
    ap.add_argument("--baslangic", type=float, help="saniye; --bitis ile birlikte verilmeli")
    ap.add_argument("--bitis", type=float, help="saniye; --baslangic ile birlikte verilmeli")
    ap.add_argument("--altyazi", action="store_true")
    ap.add_argument("--arka-plan", choices=["renk", "bulanik"], default="renk",
                    help="sunucunun yanındaki boşluk: duvar rengi (varsayılan) veya bulanık sunucu")
    ap.add_argument("--cikti", default="shorts.mp4")
    ap.add_argument("--transkript", help="hazır YouTube transkripti (.txt); verilirse Whisper çalışmaz")
    ap.add_argument("--transkript-yaz", metavar="TXT",
                    help="Whisper cümlelerini '[bas-bit] metin' olarak bu dosyaya yaz ve dur (kesiti Claude seçsin)")
    ap.add_argument("--gemini-key", default=os.environ.get("GEMINI_API_KEY"))
    ap.add_argument("--gemini-model", default=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"))
    ap.add_argument("--whisper-model", default="large-v3", help="CPU'da yavaşsa medium / small dene")
    ap.add_argument("--cihaz", choices=["cpu", "cuda"], default="cpu", help="NVIDIA GPU varsa cuda")
    a = ap.parse_args()

    if (a.baslangic is None) != (a.bitis is None):
        ap.error("--baslangic ve --bitis birlikte verilmeli")
    if a.baslangic is not None and a.bitis <= a.baslangic:
        ap.error("--bitis, --baslangic'tan büyük olmalı")
    if a.baslangic is None and not a.gemini_key and not a.transkript_yaz:
        ap.error("Kesit için --baslangic/--bitis ver (Claude seçer); transkript lazımsa --transkript-yaz kullan. "
                 "Gemini ile otomatik seçim için GEMINI_API_KEY gerekir")
    if not a.kaynak.startswith("http") and not os.path.isfile(a.kaynak):
        ap.error(f"Dosya bulunamadı: {a.kaynak}")

    if a.transkript and not os.path.isfile(a.transkript):
        ap.error(f"Transkript bulunamadı: {a.transkript}")
    elle = a.baslangic is not None
    video = indir(a.kaynak) if a.kaynak.startswith("http") else a.kaynak
    if a.transkript:
        kelimeler = transkript_dosyadan(a.transkript)   # Whisper çalışmaz
    else:
        kelimeler = transkript(video, a.whisper_model, a.cihaz) if (a.baslangic is None or a.altyazi) else None
    cumleler = cumlelere_bol(kelimeler) if kelimeler else None
    if a.transkript_yaz:
        if cumleler is None:
            cumleler = cumlelere_bol(transkript(video, a.whisper_model, a.cihaz))
        with open(a.transkript_yaz, "w", encoding="utf-8") as f:
            f.write("\n".join(f"[{c['s']:.1f}-{c['e']:.1f}] {c['t']}" for c in cumleler) + "\n")
        print(f"Transkript yazıldı: {a.transkript_yaz} ({len(cumleler)} cümle, video: {video})")
        return
    if a.baslangic is None:
        sec = kesit_sec(cumleler, a.gemini_key, a.gemini_model)
        print("Gemini:", sec)
        a.baslangic, a.bitis = sec["baslangic"], sec["bitis"]

    # Dosya transkriptinde cümle sınırları yaklaşık: elle verilen aralığı cümleye çekme, sadece sessizliğe oturt
    bas, bit = oturt(video, a.baslangic, a.bitis, None if (a.transkript and elle) else cumleler)
    sure = bit - bas
    print(f"Kesim: {bas} -> {bit}  ({sure:.1f} sn)")
    if not UYARI_MIN <= sure <= UYARI_MAX:
        print(f"Uyarı: süre {sure:.1f} sn, hedef {UYARI_MIN}-{UYARI_MAX} sn dışında.", file=sys.stderr)

    w, h = video_boyut(video)
    if (w, h) != (REF_W, REF_H):
        print(f"Not: kaynak {w}x{h}; kırpma koordinatları {REF_W}x{REF_H}'ya göre orantılandı.")
    sapma = kadraj_kontrol(video, bas, bit, w, h)
    if sapma:
        print(f"Uyarı: sunucu kadrajı şu saniyelerde farklı görünüyor (tam ekran video / farklı plan olabilir): "
              f"{sapma}. Çıktıyı bu yerlerde elle kontrol et.", file=sys.stderr)

    ass = None
    if a.altyazi:
        ass = os.path.splitext(a.cikti)[0] + ".ass"
        ass_yaz(kelimeler, bas, bit, ass)
    renk = arka_plan_rengi(video, bas + 3, w, h) if a.arka_plan == "renk" else VARSAYILAN_RENK
    render(video, bas, bit, a.cikti, ass, renk, a.arka_plan)
    print("Hazır:", a.cikti)


if __name__ == "__main__":
    main()
```

## 6. Bilinen sınırlar

- **Üstteki bant her karede yok.** Bazı haber görsellerinde (gazete sayfası, tam ekran fotoğraf) koyu bant olmuyor; altyazı görselin üstüne biniyor. Siyah kenarlık sayesinde okunuyor ama görselin tepesini kapatıyor.
- **Alttan kırpma.** Haber alanı alttan 108 px (panelin ~%17'si) kesildiği için görsellerin alt kenarı (ör. alıntı kutusunun alt çizgisi, bazı tweetlerin alt kısmı, "SERBEST ATIŞ" etiketi) görünmüyor. `UST_H`/`ALT_H` ile denge ayarlanabilir (bölüm 2).
- **Omuzlar kenara değmiyor.** Sunucu küçültüldüğü için yanlarda yaklaşık 93 px boşluk kalıyor. Daha fazla büyütmek saçın üstünü kırpar.
- **Birleşme izi.** Düz renk modunda panelin sağ kenarı koyu ve mikrofonlu olduğu için sunucu ile dolgu arasında hafif iz görülebilir. v3 rengi yalnızca sol duvardan aldığı için eskisinden daha az belirgin olmalı; olursa `--arka-plan bulanik` dene. Bulanık modun gerçek yayında nasıl göründüğü henüz denenmedi.
- **Kadraj kontrolü yalnızca uyarır.** Tam ekran video ya da farklı stüdyo planı çıkarsa üretimi durdurmaz, saniyeleri yazar; o kesitte kadrajı elle kontrol et. Eşik (`esik=45`) gerçek yayında ayarlanmalı.
- **Altyazı metni Whisper'dan çıktığı gibi.** Özel isimler (Fatma Betül, Taha Çakmak gibi) yanlış çıkabilir; yayından önce bir kez gözden geçirmek gerekir.
- **Kesit seçimi öneri.** Claude'un (ya da Gemini'nin) seçtiği kesit sunucunun ağzından çıkan en çarpıcı kısım olmayabilir; `--baslangic` / `--bitis` ile elle değiştirmek her zaman mümkün.
- **Hazır transkriptte zamanlama yaklaşık.** YouTube transkriptinde yalnızca satır başı zamanı var; altyazı 1–2 sn kayabilir, yazım hataları (ör. "söylü terörist" → "terörsüz") olduğu gibi gelir.
- **Git Bash'ten Türkçe dosya adı.** `PYTHONUTF8=1 python shorts_ajani.py ...` şeklinde çalıştır; yoksa dosya adı bozuk iletilir.
- **Whisper CPU'da yavaş.** Uzun programda `large-v3` + CPU saatler sürebilir; GPU yoksa `--whisper-model medium` dene.
- **Yalnızca bu program düzeni için.** Yerleşim sayıları (`SUNUCU_KIRP`, `HABER_KIRP`, `DUVAR_ORNEK`) başka bir programın şablonunda yeniden ayarlanmalı.

# YouTube Shorts Şablonu

Sunucunun solda, haber görselinin sağda durduğu yatay (16:9) haber/yorum programlarından 720×1280 dikey YouTube Shorts üretir. Sunucu üstte, haber paneli altta yer alır, altyazı her zaman eklenir. Tek seferde birden fazla Shorts çıkarılabilir. Ses kesilmez, hızlandırılmaz.

```
┌──────────────┬───────────────────┐          ┌───────────┐
│              │                   │          │  sunucu   │
│   sunucu     │   haber görseli   │   ──▶    │           │
│              │                   │          ├───────────┤
└──────────────┴───────────────────┘          │  altyazı  │
          1920×1080                           │   haber   │
                                              └───────────┘
                                                720×1280
```

## Klasör

| Dosya | Ne işe yarar |
|---|---|
| `shorts_ajani.py` | Tüm işi yapan betik: indirme, transkript, kesimi konuşmaya oturtma, altyazı, tek FFmpeg komutuyla render |
| `youtube-shorts-ajani-v3.md` | Tasarım belgesi: yerleşim ölçüleri, akış, kesit seçim ölçütleri, bilinen sınırlar |
| `.claude/agents/leventin-cirag.md` | Claude Code ajanı: transkripti okur, kesiti seçer, betiği çalıştırır, sonucu denetler |
| `fonts/Inter-Bold.otf` | Altyazı fontu |
| `LICENSES/Inter-OFL.txt` | Inter fontunun lisansı (SIL OFL 1.1) |

Videolar, transkriptler ve altyazı dosyaları `.gitignore` ile depo dışında tutulur.

## Kurulum (Windows)

```bash
pip install yt-dlp faster-whisper pillow
```

- FFmpeg ve ffprobe PATH'te olmalı. Altyazı için `libass` destekli bir sürüm gerekir (ör. "full" build).
- `google-genai` yalnızca Gemini ile otomatik kesit seçimi kullanılacaksa gerekir; varsayılan akışta gerekmez.

## Kullanım

### Claude Code ile (önerilen)

1. Yayın videosunu (`.mp4`) ve varsa YouTube'dan kopyalanmış transkriptini (`levent-GG-AA-YYYY-YT.txt`) bu klasöre koy.
2. Claude Code'da klasörü aç ve iste:
   - `bu videodan 2 dakikalık shorts çıkar`
   - `3 shorts çıkar` → birbiriyle çakışmayan, ayrı konulardan 3 altyazılı Shorts
   - `08:08 ile 08:44 arasını yap`
   - `altyazıyı düzelt ve yeniden çıkar`

Kesitleri Claude seçer; API anahtarı gerekmez. Dosyalar `levent-shorts-GG-AA-YYYY-<sıra>-<konu>.mp4` adıyla çıkar. Seçim ölçütleri `youtube-shorts-ajani-v3.md` bölüm 3.1'de.

### Betiği doğrudan çalıştırma

Git Bash'te Türkçe dosya adları için `PYTHONUTF8=1` ile çalıştır.

```bash
# Hazır transkriptle, elle aralık (saniye) — altyazılı, Whisper çalışmaz, birkaç saniye sürer
PYTHONUTF8=1 python shorts_ajani.py video.mp4 --baslangic 315.5 --bitis 449.5 --transkript levent-19-11-2026-YT.txt

# Hazır transkript yoksa: Whisper ile bir kez transkript çıkar, sonra her kesitte o dosyayı ver
PYTHONUTF8=1 python shorts_ajani.py video.mp4 --transkript-yaz video.txt --whisper-model medium
PYTHONUTF8=1 python shorts_ajani.py video.mp4 --baslangic 315.5 --bitis 449.5 --transkript video.txt

# Elle düzeltilmiş altyazıyla yeniden render
PYTHONUTF8=1 python shorts_ajani.py video.mp4 --baslangic 315.5 --bitis 449.5 --ass shorts.ass --cikti shorts.mp4
```

| Seçenek | Açıklama |
|---|---|
| `--baslangic`, `--bitis` | Kesit aralığı, saniye cinsinden (ikisi birlikte) |
| `--altyazisiz` | Altyazısız çıkar (altyazı varsayılan olarak açık) |
| `--transkript <txt>` | Hazır transkripti kullan, Whisper'ı atla (YouTube kopyası ya da `--transkript-yaz` çıktısı) |
| `--ass <dosya>` | Elle düzeltilmiş altyazı dosyasını yeniden üretmeden kullan |
| `--transkript-yaz <txt>` | Whisper transkriptini dosyaya yaz ve dur |
| `--cikti <ad>.mp4` | Çıktı dosyasının adı |
| `--arka-plan bulanik` | Sunucunun yanındaki boşluğu düz renk yerine bulanık görüntüyle doldur |
| `--whisper-model medium` | GPU yoksa `large-v3` yerine daha hızlı model |
| `--cihaz cuda` | NVIDIA GPU varsa |

Kaynak olarak YouTube linki de verilebilir; betik `yt-dlp` ile indirir.

## Bilmen gerekenler

- **Hazır transkriptte altyazı zamanlaması yaklaşıktır.** YouTube transkriptinde yalnızca satır başı zamanı var; altyazı 1–2 sn kayabilir. Yazım hataları (özel isimler, "kayım" → "kayyum" gibi) olduğu gibi gelir, yayından önce `.ass` dosyasını gözden geçir.
- **Whisper CPU'da yavaştır.** GPU yoksa `large-v3` uzun bir programda saatler sürebilir; hazır transkript kullan ya da `--whisper-model medium` seç.
- **Yalnızca bu program düzeni için.** Kırpma koordinatları (`SUNUCU_KIRP`, `HABER_KIRP`, `DUVAR_ORNEK`) başka bir programın şablonu için `shorts_ajani.py` içinde yeniden ayarlanmalı.
- **`fonts` klasörüne font dışında dosya koyma.** FFmpeg oradaki her dosyayı font olarak yüklemeye çalışır.

Ayrıntılar ve diğer sınırlar için `youtube-shorts-ajani-v3.md` bölüm 6'ya bak.

## Lisans

Betik, ajan ve belgeler MIT lisansıyla dağıtılır, bkz. `LICENSE`. Inter fontu bu lisansa dahil değildir; SIL Open Font License 1.1 ile dağıtılır, bkz. `LICENSES/Inter-OFL.txt`.

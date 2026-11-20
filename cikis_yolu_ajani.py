#!/usr/bin/env python3
"""Çıkış Yolu (Levent Kenez solda, Ekrem Dumanlı sağda) yatay videosundan 9:16 YouTube Shorts üretir.

Yerleşim (720x1280): üstte Levent, ortada gri altyazı bandı (iki satır), altta Ekrem.
Transkript, kesim oturtma ve altyazı üretimi shorts_ajani.py'den gelir; burada yalnızca yerleşim ve render farklıdır.

Kullanım:
  python cikis_yolu_ajani.py video.mp4 --baslangic 19 --bitis 150 --transkript yayin.txt --cikti ad.mp4
  python cikis_yolu_ajani.py video.mp4 --baslangic 19 --bitis 150 --ass duzeltilmis.ass --cikti ad.mp4   # düzeltilmiş altyazıyla yeniden render
"""
import argparse, os, subprocess, sys

import shorts_ajani as S

# ---------- YERLEŞİM (koordinatlar 1920x1080 kaynağa göre) ----------
LEVENT_KIRP = (0, 30, 950, 765)            # x, y, w, h  (alttaki isim bandı ve kayan yazı atılır)
EKREM_KIRP = (965, 30, 950, 765)
PANEL_H = 580                               # her konuşmacı alanı
BAND_H = S.CIKTI_H - 2 * PANEL_H            # 120: ortadaki gri altyazı bandı
BAND_RENK = "0x4A4A4A"
ALTYAZI_PUNTO = 36

S.SUNUCU_KIRP = LEVENT_KIRP                 # kadraj_kontrol Levent alanına bakar
S.ALTYAZI_Y = PANEL_H + BAND_H // 2         # altyazı bandın ortasında
S.ALTYAZI_PUNTO = ALTYAZI_PUNTO


# İsim/logo rozetleri: dosya adı -> (köşe, panel). Ölçek, kaynaktaki 950 px'lik kırpımın 720'ye küçülme oranıdır.
ROZET_OLCEK = S.CIKTI_W / 950
ROZETLER = [                                # (dosya, x, y) ; x/y: "sol"/"sag" ve çıktı piksel konumu
    ("levent-isim.png", "sol", "alt", PANEL_H),                    # Levent panelinin sol alt köşesi
    ("ekrem-isim.png", "sol", "alt", S.CIKTI_H),                   # Ekrem panelinin sol alt köşesi
    # ÇIKIŞ ve YOLU sağ kenarda, gri bandın tam ortasında uç uca değer (dik modda alttan yukarı: ÇIKIŞ, YOLU)
    ("cikis.png", "sag", "ust", PANEL_H + BAND_H // 2),            # üst kenarı bandın ortasında
    ("yolu.png", "sag", "alt", PANEL_H + BAND_H // 2),             # alt kenarı bandın ortasında
]


def render(video, bas, bit, cikti, ass=None, rozet_klasor=None, dik=False):
    w, h = S.video_boyut(video)
    lx, ly, lw, lh = S.olcekle(LEVENT_KIRP, w, h)
    ex, ey, ew, eh = S.olcekle(EKREM_KIRP, w, h)
    f = (f"[0:v]split=2[a][b];"
         f"[a]crop={lw}:{lh}:{lx}:{ly},scale={S.CIKTI_W}:{PANEL_H}:flags=lanczos[top];"
         f"[b]crop={ew}:{eh}:{ex}:{ey},scale={S.CIKTI_W}:{PANEL_H}:flags=lanczos[bot];"
         f"color=c={BAND_RENK}:s={S.CIKTI_W}x{BAND_H}:r=30[band];"
         f"[top][band][bot]vstack=inputs=3,setsar=1,fps=30[g]")
    girdiler, son = [], "g"
    if rozet_klasor:
        for i, (ad, yan, dikey, kenar) in enumerate(ROZETLER, start=1):
            yol = os.path.join(rozet_klasor, ad)
            if not os.path.isfile(yol):
                print(f"Uyarı: {yol} yok, atlandı.", file=sys.stderr)
                continue
            girdiler += ["-i", yol]
            n = len(girdiler) // 2
            x = "0" if yan == "sol" else "W-w"
            y = f"{kenar}-h" if dikey == "alt" else str(kenar)
            don = ",transpose=2" if dik else ""      # 90° saat yönünün tersi: yazı alttan yukarı okunur
            f += (f";[{n}:v]scale=iw*{ROZET_OLCEK:.5f}:-1:flags=lanczos{don}[r{n}];"
                  f"[{son}][r{n}]overlay={x}:{y}[o{n}]")
            son = f"o{n}"
    f += f";[{son}]null"
    if ass:
        f += f",ass='{S.ff_kac(ass)}'"
        if os.path.isdir(S.FONT_DIR):
            f += f":fontsdir='{S.ff_kac(S.FONT_DIR)}'"
        else:
            print(f"Uyarı: {S.FONT_DIR} yok; altyazı sistem fontuyla çizilecek.", file=sys.stderr)
    sure = bit - bas
    f += f"[v];[0:a]afade=t=in:d=0.03,afade=t=out:st={sure-0.05:.2f}:d=0.05[aa]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{bas:.3f}", "-t", f"{sure:.2f}", "-i", video, *girdiler,
                    "-filter_complex", f, "-map", "[v]", "-map", "[aa]", "-shortest",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", cikti],
                   check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kaynak", help="yerel mp4")
    ap.add_argument("--baslangic", type=float, required=True)
    ap.add_argument("--bitis", type=float, required=True)
    ap.add_argument("--transkript", help="hazır YouTube transkripti (.txt) veya --transkript-yaz çıktısı")
    ap.add_argument("--ass", help="elle düzeltilmiş altyazıyı yeniden üretmeden kullan")
    ap.add_argument("--rozet-klasor", help="levent-isim/ekrem-isim/cikis/yolu .png dosyalarının klasörü; verilirse köşelere yerleştirilir")
    ap.add_argument("--rozet-dik", action="store_true", help="rozetleri 90° döndür (alttan yukarı okunur)")
    ap.add_argument("--cikti", required=True)
    a = ap.parse_args()

    if a.bitis <= a.baslangic:
        ap.error("--bitis, --baslangic'tan büyük olmalı")
    if not os.path.isfile(a.kaynak):
        ap.error(f"Dosya bulunamadı: {a.kaynak}")
    if not a.ass and not a.transkript:
        ap.error("--transkript (altyazı için) ya da --ass ver")
    if os.path.exists(a.cikti):
        ap.error(f"{a.cikti} zaten var; üzerine yazmıyorum, başka ad ver")

    kelimeler = S.transkript_dosyadan(a.transkript) if a.transkript else None
    # Dosya transkriptinde cümle sınırları yaklaşık: elle verilen aralığı yalnızca sessizliğe oturt
    bas, bit = S.oturt(a.kaynak, a.baslangic, a.bitis, None)
    sure = bit - bas
    print(f"Kesim: {bas} -> {bit}  ({sure:.1f} sn)")
    if not S.UYARI_MIN <= sure <= S.UYARI_MAX:
        print(f"Uyarı: süre {sure:.1f} sn, hedef {S.UYARI_MIN}-{S.UYARI_MAX} sn dışında.", file=sys.stderr)

    w, h = S.video_boyut(a.kaynak)
    sapma = S.kadraj_kontrol(a.kaynak, bas, bit, w, h)
    if sapma:
        print(f"Uyarı: kadraj şu saniyelerde farklı görünüyor (tam ekran video / farklı plan olabilir): {sapma}.",
              file=sys.stderr)

    ass = a.ass
    if not ass:
        ass = os.path.splitext(a.cikti)[0] + ".ass"
        S.ass_yaz(kelimeler, bas, bit, ass)
    render(a.kaynak, bas, bit, a.cikti, ass, a.rozet_klasor, a.rozet_dik)
    print("Hazır:", a.cikti)


if __name__ == "__main__":
    main()

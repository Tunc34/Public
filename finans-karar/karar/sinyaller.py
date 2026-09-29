"""Koddan hesaplanan kesin sinyaller.

Jev hesap makinesi değildir; sayısal karşılaştırmalar burada yapılır.
Modele sayıların kendisi değil, anlamı (ör. "her zamankinin ~37 katı") gider.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Sinyaller:
    tutar_orani: float                 # tutar / müşterinin ortalama işlem tutarı
    bakiye_yetersiz: bool
    gunluk_limit_asimi: bool
    yaptirim_eslesmesi: bool
    yeni_alici: bool
    alici_hesap_yeni: bool             # alıcı hesabı 30 günden genç
    ele_gecirme_izi: bool              # yeni cihaz + son 24 saatte şifre değişimi
    gece_islemi: bool                  # 00:00-06:00
    aciklamalar: list[str] = field(default_factory=list)  # modele gidecek anlamsal özet


def hesapla(islem: dict, yaptirim_listesi: set[str]) -> Sinyaller:
    m = islem["musteri"]
    a = islem["alici"]
    k = islem.get("kanal", {})

    ort = max(m.get("ort_islem_tutari", 0), 1)
    oran = islem["tutar"] / ort
    saat = datetime.fromisoformat(islem["zaman"]).hour
    sifre_saat = k.get("sifre_degisimi_saat_once")

    s = Sinyaller(
        tutar_orani=oran,
        bakiye_yetersiz=islem["tutar"] > m["bakiye"],
        gunluk_limit_asimi=m.get("bugun_harcanan", 0) + islem["tutar"] > m["gunluk_limit"],
        yaptirim_eslesmesi=a["ad"].strip().casefold() in yaptirim_listesi,
        yeni_alici=a.get("ilk_kez", False),
        alici_hesap_yeni=a.get("hesap_yasi_gun", 9999) < 30,
        ele_gecirme_izi=bool(k.get("cihaz_yeni")) and sifre_saat is not None and sifre_saat < 24,
        gece_islemi=saat < 6,
    )

    # Sayıları kelimeye çevir (Jev anlamsal ifadelerde daha iyi).
    if oran >= 10:
        s.aciklamalar.append(f"Amount is far above normal: about {oran:.0f}x the customer's typical transaction.")
    elif oran >= 3:
        s.aciklamalar.append(f"Amount is noticeably above normal: about {oran:.1f}x the customer's typical transaction.")
    else:
        s.aciklamalar.append("Amount is within the customer's normal range.")
    s.aciklamalar.append("Recipient has never been paid before." if s.yeni_alici else "Recipient has been paid before.")
    if s.alici_hesap_yeni:
        s.aciklamalar.append("Recipient's account was opened less than 30 days ago.")
    if s.gece_islemi:
        s.aciklamalar.append("Transaction is made between midnight and 6 AM.")
    return s

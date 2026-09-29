"""Karar politikası: kod sahibi, model yalnızca yargı sağlar.

Eşikler örnektir; kendi etiketli verinizle ayarlayın.
"""

from dataclasses import dataclass, field
from enum import Enum

from .sinyaller import Sinyaller


class Karar(str, Enum):
    ONAY = "ONAY"          # otomatik geçir
    DOGRULA = "DOGRULA"    # uygulama içi / SMS ek doğrulama
    BEKLET = "BEKLET"      # analist incelemesi, müşteri aranır
    RED = "RED"            # kesin kural ihlali


@dataclass
class Yargilar:
    """Modelden gelen ham yargılar (tekrar kullanılabilir, politika değişince yeniden sorulmaz)."""
    scam_coaching: float
    purpose: str
    purpose_confidence: float
    behavior_fit: float          # 0 (tamamen alışılmadık) .. 3 (rutin)
    behavior_fit_confidence: float
    description_mismatch: float


@dataclass
class Sonuc:
    karar: Karar
    risk_puani: int
    gerekceler: list[str] = field(default_factory=list)
    yargilar: Yargilar | None = None


# --- Ayarlanabilir eşikler ---
DOLANDIRICILIK_KESIN = 0.70
DOLANDIRICILIK_SUPHELI = 0.40
UYUMSUZLUK_ESIK = 0.60
DUSUK_GUVEN = 0.50
DOGRULA_ESIK = 2
BEKLET_ESIK = 4


def kesin_kurallar(s: Sinyaller) -> Sonuc | None:
    """Model çağrısından önce: kesin kurallar karar verirse modele hiç gidilmez."""
    if s.yaptirim_eslesmesi:
        return Sonuc(Karar.BEKLET, 0, ["Alıcı yaptırım listesiyle eşleşiyor, uyum ekibine yönlendirildi."])
    if s.bakiye_yetersiz:
        return Sonuc(Karar.RED, 0, ["Bakiye yetersiz."])
    if s.gunluk_limit_asimi:
        return Sonuc(Karar.RED, 0, ["Günlük limit aşılıyor."])
    return None


def karar_ver(s: Sinyaller, y: Yargilar) -> Sonuc:
    puan, neden = 0, []

    # Dolandırıcı yönlendirmesi: tek başına yeterince ciddi, puanlamaya karışmaz.
    if y.scam_coaching >= DOLANDIRICILIK_KESIN:
        return Sonuc(Karar.BEKLET, 99, [f"Müşteri dolandırıcı yönlendirmesiyle işlem yapıyor olabilir (p={y.scam_coaching:.2f})."], y)
    if y.scam_coaching >= DOLANDIRICILIK_SUPHELI:
        puan += 2; neden.append(f"Olası dolandırıcı yönlendirmesi (p={y.scam_coaching:.2f}).")

    if y.description_mismatch >= UYUMSUZLUK_ESIK:
        puan += 2; neden.append("Açıklama ile alıcı uyuşmuyor.")

    if y.behavior_fit <= 1.0:
        puan += 2; neden.append(f"Müşterinin alışkanlıklarına aykırı (uyum={y.behavior_fit:.1f}/3).")
    elif y.behavior_fit <= 1.8:
        puan += 1; neden.append(f"Müşteri için alışılmadık (uyum={y.behavior_fit:.1f}/3).")

    if y.purpose == "investment_crypto" and s.yeni_alici and s.tutar_orani >= 10:
        puan += 2; neden.append("Yeni alıcıya yüksek tutarlı yatırım/kripto transferi.")

    # Kod sinyalleri
    if s.ele_gecirme_izi:
        puan += 3; neden.append("Yeni cihaz + son 24 saatte şifre değişimi (hesap ele geçirme izi).")
    if s.yeni_alici and s.alici_hesap_yeni:
        puan += 1; neden.append("Alıcı hem yeni hem de hesabı 30 günden genç.")
    if s.tutar_orani >= 10:
        puan += 1; neden.append(f"Tutar ortalamanın ~{s.tutar_orani:.0f} katı.")
    if s.gece_islemi:
        puan += 1; neden.append("Gece saatinde işlem.")

    karar = Karar.ONAY if puan < DOGRULA_ESIK else Karar.DOGRULA if puan < BEKLET_ESIK else Karar.BEKLET

    # Güven kapısı: risk varken model kararsızsa bir kademe yukarı çık.
    if karar == Karar.DOGRULA and min(y.purpose_confidence, y.behavior_fit_confidence) < DUSUK_GUVEN:
        karar = Karar.BEKLET; neden.append("Model yargısı belirsiz, insan incelemesine yükseltildi.")

    if not neden:
        neden.append("Risk sinyali yok.")
    return Sonuc(karar, puan, neden, y)

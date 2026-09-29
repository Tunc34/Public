"""Akış: kesin kurallar -> TypeSafe (tek istek, 4 paralel soru) -> politika."""

import time

from typesafe_sdk import TypeSafeAPIError, TypeSafeClient, TypeSafeError

from . import politika, sinyaller
from .politika import Karar, Sonuc, Yargilar
from .sorular import SORULAR, state_olustur


def yargilari_cek(yanit) -> Yargilar:
    return Yargilar(
        scam_coaching=yanit.nouls["scam_coaching"].noul,
        purpose=yanit.choices["purpose"].choice,
        purpose_confidence=yanit.choices["purpose"].confidence,
        behavior_fit=yanit.scores["behavior_fit"].score,
        behavior_fit_confidence=yanit.scores["behavior_fit"].confidence,
        description_mismatch=yanit.nouls["description_mismatch"].noul,
    )


def degerlendir(islem: dict, client: TypeSafeClient, yaptirim_listesi: set[str] = frozenset()) -> tuple[Sonuc, float]:
    """İşlemi değerlendirir; (sonuç, milisaniye) döner."""
    basla = time.perf_counter()
    s = sinyaller.hesapla(islem, {ad.casefold() for ad in yaptirim_listesi})

    sonuc = politika.kesin_kurallar(s)
    if sonuc is None:
        try:
            yanit = client.system_one(state_olustur(islem, s), SORULAR, timeout=5.0)
            sonuc = politika.karar_ver(s, yargilari_cek(yanit))
        except (TypeSafeAPIError, TypeSafeError) as hata:
            # Servis hatası: işlemi körlemesine geçirme, incelemeye al.
            sonuc = Sonuc(Karar.BEKLET, 0, [f"Karar servisi hatası ({type(hata).__name__}), güvenli tarafa alındı."])

    return sonuc, (time.perf_counter() - basla) * 1000

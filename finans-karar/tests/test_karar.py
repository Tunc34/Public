"""Ağ gerektirmeyen testler: politika ve akış, sahte TypeSafe yanıtlarıyla.

Buradaki yargı değerleri elle yazılmıştır; modelin gerçek çıktısı değildir.
Canlı doğrulama için `calistir.py` kullanın.
"""

import json
from pathlib import Path

from typesafe_sdk import SystemOneResponse, TypeSafeAPIError
from typesafe_sdk._core.questions import normalize_questions

from karar import politika, sinyaller
from karar.motor import degerlendir
from karar.politika import Karar, Yargilar
from karar.sorular import SORULAR, state_olustur

ISLEMLER = {i["id"]: i for i in json.loads((Path(__file__).parent.parent / "ornekler/islemler.json").read_text("utf-8"))}


def yanit(scam=0.05, purpose="rent_housing", pconf=0.9, fit=2.8, fconf=0.9, mismatch=0.05):
    return SystemOneResponse.model_validate_json(json.dumps({
        "model": "jev-test",
        "usage": {"input_tokens": 1, "output_tokens": 1},
        "answers": {
            "scam_coaching": {"type": "noul", "noul": scam},
            "purpose": {"type": "choice", "choice": purpose, "confidence": pconf, "probabilities": {purpose: pconf}},
            "behavior_fit": {"type": "score", "score": fit, "confidence": fconf,
                             "legend": {"0": "a", "1": "b", "2": "c", "3": "d"}, "probabilities": {"3": 1.0}},
            "description_mismatch": {"type": "noul", "noul": mismatch},
        },
    }))


class SahteClient:
    def __init__(self, cevap=None, hata=None):
        self.cevap, self.hata, self.cagri = cevap, hata, 0

    def system_one(self, state, questions, **_):
        self.cagri += 1
        normalize_questions(questions)
        if self.hata:
            raise self.hata
        return self.cevap


def test_sorular_sdk_dogrulamasindan_gecer():
    normalize_questions(SORULAR)


def test_state_sayi_yerine_anlam_tasir():
    s = sinyaller.hesapla(ISLEMLER["TX-1002"], set())
    st = state_olustur(ISLEMLER["TX-1002"], s)
    assert any("66x" in f for f in st["facts"])
    assert "Recipient has never been paid before." in st["facts"]


def test_rutin_kira_onaylanir():
    c = SahteClient(yanit())
    sonuc, _ = degerlendir(ISLEMLER["TX-1001"], c)
    assert sonuc.karar == Karar.ONAY and c.cagri == 1


def test_guvenli_hesap_dolandiriciligi_bekletilir():
    c = SahteClient(yanit(scam=0.93, purpose="unclear", fit=0.2))
    sonuc, _ = degerlendir(ISLEMLER["TX-1002"], c)
    assert sonuc.karar == Karar.BEKLET and sonuc.risk_puani == 99


def test_ele_gecirme_ve_uyumsuz_aciklama_bekletilir():
    c = SahteClient(yanit(scam=0.3, purpose="investment_crypto", fit=0.4, mismatch=0.88))
    sonuc, _ = degerlendir(ISLEMLER["TX-1003"], c)
    assert sonuc.karar == Karar.BEKLET
    assert any("ele geçirme" in g for g in sonuc.gerekceler)


def test_alisilmadik_ama_makul_islem_dogrulama_ister():
    s = sinyaller.hesapla(ISLEMLER["TX-1004"], set())
    sonuc = politika.karar_ver(s, Yargilar(0.05, "purchase", 0.9, 1.5, 0.9, 0.05))
    assert sonuc.karar == Karar.ONAY  # tek hafif sinyal (+1)
    sonuc = politika.karar_ver(s, Yargilar(0.45, "purchase", 0.9, 1.5, 0.9, 0.05))
    assert sonuc.karar == Karar.DOGRULA  # şüpheli yönlendirme (+2) + alışılmadık (+1)


def test_belirsiz_model_riskli_islemi_yukseltir():
    s = sinyaller.hesapla(ISLEMLER["TX-1004"], set())
    kesin = politika.karar_ver(s, Yargilar(0.05, "purchase", 0.9, 0.8, 0.9, 0.05))
    belirsiz = politika.karar_ver(s, Yargilar(0.05, "purchase", 0.3, 0.8, 0.9, 0.05))
    assert kesin.karar == Karar.DOGRULA and belirsiz.karar == Karar.BEKLET


def test_kesin_kural_modeli_cagirmaz():
    c = SahteClient(yanit())
    sonuc, _ = degerlendir(ISLEMLER["TX-1005"], c)
    assert sonuc.karar == Karar.RED and c.cagri == 0


def test_yaptirim_eslesmesi_uyuma_gider():
    c = SahteClient(yanit())
    sonuc, _ = degerlendir(ISLEMLER["TX-1001"], c, {"mehmet kaya"})
    assert sonuc.karar == Karar.BEKLET and c.cagri == 0


def test_servis_hatasinda_islem_gecmez():
    c = SahteClient(hata=TypeSafeAPIError.__new__(TypeSafeAPIError))
    sonuc, _ = degerlendir(ISLEMLER["TX-1001"], c)
    assert sonuc.karar == Karar.BEKLET

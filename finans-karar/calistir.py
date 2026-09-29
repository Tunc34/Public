"""Örnek işlemleri değerlendirir.

Kullanım:
    export TYPESAFE_API_KEY=...
    python calistir.py ornekler/islemler.json
"""

import json
import os
import sys

from typesafe_sdk import TypeSafeClient

from karar.motor import degerlendir

YAPTIRIM_LISTESI = {"Örnek Yaptırımlı Şirket Ltd."}  # gerçek listeyle değiştirin


def main(yol: str) -> None:
    if not os.environ.get("TYPESAFE_API_KEY"):
        sys.exit("TYPESAFE_API_KEY tanımlı değil.")
    with open(yol, encoding="utf-8") as f:
        islemler = json.load(f)

    with TypeSafeClient(model="jev-latest") as client:
        for islem in islemler:
            sonuc, ms = degerlendir(islem, client, YAPTIRIM_LISTESI)
            print(f"\n{islem['id']}  {islem['tutar']:>9,.0f} TL  ->  {sonuc.karar.value}  (risk {sonuc.risk_puani}, {ms:.0f} ms)")
            for g in sonuc.gerekceler:
                print(f"   - {g}")
            if sonuc.yargilar:
                y = sonuc.yargilar
                print(f"   yargılar: dolandırıcı={y.scam_coaching:.2f}  amaç={y.purpose}({y.purpose_confidence:.2f})  "
                      f"uyum={y.behavior_fit:.1f}/3({y.behavior_fit_confidence:.2f})  uyumsuzluk={y.description_mismatch:.2f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ornekler/islemler.json")

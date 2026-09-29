# finans-karar

Banka havale ve kart işlemleri için anlık risk kararı veren örnek bir [TypeSafe](https://docs.typesafe.ai) projesi.

Her işlem dört karardan birini alır:

| Karar | Anlamı |
|---|---|
| `ONAY` | Otomatik geçir |
| `DOGRULA` | Uygulama içi onay veya SMS ile ek doğrulama iste |
| `BEKLET` | Analist incelemesi, müşteri aranır |
| `RED` | Kesin kural ihlali (bakiye, limit) |

## Nasıl çalışır

```
işlem ─► sinyaller.py ─► kesin kurallar ──(karar verildi)──► sonuç
          (kodla hesap)        │
                               ▼
                   TypeSafe Jev: tek istek, 4 paralel soru
                               │
                               ▼
                   politika.py: puanlama + güven kapısı ─► sonuç
```

**Kodda kalanlar.** Tutar oranı, bakiye, limit, yaptırım listesi, yeni cihaz ve şifre değişimi, gece saati. Jev hesap makinesi değildir; sayılar modele kelime olarak gider ("her zamankinin ~66 katı" gibi).

**Jev'e sorulanlar.** Bunlar koda yazılamayan anlamsal yargılar:

| Soru | Tip | Ne yakalar |
|---|---|---|
| `scam_coaching` | Noul | "Savcılık aradı, güvenli hesaba aktar" gibi dolandırıcı yönlendirmeleri |
| `purpose` | Choice | Ödemenin amacı (kira, fatura, yatırım/kripto, …) |
| `behavior_fit` | Score 0–3 | İşlemin müşterinin geçmiş hareketlerine ne kadar uyduğu |
| `description_mismatch` | Noul | Açıklama ile alıcının çelişmesi ("kira" yazıp kripto borsasına göndermek gibi) |

**Güvenlik tercihleri.**
- Model servisi hata verirse işlem geçirilmez, `BEKLET` durumuna alınır.
- Risk varken model kararsızsa (confidence < 0.5), karar bir kademe yükseltilir.
- Kesin kurallar karar verdiyse modele hiç gidilmez. Bu gecikmeyi ve maliyeti azaltır.

## Kurulum

```bash
pip install -r requirements.txt
export TYPESAFE_API_KEY=...
python calistir.py ornekler/islemler.json
```

Testler ağ gerektirmez; sahte model yanıtlarıyla politikayı doğrular:

```bash
python -m pytest -q
```

## Örnek işlemler

| ID | Senaryo | Beklenen |
|---|---|---|
| TX-1001 | Her ay ödenen kira | ONAY |
| TX-1002 | "Savcılık aradı, güvenli hesaba aktar" | BEKLET |
| TX-1003 | Yeni cihaz, 3 saat önce şifre değişimi, gece 03:12'de kripto borsasına "kira" açıklamalı transfer | BEKLET |
| TX-1004 | Alışılmıştan biraz yüksek elektronik alışverişi | ONAY / DOGRULA |
| TX-1005 | Bakiye yetersiz | RED (model çağrılmaz) |

## Canlıya almadan önce

- `politika.py` içindeki eşikler örnektir. Etiketli geçmiş işlemlerle ayarlayın.
- Jev en iyi İngilizcede çalışır; Türkçe açıklamalar desteklenir ama eşit derecede iyi değildir. Kendi verinizle ölçün.
- Ham yargılar (`Yargilar`) saklanabilir. Eşik değiştirmek için modeli yeniden çağırmak gerekmez, ve bu yargılar ileride klasik bir ML modeline özellik olarak verilebilir.
- API anahtarını yalnızca sunucu tarafında tutun.

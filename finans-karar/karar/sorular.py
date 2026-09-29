"""TypeSafe soruları ve modele gidecek state.

Dört bağımsız yargı tek istekte paralel sorulur. Talimatlar İngilizce
(Jev'in en güçlü dili); işlem açıklamaları olduğu gibi Türkçe kalır.
"""

from typesafe_sdk import Choice, Noul, Score

from .sinyaller import Sinyaller

AMACLAR = {
    "rent_housing": "Rent, dues, or other housing payment.",
    "bills": "Utility, phone, internet, tax, or other bill payment.",
    "family_personal": "Money sent to family or friends for personal support.",
    "purchase": "Paying for goods or services from a seller.",
    "business": "Salary, supplier, or other business payment.",
    "investment_crypto": "Investment, trading, crypto, forex, or promised-return scheme.",
    "debt": "Loan, credit card, or debt repayment.",
    "unclear": "No purpose can be inferred from the available information.",
}

SORULAR = {
    "scam_coaching": Noul(
        instructions=(
            "Based on `transaction.description`, `customer_note`, and the facts, does the customer appear "
            "to be sending this money on the instructions of a third party who is deceiving them? "
            "Typical signs: someone posing as police, prosecutor, bank staff, or government; a 'safe account'; "
            "urgency or secrecy; guaranteed investment returns; an online seller or romance contact asking "
            "for payment outside a platform."
        ),
        criteria={
            "true": "The customer is likely being coached or pressured by a scammer.",
            "false": "The payment looks self-directed and ordinary.",
        },
    ),
    "purpose": Choice(
        instructions="What is the most likely purpose of this payment, given `transaction.description`, the recipient, and `customer_note`?",
        criteria=AMACLAR,
    ),
    "behavior_fit": Score(
        instructions=(
            "How consistent is this transaction with the customer's recent activity in `recent_transactions` "
            "and the facts about amount and recipient?"
        ),
        criteria=[
            "Clearly out of character: a kind of payment, recipient, or size this customer has never made.",
            "Unusual: related to past activity but with a surprising size, recipient, or purpose.",
            "Mostly consistent: a plausible, occasional variation on the customer's habits.",
            "Routine: matches payments the customer regularly makes.",
        ],
    ),
    "description_mismatch": Noul(
        instructions=(
            "Is the stated `transaction.description` inconsistent with who the recipient is "
            "(for example, 'rent' paid to a crypto exchange, or 'family' paid to a company)?"
        ),
        criteria={
            "true": "The description and the recipient do not fit together.",
            "false": "The description fits the recipient, or there is not enough information to see a conflict.",
        },
    ),
}


def state_olustur(islem: dict, sinyaller: Sinyaller) -> dict:
    """Karara ilgisi olan alanları seç; gürültüyü dışarıda bırak (Jev uzun state'te zayıflar)."""
    return {
        "transaction": {
            "type": islem["tip"],
            "description": islem.get("aciklama", ""),
            "channel": islem.get("kanal", {}).get("ad", "mobile"),
        },
        "recipient": {"name": islem["alici"]["ad"], "kind": islem["alici"].get("tur", "unknown")},
        "customer_note": islem.get("musteri_notu", ""),
        "recent_transactions": islem.get("son_islemler", [])[-10:],
        "facts": sinyaller.aciklamalar,
    }

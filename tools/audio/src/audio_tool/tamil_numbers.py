"""Tamil cardinal numbers as narrators read them, for aligning verses that
print digits (IRV 484 verses, TCV 377): `1,400` → ஆயிரத்து நானூறு.

Indian grouping (கோடி 10⁷, இலட்சம் 10⁵, ஆயிரம் 10³, நூறு 10²), with the
combining form (நூற்று, ஆயிரத்து, இருபத்து …) whenever more follows. A
spelling that differs a little from the narrator's only lowers that word's
score; the verse boundaries either side still come from the words around it.
"""

UNITS = ['', 'ஒன்று', 'இரண்டு', 'மூன்று', 'நான்கு', 'ஐந்து', 'ஆறு', 'ஏழு', 'எட்டு', 'ஒன்பது']
TEENS = ['பத்து', 'பதினொன்று', 'பன்னிரண்டு', 'பதின்மூன்று', 'பதினான்கு', 'பதினைந்து', 'பதினாறு', 'பதினேழு', 'பதினெட்டு', 'பத்தொன்பது']
TENS = ['', 'பத்து', 'இருபது', 'முப்பது', 'நாற்பது', 'ஐம்பது', 'அறுபது', 'எழுபது', 'எண்பது', 'தொண்ணூறு']
TENS_JOIN = ['', 'பத்து', 'இருபத்து', 'முப்பத்து', 'நாற்பத்து', 'ஐம்பத்து', 'அறுபத்து', 'எழுபத்து', 'எண்பத்து', 'தொண்ணூற்று']
HUNDREDS = ['', 'நூறு', 'இருநூறு', 'முந்நூறு', 'நானூறு', 'ஐந்நூறு', 'அறுநூறு', 'எழுநூறு', 'எண்ணூறு', 'தொள்ளாயிரம்']
HUNDREDS_JOIN = ['', 'நூற்று', 'இருநூற்று', 'முந்நூற்று', 'நானூற்று', 'ஐந்நூற்று', 'அறுநூற்று', 'எழுநூற்று', 'எண்ணூற்று', 'தொள்ளாயிரத்து']
# n thousand for n = 1..10, where the fused forms are irregular.
THOUSANDS = ['', 'ஆயிரம்', 'இரண்டாயிரம்', 'மூவாயிரம்', 'நான்காயிரம்', 'ஐயாயிரம்', 'ஆறாயிரம்', 'ஏழாயிரம்', 'எட்டாயிரம்', 'ஒன்பதாயிரம்', 'பத்தாயிரம்']
THOUSANDS_JOIN = ['', 'ஆயிரத்து', 'இரண்டாயிரத்து', 'மூவாயிரத்து', 'நான்காயிரத்து', 'ஐயாயிரத்து', 'ஆறாயிரத்து', 'ஏழாயிரத்து', 'எட்டாயிரத்து', 'ஒன்பதாயிரத்து', 'பத்தாயிரத்து']

U = 'ு'  # ு, the final "u" dropped before a vowel


def _below_100(n: int, join: bool = False) -> str:
    if n < 10:
        return UNITS[n]
    if n < 20:
        return TEENS[n - 10]
    t, u = divmod(n, 10)
    if u == 0:
        return TENS_JOIN[t] if join else TENS[t]
    return f'{TENS_JOIN[t]} {UNITS[u]}'


def _below_1000(n: int, join: bool = False) -> str:
    h, rest = divmod(n, 100)
    if h == 0:
        return _below_100(rest, join)
    if rest == 0:
        return HUNDREDS_JOIN[h] if join else HUNDREDS[h]
    return f'{HUNDREDS_JOIN[h]} {_below_100(rest, join)}'


def _fuse(word: str, suffix: str) -> str:
    """Join a multiplier to ஆயிரம் / ஆயிரத்து: இருபத்தைந்து + ஆயிரம் → இருபத்தைந்தாயிரம்."""
    last = word.split(' ')[-1]
    head = word[: len(word) - len(last)]
    if last.endswith(U):
        return f'{head}{last[:-1]}ா{suffix[1:]}'
    return f'{word} {suffix}'


def _thousands(n: int, join: bool) -> str:
    if n <= 10:
        return (THOUSANDS_JOIN if join else THOUSANDS)[n]
    return _fuse(_below_1000(n), 'ஆயிரத்து' if join else 'ஆயிரம்')


def spell(n: int) -> str:
    """A cardinal from 0 to 99,99,99,999 in words."""
    if n < 0:
        raise ValueError(n)
    if n == 0:
        return 'பூஜ்ஜியம்'
    parts = []
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, n = divmod(n, 1000)
    rest = n
    if crore:
        parts.append(('கோடி' if crore == 1 else f'{spell(crore)} கோடி') if not (lakh or thousand or rest) else ('கோடியே' if crore == 1 else f'{spell(crore)} கோடியே'))
    if lakh:
        more = bool(thousand or rest)
        word = 'இலட்சத்து' if more else 'இலட்சம்'
        parts.append(word if lakh == 1 else f'{_below_100(lakh)} {word}')
    if thousand:
        parts.append(_thousands(thousand, join=bool(rest)))
    if rest:
        parts.append(_below_1000(rest))
    return ' '.join(parts)

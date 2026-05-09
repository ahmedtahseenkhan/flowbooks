"""Shared utility functions used across the application."""


# ── Amount in Words (South Asian format: Lakh / Crore) ────────────────────────

_ONES = [
    '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
    'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
    'Seventeen', 'Eighteen', 'Nineteen',
]
_TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty',
         'Sixty', 'Seventy', 'Eighty', 'Ninety']


def _below100(n):
    return _ONES[n] if n < 20 else _TENS[n // 10] + (' ' + _ONES[n % 10] if n % 10 else '')


def _below1000(n):
    if n >= 100:
        return _ONES[n // 100] + ' Hundred' + (' ' + _below100(n % 100) if n % 100 else '')
    return _below100(n)


def amount_to_words(amount):
    """Convert a numeric amount to words (Lakh/Crore format, appends 'Only')."""
    try:
        amount = float(str(amount).replace(',', '') or 0)
    except (ValueError, TypeError):
        return ''
    if amount == 0:
        return 'Zero Only'

    negative = amount < 0
    n = int(abs(amount))
    parts = []

    # South Asian: 1 Crore = 10,000,000 | 1 Lakh = 100,000
    if n >= 1_00_00_000:             # 1 Crore = 10,000,000
        parts.append(_below1000(n // 1_00_00_000) + ' Crore')
        n %= 1_00_00_000
    if n >= 1_00_000:                # 1 Lakh = 100,000
        parts.append(_below100(n // 1_00_000) + ' Lakh')
        n %= 1_00_000
    if n >= 1_000:
        parts.append(_below1000(n // 1_000) + ' Thousand')
        n %= 1_000
    if n > 0:
        parts.append(_below1000(n))

    result = ' '.join(p for p in parts if p).strip()
    if negative:
        result = 'Minus ' + result
    return result + ' Only'


# ── Number formatting helpers ──────────────────────────────────────────────────

def safe_float(value, default=0.0):
    try:
        return float(str(value).replace(',', '') or default)
    except (ValueError, TypeError):
        return default


def fmt(n, decimals=2):
    """Format a number with commas and fixed decimal places."""
    try:
        return f"{float(n):,.{decimals}f}"
    except (ValueError, TypeError):
        return ''

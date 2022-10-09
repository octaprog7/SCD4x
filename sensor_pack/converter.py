"""Преобразование значений из одной единицы измерения в другую.
Сonverting values from one unit of measure to another"""


def pa_mmhg(value: float) -> float:
    """Перевод атмосферного давления из Па в мм рт.ст.
    Convert air pressure from Pa to mm Hg."""
    return 7.50062E-3 * value
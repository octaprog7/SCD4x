import micropython


@micropython.native
def _bitmask(start: int, stop: int) -> int:
    """возвращает битовую маску по занимаемым битам.
    start - номер младшего бита маски (0..31).
    stop - номер старшего бита маски (0..31)."""
    res = 0
    for i in range(start, 1 + stop):
        res |= 1 << i
    return res


def check(start: int, stop: int):
    if start > stop:
        raise ValueError(f"Invalid start: {start}, stop value: {stop}")


class BitField:
    """Класс для удобной работы с битовым полем.
    Class for convenient work with a bit field."""

    def __init__(self, start: int, stop: int, alias: [str, None]):
        """alias - псевдоним (для удобства, например "work_mode3:0")
        start - номер младшего бита с которого начинается битовое поле.
        start - номер старшего бита на котором заканчивается битовое поле

        alias - alias (for convenience, for example "work_mode3:0")
        start - number of the least significant bit from which the bit field starts.
        start - the high bit number where the bit field ends
        """
        check(start, stop)
        self.alias = alias
        self.start = start
        self.stop = stop
        self.bitmask = _bitmask(start, stop)   # вычисление маски

    def put(self, source: int, value: int) -> int:
        """Записывает value в битовый диапазон source.
        Writes value to source's bit range"""
        src = source & ~self.bitmask    # чистка битового диапазона
        src |= (value << self.start) & self.bitmask    # установка битов в заданном диапазоне
        return src

    def get(self, source: int) -> int:
        """Возвращает значение, находящееся в битовом диапазоне source.
        Returns a value in the bit range of source"""
        return (source & self.bitmask) >> self.start     # выделение маской битового диапазона и его сдвиг вправо


@micropython.native
def put(start: int, stop: int, source: int, value: int) -> int:
    """Записывает value в битовый диапазон source.
    Writes value to source's bit range"""
    check(start, stop)
    bitmask = _bitmask(start, stop)     # вычисление маски
    src = source & bitmask              # чистка битового диапазона
    src |= (value << start) & bitmask   # установка битов в заданном диапазоне
    return src

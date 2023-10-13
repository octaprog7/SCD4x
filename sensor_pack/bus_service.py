# micropython
# MIT license
# Copyright (c) 2022 Roman Shevchik   goctaprog@gmail.com
"""MicroPython модуль для работы с шинами ввода/вывода"""

import math
from machine import I2C, SPI, Pin


def _mpy_bl(value: int) -> int:
    """Возвращает место, занимаемое значением value в битах.
    Аналог int.bit_length(), которая есть в Python, но отсутствует в MicroPython!"""
    if 0 == value:
        return 0
    return 1 + int(math.log2(abs(value)))


class BusAdapter:
    """Посредник между шиной ввода/вывода и классом ввода/вывода устройства"""
    def __init__(self, bus: [I2C, SPI]):
        self.bus = bus

    def get_bus_type(self) -> type:
        """Возвращает тип шины"""
        return type(self.bus)

    def read_register(self, device_addr: [int, Pin], reg_addr: int, bytes_count: int) -> bytes:
        """считывает из регистра датчика значение.
        device_addr - адрес датчика на шине. Для шины SPI это физический вывод MCU!
        reg_addr - адрес регистра в адресном пространстве датчика.
        bytes_count - размер значения в байтах."""
        raise NotImplementedError

    def write_register(self, device_addr: [int, Pin], reg_addr: int, value: [int, bytes, bytearray],
                       bytes_count: int, byte_order: str):
        """записывает данные value в датчик, по адресу reg_addr.
        bytes_count - кол-во записываемых байт из value.
        byte_order - порядок расположения байт в записываемом значении."""
        raise NotImplementedError

    def read(self, device_addr: [int, Pin], n_bytes: int) -> bytes:
        raise NotImplementedError

    def write(self, device_addr: [int, Pin], buf: bytes):
        raise NotImplementedError

    def write_const(self, device_addr: [int, Pin], val: int, count: int):
        """Отправляет пакет байт со значение val количеством count на шину.
        Часто, при работе с дисплеями или памятью, требуется заполнение экрана/области
        постоянным значением. Для этого и предназначен этот метод!
        Вызов его для сравнительно медленных шин - плохая идея!"""
        if 0 == count:
            return  # нет ничего
        # bl = val.bit_length()     # bit_length() отсутствует в MicroPython
        bl = _mpy_bl(val)
        if bl > 8:
            raise ValueError(f"The value must take no more than 8 bits! Current: {bl}")
        _max = 16
        if count < _max:
            _max = count
        # вычисляю кол-во повторений тела цикла
        repeats = count // _max  # количество итераций
        b = bytearray([val for _ in range(_max)])
        for _ in range(repeats):
            self.write(device_addr, b)
        # вычисляю остаток
        remainder = count - _max * repeats
        if remainder:
            b = bytearray([val for _ in range(remainder)])
            self.write(device_addr, b)


class I2cAdapter(BusAdapter):
    """"""
    def __init__(self, bus: I2C):
        super().__init__(bus)

    def write_register(self, device_addr: int, reg_addr: int, value: [int, bytes, bytearray],
                       bytes_count: int, byte_order: str):
        """записывает данные value в датчик, по адресу reg_addr.
        bytes_count - кол-во записываемых данных
        value - должно быть типов int, bytes, bytearray"""
        buf = None
        if isinstance(value, int):
            buf = value.to_bytes(bytes_count, byte_order)
        if isinstance(value, (bytes, bytearray)):
            buf = value

        return self.bus.writeto_mem(device_addr, reg_addr, buf)

    def read_register(self, device_addr: int, reg_addr: int, bytes_count: int) -> bytes:
        """считывает из регистра датчика значение.
        bytes_count - размер значения в байтах"""
        return self.bus.readfrom_mem(device_addr, reg_addr, bytes_count)

    def read(self, device_addr: int, n_bytes: int) -> bytes:
        return self.bus.readfrom(device_addr, n_bytes)

    def readfrom_into(self, device_addr: int, buf):
        """Читает из устройства на шине с адресом device_addr в буфер buf количество байт, равное длине(len) буфера!"""
        return self.bus.readfrom_into(device_addr, buf)
    
    def read_buf_from_mem(self, device_addr: int, mem_addr, buf):
        """Читает из устройства с адресом device_addr в буфер buf, начиная с адреса в устройстве mem_addr.
        Количество считываемых байт определяется длинной буфера buf."""
        return self.bus.readfrom_mem_into(device_addr, mem_addr, buf)

    def write(self, device_addr: int, buf: bytes):
        return self.bus.writeto(device_addr, buf)

    def write_buf_to_mem(self, device_addr: int, mem_addr, buf):
        """Записывает в устройство с адресом device_addr все байты из буфера buf.
        Запись начинается с адреса в устройстве: mem_addr."""
        return self.bus.writeto_mem(device_addr, mem_addr, buf)


class SpiAdapter(BusAdapter):
    """Параметр data_mode представляет собой вывод MCU, который используется для установки флага, что посылка является
    данными (high) или командой (low). Например это необходимо при обмене ILI9481."""
    def __init__(self, bus: SPI, data_mode: Pin = None):
        super().__init__(bus)
        # вывод MCU для режима данных
        self.data_mode_pin = data_mode
        # использовать ли вывод MCU для режима данных (Истина) или команд (Ложь)
        self.use_data_mode_pin = False
        # флаг для методов write.. . Если Истина, то data_mode (Pin) будет установлена в Истина, иначе в Ложь!
        # flag for write.. methods. If True, then data_mode (Pin) will be set to True, otherwise to False!
        self.data_packet = False

    def read_register(self, device_addr: Pin, reg_addr: int, bytes_count: int) -> bytes:
        raise NotImplementedError

    def write_register(self, device_addr: Pin, reg_addr: int, value: [int, bytes, bytearray],
                       bytes_count: int, byte_order: str):
        raise NotImplementedError

    def read(self, device_addr: Pin, n_bytes: int) -> bytes:
        """Read a number of bytes specified by n_bytes while continuously writing the single byte given by write.
        Returns a bytes object with the data that was read."""
        try:
            device_addr.low()
            return self.bus.read(n_bytes)
        finally:
            device_addr.high()

    def readinto(self, device_addr: Pin, buf):
        """Read into the buffer specified by buf while continuously writing the single byte given by write.
        Returns None."""
        try:
            device_addr.low()
            return self.bus.readinto(buf, 0x00)
        finally:
            device_addr.high()

    def write(self, device_addr: Pin, buf: bytes):
        """Параметр data_packet представляет собой признак того, что посылка является данными (high) или командой (low).
        Например это необходимо при обмене ILI9481.
        Write the bytes contained in buf. Returns None.
        The data_packet parameter is an indication that the package is data (high) or command (low).
         For example, this is necessary when exchanging ILI9481."""
        try:
            device_addr.low()   # chip select
            if self.use_data_mode_pin and self.data_mode_pin:
                self.data_mode_pin.value(self.data_packet)
            return self.bus.write(buf)
        finally:
            device_addr.high()

    def write_and_read(self, device_addr: Pin, wr_buf: bytes, rd_buf: bytes):
        """Параметр data_packet представляет собой признак того, что посылка является данными (high) или командой (low).
        Например это необходимо при обмене ILI9481.
        Write the bytes from write_buf while reading into read_buf. The buffers can be the same or different,
        but both buffers must have the same length. Returns None.
        The data_packet parameter is an indication that the package is data (high) or command (low).
         For example, this is necessary when exchanging ILI9481."""
        try:
            device_addr.low()   # chip select
            if self.use_data_mode_pin and self.data_mode_pin:
                self.data_mode_pin.value(self.data_packet)
            return self.bus.write_readinto(wr_buf, rd_buf)
        finally:
            device_addr.high()

# micropython
# MIT license
# Copyright (c) 2022 Roman Shevchik   goctaprog@gmail.com
"""service class for I/O bus operation"""

from machine import I2C


class BusAdapter:
    """Proxy between I/O bus and device I/O class"""
    def __init__(self, bus):
        self.bus = bus

    def read_register(self, device_addr: int, reg_addr: int, bytes_count: int) -> bytes:
        """считывает из регистра датчика значение.
        device_addr - адрес датчика на шине.
        reg_addr - адрес регистра в адресном пространстве датчика.
        bytes_count - размер значения в байтах.
        reads value from sensor register.
        device_addr - address of the sensor on the bus.
        reg_addr - register address in the address space of the sensor"""
        raise NotImplementedError

    def write_register(self, device_addr: int, reg_addr: int, value: [int, bytes, bytearray],
                       bytes_count: int, byte_order: str):
        """записывает данные value в датчик, по адресу reg_addr.
        bytes_count - кол-во записываемых байт из value.
        byte_order - порядок расположения байт в записываемом значении.
        writes value data to the sensor, at reg_addr.
        bytes_count - number of bytes written from value.
        byte_order - the order of bytes in the value being written.
        """
        raise NotImplementedError

    def read(self, device_addr, n_bytes: int) -> bytes:
        raise NotImplementedError

    def write(self, device_addr, buf: bytes):
        raise NotImplementedError


class I2cAdapter(BusAdapter):
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

    def read(self, device_addr, n_bytes: int) -> bytes:
        return self.bus.readfrom(device_addr, n_bytes)
    
    def read_buf_from_mem(self, device_addr, mem_addr, buf):
        """Читает из устройства с адресом device_addr в буфер buf, начиная с адреса в устройстве mem_addr.
        Количество считываемых байт определяется длинной буфера buf.
        Reads from device address device_addr into buf, starting at the address in device mem_addr.
        The number of bytes read is determined by the length of the buffer buf"""
        return self.bus.readfrom_mem_into(device_addr, mem_addr, buf)

    def write(self, device_addr, buf: bytes):
        return self.bus.writeto(device_addr, buf)

    def write_buf_to_mem(self, device_addr, mem_addr, buf):
        """Записывает в устройство с адресом device_addr все байты из буфера buf.
        Запись начинается с адреса в устройстве: mem_addr.
        Writes to device address device_addr all the bytes in buf.
        The entry starts at an address in the device: mem_addr."""
        return self.bus.writeto_mem(device_addr, mem_addr, buf)

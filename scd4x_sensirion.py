"""SCD4x Sensirion module"""

from sensor_pack import bus_service
from sensor_pack.base_sensor import BaseSensor, Iterator
from sensor_pack import base_sensor
from sensor_pack.crc_mod import crc8
from sensor_pack import bitfield
import struct
import array


class SCD4xSensirion(BaseSensor, Iterator):
    """Class for work with Sensirion SCD4x sensor"""
    def __init__(self, adapter: bus_service.BusAdapter, address=0x62):
        super().__init__(adapter, address, True)    # Big Endian

    def _read(self, n_bytes: int) -> bytes:
        return self.adapter.read(self.address, n_bytes)

    def _write(self, buf: bytes) -> bytes:
        return self.adapter.write(self.address, buf)

    # BaseSensor
    def get_id(self) -> tuple:
        """Return 3 words of unique serial number can be used to identify
        the chip and to verify the presence of the sensor."""
        cmd = 0x3682
        self._write(cmd.to_bytes(2, "big"))
        b = self._read(9)
        base_sensor.check_value(len(b), (9,), f"Invalid buffer length: {len(b)}")   # check length of buffer
        crc_from_buf = [b[i] for i in range(2, 9, 3)]  # build list of CRC from buf
        calculated_crc = [crc8((b[i], b[i+1]), 0x31, 0xFF) for i in range(0, 9, 3)]  # build list of calculated CRC
        # print(crc_from_buf, calculated_crc)
        if crc_from_buf != calculated_crc:      # compare CRC from buf and calculated CRC
            base_sensor.check_value(1, (0,),    # Fail!
                                    f"Invalid СRC value(s): received: {crc_from_buf}, calculated: {calculated_crc}")
        return tuple([(b[i] << 8) | b[i+1] for i in range(0, 9, 3)])    # Success

    def soft_reset(self):
        pass

    # Iterator
    def __iter__(self):
        return self

    def __next__(self):
        pass

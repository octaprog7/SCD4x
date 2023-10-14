"""SCD4x Sensirion module"""

from sensor_pack import bus_service
from sensor_pack.base_sensor import BaseSensor, Iterator
from sensor_pack import base_sensor
from sensor_pack.crc_mod import crc8
import micropython
import time


def _calc_crc(sequence) -> int:
    """Обертка для короткого вызова.
    Wrapper for a short call."""
    return crc8(sequence, polynomial=0x31, init_value=0xFF)


class SCD4xSensirion(BaseSensor, Iterator):
    """Class for work with Sensirion SCD4x sensor"""
    def __init__(self, adapter: bus_service.BusAdapter, address=0x62,
                 this_is_scd41: bool = True, check_crc: bool = True):
        """Если check_crc в Истина, то каждый, принятый от датчика пакет данных, проверяется на правильность путем
        расчета контрольной суммы.
        Если this_is_scd41 == True, то будут доступны методы для SCD41, иначе будут доступны методы ОБЩИЕ для SCD40/41!
        If check_crs is True, then each data packet received from the sensor is checked for correctness by
        calculating the checksum.
        If this_is_scd41 == True then methods for SCD41 will be available,
        otherwise GENERAL methods for SCD40/41 will be available!"""
        super().__init__(adapter, address, True)    # Big Endian
        self._buf_3 = bytearray((0 for _ in range(3)))
        self._buf_9 = bytearray((0 for _ in range(9)))
        self.check_crc = check_crc
        # power mode
        self._low_power_mode = False
        # measurement mode (single shot, continuous)
        self._single_shot_mode = False
        self._rht_only = False
        self._isSCD41 = this_is_scd41
        # сохраняю, чтобы не вызывать 125 раз
        self.byte_order = self._get_byteorder_as_str()

    def _get_local_buf(self, bytes_for_read: int) -> [None, bytearray]:
        """возвращает локальный буфер для операции чтения"""
        if bytes_for_read not in (0, 3, 9):
            raise ValueError(f"Invalid value for bytes_for_read: {bytes_for_read}")
        if not bytes_for_read:
            return None
        if 3 == bytes_for_read:
            return self._buf_3
        return self._buf_9

    def _to_bytes(self, value, length: int):
        byteorder = self.byte_order[0]
        return value.to_bytes(length, byteorder)

    # def _read(self, n_bytes: int) -> bytes:
    #    return self.adapter.read(self.address, n_bytes)

    def _write(self, buf: bytes) -> bytes:
        return self.adapter.write(self.address, buf)

    def _readfrom_into(self, buf):
        """Читает из устройства в буфер"""
        return self.adapter.readfrom_into(self.address, buf)

    def _send_command(self, cmd: int, value: [bytes, None],
                      wait_time: int = 0, bytes_for_read: int = 0,
                      crc_index: range = None,
                      value_index: tuple = None) -> [bytes, None]:
        """Передает команду датчику по шине.
        cmd - код команды.
        value - последовательность, передаваемая после кода команды.
        wait_time - время в мс. которое нужно подождать для обработки команды датчиком.
        bytes_for_read - количество байт в ответе датчика, если не 0, то будет считан ответ,
        проверена CRC (зависит от self.check_crc) и этот ответ будет возвращен, как результат.
        crc_index_range - индексы crc в последовательности.
        value_index_ranges- кортеж индексов (range) данных значений в
        последовательности. (range(3), range(4,6), range(7,9))"""
        # print(f"DBG: bytes_for_read: {bytes_for_read}")
        raw_cmd = self._to_bytes(cmd, 2)
        raw_out = raw_cmd
        if value:
            raw_out += value    # добавляю value и его crc
            raw_out += self._to_bytes(_calc_crc(value), 1)     # crc считается только для данных!
        self._write(raw_out)    # выдача на шину
        if wait_time:
            time.sleep_ms(wait_time)   # ожидание
        if not bytes_for_read:
            return None
        # b = self._read(bytes_for_read)  # читаю с шины с проверкой количества считанных байт
        b = self._get_local_buf(bytes_for_read)
        self._readfrom_into(b)      # обновление
        base_sensor.check_value(len(b), (bytes_for_read,),
                                f"Invalid buffer length for cmd: {cmd}. Received {len(b)} out of {bytes_for_read}")
        if self.check_crc:
            crc_from_buf = [b[i] for i in crc_index]  # build list of CRC from buf
            calculated_crc = [_calc_crc(b[rng.start:rng.stop]) for rng in value_index]
            if crc_from_buf != calculated_crc:
                raise ValueError(f"Invalid CRC! Calculated{calculated_crc}. From buffer {crc_from_buf}")
        return b    # возврат bytearray со считанными данными

    # BaseSensor
    # Advanced features
    def save_config(self):
        """Настройки конфигурации, такие как смещение температуры, высота расположения датчика над уровнем моря
        по умолчанию сохраняются только в энергозависимой памяти (ОЗУ) и будут потеряны после выключения и включения
        питания. Метод сохраняет текущую конфигурацию в EEPROM SCD4x, сохраняя ее при отключении питания.
        Чтобы избежать ненужного износа EEPROM, метод следует вызывать только в том случае, если это необходимо(!) и
        если были внесены фактические изменения в конфигурацию. EEPROM гарантированно выдерживает не менее 2000
        циклов записи до отказа(!).
        Configuration settings such as temperature offset, sensor altitude are stored by default only in volatile memory
        (RAM) and will be lost after a power cycle. The method saves the current configuration in the EEPROM of the
        SCD4x, saving it when the power is turned off. To avoid unnecessary wear on the EEPROM, the method should only
        be called if necessary(!) and if actual configuration changes have been made.
        EEPROM is guaranteed to withstand at least 2000 write cycles to failure (!)"""
        cmd = 0x3615
        self._send_command(cmd, None, 800)

    def get_id(self) -> tuple:
        """Return 3 words of unique serial number can be used to identify
        the chip and to verify the presence of the sensor."""
        # создатели датчика 'обрадовали'. вместо подсчета одного байта CRC на 6 байт (3 двухбайтных слова)
        # они считают CRC для каждого из 3-х двухбайтных слов!
        cmd = 0x3682
        b = self._send_command(cmd, None, 0, bytes_for_read=9,
                               crc_index=range(2, 9, 3), value_index=(range(2), range(3, 5), range(6, 8)))
        # return result
        return tuple([(b[i] << 8) | b[i+1] for i in range(0, 9, 3)])    # Success

    def soft_reset(self):
        """Я сознательно не стал использовать команду perfom_factory_reset, чтобы было невозможно испортить датчик
        программным путем, так-как количество циклов записи во внутреннюю FLASH память датчика ограничено!
        I deliberately did not use the perfom_factory_reset command, so that it would be impossible to spoil the
        sensor programmatically, since the number of write cycles to the internal FLASH memory of the
        sensor is limited!"""
        return None

    def exec_self_test(self) -> bool:
        """"Этот метод можно использовать в качестве конечного теста для проверки работоспособности датчика и
        проверки подачи питания на датчик. Возвращает Истина, когда тест пройден успешно.
        The feature can be used as an end-of-line test to check sensor functionality and the customer power
        supply to the sensor. Returns True when the test is successful."""
        cmd = 0x3639
        length = 3
        b = self._send_command(cmd, None, wait_time=10_000,     # да, ждать 10 секунд! yes, wait 10 seconds!
                               bytes_for_read=length, crc_index=range(2, 3), value_index=(range(2),))
        res = self.unpack("H", b)[0]
        return 0 == res

    def reinit(self) -> None:
        """Команда reinit повторно инициализирует датчик, загружая пользовательские настройки из EEPROM.
        Перед отправкой команды reinit необходимо выполнить метод stop_measurement. Если команда reinit не вызывает
        желаемой повторной инициализации, к SCD4x следует применить цикл включения и выключения питания.
        The reinit command reinitializes the sensor by reloading user settings from EEPROM.
        Before sending the reinit command, the stop_measurement method must be called.
        If the reinit command does not trigger the desired re-initialization,
        a power-cycle should be applied to the SCD4x."""
        cmd = 0x3646
        self._send_command(cmd, None, 20)

    # On-chip output signal compensation
    def set_temperature_offset(self, offset: float):    # вызов нужно делать только в IDLE режиме датчика!
        """Смещение температуры не влияет на точность измерения CO2 . Правильная установка смещения температуры SCD4x
        внутри пользовательского устройства позволяет пользователю использовать выходные сигналы RH и T. Обратите
        внимание, что смещение температуры может зависеть от различных факторов, таких как режим измерения SCD4x,
        самонагрев близких компонентов, температура окружающей среды и расход воздуха. Таким образом, смещение
        температуры SCD4x должно определяться внутри пользовательского устройства в типичных условиях его работы
        (включая режим работы, который будет использоваться в приложении) и при тепловом равновесии. По умолчанию
        смещение температуры установлено в 4°C.
        The temperature offset has no influence on the SCD4x CO 2 accuracy. Setting the temperature offset of the SCD4x
        inside the customer device correctly allows the user to leverage the RH and T output signal. Note that the
        temperature offset can depend on various factors such as the SCD4x measurement mode, self-heating of close
        components, the ambient temperature and air flow.
        Метод нужно вызывать только в IDLE режиме датчика!
        The method should be called only in IDLE sensor mode!

        𝑇 𝑜𝑓𝑓𝑠𝑒𝑡_𝑎𝑐𝑡𝑢𝑎𝑙 = 𝑇 𝑆𝐶𝐷40 − 𝑇 𝑅𝑒𝑓𝑒𝑟𝑒𝑛𝑐𝑒 + 𝑇 𝑜𝑓𝑓𝑠𝑒𝑡_ 𝑝𝑟𝑒𝑣𝑖𝑜𝑢𝑠"""
        cmd = 0x241D
        offset_raw = self._to_bytes(int(374.49142857 * offset), 2)
        self._send_command(cmd, offset_raw, 1)

    def get_temperature_offset(self) -> float:
        """Метод нужно вызывать только в IDLE режиме датчика!
        The method should be called only in IDLE sensor mode!"""
        cmd = 0x2318
        b = self._send_command(cmd, None, wait_time=1, bytes_for_read=3, crc_index=range(2, 3), value_index=(range(2),))
        temp_offs = self.unpack("H", b)[0]
        return 0.0026702880859375 * temp_offs

    def set_altitude(self, masl: int):  # вызов нужно делать только в IDLE режиме датчика!
        """Чтение и запись высоты датчика должны выполняться, когда SCD4x находится в режиме ожидания.
        Как правило, высота датчика устанавливается один раз после установки устройства. Чтобы сохранить настройку
        в EEPROM, необходимо выполнить метод save_config. По умолчанию высота датчика установлена в
        0 метров над уровнем моря (masl).
        Reading and writing sensor height must be done when the SCD4x is in standby mode. As a rule, the height of the
        sensor is set once after the installation of the device. To save the configuration to EEPROM, you must execute
        the save_config method. By default, the sensor height is set to 0 meters above sea level (masl).
        Метод нужно вызывать только в IDLE режиме датчика!
        The method should be called only in IDLE sensor mode!"""
        cmd = 0x2427
        masl_raw = self._to_bytes(masl, 2)
        self._send_command(cmd, masl_raw, 1)

    def get_altitude(self) -> int:
        """Метод нужно вызывать только в IDLE режиме датчика!
        The method should be called only in IDLE sensor mode!"""
        cmd = 0x2322
        b = self._send_command(cmd, None, wait_time=1, bytes_for_read=3, crc_index=range(2, 3), value_index=(range(2),))
        return self.unpack("H", b)[0]

    def set_ambient_pressure(self, pressure: float):
        """Метод может быть вызван во время периодических измерений, чтобы включить непрерывную компенсацию давления.
        Обратите внимание, что установка давления окружающей среды с помощью set_ambient_pressure отменяет любую
        компенсацию давления, основанную на ранее установленной высоте датчика. Использование этой команды настоятельно
        рекомендуется для приложений со значительными изменениями давления окружающей среды,
        чтобы обеспечить точность датчика.
        The method can be called during periodic measurements to enable continuous pressure compensation.
        Note that setting the ambient pressure using set_ambient_pressure overrides any pressure compensation based
        on the previously set sensor height. The use of this command is highly recommended for applications with
        significant changes in ambient pressure to ensure sensor accuracy."""
        cmd = 0xE000
        press_raw = self._to_bytes(int(pressure // 100), 2)     # Pascal // 100
        self._send_command(cmd, press_raw, 1)

    # Field calibration
    def force_recalibration(self, target_co2_concentration: int) -> int:
        """Please read '3.7.1 perform_forced_recalibration'"""
        base_sensor.check_value(target_co2_concentration, range(2**16),
                                f"Invalid target CO2 concentration: {target_co2_concentration} ppm")
        cmd = 0x362F
        target_raw = self._to_bytes(target_co2_concentration, 2)
        b = self._send_command(cmd, target_raw, 400, 3, crc_index=range(2, 3), value_index=(range(2),))
        return self.unpack("h", b)[0]

    def is_auto_calibration(self) -> bool:
        """Please read '3.7.3 get_automatic_self_calibration_enabled'"""
        cmd = 0x2313
        b = self._send_command(cmd, None, 1, 3, crc_index=range(2, 3), value_index=(range(2),))
        return 0 != self.unpack("H", b)[0]

    def set_auto_calibration(self, value: bool):
        """Please read '3.7.2 set_automatic_self_calibration_enabled'"""
        cmd = 0x2416
        value_raw = self._to_bytes(value, 2)
        self._send_command(cmd, value_raw, 1, 3)

    def set_measurement(self, start: bool, single_shot: bool = False, rht_only: bool = False):
        """Используется для запуска или остановки периодических измерений.
        single_shot = False. rht_only не используется!
        А также для запуска ОДНОКРАТНОГО измерения. single_shot = True. rht_only используется!
        Если rht_only == True то датчик не вычисляет CO2 и оно будет равно нулю! Смотри метод get_meas_data()
        start используется только при False == single_shot (periodic mode)

        Used to start or stop periodic measurements. single_shot = False. rht_only is not used!
        And also to start a SINGLE measurement. single_shot = True. rht_only is used!
        If rht_only == True then the sensor does not calculate CO2 and it will be zero! See get_meas_data() method
        start is used only when False == single_shot (periodic mode)"""
        if single_shot:
            return self._single_shot_meas(rht_only)
        return self._periodic_measurement(start)

    # Basic Commands
    def _periodic_measurement(self, start: bool):
        """Start periodic measurement. In low power mode, signal update interval is approximately 30 seconds.
        In normal power mode, signal update interval is approximately 5 seconds.
        If start == True then measurement started, else stopped.
        Для чтения результатов используйте метод get_meas_data.
        To read the results, use the get_meas_data method."""
        wt = 0
        if start:
            cmd = 0x21AC if self._low_power_mode else 0x21B1
        else:   # stop periodic measurement
            cmd = 0x3F86
            wt = 500
        self._send_command(cmd, None, wt)
        self._single_shot_mode = False
        self._rht_only = False

    def get_meas_data(self) -> tuple:
        """Чтение выходных данных датчика. Данные измерения могут быть считаны только один раз за интервал
        обновления сигнала, так как буфер очищается при считывании. Смотри get_conversion_cycle_time()!
        Read sensor data output. The measurement data can only be read out once per signal update interval
        as the buffer is emptied upon read-out. See get_conversion_cycle_time()!"""
        cmd = 0xEC05
        val_index = (range(2), range(3, 5), range(6, 8))
        b = self._send_command(cmd, None, 1, bytes_for_read=9,
                               crc_index=range(2, 9, 3), value_index=val_index)
        words = [self.unpack("H", b[val_rng.start:val_rng.stop])[0] for val_rng in val_index]
        #       CO2 [ppm]           T, Celsius              Relative Humidity, %
        return words[0], -45 + 0.0026703288 * words[1], 0.0015259022 * words[2]

    def is_data_ready(self) -> bool:
        """Return data ready status"""
        cmd = 0xE4B8
        b = self._send_command(cmd, None, 1, 3, crc_index=range(2, 3), value_index=(range(2),))
        return bool(self.unpack("H", b)[0] & 0b0000_0111_1111_1111)

    @micropython.native
    def get_conversion_cycle_time(self) -> int:
        """Возвращает время преобразования данных датчиком в зависимости от его настроек. мс.
        returns the data conversion time of the sensor, depending on its settings. ms."""
        if self.is_single_shot_mode and self.is_rht_only:
            return 50
        return 5000

    # SCD41 only
    def set_power(self, value: bool):
        if not self._isSCD41:
            return
        """Please read '3.10.3 power_down' and '3.10.4 wake_up'"""
        cmd = 0x36F6 if value else 0x36E0
        wt = 20 if value else 1
        self._send_command(cmd, None, wt)

    def _single_shot_meas(self, rht_only: bool = False):
        """Only for SCD41. Single shot measurement!
        Запускает измерение температуры и относительной влажности!
        После вызова этого метода, результаты будут готовы примерно через 5 секунд!
        Для чтения результатов используйте метод get_meas_data. Содержание CO2 будет равно нулю, если true == rht_only!
        After calling this method, the results will be ready in about 5 seconds!
        To read the results, use the get_meas_data method.
        SCD41 features a single shot measurement mode, i.e. allows for on-demand measurements.
        Please see '3.10 Low power single shot (SCD41)'"""
        if not self._isSCD41:
            return
        cmd = 0x2196 if rht_only else 0x219D
        self._send_command(cmd, None, 0)
        self._single_shot_mode = True
        self._rht_only = rht_only

    @property
    def is_single_shot_mode(self) -> bool:
        return self._single_shot_mode

    @property
    def is_rht_only(self) -> bool:
        return self._rht_only

    # Iterator
    def __iter__(self):
        return self

    def __next__(self) -> [tuple, None]:
        if self._single_shot_mode:
            return None
        if self.is_data_ready():
            return self.get_meas_data()
        return None

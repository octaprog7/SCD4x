import time

from scd4x_sensirion import SCD4xSensirion
from machine import I2C
from sensor_pack.bus_service import I2cAdapter


if __name__ == '__main__':
    # пожалуйста установите выводы scl и sda в конструкторе для вашей платы, иначе ничего не заработает!
    # please set scl and sda pins for your board, otherwise nothing will work!
    # https://docs.micropython.org/en/latest/library/machine.I2C.html#machine-i2c
    # i2c = I2C(0, scl=Pin(13), sda=Pin(12), freq=400_000) # для примера
    # bus =  I2C(scl=Pin(4), sda=Pin(5), freq=100000)   # на esp8266    !
    # Внимание!!!
    # Замените id=1 на id=0, если пользуетесь первым портом I2C !!!
    # Warning!!!
    # Replace id=1 with id=0 if you are using the first I2C port !!!
    i2c = I2C(id=1, freq=400_000)  # on Arduino Nano RP2040 Connect tested
    adaptor = I2cAdapter(i2c)
    # sensor
    sen = SCD4xSensirion(adaptor)
    # Force return sensor in IDLE mode!
    # Принудительно перевожу датчик в режим IDLE!
    sen.set_measurement(start=False, single_shot=False)
    sid = sen.get_id()
    print(f"Sensor id 3 x Word: {sid[0]:x}:{sid[1]:x}:{sid[2]:x}")
    t_offs = 0.0
    # Warning: To change or read sensor settings, the SCD4x must be in idle mode!!!
    # Otherwise an EIO exception will be raised!
    # print(f"Set temperature offset sensor to {t_offs} Celsius")
    # sen.set_temperature_offset(t_offs)
    t_offs = sen.get_temperature_offset()
    print(f"Get temperature offset from sensor: {t_offs} Celsius")
    masl = 160
    print(f"Set my place M.A.S.L. to {masl} meter")
    sen.set_altitude(masl)
    masl = sen.get_altitude()
    print(f"Get M.A.S.L. from sensor: {masl} meter")
    # data ready
    if sen.is_data_ready():
        print("Measurement data can be read!")  # Данные измерений могут быть прочитаны!
    else:
        print("Measurement data missing!")
    
    if sen.is_auto_calibration():
        print("The automatic self-calibration is ON!")
    else:
        print("The automatic self-calibration is OFF!")

    sen.set_measurement(start=True, single_shot=False)
    wt = sen.get_conversion_cycle_time()
    print(f"conversion cycle time [ms]: {wt}")
    print("Periodic measurement started")
    for i in range(5):
        time.sleep_ms(wt)
        co2, t, rh = sen.get_meas_data()
        print(f"CO2 [ppm]: {co2}; T [°C]: {t}; RH [%]: {rh}")
    
    print(20*"*_")
    print("Reading using an iterator!")
    for counter, items in enumerate(sen):
        time.sleep_ms(wt)
        if items:
            co2, t, rh = items
            print(f"CO2 [ppm]: {co2}; T [°C]: {t}; RH [%]: {rh}")
            if 5 == counter:
                break

    print(20 * "*_")
    print("Using single shot mode!")
    # Force return sensor in IDLE mode!
    # Принудительно перевожу датчик в режим IDLE!
    sen.set_measurement(start=False, single_shot=False)
    while True:
        sen.set_measurement(start=False, single_shot=True, rht_only=False)
        time.sleep_ms(3 * wt)      # 3x period
        co2, t, rh = sen.get_meas_data()
        print(f"CO2 [ppm]: {co2}; T [°C]: {t}; RH [%]: {rh}")

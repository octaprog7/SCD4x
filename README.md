# SCD4x
MicroPython module for work with SCD4x temperature&humidity&CO2 sensor from Sensirion.

Just connect your SCD4x board to Arduino, ESP or any other board with MicroPython firmware.

Supply voltage SCD4x 3.3 Volts or 5.0 Volts!
1. VCC
2. GND
3. SDA
4. SCL

Upload MicroPython firmware to the NANO(ESP, etc) board, and then files: main.py, SCD4x_sensirion.py 
and sensor_pack folder. Then open main.py in your IDE and run it.

# Pictures

## IDE
![alt text](https://github.com/octaprog7/SCD4x/blob/master/scd4x_ide.png)
## Breadboard
![alt text](https://github.com/octaprog7/SCD4x/blob/master/scd4x_board.jpg)

# Самоподогрев
При периодическом измерении (период считывания данных 5 секунд) я обраружил подозрительный рост температуры, 
считываемой с датчика. При переходе в режим однократного измерения с периодом 15 секунд, я увидел падение температуры. 
Очень похоже, что в режиме периодического измерения датчик самоподогревается!
Рекомендую переводить датчик в режим однократного измерения с периодом измерения не менее 15 секунд!

# Self heating
During periodic measurement (data reading period of 5 seconds), I detected a suspicious 
increase in temperature read from the sensor.
When switching to single measurement mode with a period of 15 seconds, I saw a drop in temperature.
It looks like the sensor is self-heating in the periodic measurement mode!
I recommend switching the sensor to single measurement mode with a period of at least 15 seconds!

## Self heating picture
![alt text](https://github.com/octaprog7/SCD4x/blob/master/self_heat.png)

# Autocalibration problem

The person expressed a useful idea in my opinion. You can read it at the [link](https://www.reddit.com/r/esp32/comments/12y0x5k/warning_about_the_sensirion_scd4041_co2_sensors/).

Человек высказал, на мой взгляд, полезную мысль. С ней вы можете ознакомится по [тут](https://www.reddit.com/r/esp32/comments/12y0x5k/warning_about_the_sensirion_scd4041_co2_sensors/).
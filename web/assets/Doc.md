I want to design a PCB board for RC carbot by ESP32.

The features I need are:-

1 - Two TT yellow motors.

2- Calculate distance by using Ultarsonic

3- Passive buzzer.

4- Line follower.

5- OLED 0.96''display.

6- WS2812 5050 RGB LED Driver Module Board 8 LEDs.

7- Charging battery.

8- Two batteries (18650) 2550 mAh; if we need three, tell me.

---
- I want to make driver design be more professional and robust.
- I want to do not use delay and block the system.
- I want to be have a non blocking functions.
- The driver have a cyclic function the OS call it every time to check if there command should run or not.
- The cyclic function should handel if the command is run and after time will stop should this function stop the command after this time.
for example if i want to run buzzer for 500ms, The system should not blocked!! until the buzzer time is finsh the cyclic time handel this.
- Please, Can you make a plan and Architectural Design for driver.
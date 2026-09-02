# hal_motor.py
from machine import Pin, PWM
from pin_config import PINS

class Motor:
    """
    Hardware abstraction for a single DC motor driven by a DRV8833.
    Uses PWM to control speed and direction.
    """
    def __init__(self, pin_in1, pin_in2, freq=1000):
        self.pwm1 = PWM(Pin(pin_in1), freq=freq)
        self.pwm2 = PWM(Pin(pin_in2), freq=freq)
        self.pwm1.duty(0)
        self.pwm2.duty(0)

    def set_speed(self, speed):
        """
        Set motor speed and direction.
        speed: int from -100 (full reverse) to 100 (full forward)
        """
        # Constrain speed to -100 to 100
        speed = max(-100, min(100, int(speed)))
        
        # Convert percentage (0-100) to 10-bit duty cycle (0-1023)
        duty = int(abs(speed) * 10.23)
        
        if speed > 0:
            self.pwm1.duty(duty)
            self.pwm2.duty(0)
        elif speed < 0:
            self.pwm1.duty(0)
            self.pwm2.duty(duty)
        else:
            self.stop()
            
    def stop(self):
        """Stop the motor."""
        self.pwm1.duty(0)
        self.pwm2.duty(0)

class RobotDrive:
    """
    Hardware abstraction for the EZ-BOTIX differential drive base.
    """
    def __init__(self):
        # Left motors (OUT3 & OUT4) controlled by M_IN1 and M_IN2
        self.motor_left = Motor(PINS["MOTOR_L_IN1"], PINS["MOTOR_L_IN2"])
        
        # Right motors (OUT1 & OUT2) controlled by M_IN3 and M_IN4
        self.motor_right = Motor(PINS["MOTOR_R_IN1"], PINS["MOTOR_R_IN2"])

    def drive(self, left_speed, right_speed):
        """
        Drive both motors independently.
        Speeds from -100 to 100.
        """
        self.motor_left.set_speed(left_speed)
        self.motor_right.set_speed(right_speed)

    def forward(self, speed):
        """Drive forward at given speed (0-100)."""
        self.drive(speed, speed)

    def backward(self, speed):
        """Drive backward at given speed (0-100)."""
        self.drive(-speed, -speed)

    def turn_left(self, speed):
        """Turn left in place at given speed (0-100)."""
        self.drive(-speed, speed)

    def turn_right(self, speed):
        """Turn right in place at given speed (0-100)."""
        self.drive(speed, -speed)

    def stop(self):
        """Stop all motors."""
        self.drive(0, 0)

# Expose a global instance for easy use in user code
car = RobotDrive()

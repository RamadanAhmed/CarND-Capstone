import rospy
from yaw_controller import YawController
from pid import PID
from lowpass import LowPassFilter

GAS_DENSITY = 2.858
ONE_MPH = 0.44704


class Controller(object):
    def __init__(self, vehicle_mass, fuel_capacity, brake_deadband, decel_limit, accel_limit, steer_ratio, wheel_radius, wheel_base, max_lat_accel, max_steer_angle):
        self.vehicle_mass = vehicle_mass
        self.fuel_capacity = fuel_capacity
        self.brake_deadband = brake_deadband
        self.decel_limit = decel_limit
        self.accel_limit = accel_limit
        self.steer_ratio = steer_ratio
        self.wheel_radius = wheel_radius
        wheel_base = wheel_base
        max_lat_accel = max_lat_accel
        max_steer_angle = max_steer_angle

        self.yaw_controller = YawController(
            wheel_base, self.steer_ratio, 0.1, max_lat_accel, max_steer_angle)

        kp = 0.3
        ki = 0.1
        kd = 0.
        mn = 0.  # Min Throttle value
        mx = 0.2  # Max Throttle value

        self.throttle_controller = PID(kp, ki, kd, mn, mx)

        tau = 0.5  # 1/ (2 * pi * tau) = cutoff freq
        ts = 0.02  # sample time

        self.vel_lpf = LowPassFilter(tau, ts)
        self.last_vel = None
        self.last_time = rospy.get_time()

    def control(self, current_vel, dbw_enabled, linear_vel, angular_vel):
        # Return throttle, brake, steer
        if not dbw_enabled:
            self.throttle_controller.reset()
            return 0., 0., 0.
        current_vel = self.vel_lpf.filt(current_vel)

        steering = self.yaw_controller.get_steering(
            linear_vel, angular_vel, current_vel)

        val_error = linear_vel - current_vel

        self.last_vel = current_vel

        current_time = rospy.get_time()
        sample_time = current_time - self.last_time
        self.last_time = current_time

        throttle = self.throttle_controller.step(val_error, sample_time)

        brake = 0.

        if linear_vel == 0. and current_vel < 0.1:
            throttle = 0.
            brake = 700
        elif throttle < .1 and val_error < 0:
            throttle = 0
            decel = max(val_error, self.decel_limit)
            brake = abs(decel) * self.vehicle_mass * self.wheel_radius

        return throttle, brake, steering

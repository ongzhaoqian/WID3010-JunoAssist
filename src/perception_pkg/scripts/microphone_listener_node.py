#!/usr/bin/env python3
import rospy
from std_msgs.msg import Float32MultiArray
import numpy as np

class AudioChangeDetector:
    def __init__(self):
        # Sensitivity settings
        self.threshold_multiplier = 2.5  # Trigger if signal is 2.5x louder than noise
        self.alpha = 0.1                 # Smoothing factor for background noise
        self.background_rms = 0.0        # Initial noise floor estimate
        
        # ROS setup
        rospy.init_node('audio_change_detector', anonymous=True)
        self.sub = rospy.Subscriber('/audio/raw', Float32MultiArray, self.callback)
        rospy.loginfo("Monitoring audio for significant changes...")

    def callback(self, msg):
        # Convert to numpy array
        audio_data = np.array(msg.data, dtype=np.float32)

        if audio_data.size == 0:
            return

        # 1. Calculate current RMS (Root Mean Square)
        current_rms = np.sqrt(np.mean(audio_data ** 2))

        # 2. Initialize or Update Background Noise Floor (moving average)
        if self.background_rms == 0:
            self.background_rms = current_rms
        else:
            # Gradually adapt to the environment
            self.background_rms = (self.alpha * current_rms) + (1 - self.alpha) * self.background_rms

        # 3. Detect Change
        # Logic: If current volume > (threshold * average noise)
        if current_rms > (self.background_rms * self.threshold_multiplier):
            rospy.logwarn(f"SIGNIFICANT CHANGE DETECTED | RMS: {current_rms:.6f} (Noise Floor: {self.background_rms:.6f})")
        else:
            # Use end='\r' to keep the terminal clean while monitoring
            print(f"Monitoring... RMS: {current_rms:.6f} | Noise Floor: {self.background_rms:.6f}", end='\r')

    def run(self):
        rospy.spin()

if __name__ == "__main__":
    detector = AudioChangeDetector()
    detector.run()
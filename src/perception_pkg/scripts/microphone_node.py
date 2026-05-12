#!/usr/bin/env python3
import rospy
from std_msgs.msg import Float32MultiArray
import pyaudio
import numpy as np

def microphone_node():
    rospy.init_node('microphone_node', anonymous=True)

    pub = rospy.Publisher('/audio/raw', Float32MultiArray, queue_size=10)

    device_index = 0
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 48000

    p = pyaudio.PyAudio()

    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=CHUNK
    )

    rospy.loginfo("Mic node publishing FLOAT32 audio")

    while not rospy.is_shutdown():
        data = stream.read(CHUNK, exception_on_overflow=False)

        audio_int16 = np.frombuffer(data, dtype=np.int16)

        # convert ONCE here
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        audio_float32 = audio_float32[::3].copy()
        msg = Float32MultiArray()
        msg.data = audio_float32.tolist()

        pub.publish(msg)

    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == '__main__':
    microphone_node()
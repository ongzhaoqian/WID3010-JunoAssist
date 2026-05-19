#!/usr/bin/env python3
import os

import numpy as np
import pyaudio
import rospy
from std_msgs.msg import Float32MultiArray


def microphone_node():
    rospy.init_node('microphone_node', anonymous=True)

    audio_topic = rospy.get_param('~audio_topic', '/audio/raw')
    pub = rospy.Publisher(audio_topic, Float32MultiArray, queue_size=10)

    # The `anas` branch used device index 7 successfully on the robot setup.
    # Keep it as the default, but allow override for other laptops/robots.
    device_index = int(rospy.get_param('~input_device_index', os.getenv('JUNO_MIC_DEVICE_INDEX', '7')))
    chunk = int(rospy.get_param('~chunk_size', os.getenv('JUNO_MIC_CHUNK_SIZE', '1024')))
    source_rate = int(rospy.get_param('~source_rate', os.getenv('JUNO_MIC_SOURCE_RATE', '48000')))
    target_rate = int(rospy.get_param('~target_rate', os.getenv('JUNO_ASR_SAMPLE_RATE', '16000')))
    channels = int(rospy.get_param('~channels', os.getenv('JUNO_MIC_CHANNELS', '1')))
    downsample_factor = max(1, source_rate // target_rate)

    p = pyaudio.PyAudio()

    stream = p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=source_rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=chunk,
    )

    rospy.loginfo(
        'Mic node publishing FLOAT32 audio to %s from device %s, %s Hz -> ~%s Hz',
        audio_topic,
        device_index,
        source_rate,
        source_rate // downsample_factor,
    )

    try:
        while not rospy.is_shutdown():
            data = stream.read(chunk, exception_on_overflow=False)
            audio_int16 = np.frombuffer(data, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            audio_float32 = audio_float32[::downsample_factor].copy()

            msg = Float32MultiArray()
            msg.data = audio_float32.tolist()
            pub.publish(msg)
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


if __name__ == '__main__':
    microphone_node()

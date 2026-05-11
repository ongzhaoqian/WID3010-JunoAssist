#!/usr/bin/env python3
import rospy
import numpy as np
import threading
from std_msgs.msg import Float32MultiArray
import moonshine_onnx as moonshine

# Settings
SAMPLE_RATE = 16000
BUFFER_SECONDS = 3
BUFFER_SIZE = SAMPLE_RATE * BUFFER_SECONDS

class MoonshineTranscriber:
    def __init__(self):
        rospy.init_node('moonshine_transcriber')
        
        self.audio_lock = threading.Lock()
        self.audio_buffer = [] # List for faster appending
        self.current_length = 0
        
        # Initialize model once
        rospy.loginfo("Loading Moonshine model...")
        self.model_name = "moonshine/tiny"
        
        self.sub = rospy.Subscriber('/audio/raw', Float32MultiArray, self.audio_callback)
        
        # Start the processing thread
        self.process_thread = threading.Thread(target=self.inference_loop)
        self.process_thread.daemon = True
        self.process_thread.start()
        
        rospy.loginfo("Transcriber Ready.")

    def audio_callback(self, msg):
        with self.audio_lock:
            chunk = np.array(msg.data, dtype=np.float32)
            self.audio_buffer.append(chunk)
            self.current_length += len(chunk)

    def inference_loop(self):
        while not rospy.is_shutdown():
            # Check if we have enough audio
            if self.current_length >= BUFFER_SIZE:
                with self.audio_lock:
                    # Combine chunks and grab 3 seconds
                    full_audio = np.concatenate(self.audio_buffer)
                    audio_to_process = full_audio[:BUFFER_SIZE]
                    
                    # Keep the remainder
                    remaining_audio = full_audio[BUFFER_SIZE:]
                    self.audio_buffer = [remaining_audio]
                    self.current_length = len(remaining_audio)

                # Perform transcription OUTSIDE the lock
                # so the callback can keep receiving audio
                try:
                    result = moonshine.transcribe(audio_to_process, self.model_name)
                    if result and result[0].strip():
                        print(f"Transcription: {result[0]}")
                except Exception as e:
                    rospy.logerr(f"Inference error: {e}")
            
            # Small sleep to prevent CPU spinning
            rospy.sleep(0.05)

if __name__ == '__main__':
    try:
        node = MoonshineTranscriber()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
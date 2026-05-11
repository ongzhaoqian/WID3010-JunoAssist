import pyaudio

def list_input_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    num_devices = info.get('deviceCount')

    print("\n--- AVAILABLE INPUT DEVICES ---")
    print(f"{'Index':<7} {'Name':<40} {'Channels':<10} {'Sample Rate'}")
    print("-" * 75)

    for i in range(num_devices):
        device = p.get_device_info_by_index(i)
        # Only show devices that have at least 1 input channel
        if device.get('maxInputChannels'):
            print(f"{i:<7} {device.get('name')[:38]:<40} "
                  f"{device.get('maxInputChannels'):<10} "
                  f"{int(device.get('defaultSampleRate'))}Hz")
    
    print("-" * 75)
    
    default_device = p.get_default_input_device_info()
    print(f"System Default: Index {default_device['index']} ({default_device['name']})")
    
    p.terminate()

if __name__ == "__main__":
    list_input_devices()
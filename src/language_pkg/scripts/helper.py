#!/usr/bin/env python3
import os
import rospy
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig

def download_moonshine_model():
    """
    Downloads the Moonshine base model into the language_pkg/models directory
    using Hugging Face Transformers.
    """
    rospy.init_node('moonshine_downloader', anonymous=True)

    # Path to your ROS package
    pkg_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_path = os.path.join(pkg_path, 'models')
    os.makedirs(models_path, exist_ok=True)

    rospy.loginfo(f"Downloading Moonshine base model into: {models_path}")

    # Specify Moonshine model identifier from Hugging Face Hub
    model_name = "UsefulSensors/moonshine"  # replace with correct HF model ID

    # Download tokenizer and model locally
    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=models_path)
    model = AutoModelForCausalLM.from_pretrained(model_name, cache_dir=models_path)

    rospy.loginfo("Moonshine base model downloaded successfully!")

if __name__ == "__main__":
    try:
        download_moonshine_model()
    except rospy.ROSInterruptException:
        pass
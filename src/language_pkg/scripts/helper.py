#!/usr/bin/env python3
<<<<<<< HEAD
"""Helper for pre-downloading Whisper Tiny model assets for ROS demos."""

import os

import rospy
from huggingface_hub import snapshot_download


def download_whisper_assets():
    rospy.init_node('whisper_tiny_downloader', anonymous=True)

=======
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
>>>>>>> origin/anas
    pkg_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_path = os.path.join(pkg_path, 'models')
    os.makedirs(models_path, exist_ok=True)

<<<<<<< HEAD
    model_id = os.getenv('JUNO_ASR_MODEL_ID', 'openai/whisper-tiny')

    rospy.loginfo('Downloading Whisper Tiny model into cache: %s', models_path)
    snapshot_download(repo_id=model_id, cache_dir=models_path)
    rospy.loginfo('Whisper Tiny assets downloaded successfully.')


if __name__ == "__main__":
    try:
        download_whisper_assets()
    except rospy.ROSInterruptException:
        pass
=======
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
>>>>>>> origin/anas

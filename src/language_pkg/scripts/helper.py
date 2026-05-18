#!/usr/bin/env python3
"""Helper for pre-downloading Hugging Face model assets for ROS demos."""

import os

import rospy
from huggingface_hub import snapshot_download


def download_malaysian_llama_assets():
    rospy.init_node('malaysian_llama_downloader', anonymous=True)

    pkg_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_path = os.path.join(pkg_path, 'models')
    os.makedirs(models_path, exist_ok=True)

    base_model_id = os.getenv('JUNO_LLM_MODEL_ID', 'mesolitica/Malaysian-Llama-3.2-3B-Instruct')
    adapter_id = os.getenv('JUNO_LLM_ADAPTER_ID', 'mackwongyy/malaysian-feedback-lora-5k-data')

    rospy.loginfo('Downloading base model into cache: %s', models_path)
    snapshot_download(repo_id=base_model_id, cache_dir=models_path)

    rospy.loginfo('Downloading LoRA adapter into cache: %s', models_path)
    snapshot_download(repo_id=adapter_id, cache_dir=models_path)

    rospy.loginfo('Malaysian Llama and LoRA adapter assets downloaded successfully.')


if __name__ == "__main__":
    try:
        download_malaysian_llama_assets()
    except rospy.ROSInterruptException:
        pass

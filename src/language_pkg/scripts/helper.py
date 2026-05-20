#!/usr/bin/env python3
"""Helper for pre-downloading Whisper Tiny model assets for ROS demos."""

import os

import rospy
from huggingface_hub import snapshot_download


def download_whisper_assets():
    rospy.init_node('whisper_tiny_downloader', anonymous=True)

    pkg_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_path = os.path.join(pkg_path, 'models')
    os.makedirs(models_path, exist_ok=True)

    model_id = os.getenv('JUNO_ASR_MODEL_ID', 'openai/whisper-tiny')

    rospy.loginfo('Downloading Whisper Tiny model into cache: %s', models_path)
    snapshot_download(repo_id=model_id, cache_dir=models_path)
    rospy.loginfo('Whisper Tiny assets downloaded successfully.')


if __name__ == "__main__":
    try:
        download_whisper_assets()
    except rospy.ROSInterruptException:
        pass

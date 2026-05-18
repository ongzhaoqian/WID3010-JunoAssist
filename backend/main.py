import logging

from src.api.app import create_app
from src.core.config import settings
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        # Uvicorn reload starts an extra process, which can confuse rospy node
        # initialisation. Keep reload off when backend is connected to ROS.
        reload=not settings.use_ros_robot,
        log_level="info",
    )

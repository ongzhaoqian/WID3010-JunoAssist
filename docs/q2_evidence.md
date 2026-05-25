# Q2 Evidence — ROS Workspace Setup

## System Information

```
Distributor ID: Ubuntu
Description:    Ubuntu 20.04.6 LTS
Release:        20.04
Codename:       focal

Python 3.8.10

ROS Noetic
```

## Workspace Structure

```
mustar@jupiter:~/Desktop/WID3010-JunoAssist$ pwd
/home/mustar/Desktop/WID3010-JunoAssist

mustar@jupiter:~/Desktop/WID3010-JunoAssist$ ls
backend   build   dashboard   devel   docs   LICENSE   README.md   src   WID3010 AA (Q)_2025.2026.pdf

mustar@jupiter:~/Desktop/WID3010-JunoAssist$ ls src
CMakeLists.txt  juno_bringup  language_pkg  perception_pkg
```

## Catkin Workspace Files

```
mustar@jupiter:~/Desktop/WID3010-JunoAssist$ ls -la .catkin_workspace src/CMakeLists.txt
-rw-rw-r-- 1 mustar mustar   98 May 20 17:02 .catkin_workspace
-rw-rw-r-- 1 mustar mustar 1907 May 25 14:40 src/CMakeLists.txt

mustar@jupiter:~/Desktop/WID3010-JunoAssist$ find src -maxdepth 2 -name package.xml -print
src/perception_pkg/package.xml
src/language_pkg/package.xml
src/juno_bringup/package.xml

mustar@jupiter:~/Desktop/WID3010-JunoAssist$ find src -maxdepth 2 -name CMakeLists.txt -print
src/perception_pkg/CMakeLists.txt
src/language_pkg/CMakeLists.txt
src/CMakeLists.txt
src/juno_bringup/CMakeLists.txt
```

## Catkin Build

```
mustar@jupiter:~/Desktop/WID3010-JunoAssist$ source /opt/ros/noetic/setup.bash
mustar@jupiter:~/Desktop/WID3010-JunoAssist$ catkin_make
Base path: /home/mustar/Desktop/WID3010-JunoAssist
Source space: /home/mustar/Desktop/WID3010-JunoAssist/src
Build space: /home/mustar/Desktop/WID3010-JunoAssist/build
Devel space: /home/mustar/Desktop/WID3010-JunoAssist/devel
Install space: /home/mustar/Desktop/WID3010-JunoAssist/install
####
#### Running command: "make cmake_check_build_system" in "/home/mustar/Desktop/WID3010-JunoAssist/build"
####
####
#### Running command: "make -j12 -l12" in "/home/mustar/Desktop/WID3010-JunoAssist/build"
####
```

Build completed successfully with no errors.

## Workspace Sourcing and Package Discovery

```
mustar@jupiter:~/Desktop/WID3010-JunoAssist$ source devel/setup.bash
mustar@jupiter:~/Desktop/WID3010-JunoAssist$ echo $ROS_PACKAGE_PATH
/home/mustar/Desktop/WID3010-JunoAssist/src:/home/mustar/robot_project/src:/home/mustar/catkin_ws/src:/opt/ros/noetic/share

mustar@jupiter:~/Desktop/WID3010-JunoAssist$ rospack find perception_pkg
/home/mustar/Desktop/WID3010-JunoAssist/src/perception_pkg

mustar@jupiter:~/Desktop/WID3010-JunoAssist$ rospack find language_pkg
/home/mustar/Desktop/WID3010-JunoAssist/src/language_pkg

mustar@jupiter:~/Desktop/WID3010-JunoAssist$ rospack find juno_bringup
/home/mustar/Desktop/WID3010-JunoAssist/src/juno_bringup
```

## Auto-Source via ~/.bashrc (New Terminal)

The following lines were added to `~/.bashrc` so the workspace is loaded automatically on every new terminal:

```bash
source /opt/ros/noetic/setup.bash          # line 119
source ~/Desktop/WID3010-JunoAssist/devel/setup.bash   # line 135
```

Verified in a new terminal without any manual sourcing:

```
mustar@jupiter:~/Desktop/WID3010-JunoAssist$ echo $ROS_PACKAGE_PATH
/home/mustar/Desktop/WID3010-JunoAssist/src:/home/mustar/robot_project/src:/home/mustar/catkin_ws/src:/opt/ros/noetic/share

mustar@jupiter:~/Desktop/WID3010-JunoAssist$ rospack find perception_pkg
/home/mustar/Desktop/WID3010-JunoAssist/src/perception_pkg

mustar@jupiter:~/Desktop/WID3010-JunoAssist$ rospack find language_pkg
/home/mustar/Desktop/WID3010-JunoAssist/src/language_pkg

mustar@jupiter:~/Desktop/WID3010-JunoAssist$ rospack find juno_bringup
/home/mustar/Desktop/WID3010-JunoAssist/src/juno_bringup

mustar@jupiter:~/Desktop/WID3010-JunoAssist$ grep -n "WID3010\|ros/noetic" ~/.bashrc
119:source /opt/ros/noetic/setup.bash
135:source ~/Desktop/WID3010-JunoAssist/devel/setup.bash
```

All three packages (`perception_pkg`, `language_pkg`, `juno_bringup`) are discoverable automatically in every new terminal without manual sourcing.

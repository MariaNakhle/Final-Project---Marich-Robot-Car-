# MARICH - AI-Powered Intelligent Robot Car

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red.svg)](https://www.raspberrypi.org/)

> **A comprehensive AI-powered robotic platform featuring voice interaction, computer vision, and autonomous behaviors**
>
> *BSc Final Project in Electrical and Electric engineering*  
> *Authors: Maria Nakhle & Christian*

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Hardware Requirements](#hardware-requirements)
- [Software Dependencies](#software-dependencies)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
- [Project Structure](#project-structure)
- [Technical Implementation](#technical-implementation)
- [Demonstrations](#demonstrations)
- [Future Enhancements](#future-enhancements)
- [Acknowledgments](#acknowledgments)
- [License](#license)

---

## 🎯 Overview

**MARICH** (derived from **Maria** + **Christian**) is an advanced intelligent robot car platform that combines artificial intelligence, computer vision, and embedded systems to create an interactive and autonomous robotic companion. The project demonstrates the integration of multiple AI technologies including natural language processing, speech recognition, computer vision, and robotics control systems.

Built on a Raspberry Pi platform, MARICH showcases practical applications of AI in robotics, including:
- Natural voice-based human-robot interaction
- Real-time computer vision processing
- Autonomous navigation and object tracking
- Interactive gaming capabilities
- Emotion expression through visual and LED feedback

This project serves as a comprehensive demonstration of modern AI and robotics integration techniques suitable for educational purposes, research, and entertainment applications.

---

## ✨ Key Features

### 🤖 AI Chatbot & Voice Interaction
- **Speech Recognition**: Real-time voice command processing using Vosk ASR
- **Natural Language Processing**: Context-aware conversations powered by Gemma 2B LLM via Ollama
- **Text-to-Speech**: Natural voice synthesis using Piper TTS
- **Emotion System**: Dynamic facial expressions and LED indicators reflecting robot's emotional state
- **Memory Management**: Intelligent conversation history with automatic memory optimization

### 👁️ Computer Vision Capabilities
- **Color Tracking**: Real-time tracking and following of colored objects (red, green, blue, yellow)
- **Face Detection & Recognition**: Identify and track human faces
- **Gesture Recognition**: Hand gesture detection and interpretation
- **Object Recognition**: TensorFlow-based object detection using SSD MobileNet
- **License Plate Recognition**: Automatic vehicle license plate detection and reading

### 🎮 Interactive Gaming
- **Rock-Paper-Scissors**: Play against the robot using hand gestures
  - Real-time gesture detection via camera
  - Emotional responses (celebration on win, frustration on loss)
  - Synchronized LED light shows and movement routines

### 🚗 Motion Control
- **Omnidirectional Movement**: Forward, backward, lateral, diagonal, and rotational motion
- **Autonomous Behaviors**: Color following, face tracking, gesture-based control
- **Dance Routines**: Choreographed movement sequences with synchronized lighting
- **Patrol Mode**: Autonomous square patrol pattern

### 💡 Hardware Integration
- **LED Expression System**: RGB LED bar for emotional and status indication
- **Ultrasonic Sensing**: Distance measurement for proximity detection (high-five interaction)
- **Line Tracking**: Ground detection using infrared sensors
- **IR Remote Control**: Wireless control via infrared remote
- **Buzzer Feedback**: Audio feedback for interactions and alerts

### 🎨 Graphical User Interface
- **Animated Face**: Dynamic facial expressions with multiple emotions:
  - Neutral, Happy, Angry, Shy, Confused, Scared
- **Eye Animations**: Natural blinking, pupil movement, and eye tracking
- **Mouth Animation**: Synchronized lip movement during speech
- **Background Effects**: Animated starfield for enhanced visual appeal
- **Touch Interaction**: Responsive to screen taps and pats

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MARICH Robot System                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Face GUI    │  │   Chatbot    │  │   Camera     │      │
│  │  (Tkinter)   │  │   Logic      │  │   Master     │      │
│  │              │  │              │  │              │      │
│  │ - Emotions   │  │ - Vosk ASR   │  │ - Tracking   │      │
│  │ - Animation  │  │ - Ollama LLM │  │ - Detection  │      │
│  │ - Touch UI   │  │ - Piper TTS  │  │ - Recognition│      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                 │
│                   ┌────────▼─────────┐                      │
│                   │  Big Main App    │                      │
│                   │  (Orchestrator)  │                      │
│                   └────────┬─────────┘                      │
│                            │                                 │
│         ┌──────────────────┼──────────────────┐             │
│         │                  │                  │             │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐     │
│  │   Hardware   │  │   IR Remote  │  │   RPS Game   │     │
│  │   Control    │  │   Control    │  │   Engine     │     │
│  │              │  │              │  │              │     │
│  │ - Motors     │  │ - Mode Select│  │ - Gestures   │     │
│  │ - LEDs       │  │ - AI Toggle  │  │ - Strategy   │     │
│  │ - Sensors    │  │ - Navigation │  │ - Reactions  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **User Input** → IR Remote / Voice Commands / Touch Interface / Camera
2. **Processing** → Big Main App coordinates between subsystems
3. **AI Processing** → Chatbot (Vosk → Ollama → Piper) or Camera Vision
4. **Output** → Face GUI + LED Lights + Motor Actions + Voice Response

---

## 🔧 Hardware Requirements

### Core Components
- **Raspberry Pi 4 Model B** (4GB RAM minimum recommended)
- **Robot Car Chassis** (4-wheel mecanum or omnidirectional platform)
- **DC Motors** with motor driver board (L298N or similar)
- **Camera Module** (Raspberry Pi Camera v2 or USB webcam)

### Sensors & Actuators
- **Ultrasonic Distance Sensor** (HC-SR04 or I2C variant)
- **Line Tracking Sensor Module** (4-channel IR sensors)
- **RGB LED Strip** (WS2812B/NeoPixel compatible)
- **Buzzer** (active or passive)
- **IR Receiver Module** for remote control

### Power & Connectivity
- **Power Supply**: 7.4V-12V battery pack (2S-3S LiPo or 8x AA batteries)
- **Voltage Regulator**: 5V for Raspberry Pi
- **Micro SD Card**: 32GB+ Class 10 for OS and software
- **Optional**: USB Microphone for better voice recognition
- **Optional**: External speaker for louder audio output

### Display (Optional)
- 7-inch touchscreen display for face GUI interaction
- Or HDMI monitor for development/demonstration

---

## 📦 Software Dependencies

### Operating System
- **Raspberry Pi OS** (64-bit, Bullseye or newer)
- Python 3.8 or higher

### Core Python Libraries
```bash
# Computer Vision
opencv-python>=4.5.0
numpy>=1.19.0
tensorflow>=2.4.0  # For object recognition

# GUI
tkinter  # Usually pre-installed
Pillow>=8.0.0

# Audio Processing
pyaudio>=0.2.11
vosk>=0.3.45  # Speech recognition

# AI & NLP
ollama  # LLM interface
typing-extensions>=4.0.0

# Hardware Control
RPi.GPIO  # Raspberry Pi GPIO
smbus2  # I2C communication
```

### External Software
1. **Vosk Speech Recognition Model**
   - Download: [vosk-model-small-en-us-0.15](https://alphacephei.com/vosk/models)
   - Extract to project root directory

2. **Piper TTS**
   - Download from: [Piper Releases](https://github.com/rhasspy/piper/releases)
   - Voice model: `en_US-amy-medium.onnx`
   - Place in `piper/` subdirectory

3. **Ollama with Gemma 2B**
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Pull the Gemma 2B model
   ollama pull gemma2:2b
   ```

4. **TensorFlow Object Detection Models** (Optional)
   - Download SSD MobileNet COCO model
   - Extract to `CameraLib/04.Tensorflow_object_recognition/`

### Custom Hardware Libraries
The project uses proprietary hardware control libraries:
- `Raspbot_Lib` - Main robot hardware interface
- `McLumk_Wheel_Sports` - Motor control library
- `CameraLib` - Integrated camera processing library

*Note: These libraries are specific to the robot hardware platform used. The code includes simulation mode for testing without hardware.*

---

## 🚀 Installation

### 1. System Preparation

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
sudo apt-get install -y python3-pip python3-dev python3-venv
sudo apt-get install -y libportaudio2 portaudio19-dev
sudo apt-get install -y libasound2-dev
sudo apt-get install -y git

# Install OpenCV dependencies
sudo apt-get install -y libopencv-dev python3-opencv
sudo apt-get install -y libatlas-base-dev
```

### 2. Clone Repository

```bash
git clone https://github.com/MariaNakhle/Final-Project---Marich-Robot-Car-.git
cd Final-Project---Marich-Robot-Car-
```

### 3. Python Environment Setup

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt  # If available
# Or install manually:
pip install opencv-python numpy pillow pyaudio vosk ollama
```

### 4. Download Required Models

```bash
# Create directories
mkdir -p vosk-model-small-en-us-0.15
mkdir -p piper
mkdir -p CameraLib/04.Tensorflow_object_recognition

# Download Vosk model
cd vosk-model-small-en-us-0.15
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
cd ..

# Download Piper (adjust URL for ARM architecture)
cd piper
wget [Piper ARM release URL]
# Extract and ensure piper binary is executable
chmod +x piper
cd ..
```

### 5. Install Ollama & LLM

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve &

# Pull Gemma 2B model
ollama pull gemma2:2b
```

### 6. Configure Hardware

```bash
# Enable I2C, Camera, and other interfaces
sudo raspi-config
# Navigate to: Interface Options
# Enable: Camera, I2C, Serial Port

# Add user to required groups
sudo usermod -a -G i2c,gpio,video $USER

# Reboot to apply changes
sudo reboot
```

### 7. Test Installation

```bash
# Test camera
raspistill -o test.jpg

# Test audio
arecord -l  # List recording devices
aplay -l    # List playback devices

# Test Python imports
python3 -c "import cv2, vosk, tkinter; print('All imports successful')"
```

---

## 🎮 Usage Guide

### Starting the System

```bash
# Navigate to project directory
cd /path/to/Final-Project---Marich-Robot-Car-

# Run the main application
python3 big_main.py
```

### IR Remote Control Mapping

The robot is controlled via an infrared remote with the following button mappings:

| Button Code | Function | Description |
|------------|----------|-------------|
| `0x01` | Red Color Mode | Track and follow red objects |
| `0x04` | Blue Color Mode | Track and follow blue objects |
| `0x06` | Green Color Mode | Track and follow green objects |
| `0x09` | Yellow Color Mode | Track and follow yellow objects |
| `0x10` | Face Tracking | Detect and follow faces |
| `0x11` | Gesture Mode | Follow hand gestures |
| `0x12` | Object Recognition | Identify objects in view |
| `0x14` | License Plate Mode | Detect license plates |
| `0x19` | RPS Game | Play Rock-Paper-Scissors |
| `0x15` | Presentation Mode | Self-introduction sequence |
| `0x02` | AI Toggle | Enable/disable voice AI |
| `0x05` | Stop All | Stop all activities |
| `0x00` | Exit | Close application |

*Note: Button codes may vary based on your specific IR remote. Set `IR_DEBUG = True` in `big_main.py` to discover your remote's codes.*

### Voice Commands (AI Mode)

When AI mode is enabled (press `0x02`), you can use voice commands:

**Movement Commands:**
- "Move forward" / "Move back"
- "Move left" / "Move right"
- "Turn left" / "Turn right"
- "Stop"

**Action Commands:**
- "Dance" - Perform choreographed routine
- "Move square" / "Car patrol" - Execute patrol pattern

**Conversation:**
- Talk naturally to Marich
- Ask questions or make statements
- Say "goodbye" or "exit" to close AI mode

**Special Interactions:**
- **High Five**: Move your hand close (< 12cm) then quickly away
- **Pat**: Slide your finger on the screen
- **Tap**: Single tap on screen to trigger beep

### Playing Rock-Paper-Scissors

1. Press the RPS game button (`0x19`) on the IR remote
2. Marich will announce the game start
3. When prompted "Rock, Paper, Scissors, shoot!", show your gesture:
   - **Rock**: Closed fist (0 or 1 finger)
   - **Paper**: Open hand (4 or 5 fingers)
   - **Scissors**: Two fingers (2 or 3 fingers)
4. Marich will show its choice and react to the result
5. Continue playing or press Stop All to exit

### Camera Modes

Each camera mode can be activated via IR remote:

- **Color Tracking**: Robot follows objects of the selected color
- **Face Tracking**: Robot tracks and follows detected faces
- **Gesture Mode**: Robot responds to hand gestures (directional control)
- **Object Recognition**: Identifies and labels objects (uses TensorFlow)
- **License Plate**: Detects and reads vehicle license plates

### Presentation Mode

Press the Presentation button (`0x15`) to activate a pre-programmed self-introduction sequence where Marich introduces itself.

---

## 📁 Project Structure

```
Final-Project---Marich-Robot-Car-/
├── big_main.py                 # Main application orchestrator
├── chatbot_logic.py           # AI chatbot implementation
├── face_gui.py                # GUI and face animation system
├── robot_hardware.py          # Hardware control abstraction
├── rock_paper_scissors.py     # RPS game logic
├── presentation_sequence.py   # Presentation mode script
│
├── CameraLib/                 # Camera processing library
│   ├── camera_master_lib.py  # Main camera controller
│   ├── 01.Color_tracking/    # Color tracking module
│   ├── 02.Face_tracking/     # Face detection module
│   ├── 03.Gesture_following/  # Gesture recognition
│   ├── 04.Tensorflow_object_recognition/  # Object detection
│   └── 05.License_plate/     # License plate recognition
│
├── McLumk_Wheel_Sports.py     # Motor control library
├── Raspbot_Lib.py             # Robot hardware interface
│
├── vosk-model-small-en-us-0.15/  # Speech recognition model
├── piper/                     # Text-to-speech engine
│   ├── piper                  # TTS binary
│   ├── en_US-amy-medium.onnx  # Voice model
│   └── en_US-amy-medium.onnx.json  # Model config
│
├── rock.png                   # RPS game assets
├── paper.png
├── scissors.png
│
├── README.md                  # This file
├── LICENSE                    # MIT License
└── *.pdf                      # Project documentation
```

---

## 🔬 Technical Implementation

### Multi-Threading Architecture

The system uses a sophisticated multi-threaded architecture to handle concurrent operations:

```python
Main Thread (Tkinter)
├── GUI Event Loop
├── Face Animation Updates
└── Camera Frame Display

Background Threads
├── IR Remote Listener
├── AI Chatbot Thread
│   ├── Voice Recognition Loop
│   ├── Sensor Monitoring (Ultrasonic, Line Tracker)
│   └── LLM Processing
├── RPS Game Thread
├── Presentation Sequence Thread
└── Hardware Control Threads
    ├── Motor Commands
    ├── LED Sequences
    └── Sensor Polling
```

### Memory Optimization

Due to Raspberry Pi's limited RAM, the system implements aggressive memory management:

- **Lazy Loading**: Camera and AI subsystems initialized only when needed
- **Mutual Exclusivity**: Camera modes and AI mode cannot run simultaneously
- **Swap Management**: Automatic swap file creation for AI model loading
- **Process Cleanup**: Automatic termination of memory-heavy processes before AI activation
- **Garbage Collection**: Strategic Python garbage collection calls
- **Model Pre-loading**: LLM model kept in memory after first use for faster responses

### Computer Vision Pipeline

```
Camera Input
    ↓
Frame Capture (OpenCV)
    ↓
Mode-Specific Processing
├── Color Tracking → HSV color space filtering
├── Face Detection → Haar Cascade / DNN
├── Gesture Recognition → Hand landmark detection
├── Object Detection → TensorFlow SSD MobileNet
└── License Plate → OCR processing
    ↓
Action Decision
    ↓
Motor Commands / LED Updates
```

### AI Conversation Flow

```
Voice Input (Microphone)
    ↓
Vosk Speech Recognition
    ↓
Text Transcription
    ↓
Command Parsing
├── Movement Command? → Execute motor action
├── Special Keyword? → Execute specific behavior
└── General Chat → Process through LLM
    ↓
Ollama (Gemma 2B) with Emotion Detection
    ↓
JSON Response {text, emotion}
    ↓
Piper TTS Synthesis
    ↓
Audio Playback + Face Animation + LED Update
```

### Emotion System

The robot expresses emotions through multiple channels:

| Emotion | Face Display | LED Color | Behaviors |
|---------|-------------|-----------|-----------|
| Neutral | Straight mouth, normal eyes | Blue | Default state |
| Happy | Curved smile, rosy cheeks | Green | Celebrations, dance |
| Angry | Downturned mouth, angry brows | Red | Jerky movements, protests |
| Shy | Small smile, blushing | Pink/Purple | Reduced eye contact |
| Confused | Wavering mouth | Yellow | Uncertain movements |
| Scared | Wide eyes, small O mouth | Flashing Red | Alarm reactions |

### Sensor Integration

**Ultrasonic (High-Five Detection):**
```python
Distance < 120mm → Hand approached
Distance > 170mm (within 1s) → Hand receded quickly → HIGH FIVE!
```

**Line Tracker (Lift Detection):**
```python
All 4 sensors read "white" (0x00) → Robot lifted → SCARED REACTION!
```

---

## 🎬 Demonstrations

### Interactive Capabilities

1. **Natural Conversation**
   - Speak to Marich naturally
   - Context-aware responses with appropriate emotions
   - Remembers conversation history

2. **Autonomous Navigation**
   - Follows colored objects in real-time
   - Tracks and maintains distance from faces
   - Responds to hand gesture commands

3. **Game Playing**
   - Competitive Rock-Paper-Scissors with emotional reactions
   - Win celebrations with dance routines
   - Frustration displays on losses

4. **Touch Interaction**
   - Pat the screen for shy reaction
   - Tap for attention beep
   - High-five detection via ultrasonic sensor

### Example Interaction Scenarios

**Scenario 1: Morning Greeting**
```
User: [Enables AI mode]
Marich: "Hello! My name is Marich."
User: "Good morning, how are you?"
Marich: [Happy emotion] "I'm functioning optimally, thanks for asking!"
```

**Scenario 2: Playing Games**
```
User: [Presses RPS button]
Marich: "Challenge accepted! Let's play rock paper scissors!"
[Game proceeds with gesture detection]
Marich: [After winning] "Yes! I win again! Victory is mine!"
[Performs victory dance with LED light show]
```

**Scenario 3: Color Tracking**
```
User: [Presses red color button]
Marich: [Blue LEDs turn RED]
[Robot actively follows red objects with camera]
[Motors adjust to keep object centered]
```

---

## 🚀 Future Enhancements

### Planned Features
- [ ] **Autonomous Navigation**: SLAM-based room mapping and obstacle avoidance
- [ ] **Multi-Robot Coordination**: Communication protocol between multiple Marich units
- [ ] **Advanced NLP**: Upgrade to larger language models (Llama 3, GPT-4)
- [ ] **Vision Improvements**: 
  - Person re-identification
  - Emotion recognition from facial expressions
  - 3D object detection
- [ ] **Cloud Integration**: 
  - Remote monitoring via web interface
  - Cloud-based model inference
  - Data logging and analytics

### Technical Improvements
- [ ] Real-time operating system for better timing control
- [ ] Hardware acceleration for computer vision (Coral TPU, Neural Compute Stick)
- [ ] Battery management system with automatic charging
- [ ] Improved audio with beamforming microphone array
- [ ] Mobile application for remote control

### Educational Extensions
- [ ] Modular curriculum for robotics education
- [ ] Programming interface for custom behaviors
- [ ] Simulation environment for testing without hardware
- [ ] Documentation for classroom deployment

---

## 🤝 Acknowledgments

This project was developed as a Bachelor of Science final project in Computer Science, representing the culmination of academic learning in AI, robotics, and embedded systems.

### Technologies Used
- **Vosk** - Speech recognition by Alpha Cephei
- **Ollama** - LLM inference framework
- **Gemma 2B** - Language model by Google
- **Piper** - Neural text-to-speech by Rhasspy
- **OpenCV** - Computer vision library
- **TensorFlow** - Machine learning framework
- **Tkinter** - Python GUI framework

### Special Thanks
- Our academic advisors for their guidance
- The open-source community for exceptional tools
- Raspberry Pi Foundation for accessible computing platforms
- All beta testers who provided valuable feedback

### Contributors
- **Maria Nakhle** - AI Systems, Computer Vision, Integration
- **Christian** - Robotics, Hardware Control, System Architecture

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 Maria Nakhle & Christian

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

<div align="center">

**⭐ If you find this project interesting, please consider giving it a star! ⭐**

*Built with ❤️ by Maria & Christian*

</div>

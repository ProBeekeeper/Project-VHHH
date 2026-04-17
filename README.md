# 📡 Project VHHH

🎥 **[Click Here to Watch the Gameplay & Introduction Trailer](https://youtu.be/R9dOkh-zBvM)**

An Air Traffic Control simulator written in Python. Designed as an authentic training environment for those aspiring to join the Air Traffic Control industry, this project simulates the complex Hong Kong Terminal Maneuvering Area. To ensure absolute realism, all aeronautical data is sourced directly from the latest **[Hong Kong Civil Aviation Department eAIP](https://www.ais.gov.hk/)**. Furthermore, all navigational and airspace data is structured in simple `JSON` files, meaning future AIRAC cycle updates are as easy as replacing a text file.

## 👥 Project Members
[KaiWang Wu](https://github.com/ProBeekeeper), [ShingYung Chan](https://github.com/xTeStX1), [KinLam Chan](https://github.com/chakila0603)

## 🎯 Project Overview
Project VHHH is a real-time approach-and-departure radar control simulation. The primary objective is to sequence and direct aircraft to the active runways while strictly maintaining standard separation minimums. 

## ✨ Key Features & Technical Highlights

* **MVC Architecture:** Logic modules handle autonomous physics and routing, while isolated rendering pipelines manage the GUI and GPU drawing independently.
* **LNAV Routing (Dijkstra's Algorithm):** Aircraft feature autonomous route recovery. If an aircraft is vectored off-course and instructed to resume navigation, the system uses Dijkstra's shortest-path algorithm to dynamically determine the optimal forward-facing waypoint to reconnect to the STAR/SID procedure.
* **Safety Systems (TCAS & STCA):** Continuous background matrix calculations predict Short-Term Conflict Alerts up to 120 seconds in advance, drawing visual prediction lines. Features full Wake Turbulence detection and TCAS alert.
* **Text-to-Speech:** Fully threaded, asynchronous [pyttsx3](https://github.com/nateshmbhat/pyttsx3) integration for automated ATC clearances and pilot readbacks without interrupting the main game loop.
* **ILS & Glideslope Tracking:** Automated Localizer and Glideslope interception logic utilizing proportional navigation for smooth final approaches.

---

## 🚀 Installation & Quick Start

### Option 1: Download & Play (Windows)
The easiest way to jump into the radar room:
1. Go to the **[Releases](../../releases)** page of this repository.
2. Download the latest `.zip` release file.
3. Extract the folder to your computer.
4. Double-click the executable file (e.g., `Project VHHH.exe`) to start the simulator. No Python installation is required!

### Option 2: Run from Source Code
For developers or users on other operating systems (macOS/Linux):
1. Clone this repository to your local machine:
   ```
   git clone https://github.com/ProBeekeeper/project-vhhh.git
   cd project-vhhh
   ```
2. Ensure you have Python 3.9 or newer installed. Install the required dependencies:
   ```
   pip install arcade pyttsx3
   ```
3. python main.py

---

## 🎮 How to Play

As an ATC controller, you can issue commands via Mouse, Keyboard Shortcuts, or the built-in Command Line Interface.

### 🖱️ Mouse Controls
* **Select Aircraft:** `Left Click` on a radar target or click its corresponding Flight Strip on the right panel.
* **Radar Vectoring (Heading):** `Left Click & Drag` from a selected aircraft to draw a yellow target heading line. Release to issue the heading command.
* **Direct To (Waypoint):** `Drag` the heading line directly over a navigational waypoint and release. The aircraft will automatically adjust its route to fly directly.
* **Change Altitude:** `Scroll Up/Down` while an aircraft is selected to increase/decrease target altitude in 1,000 ft increments.
* **Camera Pan & Zoom:** `Left Click & Drag` on an empty map area to pan. `Scroll Up/Down` on the map to zoom in/out dynamically.

### 🎛️ UI Panel Controls
Select an aircraft to access the tactical command panel:
* **< / > Buttons:** Fine-tune Target Heading (5°), Target Speed (10kts), and Target Altitude (1,000ft).
* **APP / DEP / HOLDING:** Toggle between autonomous LNAV (following the flight plan) and manual vectoring.
* **ILS [RWY]:** Clear an arriving aircraft for the ILS approach to a specific runway.
* **HANDOFF:** Transfer communication to Tower/Radar when the aircraft is safely established on the localizer or leaving the TMA.

### ⌨️ Keyboard Shortcuts & Time Control
* `SPACE`: Pause / Resume the simulation.
* `1` to `5`: Set simulation speed from 1x to 5x.
* `0`: Fast-forward mode (20x speed).
* `ENTER`: Open/Close the Command Line Interface.

### 💻 Command Line Interface
Press `ENTER` to activate the CLI at the top left. Issue rapid text commands using the format: `[CALLSIGN] [CMD] [VALUE]`
* **Heading:** `CPA924 H 270`
* **Speed:** `CPA924 S 220`
* **Altitude:** `CPA924 A 100` *(Note: Altitude in CLI is expressed in Flight Levels. 100 = 10,000 ft)*
* *Example of chained commands:* `CPA924 H 180 S 200 A 60`

---

## ⚙️ System Settings

Click the `⚙️` gear icon in the bottom right corner to access System Settings:
* **Toggle TTS Voice:** Enable or completely mute the automated pilot/ATC voice system.
* **Runway Configuration:** Switch between **Config 07** and **Config 25** operations dynamically.

---

## 🛣️ Roadmap

The architecture is built to be highly extensible. Planned future modules include:

* **Dynamic Weather Systems:** Introduction of localized weather cells, wind vectors affecting aircraft ground speed/drift, and dynamic runway friction indices.
* **Speech Recognition:** Integration of asynchronous offline Voice-to-Text models (e.g., [Vosk API](https://github.com/alphacep/vosk-api)) allowing controllers to issue commands using a physical microphone.
* **Advanced VNAV Profiles:** Implementing strict altitude restrictions based on specific STAR/SID waypoint constraints.

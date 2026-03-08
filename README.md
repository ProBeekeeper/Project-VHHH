# ATC Simulator (Task 1)

A 2D vector-based Air Traffic Control (ATC) simulator written in Python. This project focuses on radar rendering, collision detection algorithms, and Object-Oriented Programming software architecture.

### 👥 Project Members

KaiWang Wu, ShingYung Chan, KinLam Chan

### 🎯 Project Overview

ATC Simulator is an approach radar control simulation. The primary objective is to direct aircraft to the active runway while strictly maintaining standard separation minimums (3 nautical miles horizontally, 1000 feet vertically).

The simulator uses GPU-accelerated graphics to render multiple flight vectors, radar UI elements, and map geometries simultaneously without performance degradation.

**To sum up**: Just a game with OOP.

### ✨ Key Features

* Radar Interface: Sweeping radar UI with target history trails.

* JSON Map Parsing: Airspace sectors, airways, and coastlines are dynamically generated from JSON configuration files.

* Flight Vectoring: Command interface to issue heading (HDG), altitude (ALT), and speed (SPD) instructions to aircraft objects.

* Conflict Detection (TCAS): Automated visual and auditory alerts triggered when aircraft breach separation minimums.

* Flight Data Blocks: Real-time display of callsigns, current altitudes, and speed vectors adjacent to radar targets.

### 🛠️ Technology Stack & Architecture

This project is structured around Object-Oriented Programming (OOP) principles to model the physical entities of air traffic control.

1. Core Framework

Python Arcade: Utilized for OpenGL/GPU acceleration. It efficiently processes rendering operations for thousands of vector lines (map data) via ShapeElementLists.

2. Software Architecture (OOP)

Encapsulation: The Aircraft class processes its own kinematics (e.g., turn rates, descent profiles). The core Tower system interacts with aircraft solely by passing vector commands, preventing direct manipulation of an aircraft's absolute coordinates.

Polymorphism: Derived classes such as CommercialJet and Helicopter inherit from a base Flight class, executing shared commands using internal logic.

3. Algorithm Optimizations

Spatial Partitioning: To optimize collision detection, the airspace is divided into a grid matrix. Aircraft only compute distances against entities within their immediate or adjacent cells, reducing the computational complexity from $O(n^2)$ to a near-linear scale.

Surface Caching: Static JSON map geometries are rendered once into GPU memory during the initialization phase, rather than being redrawn in the main rendering loop.

### 🛣️ Roadmap

The following features are planned for future development iterations:

*  Weather Systems: Dynamic weather

* Text-to-Speech (TTS): Automated readbacks for ATC clearances.

* Speech Recognition (v2.0): Integration of asynchronous Voice-to-Text models (e.g., Vosk) for controller inputs. (Maybe, if enough time)

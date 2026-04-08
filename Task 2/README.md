# Road Connector - Kruskal's MST Simulation Game

## 1. Project Introduction
[cite_start]**Road Connector** is an interactive simulation game developed for the **COMP2090SEF/COMP8090SEF/S209W** course project. The game challenges players to connect multiple cities with the minimum total construction cost, effectively simulating the real-world problem of designing efficient infrastructure networks.

[cite_start]This project serves as the submission for **Task 2: Self-study on a new data structure AND a new algorithm**[cite: 16].

## 2. Core Features
* **Interactive Gameplay**: Click to connect cities and build your own road network.
* [cite_start]**Real-time Validation**: Uses **Disjoint Set Union (DSU)** to detect if two cities are already connected, preventing redundant construction[cite: 126].
* [cite_start]**Algorithmic Demonstration**: Provides a "Show MST" feature that visualizes the optimal solution using **Kruskal's Algorithm**[cite: 126].
* **Scoring System**: Compares your total cost against the theoretical minimum and provides a performance score.
* **Bilingual Support**: Full support for both English and Chinese (简体中文) interfaces.

## 3. Self-Study Topics (Task 2)
[cite_start]As required by the curriculum, this project explores a new data structure and a new algorithm not covered in the standard course[cite: 40]:

### A. Data Structure: Disjoint Set Union (DSU)
* [cite_start]**Abstract Data Type (ADT)**: Manages a partition of a set into disjoint subsets[cite: 45].
* **Optimizations**: 
    * **Path Compression**: Flattens the structure of the tree, making future operations faster.
    * **Union by Rank**: Ensures the tree remains balanced.
* [cite_start]**Application**: Used for cycle detection and connectivity checks in the game[cite: 126].



### B. Algorithm: Kruskal's Algorithm
* **Purpose**: A greedy algorithm used to find the **Minimum Spanning Tree (MST)** for a connected weighted graph.
* [cite_start]**Complexity**: Analyzed as $O(E \log E)$ where $E$ is the number of potential roads (edges)[cite: 46].
* **Process**: Sorts all potential edges by cost and adds them to the tree using DSU to ensure no cycles are formed.



## 4. Installation & Execution
### Prerequisites
* Python 3.x
* Pygame library

### Setup
1. Clone the repository:
   ```bash
   git clone <your-github-link>
Install dependencies:

Bash
pip install pygame
Run the game:

Bash
python main_en.py
5. Project Structure

dsu.py: Implementation of the Disjoint Set Union class with optimizations.


game.py: Main game logic, UI rendering, and Kruskal's algorithm implementation.


main_en.py: The entry point for the application

# 🧹 Video-GIF Pair Cleaner: Automated Directory Optimization

A robust Python-based utility designed to audit and clean directories containing paired media assets. This tool identifies orphaned video or GIF files and ensures your dataset remains synchronized and clutter-free.

## 🚀 The Problem it Solves
When generating GIFs from videos (or vice versa) in bulk, failed processes often leave "orphaned" files. This script automates the manual task of cross-referencing filenames to keep only the valid pairs.

## ✨ Key Features
* **Smart Matching:** Identifies pairs based on filenames regardless of extension.
* **Batch Processing:** Handles thousands of files in seconds.
* **Safety First:** Includes a dry-run mode or logging to prevent accidental deletion.
* **Lightweight:** Zero heavy dependencies; runs on pure Python logic.

## 🛠 Tech Stack
* **Language:** Python 3.x
* **Core Modules:** `os`, `pathlib`, `shutil`

## 📦 Usage
1. Place the script in your target directory (or pass the path as an argument).
2. Run the cleaner:
   ```bash
   python cleaner.py --path ./my-media-folder

   

# video-gif-pair-cleaner
Safely deletes video and GIF pairs when both exist in a folder, leaving unmatched files untouched
<img width="1096" height="339" alt="image" src="https://github.com/user-attachments/assets/4025da8d-522e-4196-8584-dde2566c82c2" />
<img width="1007" height="314" alt="image" src="https://github.com/user-attachments/assets/c7f937d4-0eae-4eea-9cf8-d0a1e622e0f5" />
<img width="1046" height="243" alt="image" src="https://github.com/user-attachments/assets/a3b56b4f-896c-4d45-98cc-2d430d656716" />



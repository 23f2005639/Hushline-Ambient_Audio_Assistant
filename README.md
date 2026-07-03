# Hushline Ambient Audio Assistant

Automatically pauses active system media when speech is detected and resumes playback after silence.

## 🚀 Getting Started

This project is managed with [uv](https://github.com/astral-sh/uv).

### Installation

1. Install `uv` if not already installed.
2. Install system dependencies:
   ```bash
   sudo apt-get install -y libportaudio2 playerctl
   ```
3. Sync environment and install package dependencies:
   ```bash
   uv pip install -e .
   ```

### Running

To start the assistant:
```bash
uv run hushline
```

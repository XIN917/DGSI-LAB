# DGSI-Lab1

This project is a laboratory exercise for the DGSI course, focusing on Large Language Models (LLMs) and related technologies.

## Requirements

- Python >= 3.10, < 3.13
- [uv](https://github.com/astral-sh/uv) for dependency management

## Installation

1.  **Clone the repository** (if not already done):
    ```bash
    git clone git@github.com:Zhipeng139/DGSI-Lab1.git
    cd DGSI-Lab1
    ```

2.  **Install dependencies using `uv`**:
    This project uses `uv` for fast dependency management.

    ```bash
    # Install uv if you haven't already
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Sync dependencies
    uv sync
    ```

    This will create a virtual environment at `.venv` and install all required packages.

## Technologies Used

Based on `pyproject.toml`, this project uses:
- **llm**: Utility for interacting with LLMs.
- **anthropic** & **openai**: Clients for accessing AI models APIs.
- **transformers** & **torch**: Libraries for deep learning and running local models.
- **pydantic**: For data validation.

## Usage

To run scripts within the virtual environment, use `uv run`:

```bash
uv run python your_script.py
```

Or activate the virtual environment manually:

```bash
source .venv/bin/activate
python your_script.py
```

## Project Structure

- `pyproject.toml`: Project configuration and dependencies.
- `uv.lock`: Locked dependency versions.
- `README.md`: Project documentation.

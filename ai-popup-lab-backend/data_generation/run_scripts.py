from pathlib import Path
import csv
import subprocess
from pprint import pprint
import os

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math
import warnings
from matplotlib.lines import Line2D

class _StatsFallback:
    @staticmethod
    def spearmanr(a, b):
        a_series = pd.Series(a)
        b_series = pd.Series(b)
        valid = ~(a_series.isna() | b_series.isna())
        if valid.sum() < 2:
            return np.nan, np.nan
        corr = a_series[valid].corr(b_series[valid], method="spearman")
        return float(corr), np.nan

BASE_DIR = Path(__file__).resolve().parent.parent
SURVEYS_DIR = BASE_DIR / "country_data" / "surveys"
EXTENDED_FRAMES_DIR = BASE_DIR / "country_data" / "extended_frames"

r_executable = os.getenv("RSCRIPT_PATH", "Rscript")

def run_survey_script(frame_filepath, environment, country):

    # R survey generation script is ran, return output directory and filename

    return SURVEYS_DIR / f"{country}_survey.csv"

def run_extension_script(

    survey_path: str | Path,
    frame_path: str | Path,
    environment: str,
    country: str,
    n_sims: int = 250,
) -> Path:
    """
    run the frame extension R script on the given survey and frame files.

    Args:
        survey_path: Path to the survey CSV file.
        frame_path: Path to the frame CSV file.
        environment: String saying which environment code is being ran on
        country: String of country name
        n_sims: Number of simulations to run (default: 250).

    Returns:
        Path to the output directory.
    """

    survey_path = Path(survey_path).resolve()
    frame_path = Path(frame_path).resolve()

    # this file lives in ai-popup-lab-backend/data_generation/
    this_file = Path(__file__).resolve()
    backend_root = this_file.parent.parent  # goes up to project root so ai-popup-lab-backend/
    r_script = backend_root / "data_generation" / "scripts" / "run_post_strat_cli.R"
    output_dir = backend_root / "data_generation" / "output" / "extension_output"

    if not r_script.exists():
        raise FileNotFoundError(f"R script not found at: {r_script}")

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        r_executable,
        str(r_script),
        str(survey_path),
        str(frame_path),
        str(output_dir),
        str(n_sims),
    ]

    print("Running command:")
    print(" ".join(cmd))

    result = subprocess.run(cmd, cwd=backend_root, capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"R script failed with exit code {result.returncode}")

    print("Finished. Outputs written to", output_dir)

    return output_dir
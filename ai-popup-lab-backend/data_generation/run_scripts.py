from pathlib import Path
import subprocess
import os
import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
SURVEYS_DIR = BASE_DIR / "country_data" / "surveys"
EXTENDED_FRAMES_DIR = BASE_DIR / "country_data" / "extended_frames"

R_EXECUTABLE = os.getenv("RSCRIPT_PATH", "Rscript")

def check_r_available():
    result = subprocess.run([R_EXECUTABLE, "--version"], capture_output=True)
    if result.returncode != 0:
        raise EnvironmentError("Rscript not found. Is R installed in the container?")

def run_survey_script(frame_filepath, environment, country):

    # R survey generation script is ran, return output directory and filename

    return SURVEYS_DIR / f"{country}_survey.csv"

def run_extension_script(

    survey_path: str | Path,
    frame_path: str | Path,
    output_dir: Path,
    country: str,
    n_sims: int = 250,
) -> Path:
    """
    run the frame extension R script on the given survey and frame files.

    Args:
        survey_path: Path to the survey CSV file.
        frame_path: Path to the frame CSV file.
        output_dir: Directory where R should write its output.
        country: String of country name
        n_sims: Number of simulations to run (default: 250).

    Returns:
        Path to the output directory.
    """

    survey_path = Path(survey_path).resolve()
    frame_path = Path(frame_path).resolve()

    output_dir  = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    r_script = Path(__file__).resolve().parent / "scripts" / "run_post_strat_cli.R"

    if not r_script.exists():
        raise FileNotFoundError(f"R script not found at: {r_script}")
    if not survey_path.exists():
        raise FileNotFoundError(f"Survey file not found: {survey_path}")
    if not frame_path.exists():
        raise FileNotFoundError(f"Frame file not found: {frame_path}")

    cmd = [
        R_EXECUTABLE,
        str(r_script),
        str(survey_path),
        str(frame_path),
        str(output_dir),
        str(n_sims),
    ]

    logger.info("Running R script for country=%s", country)
    logger.info("Command: %s", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=4500)

    if result.stdout:
        logger.info("R stdout:\n%s", result.stdout)
    if result.stderr:
        logger.warning("R stderr:\n%s", result.stderr)
    if result.returncode != 0:
        raise RuntimeError(
            f"R script failed (exit {result.returncode}) for {country}.\n"
            f"stderr: {result.stderr}"
        )

    logger.info("R script completed for country=%s. Outputs in %s", country, output_dir)
    return output_dir
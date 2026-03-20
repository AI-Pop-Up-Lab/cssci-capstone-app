from pathlib import Path

# Expose the persona_chat package under the legacy "app" package name
# so the imported standalone project can run inside this backend.
__path__ = [str(Path(__file__).resolve().parents[1] / "persona_chat")]

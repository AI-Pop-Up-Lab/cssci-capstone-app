"""Shared configuration for persona chat mode selection and model access."""

import os

from dotenv import load_dotenv


# =============================================================================
# Environment Loading
# =============================================================================

# Load environment variables once for the whole package.
load_dotenv()


# =============================================================================
# Runtime Switches
# =============================================================================

USE_LIGHTWEIGHT_RESPONSE = False


# =============================================================================
# Model Configuration
# =============================================================================

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL")
AZURE_OPENAI_BASE_URL = os.getenv("AZURE_OPENAI_BASE_URL")

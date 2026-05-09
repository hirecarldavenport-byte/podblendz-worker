"""
Application Settings
--------------------

Basic configuration for PodBlendz.

This file is used by ingestion + audio modules.
"""

# =================================
# AWS CONFIG (TEMP / LOCAL DEV)
# =================================

# ✅ Region for AWS services
AWS_REGION = "us-east-1"

# ✅ S3 Bucket for storing audio
# (this can be a placeholder for now)
EPISODE_AUDIO_BUCKET = "podblendz-audio-dev"


# =================================
# SYSTEM FLAGS (OPTIONAL)
# =================================

# Toggle S3 usage later if needed
USE_S3 = False
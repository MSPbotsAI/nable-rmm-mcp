from .._json import error_envelope

NO_TOKEN = error_envelope(
    "not_configured", "No N-able RMM API key. Send the X-Nable-Api-Token header.", False
)

class Codes:
    SUCCESS = "S000"

    INVALID_ARGS = "E100"
    INPUT_NOT_FOUND = "E110"
    UNSUPPORTED_INPUT = "E120"
    STEP_MISMATCH = "E130"

    PREPROCESS_FAIL = "E200"
    TRANSCRIBE_FAIL = "E210"

    AI_KEY_MISSING = "E300"
    AI_CALL_FAIL = "E310"
    PROMPT_MISSING = "E320"

    FILE_IO = "E400"
    INTERNAL = "E500"

    UPLOAD_FAIL = "E600"
    DOWNLOAD_FAIL = "E610"
    TASK_FAIL = "E620"


def format_message(code, message, details=None):
    msg = f"[{code}] {message}"
    if details:
        msg += f" | {details}"
    return msg


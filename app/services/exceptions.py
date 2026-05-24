"""Custom exception classes for the OCR service.

These are caught by exception handlers in main.py and mapped to
standardized HTTP responses:
    - OCRValidationError  → 400 (user-correctable input errors)
    - OCRRuntimeError     → 500 (internal system failures)
"""


class OCRValidationError(ValueError):
    """Raised for invalid user input (bad file type, malformed URL, etc.).

    Caught by the validation_error_handler in main.py to return HTTP 400.
    """


class OCRRuntimeError(RuntimeError):
    """Raised for internal system failures (conversion failure, OCR crash, etc.).

    Caught by the runtime_error_handler in main.py to return HTTP 500.
    """

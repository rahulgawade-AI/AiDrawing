"""
Validation Result.
"""

from dataclasses import dataclass, field


@dataclass
class ValidationResult:

    passed: bool = True

    warnings: list[str] = field(default_factory=list)

    errors: list[str] = field(default_factory=list)

    statistics: dict = field(default_factory=dict)

    # ---------------------------------------------

    def add_error(self, message: str):

        self.errors.append(message)

        self.passed = False

    # ---------------------------------------------

    def add_warning(self, message: str):

        self.warnings.append(message)

    # ---------------------------------------------

    @property
    def error_count(self):

        return len(self.errors)

    @property
    def warning_count(self):

        return len(self.warnings)
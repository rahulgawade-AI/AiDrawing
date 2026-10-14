from .optimizer import DesignOptimizer
from .validator import DesignValidator
from .cad_spec import build_cad_payload

class DrawingDesignService:
    def __init__(self, validator=None):
        self.validator = validator or DesignValidator()

    def generate(self, *, site, regulatory, preferences, unit_mix):
        design = DesignOptimizer(site, regulatory, preferences, unit_mix).optimize()
        validation = self.validator.validate(design)
        design.validation = validation
        return design, {
            "design": design.to_dict(),
            "validation": validation,
            "cad_payload": build_cad_payload(design),
        }

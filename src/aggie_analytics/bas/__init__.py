"""Scientific BAS label contracts plus W20 starter forecast interfaces."""
from .contracts import ExpectedMarginEvidence
from .labels import (
    build_tamu_bas_label, performance_residual, severity_flags,
    validate_nested_probability_forecast, descriptive_excess_rate,
)
__all__=['ExpectedMarginEvidence','build_tamu_bas_label','performance_residual','severity_flags','validate_nested_probability_forecast','descriptive_excess_rate']

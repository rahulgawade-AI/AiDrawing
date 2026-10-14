class WorkflowError(Exception):
    """Base workflow exception."""


class WorkflowExecutionError(WorkflowError):
    """Workflow execution failed."""


class InvalidWorkflowStateError(WorkflowError):
    """Workflow state is invalid."""
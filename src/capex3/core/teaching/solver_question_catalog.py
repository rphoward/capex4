"""Compatibility exports for solver-question catalog now owned by capex3.core."""

from capex3.core.solver_question_catalog import (
    SOLVER_QUESTION_CATALOG,
    SELECTED_SOLVER_QUESTIONS,
    SelectedSolverQuestion,
    SolverQuestionTarget,
    list_selected_solver_questions,
    selected_solver_question_catalog_to_contract,
)

__all__ = [
    "SELECTED_SOLVER_QUESTIONS",
    "SOLVER_QUESTION_CATALOG",
    "SelectedSolverQuestion",
    "SolverQuestionTarget",
    "list_selected_solver_questions",
    "selected_solver_question_catalog_to_contract",
]

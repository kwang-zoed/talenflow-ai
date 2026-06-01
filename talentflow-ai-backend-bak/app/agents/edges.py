from typing import Literal

from app.agents.state import AgentState


def route_after_fetch(state: AgentState) -> Literal["optimize_resume", "save_record"]:
    if state.get("skip_generation") is True:
        return "save_record"
    return "optimize_resume"

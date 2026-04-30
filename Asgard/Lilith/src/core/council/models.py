"""
Modelos de datos del sistema Council.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class VoteOption(Enum):
    STRONGLY_FAVOR = 2
    FAVOR = 1
    NEUTRAL = 0
    AGAINST = -1
    STRONGLY_AGAINST = -2


@dataclass
class AgentOpinion:
    agent_name: str
    option_id: str
    vote: VoteOption
    reasoning: str
    confidence: float  # 0.0–1.0


@dataclass
class ProposalOption:
    id: str
    title: str
    description: str
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    implications: List[str] = field(default_factory=list)


@dataclass
class CouncilProposal:
    id: str
    title: str
    context: str
    question: str
    options: List[ProposalOption]
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CouncilSession:
    proposal: CouncilProposal
    participants: List[str]
    opinions: List[AgentOpinion] = field(default_factory=list)
    deliberation_log: List[str] = field(default_factory=list)
    final_decision: Optional[str] = None
    consensus_reached: bool = False
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None

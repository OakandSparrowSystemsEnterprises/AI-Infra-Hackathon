from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .ports import AuthorityPort, DurableGraphPort, EffectPort, LiveStatePort, MuscleMemoryPort, SandboxPort, SecurityScannerPort, SemanticMemoryPort


@dataclass
class RuntimePorts:
    semantic_memory: SemanticMemoryPort
    durable_graph: DurableGraphPort
    live_state: LiveStatePort
    sandbox: SandboxPort
    security: SecurityScannerPort
    muscle_memory: MuscleMemoryPort
    authority: AuthorityPort
    effect: EffectPort


class CompositionRoot:
    """Event-time composition root.

    No sponsor implementations are shipped pre-event. The constructor is gated so
    functional wiring cannot be accidentally represented as pre-event work.
    """

    @staticmethod
    def wire(settings: Settings, **_: object) -> RuntimePorts:
        settings.require_build_open()
        raise NotImplementedError("Implement sponsor and authority adapters during the event build period")

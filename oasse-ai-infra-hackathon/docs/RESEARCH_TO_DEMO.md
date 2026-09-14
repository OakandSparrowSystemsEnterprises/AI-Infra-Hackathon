# Research to Demo Mapping

The hackathon shell operationalizes the Architecture of Authority research claim that authorization is the last legitimate bottleneck after computation compresses memory, retrieval, interpretation, coordination, and execution latency. The robot makes that distinction observable because an irreversible physical effect cannot be repaired by a post-hoc log alone.

The demonstration also carries forward the agent-handoff finding from OASSE's Gatekeeper V2 research. Gatekeeper V2 itself is not included in this repository. Artifact identity and actor identity are separate from authority. A valid principal can be denied. A valid artifact can move between principals without transferring permission. For the physical build, the exact evidence identity and exact proposed action are bound into the pre-dispatch decision.

The legal-reconciliation program contributes a second constraint: runtime authority should use pre-resolved deterministic policy rather than ask a model to improvise law at execution time. The hackathon policy is intentionally small and declared. It is not represented as the full legal corpus.

## Invariant-preserving authority

The deeper mathematical language for the demo is

$$
I(x_{n+1})=I(x_n)=\iota,
\qquad
X_I=\{x:I(x)=\iota\},
\qquad
C_I:X_I\rightarrow X_I.
$$

The value being governed defines the admissible transition space. Perception supplies evidence, a planner proposes an action, and authority selects only an invariant-preserving transition for execution. This yields the simple presentation sequence:

```text
Observe -> Propose -> Project into the admissible state space -> Execute -> Prove
```

The defect case is deliberately important here. A nonzero anomaly score is a fact supplied by perception, not automatically an authority violation. The governing policy may still admit the reject-route transition.

## GOI connection: a methodological distinction, not a validation claim

The GOI work is not used as a robotics safety premise, a quantum-gravity claim, or a hackathon scoring claim. Its relevance is a structural distinction that helps prevent overclaiming.

The recent work makes explicit that preserving a projected sector does not uniquely determine the transport connecting states:

$$
\Pi_B\not\Rightarrow\Phi_{xy}.
$$

The direct authority analogue is:

$$
\text{Invariant}\neq\text{policy for choosing the unique next action}.
$$

The invariant restricts what may happen. It does not choose which admissible action is optimal. Multiple transport laws may preserve the same admissible sector.

A compatible transport is therefore written

$$
x_{n+1}=\Phi_{xy}^{(n)}(x_n),
\qquad
x_n,x_{n+1}\in X_I,
\qquad
I(x_{n+1})=I(x_n)=\iota.
$$

When an actual sector projector `\Pi_I` is defined, the stronger authority-preserving condition is

$$
\Pi_I\circ\Phi_{xy}^{(n)}
=
\Phi_{xy}^{(n)}\circ\Pi_I
=
\Phi_{xy}^{(n)}.
$$

In the hackathon this is an explanatory model for why authority belongs before effect: the permitted transport should remain inside the admissible sector rather than execute first and be judged afterward.

The Planck-to-quark branch also supplies a useful research discipline. The work stopped when its axioms did not uniquely determine the remaining microscopic dynamics instead of tuning the answer into existence. The same discipline applies here: demonstrate the authority properties the implementation actually proves, and do not claim the invariant uniquely chooses the optimal action.

See [AUTHORITY_INVARIANT.md](AUTHORITY_INVARIANT.md) for the full formulation, including the exploratory zero-contradiction whiteboard notation and its explicit non-theorem status.

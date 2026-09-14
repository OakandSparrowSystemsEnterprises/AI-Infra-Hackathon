# Authority as an Invariant-Preserving Transition System

This document is the deeper conceptual architecture behind the existing Physical AI implementation. It does **not** replace the working Gatekeeper execution path, and it does **not** claim that GOI has solved quantum gravity, particle physics, robotics safety, or optimal control. The mathematics here is used to explain the authority boundary more precisely.

## Core invariant

Let `x_n` be the current system state and let `I` be the authoritative invariant whose value must survive an executable transition.

$$
\boxed{I(x_{n+1})=I(x_n)=\iota}
$$

Define the admissible state space

$$
X_I=\{x\in X:I(x)=\iota\}.
$$

Then an admissible command or controlled transition must satisfy

$$
\boxed{C_I:X_I\rightarrow X_I.}
$$

The shortest statement of the architecture is therefore

$$
\boxed{C_I:X_I\rightarrow X_I\qquad\text{with}\qquad I(C_I(x))=I(x)=\iota.}
$$

This is stronger than saying "evaluate a rule after a command is proposed." The governing value defines which state transitions count as executable actions at all.

## Observe, propose, project, execute, prove

Perception supplies evidence about the current physical state,

$$
e_n=P(x_n),
$$

and an agent, planner, human, robot, or VLA proposes

$$
a_n=C_n(x_n).
$$

Authority then maps that proposal into the admissible action space:

$$
\boxed{
\widehat a_n
=
\Pi_{I,e_n}(a_n)
=
\begin{cases}
a_n,
& I(E(a_n),e_n)=\iota,\\[4pt]
a_n',
& I(E(a_n),e_n)\neq\iota\land I(E(a_n'),e_n)=\iota,\\[4pt]
\bot,
& \nexists a' : I(E(a'),e_n)=\iota.
\end{cases}
}
$$

Here `E` denotes the effect of an action on the state. `\Pi_{I,e_n}` is an authority selection/projection operator in the architectural sense; it is not being asserted to be an orthogonal projector in a Hilbert space.

The three branches correspond directly to the current Gatekeeper semantics:

- unchanged admissible proposal -> **ALLOW**;
- admissible replacement -> **TRANSFORM**;
- no executable action under the current evidence/policy state -> **HOLD** or **DENY**, with policy reason codes distinguishing those cases.

Execution is then

$$
\boxed{
x_{n+1}
=
\begin{cases}
E(\widehat a_n),&\widehat a_n\neq\bot,\\
x_n,&\widehat a_n=\bot.
\end{cases}
}
$$

The project can therefore be summarized as

```text
Observe
  -> Propose
  -> Project into the admissible state space
  -> Execute
  -> Prove
```

## Perception is not authority

A key implementation fact becomes clearer in this formulation:

$$
\boxed{\text{Perception supplies facts. Authority determines admissibility.}}
$$

A detected anomaly is not automatically an authority violation. In the existing defect scenario, perception can report a nonzero anomaly score while the proposed reject action still receives ALLOW because the governing policy remains satisfied.

That separation is intentional. OpenVINO/Anomalib can answer questions about what is observed. The planner can answer what it proposes to do. The authority boundary answers whether that exact transition is executable now.

## Asimov connection

Asimov-style robotic laws are useful as a thought experiment because they expose the problem of self-consistent behavior under higher-order constraints. But linguistic rules still require interpretation at runtime.

This architecture attempts a stricter formulation: the robot is not merely told to remember a rule such as "do not violate invariant `I`." Its executable transition space is restricted to `X_I`.

That does **not** solve ethics or prove that every important human value can be reduced to a single invariant. It gives the hackathon a precise way to describe a narrower engineering claim: declared authority constraints can define an admissible transition space before physical effect.

## The invariant does not choose the unique next action

The recent GOI work contributes a useful methodological distinction, not a physical justification for Gatekeeper.

In that work, preserving a projected sector does not uniquely determine the dynamics that connect states:

$$
\boxed{\Pi_B\not\Rightarrow\Phi_{xy}.}
$$

The analogous authority statement is

$$
\boxed{\text{Invariant}\neq\text{policy for choosing the unique next action}.}
$$

The invariant constrains what may happen. It does not determine which admissible action is optimal, preferred, or uniquely correct among all actions that preserve the invariant.

A transport-level formulation is

$$
\boxed{
x_{n+1}=\Phi_{xy}^{(n)}(x_n),
\qquad x_n,x_{n+1}\in X_I,
\qquad I(x_{n+1})=I(x_n)=\iota.
}
$$

When a well-defined projector `\Pi_I` onto the admissible sector exists, the stronger structural condition is

$$
\boxed{
\Pi_I\circ\Phi_{xy}^{(n)}
=
\Phi_{xy}^{(n)}\circ\Pi_I
=
\Phi_{xy}^{(n)}.
}
$$

This expresses the design goal that the transport itself remain inside the authority-preserving sector rather than allowing an invalid transition and detecting it only afterward. In the hackathon implementation, the practical counterpart is the pre-send Gatekeeper/dispatch boundary.

## Exploratory zero-contradiction notation

The original whiteboard expression remains a provisional research notation:

$$
\boxed{
C\,\Delta_\mu
\left[
\theta_\Sigma^\infty\Delta
\right]_\infty^{\mu\epsilon}
=0.
}
$$

Its intended interpretation is that allowable evolution has zero component in a contradiction-producing direction. This notation is exploratory. It is **not** presented as a proved theorem, a standard identity, or a derived law of robotics.

## Research discipline from GOI

The useful lesson from the recent Planck-to-quark GOI branch is methodological. The work reached a structured `N=5`, `3+2` carrier description and then stopped when the existing axioms did not uniquely determine the inter-state channel, Yukawa matrices, quark masses, or CKM structure. The unresolved pieces were treated as underdetermined rather than tuned into existence.

The hackathon should use the same discipline. We can claim that the architecture constrains execution to invariant-preserving transitions and that the implementation demonstrates ALLOW, TRANSFORM, HOLD/DENY behavior, evidence binding, physical execution, and receipt chaining. We should **not** claim that the invariant itself discovers the uniquely optimal action or that GOI validates the robotics architecture.

## Mapping to the current code

The mathematics describes the roles already present in the repository:

- `EvidenceFrame` is the explicit runtime evidence `e_n`.
- `ProposedAction` is the proposal `a_n`.
- `AuthorityClient` / `GatekeeperClient` implement the pre-execution authority boundary.
- `ALLOW` preserves the proposed transition.
- `TRANSFORM` substitutes an explicitly authorized admissible transition.
- `HOLD` / `DENY` produce no actuator dispatch.
- the dispatch guard rechecks freshness, replay/binding, scene state and receipt integrity before effect.
- outcome and task-verification receipts provide the **Prove** stage after execution.

Nothing in this document requires rebuilding those components. The implementation remains the operational proof. This layer explains why the separation matters.

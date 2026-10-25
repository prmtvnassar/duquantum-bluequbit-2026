# BlueQubit / DuQuantum context

The current operational policy is [docs/history/workflow_final_graded.md](history/workflow_final_graded.md). This page explains the physical task; superseded interface assumptions are retained only in docs/history.

The released challenge has three public samples (50 independent programs) and four graded problems (140 ID-only programs). Each target is the expectation of Z on the qubit named in its ID after running that program from the all-zero state. The downloaded circuit already contains the intended echo; do not add another OTOC construction.

An out-of-time-order correlator checks how an initially local perturbation spreads through an evolving quantum system. In these echo circuits, forward and backward evolution allow operator paths to interfere. A small intermediate amplitude can matter later, so truncating a state or operator can change the final observable in either direction.

MPS limits the Schmidt rank retained across cuts of the state; increasing chi allows more entanglement but costs memory and time. Pauli propagation instead evolves the measured operator backward, expressing it as a sum of Pauli strings. Clifford gates mainly permute strings; non-Clifford rotations can branch them. A coefficient cutoff reduces the retained sum.

Neither approximation has a universal sign of error. They can agree through a shared bias or stabilize temporarily. That is why the workflow measures both precision sensitivity and reference error, and does not equate agreement with a guaranteed answer.

Qiskit/BlueQubit Pauli strings put qubit zero at the rightmost position. A target q in an n-qubit ID uses "I"*(n-1-q)+"Z"+"I"*q. All required IDs must have their own genuine outputs.

The local OBP eta budget in the exploratory notebook bounds discarded Pauli mass and is distinct from a per-coefficient epsilon cutoff. The final local PPS kernel merges duplicate strings before applying its cutoff. Native BlueQubit PPS can transform gates differently during transpilation, so local/native precision values are not interchangeable error guarantees.

For the derivation and research context, see [the stopping-criteria report](../reports/MPS%20PPS%20stopping%20criteria.md), the accompanying research notes, and the papers retained in papers/. The live [challenge page](https://app.bluequbit.io/hackathons/2GMaAenu3iSsIC6Z) is authoritative for released rules.

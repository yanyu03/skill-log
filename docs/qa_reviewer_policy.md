# Reviewer-authority QA policy

The semantic QA department acts like an academic reviewer, not a binary factory kill-switch.

## Decisions

- `ACCEPT`: academic content may unlock Office composition.
- `MINOR_REVISION`: non-critical wording/linkage issue. A draft may continue when profile policy allows it, but review comments remain attached.
- `MAJOR_REVISION`: fixable factual, evidence, calculation or reference issue. Office composition is blocked; the scheduler routes work back to the responsible worker and requires semantic re-review.
- `REJECT`: reserved for non-reviewable integrity failures or an unusable verification provider/report. It is not the default response to an ordinary bad citation or unsupported sentence.

## Authority boundaries

Citation verification is a specialist reviewer that reports findings; it does not own final manuscript disposition. The central semantic reviewer combines citation, evidence and calculation findings and assigns the academic decision. QA may require evidence, replacement references, added derivation, or wording downgrade, but must not silently rewrite academic substance. Office/template workers never override academic review.

## Undergraduate thesis defaults

At least five English references must be externally verified. Entity mismatch or an unmet English threshold is normally `MAJOR_REVISION`, not terminal `REJECT`.

Unsupported `measured` or `simulated` claims are normally returned with `PROVIDE_EVIDENCE_OR_DOWNGRADE_CLAIM`. Absolute claims such as “绝对不会/彻底杜绝/零损伤” are returned for conditional wording or stronger evidence. Heading labels are navigation, not evidence-bearing claims.

## Traceability

Scheduler completion records may attach review evidence. A later reviewer should be able to reconstruct the decision, the responsible worker, the required action, and whether the finding blocked Office composition.

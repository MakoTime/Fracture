---
name: Block Relationships and Invalidation
description: "Use when creating or modifying parent-child block relationships, dependency lifetime, invalidation propagation, change callbacks, destruction, or related engine tests in this project."
applyTo:
  - "engine/block_objects/**/*.py"
  - "engine/block_tasks/**/*.py"
  - "engine/task.py"
  - "objects/**/*.py"
  - "tests/test_engine.py"
  - "tests/test_registration.py"
  - "tests/test_project_serializer.py"
---

# Block Relationships and Invalidation

Block relationships are directional. A child provides data to a parent, and the parent consumes the child.

## Relationship Rules

- Use `parent.add_child_block_object(child, dependent=False)` or `child.add_parent_block_object(parent, dependent=False)` to create a normal data relationship.
- Use `remove_child_block_object()` or `remove_parent_block_object()` to remove relationships; do not edit the private relationship lists directly.
- Reject self-parent relationships.
- Keep both sides of every relationship synchronized through the public relationship methods.
- Use stable block GUIDs for task bindings and serialization identity, not object identity alone.
- Do not create a relationship merely to share a value; create one when the parent must respond to the child's state or lifetime.
- When both sides are represented by project objects, every registered block relationship must also be visible as a child alias in the parent object's tree node.
- Tree aliases must be synchronized after object registration and project deserialization, and must not duplicate the child's canonical tree node.

## Normal Child Relationships

- A normal child relationship means the parent consumes the child's processed result.
- `invalidate()` propagates from a block through its normal parents.
- `mark_changed()` invalidates the block and propagates invalidation to normal parents.
- An invalid child must be processed and committed before its parent is processed.
- A parent must not be considered valid while a normal child it consumes is invalid.
- Register task bindings for every invalid child that the runner may need to rebuild.
- Do not process a parent when a required child task is missing; report the configuration error clearly.

## Change-Only Relationships

- Use `add_change_child_block_object(child)` only when child changes should notify or refresh the parent without invalidating or scheduling the parent.
- Change-only relationships are separate from normal data dependencies and must not be used to bypass required processing order.
- `mark_changed()` propagates change callbacks through change-only relationships while keeping their invalidation semantics distinct.
- Remove change-only relationships with `remove_change_child_block_object()` when the owning object is replaced or destroyed.
- Test normal and change-only relationships separately so their different scheduling behavior remains clear.

## Invalidation Rules

- Invalidation means the block's derived result cannot currently be trusted.
- Invalidate the narrowest affected branch and let relationship propagation reach consuming parents.
- Invalidation callbacks must be safe to invoke more than once and must not mutate the relationship collections while they are being traversed.
- Use the existing visited-set propagation behavior to prevent duplicate work and recursion loops.
- Do not call `validate()` as a shortcut for processing; validity is restored only after successful processing and commit.
- If a block is invalidated while its task is queued or running, coalesce the pending rebuild and run a fresh pipeline after the current task finishes.
- Do not reuse prepared inputs after relevant child or source state has changed.
- Failed processing leaves the block invalid and must not cause an automatic success or parent rebuild.

## Destruction and Lifetime

- `destroy()` is idempotent; repeated destruction must not repeat callbacks or parent notifications.
- Destroyed blocks must not be scheduled, processed, committed, or rescheduled.
- Always remove invalidation and destruction callbacks when a task binding or importer is removed.
- A destroyed child must notify its parent through the relationship metadata.
- A dependent parent is destroyed when its dependent child is destroyed.
- A non-dependent parent survives child destruction but must be marked changed and rebuilt or repaired as appropriate.
- Remove both normal and change-only relationships during teardown to avoid stale references.
- Do not reuse a destroyed block's GUID for a live binding until the old task binding and callbacks have been removed.

## Task Runner Rules

- Resolve invalid children before scheduling a parent.
- Process children before parents in dependency order.
- A completed child task is not enough by itself; the child must have committed successfully and be valid.
- Guard dependency traversal against cycles and missing registrations.
- Do not reschedule inactive bindings or blocks whose destruction has been observed.
- When a project is cleared or replaced, stop tasks, remove callbacks, clear bindings, and detach the relationship graph before registering new blocks.

## Testing Rules

- Test that invalidation reaches every normal parent exactly once.
- Test that invalidation does not incorrectly schedule a change-only parent.
- Test that `mark_changed()` reaches both change callbacks and normal-parent invalidation callbacks with the expected state.
- Test dependent-child destruction separately from non-dependent-child destruction.
- Test relationship removal on both sides and repeated removal or destruction.
- Test child-before-parent processing, multiple children, invalid-child registration errors, and dependency cycles.
- Test invalidation while queued, running, paused, and after runner clearing.
- Assert that destroyed blocks do not receive new task work or callbacks.
- Use small fake block objects and deterministic callback recording instead of native scene widgets.

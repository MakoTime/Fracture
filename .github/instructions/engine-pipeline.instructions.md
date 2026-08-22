---
name: Engine Block Pipeline
description: "Use when creating or modifying engine block objects, block tasks, task runners, dependency scheduling, invalidation, or engine tests in this project."
applyTo:
  - "engine/**/*.py"
  - "tests/test_engine.py"
  - "tests/test_transforms.py"
  - "tests/test_registration.py"
  - "tests/test_project_serializer.py"
---

# Engine Block Pipeline

Every block computation follows this pipeline in order:

```text
prepare -> process -> commit
```

## Block Object Rules

- `prepare()` gathers and validates immutable inputs needed by the worker.
- `process(prepared, progress_callback=None)` performs the expensive computation using only the prepared inputs and produces the result.
- `commit(result)` applies the processed result to the block object, updates derived state, and marks the block valid.
- Keep worker-safe computation in `process()`; do not mutate shared Qt or application UI state from the worker.
- Keep result publication and validity changes in `commit()`.
- A successful `process()` must not be treated as a completed block computation until `commit()` has succeeded.
- A failed `prepare()`, `process()`, or `commit()` must leave the block invalid and surface the error through the task status.
- Do not call `process()` without the prepared value returned by `prepare()`.
- Do not call `commit()` before successful processing.
- Do not mark a block valid directly from a task or view; use `commit()`.
- Preserve block dependency relationships and do not process a parent while an invalid child remains uncommitted.

## Block Task Rules

- Block tasks must expose `block_object`, `prepare()`, and `process(prepared, progress_callback=None)`.
- A task may adapt a model to a block object, but it must preserve the three-stage lifecycle.
- `prepare()` belongs before the worker is queued whenever possible, so invalid inputs fail synchronously and worker state is self-contained.
- `process()` should return or store a result that can be passed to the owning block object's `commit()` method.
- Do not put UI callbacks, dialog operations, or Qt widget access in block tasks.
- Keep task names descriptive enough to identify the block operation in the engine view.

## Task Runner Rules

- The runner owns orchestration, ordering, progress reporting, cancellation or pause behavior, and task status.
- The runner must execute exactly one successful block lifecycle in this order: `prepare()`, worker `process(prepared, progress_callback)`, then `block_object.commit(result)`.
- The runner must not enqueue `process()` until dependencies are ready and the block has a prepared input.
- Commit results on the Qt/main thread or through the runner's completion callback when the block updates application-visible state.
- Do not call `commit()` for failed, cancelled, destroyed, or stale tasks.
- If a block is invalidated while its task is active, finish the current task consistently, then enqueue one fresh pipeline run rather than mutating its prepared input in place.
- Clear task bindings and invalidation callbacks when a project closes or is replaced.
- Reset task identifiers and visible task rows when the runner is cleared.
- Guard against dependency cycles and missing task registrations before processing.
- Ensure finished callbacks run after commit for successful block tasks.

## State Rules

- Only `commit()` may transition a successfully processed block to valid state.
- A block with invalid children must remain unprocessed until those children commit successfully.
- Destroyed blocks must not be prepared, processed, committed, or rescheduled.
- Replacing a block must remove its old task binding and invalidation callback before reusing its GUID.
- Persistence and scene/table refreshes should occur after commit, never from the worker's processing phase.

## Testing Rules

- Add a test that records the exact order `prepare`, `process`, and `commit` are called.
- Assert that `process()` receives the value returned by `prepare()`.
- Assert that `commit()` receives the processed result and is not called when preparation or processing fails.
- Test progress callbacks and task status transitions separately from computation correctness.
- Test invalidation while running, dependency ordering, cycle detection, destroyed blocks, and runner clearing.
- Test that successful completion callbacks observe committed, valid block state.
- Use synchronization primitives rather than arbitrary sleeps for thread-sensitive tests.
- Keep block pipeline tests independent from native scene widgets and PyVista rendering.

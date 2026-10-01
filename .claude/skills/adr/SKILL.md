---
name: adr
description: Write an Architecture Decision Record in docs/adr/ — for decisions that change a module boundary, add infrastructure or a dependency, change docs/STACK.md, or pick between real alternatives (e.g. PDF library, payment provider, embeddings model). Use when the user says "qaror", "ADR", or before introducing anything not in docs/STACK.md.
argument-hint: <decision title>
---

ADR: $ARGUMENTS

1. Next number: count files in `docs/adr/` (start at 0001). File: `docs/adr/NNNN-kebab-title.md`.
2. Content (English, short — one screen):

```markdown
# NNNN. <Title>

- Status: proposed | accepted | superseded by NNNN
- Date: YYYY-MM-DD

## Context
What problem, which constraints (solo developer, 4 languages, paid services, docs/STACK.md).

## Options
1. <option> — pros / cons
2. <option> — pros / cons

## Decision
What we chose and why, in 2–4 sentences.

## Consequences
What changes (modules, STACK.md, migrations, cost), what we accept as downsides, how to revisit.
```

3. Present the options to the user **in Uzbek** and ask for the decision unless they already gave it.
   Status stays `proposed` until the user says yes.
4. When accepted and it changes the stack, update `docs/STACK.md` in the same change.

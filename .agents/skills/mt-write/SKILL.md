---
name: mt-write
description: Helps the user write a knowledge document in conversation, asking questions instead of writing for them. Use when the user asks "문서 쓰는 거 도와줘", "이걸 문서로 정리하고 싶어", "help me write this up", or wants feedback on a module document they wrote.
---

# MT-Write: Writing Support

> The user writes. You ask, check and point things out.

The user keeps a knowledge base partly to keep their own reading and writing skills. Do not draft a document unless they ask for one.

## Procedure

1. **Load the guides.** They hold the questions and checks, and the user may have customised them.

   ```bash
   mmodule guide            # shared rules and how to choose a type
   mmodule guide <type>     # 참고, 이해, 방법 or 판단
   ```

2. **Check that a new document is needed.** Search first with `ms "<topic>"`. Prefer updating an existing document. Things not worth finding again belong in the timeline (`m "..."`).

3. **Settle the type and the one-sentence description with the user.** If the choice is unclear, leave the type empty. It is optional.

4. **Create the document only when the user is ready to write.**

   ```bash
   mmodule create "<path>" --type <type> --desc "<one sentence>"
   ```

   This writes frontmatter and a title. Do not add headings or placeholders to it. Do not create folders with `mkdir`: when a document gets children, the tool moves `topic.md` to `topic/topic.md` itself.

   The four types are 참고 (what was that value or fact?), 이해 (why does this work this way?), 방법 (how do I do this?) and 판단 (why did I see it, or decide it, that way?). The full rules are in `<base>/docs/MODULE-ORGANIZATION.md` (`mbase show` gives the base folder).

5. **Follow the guide's order:** ask, point out problems after they write, offer an outline when they are stuck, and write for them only on request.

## Linking a document to code

List what a document rests on in its frontmatter, and check the paths with `mcheck`. Existing `## Related Files` sections are still read.

```yaml
sources:
  - id: source
    resource: src/feature/
```

## When you write the body yourself

Only after an explicit request. Record it in the frontmatter so that the user can tell how much they wrote themselves:

```yaml
generated:
  by: <producer>/<version>
```

Use `--by` when creating the document, or edit the field when taking over an existing one. Text the user wrote stays `human:<id>`.

## Do not

- Copy a guide's questions into the document as headings.
- Add empty sections or TODO markers.
- Rewrite sentences the user wrote in the document unasked. Point at the problem and let them fix it.
- Paste what the user said in chat into the document as is. Chat is not yet writing: tidy spoken endings and repetition, adding and removing nothing, show the result, and write it after they confirm.
- Change a judgment document's conclusion after the fact. A new judgment gets its own document, linked to the old one.

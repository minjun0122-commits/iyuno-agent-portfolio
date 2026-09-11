---
title: "Least privilege for autonomous and semi-autonomous agents"
source_topic: "Least privilege for autonomous and semi-autonomous agents"
retrieved_date: "2026-09-08"
license: "Original summary written for this coursework project; underlying topic is public/standard technical knowledge."
---

The principle of least privilege, long established in access control, applies
directly to LLM agents that can call tools or take actions on a user's
behalf: an agent should hold only the permissions its current task requires,
not the union of everything it might ever need. Practical patterns include
scoping API credentials per tool rather than sharing one broad credential
across all tools, requiring explicit user confirmation before irreversible
or high-impact actions, capping the blast radius of any single tool call (for
example, a "delete" tool that can only act on resources the current session
already created), and logging every permission-relevant action so that
excessive agency can be detected in an audit even if it was not prevented at
call time. Systems that grant broad, standing permissions to reduce
friction tend to be the ones where a prompt-injection or reasoning failure
causes the most damage.

---
title: "Tool calling and function calling in LLM agents"
source_topic: "Tool calling and function calling in LLM agents"
retrieved_date: "2026-09-08"
license: "Original summary written for this coursework project; underlying topic is public/standard technical knowledge."
---

Tool calling lets a language model request that the surrounding system execute
a function, such as a calculator, a database query, or an external API call,
and then feed the result back into the model's context. A tool is typically
described to the model with a name, a natural-language description, and a
schema of expected arguments; the model emits a structured call matching that
schema instead of free text. The orchestrating code validates the arguments,
executes the tool in a sandboxed or permission-scoped context, and returns the
result so the model can continue reasoning or produce a final answer. Robust
tool-calling systems validate arguments strictly, cap the number of tool calls
per request to avoid infinite loops, log every call and its result for
auditability, and apply the principle of least privilege so a tool can only
touch the resources it needs.

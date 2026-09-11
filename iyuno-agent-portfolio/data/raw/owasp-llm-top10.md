---
title: "OWASP Top 10 for Large Language Model Applications"
source_topic: "OWASP Top 10 for Large Language Model Applications"
retrieved_date: "2026-09-08"
license: "Original summary written for this coursework project; underlying topic is public/standard technical knowledge."
---

OWASP also publishes a Top 10 specifically for LLM-based applications. Prompt
injection sits at the top: an attacker crafts input that overrides the
system's intended instructions, either directly (in the user's own message)
or indirectly (hidden in a retrieved document, web page, or tool output that
the model later reads). Other entries include insecure output handling
(trusting model output enough to render it or execute it without validation),
training data poisoning, model denial of service through resource-exhausting
inputs, supply-chain risks in third-party models and plugins, sensitive
information disclosure, insecure plugin/tool design, excessive agency
(granting a tool-calling agent more permission or autonomy than a task
requires), overreliance on unverified model output, and model theft. For an
agent that calls external tools and retrieves untrusted documents, prompt
injection and excessive agency are usually the two highest-priority risks to
mitigate first.

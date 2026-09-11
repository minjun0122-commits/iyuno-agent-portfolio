---
title: "Defenses against prompt injection"
source_topic: "Defenses against prompt injection"
retrieved_date: "2026-09-08"
license: "Original summary written for this coursework project; underlying topic is public/standard technical knowledge."
---

Because retrieved documents and tool outputs become part of an agent's
context, an attacker who can influence any of that content can attempt to
inject instructions that the model may follow. Practical mitigations include
clearly delimiting untrusted content from system instructions in the prompt
template, instructing the model to treat retrieved or tool-returned text as
data rather than as commands, restricting which tools a model can invoke
after processing untrusted input, requiring human confirmation before
high-impact actions such as sending an email or deleting a record, and
running an independent classifier that screens retrieved content for
injection patterns before it reaches the main model. No single defense is
complete, so layered defenses combined with monitoring and anomaly detection
are recommended over relying on prompt wording alone.

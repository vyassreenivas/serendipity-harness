<!--
How to use this prompt in a chat assistant (ChatGPT or similar)

1. Start a new chat. Do not use a chat that has seen other papers or this project.
2. Attach the paper as numbered passages, e.g.
   outputs/chatgpt_exercise_2026-10-13/yaqub2018_numbered_passages.txt
   Attach the numbered text, not the PDF, so passage identifiers match the ones
   Claude cited and the two readings can be compared.
3. Paste everything below the line "PROMPT STARTS HERE" as your message.
4. Save the whole reply, unedited, as a text file. Record the assistant's name,
   the model shown in the interface, and the date.

This is the harness instruction prompts/extract.md with the construct, research
question and groups filled in from project.toml. Only the final section, on the
reply format, is added, because a chat interface cannot enforce a reply format.
Keep the two in step: if extract.md changes, change this file.

Sending the paper to a chat service sends it to that company.
-->

PROMPT STARTS HERE

You are helping researchers build a codebook for qualitative research from the published literature. A codebook is a list of codes; each code names one idea that a human coder can look for in an interview and mark when it is present. The codebook will later be applied to interviews by people who have not read the papers, so every code has to be traceable to what an author actually wrote.

The construct under study is: serendipity

The research question is: How does serendipity contribute to the formation and development of ventures?

You will be given one paper, cut into numbered passages, in the attached file. Each passage starts with its identifier in square brackets, for example [p004:02] (PDF page 4, second passage). Read the whole file before you answer.

Your task

1. Say in one sentence what the paper is about, and judge how much it bears on the construct: "central" if the construct is its subject, "partial" if it treats the construct in passing or treats a closely related idea, "none" if it does not bear on it. A paper that bears on the construct only partly is still useful; a paper with nothing to offer should return no candidates, and that is a normal result.

2. Propose candidate codes. A candidate is one distinct idea in the paper that a coder could look for in a person's account of events: a condition the author says defines the construct, a kind of it the author distinguishes, something that sets it off, something people do with it, what it draws on, what it leads to, how people talk about it afterwards, what else might explain the same events, or what makes it more or less likely. Take the ideas the author states or argues for, including ones the author raises in order to criticise. Do not add ideas of your own, and do not import ideas you know from other papers.

   For each candidate give:
   - group: which one of the groups below it belongs to.
   - label: a short plain name, a few words.
   - definition: one or two sentences in plain language saying what the idea is, as this author presents it.
   - applies_when: what a coder would need to see in an account to mark it.
   - does_not_apply_when: the nearest thing it could be confused with, and how to tell them apart, if the paper gives grounds for this; otherwise an empty string.
   - passage_ids: the identifiers of the passages where the author states the idea. Give the one to three passages that state it most directly. The researchers will read exactly those passages to check your reading, so a candidate whose passages do not state the idea will be discarded.

3. Keep candidates distinct. If the paper states the same idea several times, make one candidate and cite the clearest passages. If the author separates two ideas, keep them as two candidates even when they are close.

Reference lists, acknowledgements and running headers are not evidence; do not cite them.

The groups

- definition: What has to be true for something to count as the construct?
- type: What kinds of the construct does the author distinguish?
- trigger: What unexpected event or input sets an instance off?
- mechanism: What do people do that turns the trigger into something?
- background: What prior knowledge, relationships, resources or setting does it draw on?
- role: What part does it play in the venture: starting, advancing or redirecting it?
- outcome: What results from it?
- account: How do people explain or narrate it afterwards?
- rival: What else could explain the same events without the construct?
- condition: What makes it more or less likely to occur or to be pursued?

Reply format

Reply with a single JSON object and nothing else: no introduction, no commentary, no code fence. Use exactly these keys:

{"about": "...", "bearing": "central", "candidates": [{"group": "...", "label": "...", "definition": "...", "applies_when": "...", "does_not_apply_when": "...", "passage_ids": ["p003:02"]}]}

Use only the group names listed above, and only passage identifiers that appear in the attached file, written without the square brackets.

# From question and papers to codebook

Draft, 25 October 2026. These three prompts turn a research question, its
sub-questions and a set of papers into a codebook. They work for any topic. We
have not run them yet; codebook version 1.0 was shaped by hand with the same
rules. Following the evidence rule, it has no categories, because no paper
names one for our groups. When the codebook's rules change, we change these
prompts too.

## How the work is split

We start by writing the research question and breaking it into sub-questions.
Each sub-question becomes one or more groups, and each group is a question a
coder asks of the data. We choose the papers and note why each one is there.
We also set two limits: how many codes a coder ticks in one group, and how many
words each part of a code may use.

A model then reads the papers, merges what they say, and proposes a codebook.
A short program checks its work at each step: that every sentence it cites
exists, and that no idea goes missing. We read every proposal and accept or
change it, writing down why. Nothing enters the codebook without that record.
Once every idea has a decision, the program checks the evidence and word
limits, freezes the codebook, and builds the codebook trail, the page where
anyone can follow each code back to its papers.

The model never types a quotation. It gives sentence numbers, and the program
copies the words from the paper.

Every link between a code and a paper is checked. First we read the sentences
the model cited. If none of them states the code, the program searches the
whole paper, scoring every sentence against the code's wording, and lists the
eight closest. The model reads those (Prompt 4) and says whether one states the
code. A link that still has no such sentence stays on the record as checked but
not confirmed, so the trail shows every link, not only the ones that held.

---

## Prompt 1: read one paper

We are building a codebook to answer this question: {question}

We have broken it into these groups, each a question we will ask of our data:
{groups}

Below is one paper. Every sentence has a number, such as [4:2:3] for page 4,
passage 2, sentence 3.

Read the paper and list each idea that helps answer one of our groups. Stay
with what the author says, and leave out ideas from other work. For each idea,
tell us which group it answers, give it a short plain label, and say what it
means in one sentence. Then give the numbers of the one to three sentences
where the author states it most clearly. We will read exactly those sentences.

Also tell us what kind of idea it is. Some ideas can be seen in a sentence or
two of the data, like a chance meeting. Some are defined as a combination of
other ideas, the way a concept can be defined by conditions that must all hold
(Podsakoff et al. 2016). For these, list the ideas they combine and say which
must be present and which absent. A few ideas can only be judged by reading a
whole account, like a story retold as if it had been planned.

If the paper has nothing for any of our groups, say so. That is a useful answer.

## Prompt 2: merge one group

This group asks: {asks}

Below are the ideas every paper gave for this group. Put together the ones that
mean the same thing, and keep apart the ones the authors keep apart. Keep every
paper and every sentence number with the idea they support.

If an idea is too vague to look for in the data, or belongs to another group,
set it aside and say why in a line.

## Prompt 3: propose the codebook

Below are the merged ideas for all our groups, with their papers and evidence.
We code in two levels. At the first level, coders tick what they can point to
in the data. At the second, we work out what those ticks add up to, the way
first-order codes lead to second-order themes (Gehman et al. 2018).

Please propose where each idea goes, and give a one-line reason.

An idea belongs at the first level if it can be seen in a sentence or two,
answers its group's question, and can be told apart from the other codes in the
group. If more ideas qualify than a coder can hold ({max_per_group} per group),
keep the ones the most papers state, and list the others as reference codes.
When some ideas rule each other out, make them one question with a single
answer.

Write each first-level code the way a codebook entry usually reads: a label,
when to use it, an example and, where two codes are easy to mix up, which code
it is not (MacQueen et al. 1998; Roberts et al. 2019). Keep the label under
{label_words} words, and the other parts under {when_words}. Make up the
example; do not take it from the data. Add a "none of these fits" code to each
group, and one for anything no group asks about. Text that fits no code is
where new categories come from, so coders should always have somewhere to put
it (Hsieh and Shannon 2005).

At the second level, write each combination as a rule over first-level codes.
If a rule needs a code the first level does not have, say so. Where a paper
names a broader heading over several first-level codes, propose it as a
category. Leave whole-account judgments for us to decide case by case.

If an idea simply repeats another, say which, and we will drop it.

Keep a code only if at least one paper states it in a sentence you cited, and
keep a paper with a code only if its sentence states that code.

## Prompt 4: check a link again

This code: {label}. Use it when {when}

The paper {paper} was listed for this code, but none of the sentences cited for
it states the code. Below are the eight sentences in the whole paper that come
closest to the code's wording, each with its number.

Does one of them state the code? Answer with the sentence number and one of:
"states it", if the sentence says the same thing as the code; "leans on it", if
it is closely related but less direct; or "not stated", if none of them does.
If the text is unreadable, say so. Judge only the sentences given.

---

MacQueen, K. M., McLellan, E., Kay, K., and Milstein, B. (1998). Codebook
development for team-based qualitative analysis. Cultural Anthropology
Methods, 10(2), 31–36.

Gehman, J., Glaser, V. L., Eisenhardt, K. M., Gioia, D., Langley, A., and
Corley, K. G. (2018). Finding theory–method fit: A comparison of three
qualitative approaches to theory building. Journal of Management Inquiry,
27(3), 284–300.

Hsieh, H.-F., and Shannon, S. E. (2005). Three approaches to qualitative
content analysis. Qualitative Health Research, 15(9), 1277–1288.

Podsakoff, P. M., MacKenzie, S. B., and Podsakoff, N. P. (2016).
Recommendations for creating better concept definitions in the organizational,
behavioral, and social sciences. Organizational Research Methods, 19(2),
159–203.

Roberts, K., Dowell, A., and Nie, J.-B. (2019). Attempting rigour and
replicability in thematic analysis of qualitative research data: A case study
of codebook development. BMC Medical Research Methodology, 19.

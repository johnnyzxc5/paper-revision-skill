# Design sources and adaptation scope

Paper Revision generalizes an author-developed manuscript workflow. Its public
instructions and tools are distributed under this repository's MIT license.
Project profiles, personal bindings, manuscript excerpts, and local execution
history are excluded. Detailed procedures live in conditional references.

The repositories below informed writing-workflow design. Their code or prose is
not bundled; their licenses do not automatically cover future copied material.
The external `notebooklm-py` runtime is installed separately and retains its own
license. There is no requirement to cite this skill or its design inspirations
in a manuscript.

Sources inspected on 2026-10-02:

| Primary source | Adopted idea | Adaptation |
| --- | --- | --- |
| [Master-cai research-paper-writing](https://github.com/Master-cai/Research-Paper-Writing-Skills/blob/main/research-paper-writing/SKILL.md) (repository MIT) | Mini-outlines, reverse outlining, section-specific guidance and skeptical review | Keep author-side maps and existing two approval gates; do not force novelty, paragraph counts or ML structures |
| [msimchowitz paper-writing](https://github.com/msimchowitz/writing-skills/blob/main/for-agents/paper-writing/SKILL.md) (repository MIT) | Claim/evidence maps, theory/empirical architecture, reader questions and figure argument | Distinguish proof from simulation/hardware evidence; no imported house voice or private corpus |
| [K-Dense scientific-writing](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-writing/SKILL.md) (skill MIT, v2.3) | Evidence-bound drafting and consistency rather than generic quality scores | Complement the supplied rubric; do not replace its scientific controls |
| [K-Dense citation-management](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/citation-management/SKILL.md) (skill MIT, v2.3) | Programmatic identifiers/metadata/BibTeX and separate claim-support checks | Small standard-library DOI helper with explicit local cache; no Scholar scraping or paid backend |
| [Orchestra ml-paper-writing](https://github.com/Orchestra-Research/AI-Research-SKILLs/blob/main/20-ml-paper-writing/ml-paper-writing/SKILL.md) (skill MIT) | Literature retrieval before citing, venue-specific preparation | Verify current official venue instructions; do not import dated templates or fixed bibliography targets |

Master-cai attributes much of its methodology to
[Peng Sida's open research notes](https://github.com/pengsida/learning_research).
These sources motivate design choices; their preferences are not universal
editorial requirements. No automatic citation to skill authors is inserted into
manuscripts. If future work copies upstream material, preserve the applicable
copyright/license notices and review each copied asset's own license.

The performance objective is less compulsory entrypoint text, fewer unnecessary
source reads/queries and reusable bibliography retrieval. Validation of package
structure and helpers does not demonstrate better acceptance rates or quantify
end-to-end token savings. Evaluate actual prose quality with an author-approved
paper task and its relevant scientific/editorial criteria.

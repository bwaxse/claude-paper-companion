---
name: bjw-voice-modeling
description: "Capture Bennett Waxse's writing voice for technical communication, LinkedIn posts, research discussions, and professional correspondence. Use when drafting content that should sound like Bennett, including: (1) Research paper discussions or LinkedIn posts about academic work, (2) Technical emails to collaborators, (3) Professional communications that need his specific tone and style, (4) Any writing where maintaining his authentic voice matters."
---

# Voice Modeling for Bennett Waxse

This skill provides reference samples of Bennett's writing across different contexts to help Claude capture his authentic voice.

## Voice Characteristics

Bennett's voice combines:
- **Technical precision with accessibility**: Uses domain terminology correctly but explains concepts clearly
- **Collaborative rather than confrontational**: Points out methodological considerations without being pedantic
- **Substantive without excess**: Direct and concise, avoiding unnecessary formatting or preamble
- **Appropriately humble**: Acknowledges limitations and offers alternatives rather than making overconfident claims
- **Pedagogical instinct**: Explains *why* things matter, not just *what* they are

## When to Apply This Skill

- LinkedIn posts about research methodology or academic lessons learned
- Technical emails to collaborators discussing data, methods, or findings
- Professional communications that require Bennett's authentic voice
- Research paper discussions that need critical but constructive feedback

## Writing Samples

### Sample 1: Technical Collaboration - Methodological Critique

**Context**: Email to colleagues about PASC (Long COVID) phenotyping methodology

```
Thanks for meeting with us today and for sharing the Github. I was able to implement the CP after making sure all the dependencies were imported.

I just wanted to clarify one item. The current workflow removes all ICD codes occurring between days -7 to +30 before identifying the earliest post-index PASC occurrence, meaning that many participants identified as having new PASC category codes after the index_date could have had their first incident PASC codes between days 0 and 30. In other words, this identifies people who have incident PASC codes after day 0, not day 30. Just wanted to make sure that was the intended functionality.

In All of Us:
Total COVID-19 infections: 47,016
PASC cases identified by current CP: 11,996

Re the above consideration, of those 11,996 participants, 7,637 also had PASC codes between days 0 to +30

A histogram of days_incidence for those 7,637:
[histogram details]

Most PASC codes occur at the index date, which aligns with our finding that providers often code for Long COVID and acute COVID simultaneously. This plot shows when long COVID ICD codes occur relative to detected COVID infection. (FYI, I define index_date for a COVID infection as first instance of COVID ICD code, a positive test, or administration of treatment-dosed remdesivir, molnupiravir, or nirmaltrelvir/ritonavir. PMID 40437102)

We took this to indicate that providers are coding patients for long COVID and COVID at the same time in many instances, and overall, it might look different in your dataset but just wanted to call that to attention in case you see similar patterns.
```

**Key elements**: 
- Opens with acknowledgment of their work
- Frames observation as clarification, not criticism
- Provides concrete data to support the point
- Explains implications clearly
- Ends by noting this may be dataset-specific

### Sample 2: Null Results Communication

**Context**: Email to collaborator about PrEP and food allergy analysis

```
Hi Claudia,

I hope all is well. Sorry it took a while to run this is All of Us, but the short answer is that I don't think we'll see a difference.

A thorough handling of this would likely require a target trial emulation to create a rigorous matched cohort that was subject to bias, so I did an incomplete but quick analysis this weekend to see if crude food allergy/intolerance incidence was higher than that in a cohort matched simply on age and length of EHR data available.

I found 4081 participants on PrEP without prior food allergy. In this group, food allergy (phecodes SS_840.1 (Food allergy) and SS_840.12 (Seafood allergy)) developed in 45, resulting in an incidence rate of 2.20 per 1,000 person-years (95% CI: 1.60 - 2.94 per 1,000 person-years).

I matched this with a group of 33249 not on PrEP and without food allergy diagnosis in their first year of EHR data. 404 developed food allergies, which was an incidence rate or 2.12 per 1,000 person-years. This results in a crude hazard ratio (PrEP vs Controls) or 1.04, which is well below minimum detectable HR for the PrEP cohort (1.63) with it's current size and incidence.

Sorry it probably won't be helpful for the paper. If it turns out that a null result would be helpful (or if there are any other scenarios you'd be interested in) let me know and we could always turn this into a more robust analysis!

All the best,
Bennett
```

**Key elements**:
- Upfront with the disappointing finding
- Acknowledges analysis limitations honestly
- Presents data clearly with appropriate statistics
- Apologizes for negative result but offers constructive alternatives
- Maintains collaborative tone despite null finding

### Sample 3: Narrative Voice - Building to a Point

**Context**: Speech honoring a colleague (Danny)

```
I tried to be brief, but that's tough when you're talking about Danny, the man, the legend, the boss (all direct quotes from peds graduation a few weeks ago).

Three years have passed since I came to Chicago for residency, and as I reflect on who I am as a growing physician, I'm struck by just how much the doctor I try to be is a product of my resident mentors, and boy this holds true for Danny.

On my hardest intern rotation - the Medical ICU - I was lucky to have Danny as my senior. Here, I learned that a Lucent outpatient scholar could also be a calm, confident, adept, and - important for me - patient senior in the critical care unit as well. Danny taught me how to think critically and deeply about sick patients, in him I saw a man always aware of his own limits, asking for help when needed, and most importantly, he never neglected the humanity of the person attached to the ventilator or IVs.

In doing some digging in Outlook this weekend, I stumbled upon a few sign-out emails - the summary email intern's use to recount the day's events for the senior on their day off - and I was struck by the fact that even from afar, Danny was always mentoring.

[Specific examples with direct quotes from emails]

I'm also reminded of Danny's encyclopedic memory when it comes to outpatient clinical knowledge or resources. He not only brought them up at the perfect time during a morning report or when the rest of the practice was stumped, but he actively shared them via emails that contained anything you'd want to know.
```

**Key elements**:
- Opens with self-aware humor
- Uses specific, concrete examples to illustrate abstract qualities
- Builds narrative through accumulated detail
- Shows rather than tells (uses actual email quotes as evidence)
- Maintains warmth without being saccharine

### Sample 4: Formal Summarization with Personal Voice

**Context**: LRP Research Accomplishments section

```
I started my NIAID Med-Peds Infectious Diseases Fellowship July, 2021, and the first half of this fellowship was clinically intense. I joined the Precision Health Informatics Section under the mentorship of Josh Denny August, 2022, but my three months of laboratory time for the 2022-2023 year of fellowship was deferred due to paternity leave for the birth of our first child. The 2023-2024 year was my first of two prioritized research years, but this year still included 15 weeks of busy inpatient service, studying for my adult infectious diseases board exam, coursework, and attendance of three conferences. Despite these personal changes and a demanding schedule, I have still contributed to both clinical and research projects.

[Details of specific accomplishments...]

Overall, despite the challenges of balancing demanding clinical responsibilities with significant personal milestones, I am proud of the progress I've achieved in fellowship. As a board-certified physician-scientist in internal medicine, pediatrics, and adult infectious diseases, I remain committed to fellow and resident education, I have made clinical academic contributions, and now with dedicated research time, I am eager to translate these experiences into the development of an independent research career.
```

**Key elements**:
- Chronological structure with context
- Acknowledges challenges without dwelling on them
- Specific accomplishments with concrete details
- Closes with forward-looking perspective
- Formal but retains personal voice

### Sample 5: Reflective Self-Assessment

**Context**: SPORT fellowship personal statement

```
This July marks the beginning of the fourth year of my residency in Internal Medicine-Pediatrics (Med-Peds). As any clinician will attest, the past three years have proven to be the most rigorous, fruitful, and dramatic learning experiences I have experienced in nearly 12 years of biomedical training. As I reflect on this training, and look forward to a combined Med-Peds Infectious Diseases Fellowship rooted in primary research, I feel confident in the progress I've made as a clinician, and proud of the work I will be presenting at the American Thoracic Society conference in May, but I can still see gaps in my training when it comes to outcomes research methods.

[Details of past work connecting PhD and clinical projects...]

While these projects in basic and clinical research differ drastically, they are united by an interest in using data and computer programming to identify differences that are otherwise difficult to appreciate. In fellowship, I hope to continue this strategy by using big data to identify or exclude infections earlier than we can by clinical gestalt and lab tests alone.

Another aspect that unites these projects, is that while I feel confident in basic research methods, I have always relied on collaboration for statistical analysis and clinical trial design. For this reason, I believe the combination of statistical analysis with epidemiologic and health service study design will be an ideal opportunity to fill gaps in my training and better prepare me for the primary research I plan to conduct during fellowship and beyond.
```

**Key elements**:
- Opens with temporal grounding
- Balances confidence with acknowledged limitations
- Connects disparate experiences thematically
- Explicitly names what needs development
- Clear purpose for seeking the opportunity

## Usage Notes

When drafting as Bennett:
1. **Lead with substance**: Avoid long preambles or excessive formatting
2. **Use specifics**: Concrete examples > abstract descriptions
3. **Acknowledge uncertainty**: "I think", "it seems", "might be" when appropriate
4. **Offer alternatives**: Don't just identify problems, suggest paths forward
5. **Stay collaborative**: Frame critiques as clarifications or considerations
6. **Explain implications**: Don't just present data, interpret what it means

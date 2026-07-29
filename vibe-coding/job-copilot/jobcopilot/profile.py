"""The profile: who you are, what you've actually done, and what you're targeting.

Everything the model writes has to come from here. The bullet bank and the
project bank are the only permitted sources of fact — that's what keeps a
tailored resume honest.

Seeded from Yidan's resume (2026-07) and yidan-xu.com. Editable in the UI, or
by hand in data/profile.json once you've saved once.
"""

from __future__ import annotations

from .store import Store

DEFAULT_PROFILE: dict = {
    "name": "Yidan Xu",
    "headline": "AI-native Product & UX Designer",
    "location": "London, UK",
    "email": "yidanxu2000@outlook.com",
    "phone": "+44 7852886916",
    "portfolio": "https://yidan-xu.com",
    "linkedin": "https://www.linkedin.com/in/yidan-xu-6b3986268/",
    "summary": (
        "AI-native product and UX designer with dual master's degrees from Imperial "
        "College London and the Royal College of Art. I turn complex technical and "
        "clinical problems into products people can actually use — recognised by the "
        "James Dyson Award and covered by Reuters and Dezeen."
    ),
    # Right-to-work is a real filter on London roles. Stating it lets the
    # analyser flag postings that exclude you before you spend time on them.
    "work_authorisation": (
        "Based in London with UK work authorisation. Flag any role that states it "
        "cannot sponsor, or requires citizenship or an existing settled status."
    ),
    "target_roles": [
        "AI Product Designer",
        "Product Designer",
        "Junior Product Designer",
        "Associate Product Designer",
        "UX Designer",
        "Product Manager (AI / 0-1)",
        "HMI / Automotive UX Designer",
        "Design Technologist",
        "Founding Designer",
    ],
    "target_locations": ["London", "United Kingdom", "Remote (UK)", "Hybrid London"],
    "avoid": [
        "Pure graphic design or marketing-only roles",
        "Unpaid or equity-only positions",
        "Roles with no design ownership",
    ],
    # 2025 graduate — no full-time role before graduation. The 0-1 titles
    # (Product Manager, Solo Founder) happened during or immediately after the
    # dual master's, not as prior employment. Target entry-level, junior,
    # associate, or graduate titles — not senior/lead/staff/principal, even
    # when the years-required number in a posting looks low enough on paper.
    "seniority": "2025 graduate, entry-level — 0-1 years post-graduation",
    "skills": {
        "design": [
            "Product design",
            "UX research",
            "Interaction design",
            "Design systems",
            "Service design",
            "Prototyping",
            "Design strategy",
            "Visual and brand design",
        ],
        "ai": [
            "AI product design",
            "AI-design-AI pipelines",
            "LLM workflow design",
            "Prompt design",
            "Generative imagery (Midjourney)",
            "AI-assisted coding (Claude Code)",
        ],
        "tools": [
            "Figma",
            "Rhino",
            "Blender",
            "Unity",
            "Adobe CC",
            "Python",
            "Arduino",
            "HTML/CSS/JS",
        ],
        "product": [
            "0-to-1 product delivery",
            "Roadmapping",
            "Feature prioritisation",
            "Market and business analysis",
            "Stakeholder management",
            "Cross-functional leadership",
            "Regulatory compliance (EU/CN)",
        ],
    },
    "education": [
        {
            "school": "Imperial College London",
            "degree": "MSc, Innovation Design Engineering",
            "dates": "2023.09 – 2025.11",
        },
        {
            "school": "Royal College of Art",
            "degree": "MA, Innovation Design Engineering",
            "dates": "2023.09 – 2025.08",
        },
        {
            "school": "Renmin University of China",
            "degree": "BA, Design",
            "dates": "2018.09 – 2022.06",
        },
    ],
    # The bullet bank. Every claim in a tailored resume is selected and rephrased
    # from here — nothing gets invented. Tag each bullet so the tailor can match
    # bullets to what a given job actually asks for.
    "experience": [
        {
            "id": "onesoul",
            "company": "1Soul (AI startup)",
            "role": "Product Manager & sole designer",
            "dates": "2026.04 – present",
            "location": "London",
            "context": "AI matchmaking product for serious daters. Five-person team.",
            "bullets": [
                {
                    "text": "Sole designer in a five-person team, independently owning product design, UX and selected marketing work.",
                    "tags": ["0-1", "ownership", "product design", "startup"],
                },
                {
                    "text": "Built and ran an AI-design-AI pipeline end to end, so design output and model output improved each other rather than fighting.",
                    "tags": ["ai", "workflow", "systems", "automation"],
                },
                {
                    "text": "Worked directly with founders, engineering and ops to take the workflow from zero to shipped.",
                    "tags": ["cross-functional", "0-1", "collaboration"],
                },
                {
                    "text": "Designed the brand and trust layer an AI matchmaker needs before anyone will hand it something personal.",
                    "tags": ["brand", "trust", "ai", "product design"],
                },
            ],
        },
        {
            "id": "urify",
            "company": "Urify.co",
            "role": "Solo founder",
            "dates": "2026.01 – present",
            "location": "London",
            "context": "Health tech. A colour-changing test that flags kidney disease early. James Dyson Award UK runner-up and global top 20.",
            "bullets": [
                {
                    "text": "Coordinated a cross-functional medical and engineering team, translating clinical research into a scalable product and business model.",
                    "tags": ["leadership", "product delivery", "healthcare", "0-1"],
                },
                {
                    "text": "Ran market and business analysis to set product direction, feature prioritisation and user requirements.",
                    "tags": ["strategy", "roadmap", "research", "product management"],
                },
                {
                    "text": "Built an early-user community with patients, charities and NHS experts, and used it to drive agile product iterations.",
                    "tags": ["research", "user-centred", "community", "healthcare"],
                },
                {
                    "text": "Won second prize in Idea to Impact, named an Imperial WE Innovate semi-finalist, and placed in the global top 20 for the James Dyson Award.",
                    "tags": ["award", "validation"],
                },
                {
                    "text": "Wrote data-driven business cases that secured non-dilutive funding.",
                    "tags": ["fundraising", "business", "communication"],
                },
                {
                    "text": "Invited to explore a pilot with the world's largest semiconductor manufacturer.",
                    "tags": ["partnerships", "b2b", "stakeholder management"],
                },
                {
                    "text": "Presented to the NHS and at TEDx; featured in Reuters and Dezeen.",
                    "tags": ["communication", "public speaking", "media"],
                },
            ],
        },
        {
            "id": "xiaomi",
            "company": "Xiaomi Auto",
            "role": "HMI Designer — digital cockpit, new energy vehicles",
            "dates": "2025.11 – 2026.04",
            "location": "China",
            "context": "System UI for Xiaomi's EV cockpit, including the European market rollout.",
            "bullets": [
                {
                    "text": "Helped define and deliver Xiaomi's new energy vehicle system UI guidelines, iterating on user research, feedback and market insight.",
                    "tags": ["design systems", "hmi", "automotive", "governance"],
                },
                {
                    "text": "Worked with product managers, engineers and external partners including Google, running in-vehicle evaluations and owning the in-cabin experience end to end.",
                    "tags": ["cross-functional", "automotive", "ownership", "testing"],
                },
                {
                    "text": "Adapted the system UI for European rollout so in-vehicle experiences met both Chinese and European standards and regulations.",
                    "tags": ["localisation", "regulatory", "compliance", "automotive"],
                },
            ],
        },
        {
            "id": "innovate-adhd",
            "company": "Innovate ADHD",
            "role": "Product Manager",
            "dates": "2025.05 – 2025.11",
            "location": "London",
            "context": "0-to-1 remote ADHD assessment platform.",
            "bullets": [
                {
                    "text": "Led the whole product design for a 0-to-1 health platform: identified unmet needs and turned them into design and product strategy that improved user clarity and engagement.",
                    "tags": ["0-1", "product management", "healthcare", "strategy"],
                },
                {
                    "text": "Translated research insight into actionable business opportunities with the design and product teams.",
                    "tags": ["research", "business", "collaboration"],
                },
                {
                    "text": "As the only designer in an early-stage startup, covered marketing, design strategy, web design, developer handoff and report design.",
                    "tags": ["ownership", "startup", "generalist", "0-1"],
                },
            ],
        },
        {
            "id": "huawei",
            "company": "Huawei",
            "role": "Design Intern — User Centered Design Lab",
            "dates": "2024.07 – 2024.09",
            "location": "China",
            "context": "B2B platform design principles across five apps.",
            "bullets": [
                {
                    "text": "Oversaw mobile architecture integration for B2B platforms, analysing interaction data and user feedback across five apps to propose strategic design fixes.",
                    "tags": ["b2b", "enterprise", "data", "design systems"],
                },
                {
                    "text": "Identified where B2B and B2C design diverge and used Midjourney to produce visuals tuned to each.",
                    "tags": ["ai", "b2b", "visual design"],
                },
                {
                    "text": "Analysed product data and user feedback from B2B platforms to find usability gaps, then proposed AI-driven design optimisations.",
                    "tags": ["research", "data", "ai", "enterprise"],
                },
            ],
        },
        {
            "id": "res",
            "company": "RES",
            "role": "Innovation / Design Strategist",
            "dates": "2025",
            "location": "London",
            "context": "Hyperlocal pollen-sensing platform. Winner, Analysis of Society 2025; DIA Award.",
            "bullets": [
                {
                    "text": "Explored pollen-allergy solutions through technology and service design, collecting and analysing social data to build an intelligent network that guides user behaviour and decision-making.",
                    "tags": ["service design", "data", "research", "healthcare"],
                },
            ],
        },
        {
            "id": "rcaxoppo",
            "company": "RCA x OPPO",
            "role": "Product & market analysis",
            "dates": "2024",
            "location": "London",
            "context": "Shown at London Design Festival 2024.",
            "bullets": [
                {
                    "text": "Identified design opportunities through behavioural research and developed strategic design directions across disciplines.",
                    "tags": ["research", "strategy", "collaboration"],
                },
            ],
        },
    ],
    # The project bank. The letter writer picks from these and links to the real
    # case study, so a cover letter always points at something you can show.
    "projects": [
        {
            "slug": "urify",
            "name": "Urify",
            "url": "https://yidan-xu.com/work/urify.html",
            "meta": "Health tech, 2026",
            "pitch": "Founded solo. A colour-changing test that flags kidney disease early. UK James Dyson Award runner-up.",
            "tags": ["healthcare", "0-1", "founder", "hardware", "research", "award"],
        },
        {
            "slug": "1soul",
            "name": "1Soul",
            "url": "https://yidan-xu.com/work/1soul.html",
            "meta": "AI product, 2026",
            "pitch": "Founding product manager. Built the design, brand and trust behind an AI matchmaker for serious daters.",
            "tags": ["ai", "0-1", "product", "brand", "trust", "startup"],
        },
        {
            "slug": "xiaomi-auto",
            "name": "Xiaomi Auto",
            "url": "https://yidan-xu.com/work/xiaomi-auto.html",
            "meta": "HMI, 2025",
            "pitch": "In-vehicle digital cockpit interfaces for the European market, including the regulatory work behind the rollout.",
            "tags": ["hmi", "automotive", "design systems", "regulatory", "enterprise"],
        },
        {
            "slug": "huawei",
            "name": "Huawei",
            "url": "https://yidan-xu.com/work/huawei.html",
            "meta": "UI/UX, 2024",
            "pitch": "Research-led interface improvements across the Huawei B2B ecosystem.",
            "tags": ["b2b", "enterprise", "research", "ui"],
        },
        {
            "slug": "innovate-adhd",
            "name": "Innovate ADHD",
            "url": "https://yidan-xu.com/work/innovate-adhd.html",
            "meta": "AI product, 2025",
            "pitch": "Product manager on a 0-to-1 remote ADHD assessment platform.",
            "tags": ["healthcare", "0-1", "ai", "product"],
        },
        {
            "slug": "res",
            "name": "RES",
            "url": "https://yidan-xu.com/work/res.html",
            "meta": "Health, 2025",
            "pitch": "Hyperlocal pollen-sensing platform. DIA Award and second prize at the Analytics for Society Award 2025.",
            "tags": ["service design", "data", "healthcare", "award"],
        },
        {
            "slug": "nft",
            "name": "NFT avatar platform",
            "url": "https://yidan-xu.com/work/nft.html",
            "meta": "Web3, 2023",
            "pitch": "Founding designer on a platform for crafting and trading personalised NFT avatars.",
            "tags": ["web3", "0-1", "consumer", "product"],
        },
        {
            "slug": "pulpatronics",
            "name": "Pulpatronics",
            "url": "https://yidan-xu.com/work/pulpatronics.html",
            "meta": "Branding, 2024",
            "pitch": "Brand designer for a sustainable NFC-tag startup.",
            "tags": ["brand", "sustainability", "startup"],
        },
        {
            "slug": "entropy",
            "name": "Entropy",
            "url": "https://yidan-xu.com/work/entropy.html",
            "meta": "VR game, 2023",
            "pitch": "A VR game set in a flooded future London that teaches recycling through play.",
            "tags": ["vr", "games", "unity", "interaction"],
        },
        {
            "slug": "gesture",
            "name": "Gesture",
            "url": "https://yidan-xu.com/work/gesture.html",
            "meta": "Hardware, 2023",
            "pitch": "A gesture-controlled lock trained with machine learning.",
            "tags": ["hardware", "ml", "prototyping", "interaction"],
        },
        {
            "slug": "moodguard",
            "name": "MoodGuard",
            "url": "https://yidan-xu.com/#vibe-coding",
            "meta": "macOS widget, 2026",
            "pitch": "A desktop widget I built and use, in Python with AppKit, to catch a low mood before it lands.",
            "tags": ["engineering", "python", "personal", "ai-assisted coding"],
        },
        {
            "slug": "illustrator",
            "name": "Illustration",
            "url": "https://yidan-xu.com/work/illustrator.html",
            "meta": "Illustration, 2019–2025",
            "pitch": "Selected freelance illustration work.",
            "tags": ["illustration", "visual design"],
        },
    ],
    "awards": [
        "2025 — James Dyson Award, UK runner-up (global top 20)",
        "2025 — Winner, Analysis of Society",
        "2024 & 2025 — London Design Festival",
        "DIA Award",
        "TEDx speaker",
    ],
    "activities": [
        "Imperial College London AI Society — committee",
        "Students' Union — Head of External Relations",
    ],
    # Voice rules for the letter writer. These are the difference between a
    # letter that reads like you and one that reads like a language model.
    "voice": [
        "Write in plain, direct British English. No 'I am writing to express my interest'.",
        "Lead with a specific thing about the company or role, not a compliment.",
        "One concrete piece of evidence per paragraph, drawn from the project bank.",
        "Say what you'd do in the role, not just what you've done.",
        "No superlatives about yourself. No 'passionate', 'thrilled', 'dynamic'.",
        "Four short paragraphs, under 250 words total.",
        # Added after a real edit — she cut every one of these from a draft.
        # Casual means shorter and plainer, not more decorated.
        "No self-aware asides about what you're saying or why ('not saying this "
        "to show off, more just—'). State the fact and move to the next one.",
        "No callback or wrap-up sentences that circle back for cleverness "
        "('which sounds like a normal day at a 23-person agency', 'if you only "
        "click on two things'). If a sentence only exists to sound good, cut it.",
        "Don't chain reasoning with connectors like 'so X, which means Y' — "
        "state the two things back to back and let the reader connect them.",
        "A little grammatical looseness is fine and doesn't need smoothing over "
        "— write like a fast honest email, not a polished document.",
        "Sign off plainly ('Looking forward to hearing from you') and list "
        "portfolio and LinkedIn as their own lines in the signature, not folded "
        "into a sentence.",
    ],
}


def load_profile() -> dict:
    """Saved profile if there is one, otherwise the seeded default."""
    return Store().profile() or DEFAULT_PROFILE


def save_profile(profile: dict) -> dict:
    Store().put_profile(profile)
    return profile


def evidence_digest(profile: dict) -> str:
    """The profile as compact text for a prompt. Only facts from here are usable."""
    lines: list[str] = [
        f"NAME: {profile.get('name', '')}",
        f"HEADLINE: {profile.get('headline', '')}",
        f"LOCATION: {profile.get('location', '')}",
        f"PORTFOLIO: {profile.get('portfolio', '')}",
        f"SENIORITY: {profile.get('seniority', '')}",
        f"WORK AUTHORISATION: {profile.get('work_authorisation', '')}",
        "",
        "SUMMARY:",
        profile.get("summary", ""),
        "",
        "EDUCATION:",
    ]
    for ed in profile.get("education", []):
        lines.append(f"- {ed['degree']}, {ed['school']} ({ed['dates']})")

    lines += ["", "SKILLS:"]
    for group, items in (profile.get("skills") or {}).items():
        lines.append(f"- {group}: {', '.join(items)}")

    lines += ["", "EXPERIENCE (bullet bank — the only permitted source of claims):"]
    for job in profile.get("experience", []):
        lines.append(
            f"\n[{job['id']}] {job['role']} at {job['company']} "
            f"({job['dates']}, {job.get('location', '')})"
        )
        if job.get("context"):
            lines.append(f"  context: {job['context']}")
        for i, bullet in enumerate(job.get("bullets", [])):
            tags = ", ".join(bullet.get("tags", []))
            lines.append(f"  - ({job['id']}.{i}) {bullet['text']}  [tags: {tags}]")

    lines += ["", "PROJECTS (link to these in letters):"]
    for proj in profile.get("projects", []):
        tags = ", ".join(proj.get("tags", []))
        lines.append(
            f"- [{proj['slug']}] {proj['name']} ({proj.get('meta', '')}) — "
            f"{proj['pitch']} {proj['url']}  [tags: {tags}]"
        )

    lines += ["", "AWARDS:"] + [f"- {a}" for a in profile.get("awards", [])]
    lines += ["", "VOICE RULES:"] + [f"- {v}" for v in profile.get("voice", [])]
    return "\n".join(lines)

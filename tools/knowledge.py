from __future__ import annotations
from pinecone import Pinecone
from config import get_settings


_index = None


def _get_index():
    global _index
    if _index is None:
        settings = get_settings()
        pc = Pinecone(api_key=settings.pinecone_api_key)
        _index = pc.Index(settings.pinecone_index_name)
    return _index


# ── Test knowledge base (used when no Pinecone configured) ───────────────────

TEST_KNOWLEDGE = [
    # ── Care Home Funding ────────────────────────────────────────────────────
    {
        "id": "funding-local-authority",
        "text": (
            "Local authority funding for care homes in England: Your local council "
            "may pay for some or all of your care home fees, depending on a financial "
            "means test. The key thresholds are: if you have less than £14,250 in "
            "savings and assets, the council pays in full (you contribute your income "
            "minus a Personal Expenses Allowance of £28.25/week). Between £14,250 and "
            "£23,250, the council pays but you contribute a 'tariff income' of £1/week "
            "for every £250 of savings above £14,250. Above £23,250, you are classed "
            "as a self-funder and must pay the full cost yourself. Your main home is "
            "usually not counted as an asset if your spouse, partner, a dependent child "
            "under 18, or a relative over 60 still lives there. If your home is "
            "included, you can apply for a Deferred Payment Agreement — this lets you "
            "delay selling your home by having the council pay your fees as a loan "
            "secured against the property, repaid when the home is eventually sold. "
            "Contact your local council's adult social care team to request a Care "
            "Needs Assessment — this is free and they must carry one out if you ask. "
            "Age UK (0800 678 1602) can help you understand what you're entitled to."
        ),
        "source": "Caretopia Guide: Paying for Care",
    },
    {
        "id": "funding-self-funder",
        "text": (
            "Self-funding a care home: If your savings and assets are above £23,250, "
            "you will need to pay for your care yourself. The average cost of a "
            "residential care home in England is around £800-£1,000 per week, while "
            "nursing care averages £1,000-£1,400 per week. In London and the South "
            "East, costs can be significantly higher. Even as a self-funder, you "
            "should still request a Care Needs Assessment from your council — this "
            "establishes your level of need and means you'll be picked up by the "
            "council if your funds drop below £23,250. Self-funders are also entitled "
            "to the Funded Nursing Care contribution (currently £219.71/week) if you "
            "need nursing care — this is paid directly to the care home by the NHS. "
            "Attendance Allowance is not means-tested and is worth £68.10/week "
            "(daytime or night-time needs) or £101.75/week (day and night needs). "
            "You can claim it even while in a care home if you're self-funding. "
            "A financial adviser specialising in later life (look for SOLLA-accredited "
            "advisers at societyoflaterlifeadvisers.co.uk) can help with planning, "
            "including care fee annuities and investment strategies."
        ),
        "source": "Caretopia Guide: Self-Funding Care",
    },
    {
        "id": "funding-nhs-chc",
        "text": (
            "NHS Continuing Healthcare (CHC): If your care needs are primarily "
            "health-related, you may qualify for NHS Continuing Healthcare — this "
            "means the NHS pays for your care in full, including care home fees. "
            "CHC is not means-tested, so your savings and assets are irrelevant. "
            "To be assessed, ask your GP, hospital discharge team, or social worker "
            "for a CHC Checklist screening. If the checklist indicates eligibility, "
            "a full assessment is carried out by a multidisciplinary team using the "
            "Decision Support Tool, which looks at 12 areas of need (behaviour, "
            "cognition, communication, mobility, nutrition, continence, skin "
            "integrity, breathing, drug therapies, symptom control, altered states "
            "of consciousness, and other significant needs). Each area is scored as "
            "no need, low, moderate, high, severe, or priority. You generally need "
            "at least one domain at 'severe' level or multiple at 'high' to qualify. "
            "If you're turned down, you have the right to appeal. Beacon (formerly "
            "CHC Appeals) at beaconchc.co.uk can help with the process. Many people "
            "with advanced dementia, neurological conditions, or complex medical "
            "needs qualify but are never assessed — always ask."
        ),
        "source": "Caretopia Guide: NHS Continuing Healthcare",
    },
    {
        "id": "funding-deferred-payment",
        "text": (
            "Deferred Payment Agreements (DPA): If your main home is being counted "
            "in the financial assessment and pushes you over the £23,250 threshold, "
            "you may not need to sell it immediately. A Deferred Payment Agreement "
            "with your local council allows you to use the value of your home to pay "
            "for care costs later — typically when the home is sold or from your "
            "estate after death. The council effectively loans you the money, secured "
            "against your property. You must still contribute your income (minus the "
            "Personal Expenses Allowance) and the council charges interest (currently "
            "around 2.2% above the Bank of England base rate) plus an admin fee. "
            "To be eligible, you must have less than £23,250 in non-housing assets, "
            "your home must be unoccupied (unless a qualifying person still lives "
            "there), and the council must agree. You should seek independent financial "
            "advice before entering a DPA — councils are legally required to ensure "
            "you have this opportunity. Contact your council's adult social care team "
            "to apply."
        ),
        "source": "Caretopia Guide: Deferred Payment Agreements",
    },

    # ── Care Homes vs Home Care ──────────────────────────────────────────────
    {
        "id": "care-homes-vs-home-care",
        "text": (
            "Care homes vs home care — deciding what's right: A care home (residential "
            "home) provides 24-hour support with all meals, activities, and personal "
            "care included. It's generally more suitable when someone needs round-the-"
            "clock supervision, has frequent falls, is at risk of wandering (common "
            "with dementia), or would benefit from constant companionship and "
            "structured activities. A nursing home is a care home with registered "
            "nurses on site 24/7, suitable for people with complex medical needs. "
            "Home care allows someone to stay in their own home with carers visiting "
            "at agreed times — this can range from a couple of visits per day to "
            "live-in care where a carer stays in the home full-time. Home care suits "
            "people who are mostly independent but need help with specific tasks, who "
            "have a strong attachment to their home and community, or whose needs can "
            "be safely met with the level of support provided. The cost comparison "
            "varies: a few hours of home care per day is usually cheaper than a care "
            "home, but once you need more than around 6-7 hours of daily support, a "
            "care home often becomes more cost-effective. Live-in care typically costs "
            "£1,000-£1,500/week, comparable to a care home but with one-to-one "
            "attention. Many families start with home care and move to a care home as "
            "needs increase — there's no single right answer, and it often depends on "
            "the individual's preferences, safety, and social needs."
        ),
        "source": "Caretopia Guide: Care Homes vs Home Care",
    },

    # ── Dementia ─────────────────────────────────────────────────────────────
    {
        "id": "dementia-types",
        "text": (
            "Types of dementia: Dementia is an umbrella term for a group of symptoms "
            "caused by brain diseases. The most common types are: Alzheimer's disease "
            "(accounts for 60-70% of cases — causes gradual memory loss, confusion, "
            "and difficulty with language and reasoning); vascular dementia (caused by "
            "reduced blood flow to the brain, often after a stroke — symptoms can come "
            "on suddenly or progress in steps); Lewy body dementia (causes visual "
            "hallucinations, movement problems similar to Parkinson's, and fluctuating "
            "alertness); frontotemporal dementia (affects personality, behaviour, and "
            "language — often starts at a younger age, typically 45-65); and mixed "
            "dementia (a combination of types, most commonly Alzheimer's and vascular). "
            "Less common forms include posterior cortical atrophy (affects vision and "
            "spatial awareness) and alcohol-related brain damage. Each type has "
            "different patterns of progression and care needs, so getting an accurate "
            "diagnosis is important for planning the right support."
        ),
        "source": "Caretopia Guide: Understanding Dementia",
    },
    {
        "id": "dementia-signs-progression",
        "text": (
            "Signs of dementia and how it progresses: Early signs to look out for "
            "include repeated forgetfulness (especially recent events), difficulty "
            "finding the right words, getting confused in familiar places, struggling "
            "with everyday tasks like managing money or following recipes, changes in "
            "mood or personality, and withdrawal from social activities. As dementia "
            "progresses, symptoms typically move through stages: early stage (person "
            "is mostly independent but may need reminders and some help), middle stage "
            "(needs more hands-on support with daily tasks, may become confused about "
            "time and place, personality changes become more noticeable, wandering and "
            "sundowning may occur), and later stage (needs full-time care, may not "
            "recognise loved ones, significant communication difficulties, mobility "
            "problems, and increased vulnerability to infections). The rate of "
            "progression varies enormously — some people live well with dementia for "
            "many years. If you're worried about a loved one, see the GP as a first "
            "step. An early diagnosis means you can plan ahead and access support "
            "sooner."
        ),
        "source": "Caretopia Guide: Recognising Dementia",
    },
    {
        "id": "dementia-support",
        "text": (
            "Supporting someone with dementia: Practical tips for families and carers: "
            "keep routines consistent — familiarity is comforting. Use simple, clear "
            "sentences and give time for responses. Focus on what they can still do, "
            "not what they've lost. Label cupboards and doors with pictures and words. "
            "Reduce background noise during conversations. If they become agitated, "
            "stay calm, don't argue, and try gentle distraction. Meaningful activities "
            "like looking at old photos, listening to music from their era, gardening, "
            "or folding laundry can improve wellbeing. Make the home safe by removing "
            "trip hazards, fitting stair gates if needed, and considering a GPS tracker "
            "if wandering is a concern. Key organisations that can help: Dementia UK "
            "(0800 888 6678) provides free support from Admiral Nurses — specialist "
            "dementia nurses who give one-to-one support to families. The Alzheimer's "
            "Society (0333 150 3456) offers information, a helpline, local support "
            "groups, and Singing for the Brain sessions. Your local authority may have "
            "a Dementia Adviser service, and many areas have Dementia Cafes and "
            "Memory Clinics. Power of Attorney should be arranged as early as "
            "possible while the person can still give consent."
        ),
        "source": "Caretopia Guide: Supporting Someone with Dementia",
    },
    {
        "id": "dementia-care-homes",
        "text": (
            "Dementia care in care homes: Specialist dementia care homes or units "
            "offer secure environments designed to be safe and calming for people with "
            "dementia. Features to look for include: secure outdoor garden areas (so "
            "residents can enjoy fresh air safely), clear signage with pictures and "
            "contrasting colours, memory boxes outside bedrooms with personal items, "
            "reminiscence rooms, sensory areas, and staff trained in person-centred "
            "dementia care approaches like Dementia Care Mapping or the Butterfly "
            "Household Model. Ask homes about their approach to managing distressed "
            "behaviours — good homes use understanding and distraction rather than "
            "sedation. Check the CQC report specifically for how the home supports "
            "people with dementia. Staff ratios matter — dementia care is labour-"
            "intensive and homes with higher ratios generally provide better care. "
            "Many homes offer dementia-specific activities like music therapy, doll "
            "therapy, pet therapy, and life story work. If the person still has "
            "periods of lucidity, ask how the home supports their independence and "
            "choice during those times."
        ),
        "source": "Caretopia Guide: Dementia Care Homes",
    },

    # ── ADHD in Children ─────────────────────────────────────────────────────
    {
        "id": "adhd-children-nursery",
        "text": (
            "ADHD in children — nursery and school choices: ADHD (Attention Deficit "
            "Hyperactivity Disorder) affects around 5% of children in the UK. "
            "Children with ADHD may struggle with sitting still, concentrating, "
            "following instructions, waiting their turn, and managing their emotions. "
            "When choosing a nursery or school, look for: small group sizes with good "
            "adult-to-child ratios, experienced SENCo (Special Educational Needs "
            "Coordinator), a structured but flexible routine, plenty of outdoor and "
            "physical play opportunities, a positive behaviour management approach "
            "(praise and reward rather than punishment), quiet spaces where a child "
            "can calm down, and willingness to work with external professionals like "
            "educational psychologists and paediatricians. Ask the nursery if they "
            "have experience with ADHD specifically and how they adapt activities. "
            "Children with ADHD may qualify for SEN support without a formal "
            "diagnosis, and with a diagnosis they may be eligible for an Education, "
            "Health and Care Plan (EHCP) which can fund additional support like 1:1 "
            "assistance. ADDISS (addiss.co.uk) and ADHD Foundation (adhdfoundation."
            "org.uk) are UK charities offering resources and parent support groups."
        ),
        "source": "Caretopia Guide: ADHD and Nursery Choices",
    },

    # ── Self-Care for Carers ─────────────────────────────────────────────────
    {
        "id": "carer-self-care",
        "text": (
            "Self-care for carers and family members: Caring for someone — whether "
            "a parent with dementia, a child with additional needs, or a partner with "
            "a long-term condition — can be physically and emotionally exhausting. "
            "You are not selfish for looking after yourself; you cannot pour from an "
            "empty cup. Practical strategies: accept help when it's offered and don't "
            "be afraid to ask for it. Take breaks — even 30 minutes to yourself makes "
            "a difference. Stay connected with friends and family; isolation makes "
            "everything harder. Look after your physical health — eat properly, try "
            "to sleep, and get fresh air. Talk to someone about how you're feeling — "
            "your GP, a friend, or a helpline. If you're feeling overwhelmed, angry, "
            "or tearful, that's normal — it doesn't make you a bad person or a bad "
            "carer. Key organisations: Carers UK (0808 808 7777, carersuk.org) offers "
            "a helpline, online forum, and information on carers' rights and benefits. "
            "You may be entitled to a Carer's Assessment from your local council, "
            "which can lead to support like respite care, equipment, or a personal "
            "budget. Carer's Allowance (£76.75/week) is available if you care for "
            "someone for at least 35 hours/week. The Samaritans (116 123) are "
            "available 24/7 if you need someone to talk to."
        ),
        "source": "Caretopia Guide: Looking After Yourself as a Carer",
    },
    {
        "id": "carer-respite",
        "text": (
            "Respite care for carers: Respite care gives you a break while someone "
            "else looks after the person you care for. Options include: a short stay "
            "in a care home (most homes offer respite stays from a few days to a few "
            "weeks), a sitting service where a volunteer or paid carer comes to your "
            "home so you can go out, day centres which provide activities and "
            "socialisation during the day, and replacement care through a home care "
            "agency. Your local council can arrange respite as part of a Carer's "
            "Assessment — you may get a direct payment to arrange it yourself. Many "
            "charities offer respite breaks specifically for carers, including Revitalise "
            "(revitalise.org.uk) which runs accessible holiday centres. Crossroads Care "
            "(carers.org) provides trained support workers who come into your home. "
            "Planning regular respite, even if it's just a few hours a week, helps "
            "prevent burnout and means you can keep caring for longer. If you feel "
            "guilty about taking a break, remember: the person you care for benefits "
            "when you're rested and well."
        ),
        "source": "Caretopia Guide: Respite Care",
    },

    # ── CQC Ratings ──────────────────────────────────────────────────────────
    {
        "id": "cqc-ratings-explained",
        "text": (
            "CQC ratings explained: The Care Quality Commission (CQC) is the "
            "independent regulator of health and social care in England. They inspect "
            "and rate care homes, home care agencies, hospitals, and GP practices. "
            "Ratings: Outstanding — the service is performing exceptionally well "
            "(around 5% of care homes achieve this). Good — the service is performing "
            "well and meeting expectations (approximately 80% of homes). Requires "
            "Improvement — the service is not performing as well as it should and the "
            "CQC has told them how they must improve (around 13%). Inadequate — the "
            "service is performing badly and the CQC has taken enforcement action "
            "(around 2%). Ratings are given across five key questions: Is the service "
            "Safe? (protecting people from abuse, avoidable harm, and neglect), "
            "Effective? (achieving good outcomes, evidence-based care), Caring? "
            "(staff treat people with compassion and dignity), Responsive? (services "
            "are organised to meet people's needs), and Well-led? (leadership, "
            "management, and governance ensure high-quality care). Each area gets its "
            "own rating, plus there's an overall rating. A home rated 'Good' overall "
            "might be 'Outstanding' in Caring but 'Requires Improvement' in Safe — "
            "always look at the individual ratings, not just the headline. Reports are "
            "free to read at cqc.org.uk. Homes are reinspected periodically, so check "
            "the inspection date — a report from 3+ years ago may not reflect the "
            "current situation."
        ),
        "source": "Caretopia Guide: Understanding CQC Ratings",
    },

    # ── Ofsted Ratings ───────────────────────────────────────────────────────
    {
        "id": "ofsted-ratings-nurseries",
        "text": (
            "Ofsted ratings for nurseries and early years settings: Ofsted (the "
            "Office for Standards in Education) inspects all registered childcare "
            "providers in England, including nurseries, pre-schools, childminders, "
            "and maintained nursery schools. Ratings: Outstanding — children receive "
            "an exceptional experience and make excellent progress. Good — children "
            "are well cared for and make good progress in their learning and "
            "development. Requires Improvement — the setting is not yet good but is "
            "not failing children; Ofsted will reinspect within 12 months. Inadequate "
            "— children are not safe or their care and learning falls significantly "
            "short of what is expected; the setting may face enforcement action or "
            "closure. Inspections assess: the quality of education (how well the "
            "curriculum supports children's learning), behaviour and attitudes, "
            "personal development, and leadership and management. Ofsted also checks "
            "safeguarding — if safeguarding is not effective, the setting cannot be "
            "rated higher than Inadequate. Under the new inspection framework "
            "(introduced 2019), there's a strong focus on the 'intent, implementation, "
            "and impact' of the curriculum. Reports are free at reports.ofsted.gov.uk. "
            "A 'Good' nursery with a recent report is a solid choice — 'Outstanding' "
            "is rare and the difference between Good and Outstanding often comes down "
            "to very specific curriculum design elements rather than how well children "
            "are looked after day to day."
        ),
        "source": "Caretopia Guide: Understanding Ofsted Ratings",
    },

    # ── Choosing a Care Home ─────────────────────────────────────────────────
    {
        "id": "choosing-care-home-visits",
        "text": (
            "How to choose a care home — what to look for on visits: Visit at least "
            "3 homes, and try to visit at different times of day (mealtimes are "
            "particularly revealing). Things to observe: Do staff know residents by "
            "name? Are residents engaged in activities or sitting unstimulated? Does "
            "the home smell clean without being overly clinical? Is the atmosphere "
            "warm and homely? Are communal areas inviting? Do residents look well-"
            "cared for and dressed appropriately? Can you see staff interacting warmly "
            "with residents, or are they mainly doing tasks? Is the outdoor space "
            "accessible and well-maintained?"
        ),
        "source": "Caretopia Guide: Choosing a Care Home",
    },
    {
        "id": "choosing-care-home-questions",
        "text": (
            "Questions to ask when visiting a care home: What is your staff-to-"
            "resident ratio during the day and at night? What is your staff turnover "
            "rate? (High turnover can mean inconsistent care.) What training do staff "
            "receive, especially for dementia or specific conditions? What does a "
            "typical day look like for residents? What activities do you offer and "
            "how are they tailored to individuals? How do you handle medical "
            "emergencies? What is included in the fees and what costs extra? (Common "
            "extras: hairdressing, chiropody, newspapers, outings.) Can residents "
            "personalise their rooms with their own furniture and belongings? How do "
            "you manage end-of-life care? Can family visit at any time? Is there a "
            "trial stay option? What is the complaints process? Ask to see a copy of "
            "the latest CQC report and the home's own quality assurance data. Trust "
            "your gut feeling — if somewhere feels right, it probably is."
        ),
        "source": "Caretopia Guide: Questions for Care Home Visits",
    },

    # ── Nursery Funding ──────────────────────────────────────────────────────
    {
        "id": "nursery-funding-15-hours",
        "text": (
            "Free nursery hours — the 15-hour universal entitlement: All children in "
            "England are entitled to 15 hours of free early education per week (570 "
            "hours per year) from the term after they turn 3 until they start school. "
            "This is universal — every family qualifies regardless of income or "
            "working status. Some 2-year-olds also qualify for 15 free hours if the "
            "family receives certain benefits (including Universal Credit with annual "
            "household income under £15,400, Income Support, Jobseeker's Allowance, "
            "or Employment and Support Allowance), or if the child is looked after by "
            "the local authority, has an Education Health and Care Plan, or receives "
            "Disability Living Allowance. You can check eligibility and apply through "
            "your local council. The hours can usually be spread across a minimum of "
            "2 days and a maximum of 5 days. Most nurseries offer the hours during "
            "term time only (38 weeks), but some 'stretch' them across more weeks "
            "with fewer hours per week."
        ),
        "source": "Caretopia Guide: Free Nursery Hours (15 Hours)",
    },
    {
        "id": "nursery-funding-30-hours",
        "text": (
            "Free nursery hours — the 30-hour extended entitlement: Working parents "
            "of 3 and 4-year-olds in England can get 30 hours of free childcare per "
            "week (1,140 hours per year) instead of the standard 15. To qualify, both "
            "parents (or one parent in a single-parent family) must be working and "
            "each earning at least the equivalent of 16 hours per week at the National "
            "Minimum Wage (currently around £8,700/year), and neither parent earns "
            "more than £100,000 per year. If one parent is on maternity, paternity, or "
            "adoption leave, or is unable to work due to disability or caring "
            "responsibilities, you may still qualify. Apply through the HMRC Childcare "
            "Service at childcarechoices.gov.uk — you'll receive an eligibility code "
            "to give to your nursery. You must reconfirm your eligibility every 3 "
            "months. From April 2024, the extended entitlement is being expanded: "
            "working parents of 2-year-olds can access 15 free hours, and from "
            "September 2025, working parents of children from 9 months can access "
            "30 free hours. Tax-Free Childcare is also available alongside funded "
            "hours — the government tops up 20p for every 80p you pay into a "
            "childcare account, up to £2,000/year per child (£4,000 for disabled "
            "children)."
        ),
        "source": "Caretopia Guide: Free Nursery Hours (30 Hours)",
    },

    # ── SEN in Nurseries ─────────────────────────────────────────────────────
    {
        "id": "sen-nursery-support",
        "text": (
            "SEN support in nurseries and early years: All nurseries and early years "
            "settings must have a Special Educational Needs Coordinator (SENCo) and "
            "follow the SEND Code of Practice. If a child is identified as needing "
            "SEN support, the setting should follow a 'graduated approach': Assess "
            "(understand the child's needs), Plan (agree outcomes and interventions "
            "with parents), Do (carry out the plan with appropriate support), and "
            "Review (evaluate progress and adjust). For children with more significant "
            "needs, you can request an Education, Health and Care (EHC) Needs "
            "Assessment from your local authority — if agreed, this leads to an EHC "
            "Plan which can fund additional support such as one-to-one assistance, "
            "specialist equipment, or therapies. Many areas also offer Portage — a "
            "free home-visiting educational service for pre-school children with "
            "additional needs. Early Support programmes, speech and language therapy, "
            "occupational therapy, and educational psychology services are available "
            "through the NHS and local authority. Your local SENDIASS (Special "
            "Educational Needs and Disabilities Information, Advice and Support "
            "Service) provides free, impartial advice to parents — find yours at "
            "councilfordisabledchildren.org.uk. Contact a Family (contact.org.uk, "
            "0808 808 3555) supports families of disabled children."
        ),
        "source": "Caretopia Guide: SEN Support in Nurseries",
    },

    # ── Home Care Types ──────────────────────────────────────────────────────
    {
        "id": "home-care-types",
        "text": (
            "Types of home care available in the UK: Domiciliary (visiting) care — "
            "carers visit your home at agreed times, typically for 30-minute or "
            "1-hour calls. This can include personal care (washing, dressing, "
            "toileting, medication prompts), meal preparation, light housework, and "
            "companionship. Costs range from £18-£28/hour depending on the area. "
            "Live-in care — a carer moves into your home and provides round-the-clock "
            "support, typically costing £1,000-£1,500/week. This is a popular "
            "alternative to a care home for people who want to stay in familiar "
            "surroundings. Complex care — specialist support for people with "
            "conditions requiring clinical skills, such as PEG feeding, tracheostomy "
            "care, ventilator support, or catheter management. Reablement — a "
            "short-term (usually 6 weeks) free service provided by the council after "
            "hospital discharge, focused on helping you regain independence. Night "
            "care — either a waking night carer (stays awake all night) or a sleeping "
            "night carer (available if needed). All home care providers in England "
            "must be registered with and inspected by the CQC. Your council's adult "
            "social care team can arrange a needs assessment to determine what support "
            "you're eligible for."
        ),
        "source": "Caretopia Guide: Types of Home Care",
    },
]


def _search_test_knowledge(query: str, top_k: int = 5) -> list[dict]:
    """Keyword matching with ID boosting against test knowledge base."""
    query_lower = query.lower()
    query_words = set(query_lower.split())
    # Remove common stop words
    stop_words = {"a", "the", "is", "in", "for", "to", "and", "of", "how", "do", "does", "what", "can", "i", "my", "me"}
    query_words -= stop_words

    scored = []
    for item in TEST_KNOWLEDGE:
        text_lower = item["text"].lower()
        id_lower = item["id"].lower()

        # Score: word matches in text
        text_hits = sum(1 for w in query_words if w in text_lower)
        # Bonus: word matches in the article ID (strong topic signal)
        id_hits = sum(2 for w in query_words if w in id_lower)

        score = (text_hits + id_hits) / max(len(query_words), 1)
        if score > 0:
            scored.append({**item, "score": round(min(score, 1.0), 2)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ── Main function ────────────────────────────────────────────────────────────

async def search_knowledge_base(
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """Search knowledge base.

    Currently uses curated test knowledge base (accurate UK care content).
    TODO: Switch to live Pinecone once embedding model is confirmed.
    The Pinecone index 'caretopia-docs' has 84 vectors at 384 dimensions —
    likely all-MiniLM-L6-v2 or similar. Need to confirm before querying.
    """
    return _search_test_knowledge(query, top_k)

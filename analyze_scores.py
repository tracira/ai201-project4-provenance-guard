import os
from dotenv import load_dotenv
load_dotenv()

from signals import classify_with_llm, compute_stylo_score, compute_formality_score, \
    _sentence_length_score, _ttr_score, _punctuation_score, _word_length_score
from scoring import compute_final_score, classify

# 5 known-human texts: attributable human-authored content with idiosyncratic voice
HUMAN_TEXTS = [
    ("Human-1: informal personal anecdote",
     "ok so i finally tried that new ramen place downtown and honestly? "
     "underwhelming. the broth was fine but they put WAY too much sodium in it and "
     "i was thirsty for like three hours after. my friend got the spicy version and "
     "said it was better. probably won't go back unless someone drags me there"),

    ("Human-2: journal entry with self-correction",
     "Tuesday again. I told myself I'd start the chapter rewrite after lunch but "
     "then I spent forty minutes reading about the history of the fax machine, which "
     "is honestly kind of fascinating? anyway. the rewrite is not started. I did "
     "reorganize my desk though, so that counts for something I guess. "
     "tomorrow. definitely tomorrow."),

    ("Human-3: personal essay fragment with expressive punctuation",
     "My grandmother never learned to drive — she didn't need to, in the village. "
     "But here she was, 74, in a DMV waiting room in suburban New Jersey, "
     "clutching her birth certificate in a plastic sleeve like it might escape. "
     "She kept asking me if her English was good enough. It was; it wasn't the "
     "problem. The problem was everything else."),

    ("Human-4: opinionated blog-style rant",
     "Hot take: open offices are a scam. Not a productivity scam — an attention "
     "scam. You're not in an 'collaborative environment,' you're in a room where "
     "Karen from accounting can watch your screen and ask if you're busy. I spent "
     "three years in one. I got more done in the first two weeks of pandemic WFH "
     "than I had in months. The data backs this up, by the way. Nobody wants to "
     "hear it, but it does."),

    ("Human-5: memoir-style observation",
     "The thing about growing up without money is that you develop weird little "
     "rituals around it. My mother saved every rubber band that came on the "
     "newspaper. Not because we needed rubber bands — we had a drawer full — "
     "but because throwing it away felt wrong. I do the same thing now. "
     "I earn enough that it's absurd. The drawer is still full."),
]

# 5 known-AI texts: outputs with the hallmarks of AI generation
AI_TEXTS = [
    ("AI-1: corporate transformation paragraph",
     "Artificial intelligence represents a transformative paradigm shift in modern "
     "society. It is important to note that while the benefits of AI are numerous, "
     "it is equally essential to consider the ethical implications. Furthermore, "
     "stakeholders across various sectors must collaborate to ensure responsible "
     "deployment and sustainable innovation ecosystems."),

    ("AI-2: educational overview with enumeration",
     "Machine learning encompasses a broad range of techniques that enable systems "
     "to learn from data and improve over time. There are three primary categories: "
     "supervised learning, unsupervised learning, and reinforcement learning. Each "
     "approach has distinct advantages and is suited to different types of problems. "
     "Understanding these distinctions is crucial for selecting the appropriate "
     "methodology for a given use case."),

    ("AI-3: structured benefits essay",
     "Remote work offers numerous advantages for both employees and organizations. "
     "First, it eliminates the need for daily commuting, saving time and reducing "
     "stress. Second, employees gain greater flexibility in managing their schedules, "
     "which can lead to improved work-life balance. Third, companies can reduce "
     "overhead costs associated with maintaining large office spaces. These benefits "
     "collectively contribute to higher employee satisfaction and retention rates."),

    ("AI-4: comprehensive guide introduction",
     "In this comprehensive guide, we will explore the key principles of effective "
     "project management. Whether you are a seasoned professional or just beginning "
     "your journey, understanding these foundational concepts will help you deliver "
     "projects on time and within budget. We will cover planning, execution, "
     "monitoring, and closure — the four essential phases of any successful project "
     "lifecycle."),

    ("AI-5: balanced analysis paragraph",
     "Climate change presents one of the most significant challenges facing humanity "
     "today. The scientific consensus is clear: global temperatures are rising due to "
     "increased greenhouse gas emissions. Addressing this issue requires a "
     "multifaceted approach that includes transitioning to renewable energy sources, "
     "improving energy efficiency, and implementing carbon pricing mechanisms. "
     "International cooperation is essential, as climate change is inherently a "
     "global problem that transcends national boundaries."),
]

ALL_INPUTS = [("HUMAN", *t) for t in HUMAN_TEXTS] + [("AI", *t) for t in AI_TEXTS]

results = {"HUMAN": [], "AI": []}

for group, label, text in ALL_INPUTS:
    llm_score, _ = classify_with_llm(text)
    s1 = _sentence_length_score(text)
    s2 = _ttr_score(text)
    s3 = _punctuation_score(text)
    s4 = _word_length_score(text)
    stylo    = compute_stylo_score(text)
    formality = compute_formality_score(text)
    final    = compute_final_score(llm_score, stylo, formality)
    classification, conf = classify(final)

    print(f"\n{'='*60}")
    print(f"  [{group}] {label}")
    print(f"{'='*60}")
    print(f"  LLM signal         : {llm_score:.3f}")
    print(f"  Stylo signal       : {stylo:.3f}")
    print(f"    sentence_length  : {s1:.3f}")
    print(f"    ttr              : {s2:.3f}")
    print(f"    punctuation      : {s3:.3f}")
    print(f"    word_length      : {s4:.3f}")
    print(f"  Formality signal   : {formality:.3f}")
    print(f"  final_score        : {final:.3f}")
    print(f"  result             : {classification} [{conf} confidence]")

    results[group].append((label, llm_score, stylo, formality, final, classification, conf))

print(f"\n{'='*60}")
print("  SUMMARY")
print(f"{'='*60}")
human_scores = [r[4] for r in results["HUMAN"]]
ai_scores    = [r[4] for r in results["AI"]]
print(f"  Human final_scores : {[round(s,3) for s in human_scores]}")
print(f"  AI    final_scores : {[round(s,3) for s in ai_scores]}")
print(f"  Human avg          : {sum(human_scores)/len(human_scores):.3f}")
print(f"  AI    avg          : {sum(ai_scores)/len(ai_scores):.3f}")

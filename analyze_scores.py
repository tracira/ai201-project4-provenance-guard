import os
from dotenv import load_dotenv
load_dotenv()

from signals import classify_with_llm, compute_stylo_score, \
    _sentence_length_score, _ttr_score, _punctuation_score, _word_length_score
from scoring import compute_final_score, classify

INPUTS = [
    ("Clearly AI-generated",
     "Artificial intelligence represents a transformative paradigm shift in modern society. "
     "It is important to note that while the benefits of AI are numerous, it is equally "
     "essential to consider the ethical implications. Furthermore, stakeholders across "
     "various sectors must collaborate to ensure responsible deployment."),

    ("Clearly human-written",
     "ok so i finally tried that new ramen place downtown and honestly? "
     "underwhelming. the broth was fine but they put WAY too much sodium in it and "
     "i was thirsty for like three hours after. my friend got the spicy version and "
     "said it was better. probably won't go back unless someone drags me there"),

    ("Borderline: formal human writing",
     "The relationship between monetary policy and asset price inflation has been "
     "extensively studied in the literature. Central banks face a fundamental tension "
     "between their mandate for price stability and the unintended consequences of "
     "prolonged low interest rates on equity and real estate valuations."),

    ("Borderline: lightly edited AI output",
     "I've been thinking a lot about remote work lately. There are genuine tradeoffs — "
     "flexibility and no commute on one side, isolation and blurred work-life boundaries "
     "on the other. Studies show productivity varies widely by individual and role type."),
]

for label, text in INPUTS:
    llm_score, _ = classify_with_llm(text)
    s1 = _sentence_length_score(text)
    s2 = _ttr_score(text)
    s3 = _punctuation_score(text)
    s4 = _word_length_score(text)
    stylo = compute_stylo_score(text)
    final = compute_final_score(llm_score, stylo)
    classification, conf = classify(final)

    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")
    print(f"  LLM signal         : {llm_score:.3f}")
    print(f"  Stylo signal       : {stylo:.3f}")
    print(f"    sentence_length  : {s1:.3f}")
    print(f"    ttr              : {s2:.3f}")
    print(f"    punctuation      : {s3:.3f}")
    print(f"    word_length      : {s4:.3f}")
    print(f"  final_score        : {final:.3f}")
    print(f"  result             : {classification} [{conf} confidence]")

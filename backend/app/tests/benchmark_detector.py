import sys
sys.path.insert(0, ".")
import pytest
from app.services.analyzer import analyze_document_risk

# --- Benchmark Dataset ---

HUMAN_PAPER = """
We present a novel methodology for measuring semantic drift in transformer-based models. 
By utilizing high-dimensional embeddings, our system captures syntactic fluctuations across temporal slices. 
First, we construct a custom corpus of 10,000 articles. 
Then, we evaluate the similarity using cosine projections. 
Our empirical results demonstrate a significant shift in word representation over time. 
Interestingly, words like 'computer' showed high stability, whereas terms related to 'social media' fluctuated wildly. 
Overall, this study provides new insights into lexicon evolution.
"""

CHATGPT_PAPER = """
It is important to note that natural language processing is rapidly evolving in the digital age. 
Delving into deep neural structures is a crucial task for researchers. 
We utilize state-of-the-art architectures to analyze this trend. 
Additionally, it is worth noting that the results show marked improvements. 
Moreover, the system is capable of high-dimensional projections. 
Furthermore, the parameters were evaluated using standard criteria. 
In conclusion, this study underscores the importance of further research in this field.
"""

GEMINI_PAPER = """
In this digital age, machine learning plays a pivotal role in shaping the future of research. 
By leveraging advanced deep neural networks, we can demystify complex data landscapes. 
A stark contrast is observed between traditional models and neural networks. 
We utilize various algorithms to optimize performance parameters. 
The system was implemented using Python, and the results were evaluated. 
Specifically, the accuracy was markedly improved under optimal conditions. 
In summary, this study provides pivotal insights that are essential for future studies.
"""

CLAUDE_PAPER = """
The field of natural language processing stands as a testament to the rapid progression of modern AI. 
To examine these transitions, we foster a deeper understanding of semantic patterns. 
This remains a challenge in the current research landscape. 
Indeed, navigating the intricate details of word vectors is highly critical. 
We demonstrated the accuracy improvements on standard benchmark datasets. 
Consequently, the overall performance was significantly boosted by our approach. 
Ultimately, this analysis sheds light on crucial developmental trajectories.
"""

MIXED_PAPER = """
We present a novel methodology for measuring semantic drift in transformer-based models. 
By utilizing high-dimensional embeddings, our system captures syntactic fluctuations across temporal slices. 
It is important to note that natural language processing is rapidly evolving in the digital age. 
Delving into deep neural structures is a crucial task for researchers. 
Our empirical results demonstrate a significant shift in word representation over time. 
In conclusion, this study underscores the importance of further research in this field.
"""


def test_human_paper_benchmark():
    res = analyze_document_risk(HUMAN_PAPER)
    score = res["overall_score"]
    details = res["risk_details"]
    print(f"\n[BENCHMARK] Human Paper AI Risk Score: {score}%")
    print(f"Details: Perplexity={details['perplexity_score']}, Entropy={details['entropy_score']}, Repetition={details['repetition_score']}%, Predictability={details['ngram_predictability']}%")
    # Human paper should be low risk
    assert score < 35.0

def test_chatgpt_paper_benchmark():
    res = analyze_document_risk(CHATGPT_PAPER)
    score = res["overall_score"]
    details = res["risk_details"]
    print(f"\n[BENCHMARK] ChatGPT Paper AI Risk Score: {score}%")
    print(f"Details: Perplexity={details['perplexity_score']}, Entropy={details['entropy_score']}, Repetition={details['repetition_score']}%, Predictability={details['ngram_predictability']}%")
    # ChatGPT paper should be high risk
    assert score > 70.0

def test_gemini_paper_benchmark():
    res = analyze_document_risk(GEMINI_PAPER)
    score = res["overall_score"]
    details = res["risk_details"]
    print(f"\n[BENCHMARK] Gemini Paper AI Risk Score: {score}%")
    print(f"Details: Perplexity={details['perplexity_score']}, Entropy={details['entropy_score']}, Repetition={details['repetition_score']}%, Predictability={details['ngram_predictability']}%")
    # Gemini paper should be high risk (>= 65.0%)
    assert score >= 65.0

def test_claude_paper_benchmark():
    res = analyze_document_risk(CLAUDE_PAPER)
    score = res["overall_score"]
    details = res["risk_details"]
    print(f"\n[BENCHMARK] Claude Paper AI Risk Score: {score}%")
    print(f"Details: Perplexity={details['perplexity_score']}, Entropy={details['entropy_score']}, Repetition={details['repetition_score']}%, Predictability={details['ngram_predictability']}%")
    # Claude paper should be high risk (>= 65.0%)
    assert score >= 65.0

def test_mixed_paper_benchmark():
    res = analyze_document_risk(MIXED_PAPER)
    score = res["overall_score"]
    details = res["risk_details"]
    print(f"\n[BENCHMARK] Mixed Paper AI Risk Score: {score}%")
    print(f"Details: Perplexity={details['perplexity_score']}, Entropy={details['entropy_score']}, Repetition={details['repetition_score']}%, Predictability={details['ngram_predictability']}%")
    # Mixed paper should be moderate risk
    assert 40.0 <= score <= 68.0

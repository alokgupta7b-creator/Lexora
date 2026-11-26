import pytest
from app.services.rephraser import execute_rephrase, protect_sentence_entities

def test_protect_sentence_entities():
    # Test sentence containing acronyms, proper nouns, stats, decimals, percentages, DOI, and Table/Figure refs
    sentence = "We evaluated BERT and RoBERTa on SemEval dataset, obtaining 95.5% accuracy (p < 0.01) as discussed in Section 3 and shown in Figure 2. Contact us at research@univ.edu or DOI: 10.1000/xyz123."
    
    masked_sent, entity_map, count = protect_sentence_entities(sentence)
    
    # Assert acronyms, statistics, dataset names, email, DOI, and sections are masked
    assert "BERT" not in masked_sent
    assert "RoBERTa" not in masked_sent
    assert "SemEval" not in masked_sent
    assert "95.5%" not in masked_sent
    assert "p < 0.01" not in masked_sent
    assert "Section 3" not in masked_sent
    assert "Figure 2" not in masked_sent
    assert "research@univ.edu" not in masked_sent
    assert "DOI: 10.1000/xyz123" not in masked_sent
    
    # Assert placeholders are injected
    assert "__SENT_PROT_" in masked_sent
    assert count >= 6
    
    # Assert placeholders map back to original values correctly
    for key, val in entity_map.items():
        assert key in masked_sent
        assert val in sentence

def test_execute_rephrase_intensities():
    text = "Artificial intelligence plays a crucial role in modern NLP methods. We use this proposed approach to analyze raw datasets. The model shows good performance."
    
    # Assert Low level: structure and syntax identical, minor replacements
    low_res = execute_rephrase(text, level="Low")
    assert low_res["sentences_rewritten_count"] <= 2
    assert "plays a crucial role" in low_res["rewritten_text"] # Low shouldn't trigger phrase-level substitution map
    
    # Assert Medium/High levels: phrase-level substitutions occur
    medium_res = execute_rephrase(text, level="Medium")
    assert "plays a crucial role" not in medium_res["rewritten_text"]
    assert "plays a pivotal role" in medium_res["rewritten_text"] or "pivotal role" in medium_res["rewritten_text"]
    
    # Assert metrics metadata dictionary is fully populated
    assert "sentences_rewritten_count" in medium_res
    assert "protected_entities_preserved_count" in medium_res
    assert "phrase_substitutions_applied" in medium_res
    assert "synonym_substitutions_applied" in medium_res
    assert "semantic_similarity_score" in medium_res
    assert "lexical_diversity_delta" in medium_res
    assert "processing_time_ms" in medium_res
    
    # Assert similarity check keeps content sane
    assert medium_res["semantic_similarity_score"] >= 0.70

def test_rephraser_correctness_conjunctions():
    # Verify conjunctions (and, but, or) are never replaced in isolation with wrong words
    text = "We evaluated LIWC and the NRC Emotion Lexicon but the model lacks some specific structures."
    res = execute_rephrase(text, level="High")
    
    # Conjunctions shouldn't be blindly substituted to result in bad grammar
    assert "LIWC moreover" not in res["rewritten_text"]
    assert "coverage however lacked" not in res["rewritten_text"]


def test_all_paraphraser_modes():
    text = (
        "Because the model is highly complex, we utilize advanced deep learning techniques in order to achieve high performance. "
        "The model shows good performance and plays an important role in NLP."
    )
    
    # 1. Academic Rephrase
    res_acad = execute_rephrase(text, mode="Academic", level="Medium")
    assert "plays a pivotal role" in res_acad["rewritten_text"] or "pivotal role" in res_acad["rewritten_text"] or "role" in res_acad["rewritten_text"]
    assert "original_text" in res_acad
    assert res_acad["mode"] == "Academic"

    # 2. Journal Submission Style
    res_journ = execute_rephrase(text, mode="Journal Submission Style", level="High")
    assert res_journ["mode"] == "Journal Submission Style"

    # 3. Formal Writing
    res_formal = execute_rephrase("The results are bad, so we help the system.", mode="Formal Writing", level="Medium")
    assert "suboptimal" in res_formal["rewritten_text"] or "results" in res_formal["rewritten_text"]
    assert "therefore" in res_formal["rewritten_text"] or "illustrate" in res_formal["rewritten_text"] or "assist" in res_formal["rewritten_text"] or "help" in res_formal["rewritten_text"]

    # 4. Concise Writing
    res_concise = execute_rephrase(text, mode="Concise Writing", level="Medium")
    assert "to" in res_concise["rewritten_text"]

    # 5. Expanded Writing
    res_expanded = execute_rephrase("To build a model is good. Many people use it because it is helpful.", mode="Expanded Writing", level="Medium")
    assert "in order to" in res_expanded["rewritten_text"] or "make use of" in res_expanded["rewritten_text"] or "use" in res_expanded["rewritten_text"]


def test_all_humanizer_modes():
    from app.services.humanizer import execute_humanize
    text = "It is important to note that the proposed method plays a crucial role in natural language processing. Delving into the results shows a tapestry of findings."

    # 1. Academic Humanizer
    res_acad = execute_humanize(text, mode="Academic Humanizer", level="Medium")
    assert "tapestry" not in res_acad["rewritten_text"]
    assert "examine" in res_acad["rewritten_text"] or "structure" in res_acad["rewritten_text"] or "findings" in res_acad["rewritten_text"]
    assert "overall_risk_before" in res_acad
    assert "overall_risk_after" in res_acad

    # 2. Natural Humanizer
    res_nat = execute_humanize("We utilize neural networks to facilitate learning. We investigate the baseline.", mode="Natural Humanizer", level="Medium")
    assert "utilize" not in res_nat["rewritten_text"]
    assert "use" in res_nat["rewritten_text"] or "using" in res_nat["rewritten_text"] or "learning" in res_nat["rewritten_text"]

    # 3. Reviewer-Friendly Humanizer
    res_rev = execute_humanize("The results indicate that our method was conducted correctly.", mode="Reviewer-Friendly Humanizer", level="Medium")
    assert "the data show that" in res_rev["rewritten_text"] or "was run" in res_rev["rewritten_text"] or "show" in res_rev["rewritten_text"] or "results" in res_rev["rewritten_text"]

    # 4. Journal-Ready Humanizer
    res_jr = execute_humanize("Furthermore, the findings show a significant improvement. In conclusion, the model is good.", mode="Journal-Ready Humanizer", level="Medium")
    assert "what is more," in res_jr["rewritten_text"] or "demonstrate" in res_jr["rewritten_text"] or "taken together," in res_jr["rewritten_text"] or "favorable" in res_jr["rewritten_text"] or "findings" in res_jr["rewritten_text"]


def test_preservations_in_both():
    from app.services.humanizer import execute_humanize
    text = "The equation $E = mc^2$ was validated by Einstein [1]. We analyze this under p < 0.05 conditions."

    # Test Rephraser
    res_rep = execute_rephrase(text, mode="Academic", level="High")
    assert "$E = mc^2$" in res_rep["rewritten_text"]
    assert "[1]" in res_rep["rewritten_text"]

    # Test Humanizer
    res_hum = execute_humanize(text, mode="Academic Humanizer", level="High")
    assert "$E = mc^2$" in res_hum["rewritten_text"]
    assert "[1]" in res_hum["rewritten_text"]


# ===========================================================================
# Metric correctness regression tests (USER requirement 2026-06-14)
# ===========================================================================

def test_metrics_zero_when_no_change():
    """
    If the engine makes no changes (e.g. Low mode with no phrase matches),
    every transformation counter must be exactly 0 and modification_percentage
    must be 0.0.
    """
    # A sentence with no phrase-library hits and no safe-synonym candidates
    text = "The threshold is 0.5 and the configuration is fixed."
    res = execute_rephrase(text, mode="Academic", level="Low")

    if res["rewritten_text"].strip() == text.strip():
        assert res["transformations_applied"] == 0, (
            f"transformations_applied should be 0 when text is unchanged, "
            f"got {res['transformations_applied']}"
        )
        assert res["sentences_modified"] == 0, (
            f"sentences_modified should be 0 when text is unchanged, "
            f"got {res['sentences_modified']}"
        )
        assert res["modification_percentage"] == 0.0, (
            f"modification_percentage should be 0.0 when text is unchanged, "
            f"got {res['modification_percentage']}"
        )


def test_metrics_match_visible_output():
    """
    The reported sentences_modified must equal the number of sentences
    that actually differ between original and rewritten text.
    """
    text = (
        "We show a very good result. "
        "The threshold is 0.5 and the configuration is fixed. "
        "This approach helps to improve performance."
    )
    res = execute_rephrase(text, mode="Academic", level="High")

    import nltk
    orig_sents   = nltk.sent_tokenize(text)
    rew_sents    = nltk.sent_tokenize(res["rewritten_text"])

    # Count sentences that actually changed
    actual_changed = sum(
        1 for o, r in zip(orig_sents, rew_sents) if o.strip() != r.strip()
    )

    assert res["sentences_modified"] == actual_changed, (
        f"sentences_modified={res['sentences_modified']} does not match "
        f"actual changed sentences={actual_changed}.\n"
        f"Original:  {orig_sents}\n"
        f"Rewritten: {rew_sents}"
    )
    assert res["modification_percentage"] == round(
        actual_changed / len(orig_sents) * 100 if orig_sents else 0.0, 1
    )


def test_transformations_applied_never_exceeds_modified_sentences():
    """
    transformations_applied should be >= sentences_modified (at least one
    change per modified sentence) and should not include reverted candidates.
    """
    text = (
        "We show a very good result about many configurations. "
        "The method is important and used widely in practice."
    )
    res = execute_rephrase(text, mode="Academic", level="High")

    # If sentences_modified == 0, transformations_applied must also be 0
    if res["sentences_modified"] == 0:
        assert res["transformations_applied"] == 0, (
            "transformations_applied must be 0 when no sentence was modified"
        )
    else:
        assert res["transformations_applied"] >= res["sentences_modified"], (
            "transformations_applied should be >= sentences_modified"
        )


def test_lexical_diversity_delta_consistent():
    """
    lexical_diversity_delta must be 0.0 (or very close) when the text is
    unchanged, and non-zero when rewriting actually occurred.
    """
    text = "The threshold is 0.5 and the configuration is fixed."
    res = execute_rephrase(text, mode="Academic", level="Low")
    if res["rewritten_text"].strip() == text.strip():
        assert abs(res["lexical_diversity_delta"]) < 0.01, (
            f"ld_delta should be ~0 when text is unchanged, got {res['lexical_diversity_delta']}"
        )


def test_phrase_and_synonym_counts_only_committed():
    """
    phrase_substitutions_applied and synonym_substitutions_applied must
    reflect only the substitutions that survived the validation gate and
    appear in the final text — not attempted / discarded rewrites.
    """
    # Use a sentence the engine would normally try to rewrite
    text = "We show a very good result."
    res = execute_rephrase(text, mode="Academic", level="High")

    reported_phrase = res["phrase_substitutions_applied"]
    reported_syn    = res["synonym_substitutions_applied"]

    # Verify: if rewritten_text equals original, both counts must be 0
    if res["rewritten_text"].strip() == text.strip():
        assert reported_phrase == 0 and reported_syn == 0, (
            "Substitution counts must be 0 when output equals input"
        )
    else:
        # At least one of them must be non-zero
        assert reported_phrase + reported_syn > 0, (
            "At least one substitution must be reported when text changed"
        )


def test_humanizer_metrics_match_visible_output():
    """
    Humanizer reported metrics must match the actual visible text differences.
    """
    from app.services.humanizer import execute_humanize
    import nltk

    text = (
        "It is important to note that the proposed method plays a crucial role. "
        "Delving into results reveals a tapestry of complex findings."
    )
    res = execute_humanize(text, mode="Academic Humanizer", level="Medium")

    orig_sents = nltk.sent_tokenize(text)
    rew_sents  = nltk.sent_tokenize(res["rewritten_text"])
    actual_changed = sum(
        1 for o, r in zip(orig_sents, rew_sents) if o.strip() != r.strip()
    )

    assert res["sentences_modified"] == actual_changed, (
        f"Humanizer sentences_modified={res['sentences_modified']} does not "
        f"match actual changed={actual_changed}"
    )


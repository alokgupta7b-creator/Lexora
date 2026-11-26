import re
from typing import Dict, Any, Optional

from app.services.rewrite_engine import (
    RewriteEngine,
    protect_sentence_entities,
    calculate_sentence_similarity,
    validate_sentence_integrity,
    preserve_special_elements,
    restore_special_elements,
    check_inflection_match,
    get_synonym_candidates,
    rank_synonyms,
    SAFE_SYNONYM_MAP,
)

# ===========================================================================
# PHRASE LIBRARIES
# ---------------------------------------------------------------------------
# All entries are (regex_pattern → replacement_string) pairs.
# Patterns target STYLISTIC / INTRODUCTORY phrasing only — never technical
# domain terms.  Patterns are ordered longest-match first to avoid partial
# overlap.
# ===========================================================================

# ---------------------------------------------------------------------------
# ACADEMIC REPHRASE — replaces over-used phrases with precise equivalents
# ---------------------------------------------------------------------------
ACADEMIC_PHRASES: Dict[str, str] = {
    # Wordy introductory clauses → concise equivalents
    r'\bdue to the fact that\b':        'because',
    r'\bin order to\b':                 'to',
    r'\bwith respect to\b':             'regarding',
    r'\bwith regard to\b':              'regarding',
    r'\bat this point in time\b':       'currently',
    r'\bhas the capability to\b':       'is capable of',
    r'\bin the case of\b':              'for',
    r'\bfor the purpose of\b':          'to',
    r'\bin light of the fact that\b':   'given that',
    r'\bby means of\b':                 'through',
    r'\bprior to\b':                    'before',
    r'\bsubsequent to\b':               'after',
    r'\bin addition to\b':              'beyond',
    r'\ba large number of\b':           'numerous',
    r'\ba number of\b':                 'several',
    r'\bvery important\b':              'critical',
    r'\bvery large\b':                  'substantial',
    r'\bvery small\b':                  'minimal',
    r'\bvery high\b':                   'considerably high',
    r'\bvery low\b':                    'notably low',
    # Over-used academic clichés
    r'\bplays a crucial role\b':        'plays a pivotal role',
    r'\bplays an important role\b':     'serves a significant role',
    r'\bplays a key role\b':            'serves a fundamental role',
    r'\bplays a significant role\b':    'occupies a central role',
    r'\bwidely used\b':                 'commonly adopted',
    r'\bcommonly used\b':               'frequently employed',
    r'\bfrequently used\b':             'extensively employed',
    r'\bis based on\b':                 'builds upon',
    r'\bare based on\b':                'build upon',
    r'\bshows good performance\b':      'demonstrates high efficacy',
    r'\bshowed good performance\b':     'demonstrated high efficacy',
    r'\bshows promising results\b':     'yields promising outcomes',
    r'\bshowed promising results\b':    'yielded promising outcomes',
    r'\bsheds light on\b':              'elucidates',
    r'\bshed light on\b':              'elucidate',
    r'\bclear evidence of\b':           'compelling evidence of',
    r'\bstrong evidence of\b':          'substantial evidence of',
    r'\bconduct an analysis of\b':      'analyze',
    r'\bconduct a study of\b':          'study',
    r'\bcarry out an analysis\b':       'perform an analysis',
    r'\bmake use of\b':                 'utilize',
    r'\bactive research area\b':        'an area of intense research focus',
    r'\bhelps researchers study\b':     'facilitates the investigation of',
    r'\bhelps in understanding\b':      'aids in understanding',
    r'\bprovided broad coverage\b':     'offered comprehensive coverage',
    r'\bshowed standard performance\b': 'demonstrated typical baseline performance',
    r'\bcomes to mind\b':               'is apparent',
    # Passive-sounding hedges → direct phrasing
    r'\bit is worth noting that\b':     'notably,',
    r'\bit is important to note that\b': 'notably,',
    r'\bit should be noted that\b':     'notably,',
    r'\bit is well known that\b':       'it is established that',
    r'\bit is widely accepted that\b':  'it is generally established that',
    r'\bit has been shown that\b':      'prior work demonstrates that',
    r'\bit can be seen that\b':         'the results reveal that',
    r'\bthe results indicate that\b':   'the results demonstrate that',
    r'\bthe results show that\b':       'the results reveal that',
}

# ---------------------------------------------------------------------------
# JOURNAL SUBMISSION STYLE — elevated, precise academic register
# ---------------------------------------------------------------------------
JOURNAL_PHRASES: Dict[str, str] = {
    **ACADEMIC_PHRASES,
    r'\bin conclusion,?\b':             'taken together,',
    r'\bin summary,?\b':                'collectively,',
    r'\boverall,?\b':                   'in aggregate,',
    r'\bwe show\b':                     'we demonstrate',
    r'\bwe found\b':                    'we identified',
    r'\bwe find\b':                     'we identify',
    r'\bwe use\b':                      'we employ',
    r'\bwe used\b':                     'we employed',
    r'\bwe propose\b':                  'we present',
    r'\bwe investigate\b':              'we examine',
    r'\bwe study\b':                    'we examine',
    r'\bwe analyze\b':                  'we systematically analyze',
    r'\bthis paper shows\b':            'this work demonstrates',
    r'\bthis paper presents\b':         'this work introduces',
    r'\bthis paper proposes\b':         'this work proposes',
    r'\bthis study shows\b':            'this study demonstrates',
    r'\bthis work shows\b':             'this work demonstrates',
    r'\bfurthermore,?\b':               'moreover,',
    r'\bmoreover,?\b':                  'furthermore,',
    r'\bhowever,?\b':                   'nevertheless,',
    r'\bthus,?\b':                      'consequently,',
    r'\btherefore,?\b':                 'accordingly,',
}

# ---------------------------------------------------------------------------
# FORMAL WRITING — business / institutional register
# ---------------------------------------------------------------------------
FORMAL_PHRASES: Dict[str, str] = {
    r'\bdue to the fact that\b':    'because',
    r'\bin order to\b':             'to',
    r'\bwith respect to\b':         'regarding',
    r'\bwith regard to\b':          'regarding',
    r'\bhas the capability to\b':   'can',
    r'\bby means of\b':             'through',
    r'\bprior to\b':                'before',
    r'\bsubsequent to\b':           'after',
    r'\ba large number of\b':       'numerous',
    r'\bgood\b':                    'satisfactory',
    r'\bbad\b':                     'suboptimal',
    r'\bhelp\b':                    'assist',
    r'\bshow\b':                    'illustrate',
    r'\bget\b':                     'obtain',
    r'\bso\b':                      'therefore',
    r'\bbut\b':                     'however',
    r'\babout\b':                   'approximately',
    r'\bfind\b':                    'determine',
}

# ---------------------------------------------------------------------------
# CONCISE WRITING — remove verbosity, tighten wording
# ---------------------------------------------------------------------------
CONCISE_PHRASES: Dict[str, str] = {
    r'\bdue to the fact that\b':        'because',
    r'\bin order to\b':                 'to',
    r'\bwith respect to\b':             'regarding',
    r'\bwith regard to\b':              'regarding',
    r'\bat this point in time\b':       'now',
    r'\bhas the capability to\b':       'can',
    r'\bfor the purpose of\b':          'to',
    r'\bin light of the fact that\b':   'given',
    r'\bby means of\b':                 'via',
    r'\bprior to\b':                    'before',
    r'\bsubsequent to\b':               'after',
    r'\ba large number of\b':           'many',
    r'\ba number of\b':                 'some',
    r'\bconduct an analysis of\b':      'analyze',
    r'\bconduct a study of\b':          'study',
    r'\bcarry out an analysis\b':       'analyze',
    r'\bmake use of\b':                 'use',
    r'\bplays an important role\b':     'matters',
    r'\bplays a crucial role\b':        'is key',
    r'\bplays a key role\b':            'is key',
    r'\bplays a significant role\b':    'is significant',
    r'\bshows good performance\b':      'performs well',
    r'\bshowed good performance\b':     'performed well',
    r'\bhelps researchers study\b':     'helps study',
    r'\bit is worth noting that\b':     'notably,',
    r'\bit is important to note that\b': 'notably,',
    r'\bit should be noted that\b':     'notably,',
}

# ---------------------------------------------------------------------------
# EXPANDED WRITING — elaborate phrasing for length / detail
# ---------------------------------------------------------------------------
EXPANDED_PHRASES: Dict[str, str] = {
    r'\bbecause\b':     'due to the fact that',
    r'\bto\b':          'in order to',
    r'\bmany\b':        'a large number of',
    r'\bsome\b':        'a number of',
    r'\bnow\b':         'at this point in time',
    r'\bregarding\b':   'with respect to',
    r'\bcan\b':         'has the capability to',
    r'\banalyze\b':     'conduct a detailed analysis of',
    r'\banalyses\b':    'conducts detailed analyses of',
    r'\buse\b':         'make use of',
    r'\bvia\b':         'by means of',
    r'\bbefore\b':      'prior to',
    r'\bafter\b':       'subsequent to',
    r'\bperforms well\b': 'exhibits highly satisfactory performance characteristics',
    r'\bis key\b':       'serves as a fundamental component',
}


# ---------------------------------------------------------------------------
# REVIEWER-FRIENDLY STYLE — clear, defensive, methodologically sound
# ---------------------------------------------------------------------------
REVIEWER_FRIENDLY_PHRASES: Dict[str, str] = {
    **ACADEMIC_PHRASES,
    r'\bobviously\b':                   'manifestly',
    r'\bclearly\b':                     'evidently',
    r'\bof course\b':                   'as anticipated',
    r'\bprove\b':                       'support the hypothesis that',
    r'\bproves\b':                      'supports the hypothesis that',
    r'\bproven\b':                      'supported',
    r'\bperfect\b':                     'optimal',
    r'\bwe check\b':                    'we verify',
    r'\bwe checked\b':                  'we verified',
    r'\bit is obvious that\b':          'the evidence suggests that',
    r'\bthere is no doubt that\b':      'the findings strongly support that',
}


def execute_rephrase(
    text: str,
    mode: str = "Academic",
    level: str = "Medium",
    section: Optional[str] = None
) -> Dict[str, Any]:
    """
    Configures and executes the shared RewriteEngine for the requested mode and
    intensity level.

    Intensity behaviour:
      Low     — phrase substitutions ONLY (no token-level synonym replacement).
      Medium  — phrase substitutions + conservative synonym replacement
                (only when no phrase hit; safe map only).
      High    — phrase substitutions + moderate synonym replacement
                (even after phrase hits; safe map only).
    """
    # ── Select phrase library ─────────────────────────────────────────────
    mode_lower = mode.lower()
    if "concise" in mode_lower:
        phrase_lib = CONCISE_PHRASES
    elif "expanded" in mode_lower:
        phrase_lib = EXPANDED_PHRASES
    elif "formal" in mode_lower:
        phrase_lib = FORMAL_PHRASES
    elif "journal" in mode_lower:
        phrase_lib = JOURNAL_PHRASES
    elif "reviewer" in mode_lower:
        phrase_lib = REVIEWER_FRIENDLY_PHRASES
    else:
        phrase_lib = ACADEMIC_PHRASES

    # Low intensity: phrase rewrites only — no synonym substitution at all.
    if level == "Low":
        phrase_lib = None

    # ── Synonym configuration (phrase-first, safe-map only) ───────────────
    # synonym_sample_rate controls what fraction of eligible tokens are sampled.
    # synonym_after_phrase controls whether synonyms run even when a phrase
    # substitution already happened in the same sentence.
    if level == "Low":
        synonym_sample_rate  = 0.0
        synonym_after_phrase = False
    elif level == "Medium":
        synonym_sample_rate  = 0.20   # 1-in-5 eligible tokens
        synonym_after_phrase = False  # phrase wins; no extra churn
    elif level == "High":
        synonym_sample_rate  = 0.30   # 1-in-3 eligible tokens
        synonym_after_phrase = True   # apply synonyms even after phrase hits
    elif level == "Aggressive":
        synonym_sample_rate  = 0.35   # 35% eligible tokens
        synonym_after_phrase = True   # apply synonyms even after phrase hits
    else:
        synonym_sample_rate  = 0.20
        synonym_after_phrase = False

    # Concise mode: never add synonyms — focus purely on reduction
    if "concise" in mode_lower:
        synonym_sample_rate  = 0.0
        synonym_after_phrase = False

    # ── Active/Passive conversion ─────────────────────────────────────────
    # Only enabled for Journal, Reviewer-Friendly and Concise modes where sentence flow matters.
    active_passive = any(m in mode_lower for m in ("journal", "reviewer", "concise"))

    config = {
        "mode_name":             mode,
        "level":                 level,
        "phrase_library":        phrase_lib,
        "synonym_sample_rate":   synonym_sample_rate,
        "synonym_after_phrase":  synonym_after_phrase,
        "active_passive_convert": active_passive,
        "min_similarity":        0.75,
        "section":               section,
    }

    return RewriteEngine.rewrite(text, config)

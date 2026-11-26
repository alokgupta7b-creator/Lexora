import re

def count_syllables(word: str) -> int:
    """Helper to count syllables in a word using basic linguistic rules."""
    word = word.lower().strip()
    if not word:
        return 0
    # Simple phonetic vowel grouping
    word = re.sub(r'[^a-z]', '', word)
    if not word:
        return 0
    
    # Exceptions
    exceptions = {"me": 1, "she": 1, "he": 1, "you": 1, "the": 1, "we": 1, "be": 1}
    if word in exceptions:
        return exceptions[word]
        
    vowels = "aeiouy"
    count = 0
    
    # Suffix exceptions
    if word.endswith("es") or word.endswith("ed"):
        # check if it shouldn't be counted (e.g. bed vs parsed)
        if not (word.endswith("led") or word.endswith("bed") or word.endswith("red") or word.endswith("ted") or word.endswith("sed")):
            word = word[:-2]
    if word.endswith("e") and not word.endswith("le"):
        word = word[:-1]
        
    in_vowel_group = False
    for char in word:
        if char in vowels:
            if not in_vowel_group:
                count += 1
                in_vowel_group = True
        else:
            in_vowel_group = False
            
    if count == 0:
        count = 1
    return count

def analyze_readability(text: str) -> dict:
    """
    Computes readability metrics:
    - Flesch Reading Ease
    - Flesch-Kincaid Grade
    - Gunning Fog Index
    - SMOG Index
    - Average Sentence Length
    - Average Word Length
    - Total Words
    - Total Sentences
    - Total Paragraphs
    """
    # Clean and parse text
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    total_paragraphs = max(1, len(paragraphs))
    
    # Split sentences (crude sentence tokenizer using delimiters)
    sentence_delimiters = re.compile(r'[.!?]+')
    sentences = [s.strip() for s in sentence_delimiters.split(text) if s.strip()]
    total_sentences = max(1, len(sentences))
    
    # Split words
    words = []
    total_syllables = 0
    complex_words = 0
    
    word_pattern = re.compile(r'\b[a-zA-Z]+[-’\']?[a-zA-Z]*\b')
    for sentence in sentences:
        s_words = word_pattern.findall(sentence)
        for w in s_words:
            words.append(w)
            syllables = count_syllables(w)
            total_syllables += syllables
            if syllables >= 3:
                complex_words += 1
                
    total_words = max(1, len(words))
    
    # Ratios
    avg_sentence_length = total_words / total_sentences
    total_letters = sum(len(w) for w in words)
    avg_word_length = total_letters / total_words
    
    # Flesch Reading Ease
    # 206.835 - (1.015 * ASL) - (84.6 * ASW)
    flesch_reading_ease = 206.835 - (1.015 * avg_sentence_length) - (84.6 * (total_syllables / total_words))
    flesch_reading_ease = max(0.0, min(100.0, flesch_reading_ease))
    
    # Flesch-Kincaid Grade
    # 0.39 * ASL + 11.8 * ASW - 15.59
    flesch_kincaid_grade = (0.39 * avg_sentence_length) + (11.8 * (total_syllables / total_words)) - 15.59
    flesch_kincaid_grade = max(0.0, min(20.0, flesch_kincaid_grade))
    
    # Gunning Fog
    # 0.4 * (ASL + percentage of complex words)
    percent_complex = (complex_words / total_words) * 100
    gunning_fog = 0.4 * (avg_sentence_length + percent_complex)
    gunning_fog = max(0.0, min(20.0, gunning_fog))
    
    # SMOG Index
    # 1.0430 * sqrt(30 * complex / sentences) + 3.1291
    if total_sentences >= 3:
        smog_index = 1.0430 * ((30 * complex_words / total_sentences) ** 0.5) + 3.1291
    else:
        smog_index = 3.0
    smog_index = max(0.0, min(20.0, smog_index))
    
    return {
        "flesch_reading_ease": round(flesch_reading_ease, 2),
        "flesch_kincaid_grade": round(flesch_kincaid_grade, 2),
        "gunning_fog": round(gunning_fog, 2),
        "smog_index": round(smog_index, 2),
        "avg_sentence_length": round(avg_sentence_length, 2),
        "avg_word_length": round(avg_word_length, 2),
        "total_words": total_words,
        "total_sentences": total_sentences,
        "total_paragraphs": total_paragraphs
    }

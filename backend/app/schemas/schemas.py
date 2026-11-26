from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    mfa_required: Optional[bool] = None
    mfa_token: Optional[str] = None

class TokenData(BaseModel):
    email: Optional[str] = None

class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

# --- Document Schemas ---
class DocumentResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str] = None
    file_name: str
    file_type: str
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentDetailResponse(DocumentResponse):
    raw_text: str
    parsed_sections: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

# --- Analysis & Risk Schemas ---
class ReadabilitySchema(BaseModel):
    flesch_reading_ease: float
    flesch_kincaid_grade: float
    gunning_fog: float
    smog_index: float
    avg_sentence_length: float
    avg_word_length: float
    total_words: int
    total_sentences: int
    total_paragraphs: int

class SentenceRisk(BaseModel):
    sentence: str
    start_char: int
    end_char: int
    score: float
    category: str  # 'Very Low', 'Low', 'Moderate', 'High', 'Very High'
    reasons: List[str]
    improvement_suggestions: List[str]
    stats: Dict[str, Any]
    section: Optional[str] = None

class SectionRisk(BaseModel):
    section_name: str
    score: float
    category: str

class AnalysisResponse(BaseModel):
    id: int
    document_id: int
    overall_score: float
    section_scores: Dict[str, float]
    readability_scores: ReadabilitySchema
    risk_details: Dict[str, Any]
    academic_quality_score: float
    publication_readiness_score: float
    created_at: datetime

    class Config:
        from_attributes = True

# --- Rephraser Schemas ---
class RephraseRequest(BaseModel):
    text: str
    mode: str = "Academic"  # Standard, Academic, Journal, Formal, Concise, Expanded, Simplified, Technical
    level: str = "Medium"  # Low, Medium, High, Aggressive
    section: Optional[str] = None # abstract, intro, methodology, etc.

class RephraseResponse(BaseModel):
    original_text: str
    rewritten_text: str
    similarity_percentage: float
    mode: str
    level: str
    preservations: Dict[str, List[str]] # saved formulas, citations, technical words
    word_count_original: Optional[int] = None
    word_count_rewritten: Optional[int] = None
    word_count_consistent: Optional[bool] = None
    # Intensity debug telemetry
    transformations_applied: Optional[int] = None
    sentences_modified: Optional[int] = None
    sentences_total: Optional[int] = None
    modification_percentage: Optional[float] = None
    # Quality metrics metadata
    sentences_rewritten_count: Optional[int] = None
    protected_entities_preserved_count: Optional[int] = None
    phrase_substitutions_applied: Optional[int] = None
    synonym_substitutions_applied: Optional[int] = None
    structural_rewrites_applied: Optional[int] = None
    semantic_similarity_score: Optional[float] = None
    lexical_diversity_delta: Optional[float] = None
    processing_time_ms: Optional[int] = None

# --- Humanizer Schemas ---
class HumanizeRequest(BaseModel):
    text: str
    mode: str = "Academic Humanizer"  # Academic Humanizer, Natural Humanizer, Reviewer-Friendly Humanizer, Journal-Ready Humanizer
    level: str = "Medium"  # Low, Medium, High

class HumanizeResponse(BaseModel):
    original_text: str
    rewritten_text: str
    similarity_percentage: float
    mode: str
    level: str
    overall_risk_before: float
    overall_risk_after: float
    word_count_original: Optional[int] = None
    word_count_rewritten: Optional[int] = None
    word_count_consistent: Optional[bool] = None
    # Intensity debug telemetry
    transformations_applied: Optional[int] = None
    sentences_modified: Optional[int] = None
    sentences_total: Optional[int] = None
    modification_percentage: Optional[float] = None

# --- Report Schemas ---
class ReportResponse(BaseModel):
    id: int
    document_id: int
    report_path: str
    report_type: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Dashboard Schemas ---
class DashboardMetrics(BaseModel):
    total_documents: int
    average_risk_score: float
    average_readability_score: float
    recent_uploads: List[DocumentResponse]
    risk_trends: List[Dict[str, Any]]
    quality_trends: List[Dict[str, Any]]

# --- Admin Schemas ---
class AdminUserUpdate(BaseModel):
    role: str
    is_active: bool


# --- Enterprise Auth Schemas ---
class MfaConfirmRequest(BaseModel):
    code: str


class MfaVerifyRequest(BaseModel):
    mfa_token: str
    code: str


class MfaDisableRequest(BaseModel):
    password: str


class EmailChangeRequest(BaseModel):
    password: str
    new_email: EmailStr


class EmailChangeConfirmRequest(BaseModel):
    token: str


class ChangePasswordAuthenticatedRequest(BaseModel):
    current_password: str
    new_password: str


class DeleteAccountRequest(BaseModel):
    password: str


class SessionResponse(BaseModel):
    id: int
    browser: Optional[str] = None
    os: Optional[str] = None
    device_type: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    is_current: bool

    class Config:
        from_attributes = True


class SessionOtherRevokeRequest(BaseModel):
    password: str


# --- Plagiarism Schemas ---
class SuspiciousPassage(BaseModel):
    sentence: str
    similarity_score: float
    matched_sentence: str
    explainable_reason: str
    recommending_rephrase: bool

class SuspiciousParagraph(BaseModel):
    paragraph: str
    matched_paragraph: str
    similarity_score: float
    explainable_reason: str
    recommending_rephrase: bool

class SideBySideComparison(BaseModel):
    source_text: str
    compared_text: str
    similarity_score: float
    match_type: str
    explanation: str

class PlagiarismMetrics(BaseModel):
    jaccard_similarity: float
    cosine_similarity: float
    ngram_3_overlap: float
    ngram_4_overlap: float
    minhash_similarity: float
    semantic_similarity: float

class PlagiarismCheckResponse(BaseModel):
    overall_similarity_percentage: float
    metrics: PlagiarismMetrics
    suspicious_passages: List[SuspiciousPassage]
    suspicious_paragraphs: Optional[List[SuspiciousParagraph]] = None
    side_by_side_comparisons: Optional[List[SideBySideComparison]] = None

class PlagiarismComparisonDetail(BaseModel):
    compared_document_id: int
    compared_document_title: str
    plagiarism_report: PlagiarismCheckResponse

class PlagiarismReportResponse(BaseModel):
    document_id: int
    document_title: str
    comparisons: List[PlagiarismComparisonDetail]


import pytest
import re
from unittest.mock import patch, MagicMock

from app.config import settings
from app.services.llm_client import query_llm, LLMClientError, get_cache_key
from app.services.rewrite_engine import (
    protect_entities_wrapped,
    restore_entities_wrapped,
    validate_rewritten_tags,
    RewriteEngine,
)


def test_protect_entities_wrapped():
    text = (
        "We evaluated BERT on ChestX-ray14 dataset. "
        "The model achieves 95.5% accuracy (p < 0.05) as shown in Figure 1 and [15]. "
        "Contact research@univ.edu or visit https://example.com/project."
    )
    
    masked, tag_map = protect_entities_wrapped(text)
    
    # Verify markers exist
    assert "BERT" in masked
    assert "⟦PROTECTED_" in masked
    assert "⟦/PROTECTED_" in masked
    assert "95.5%" in masked
    assert "Figure 1" in masked
    assert "[15]" in masked
    assert "https://example.com/project" in masked
    
    # Restore and verify it matches the original text exactly
    restored = restore_entities_wrapped(masked, tag_map)
    assert restored == text


def test_validate_rewritten_tags():
    orig_masked = "We evaluated ⟦PROTECTED_A7F19C82⟧BERT⟦/PROTECTED_A7F19C82⟧ in ⟦PROTECTED_5D21E9F4⟧Figure 1⟦/PROTECTED_5D21E9F4⟧."
    tag_map = {
        "⟦PROTECTED_A7F19C82⟧": ("BERT", "TERM", "⟦/PROTECTED_A7F19C82⟧"),
        "⟦PROTECTED_5D21E9F4⟧": ("Figure 1", "REF", "⟦/PROTECTED_5D21E9F4⟧"),
    }
    
    # Valid rewrite
    valid_rew = "In ⟦PROTECTED_5D21E9F4⟧Figure 1⟦/PROTECTED_5D21E9F4⟧, we evaluated ⟦PROTECTED_A7F19C82⟧BERT⟦/PROTECTED_A7F19C82⟧."
    assert validate_rewritten_tags(orig_masked, valid_rew, tag_map) is True
    
    # Missing tag key
    invalid_rew_1 = "In Figure 1, we evaluated ⟦PROTECTED_A7F19C82⟧BERT⟦/PROTECTED_A7F19C82⟧."
    assert validate_rewritten_tags(orig_masked, invalid_rew_1, tag_map) is False
    
    # Duplicated tag key
    invalid_rew_2 = "In ⟦PROTECTED_5D21E9F4⟧Figure 1⟦/PROTECTED_5D21E9F4⟧ and ⟦PROTECTED_5D21E9F4⟧Figure 1⟦/PROTECTED_5D21E9F4⟧, we evaluated ⟦PROTECTED_A7F19C82⟧BERT⟦/PROTECTED_A7F19C82⟧."
    assert validate_rewritten_tags(orig_masked, invalid_rew_2, tag_map) is False


@patch("requests.post")
def test_llm_client_openai_mock(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {"message": {"content": "This is rewritten text."}}
        ]
    }
    mock_post.return_value = mock_resp
    
    # Mock settings
    with patch.object(settings, "OPENAI_API_KEY", "test-key"), \
         patch.object(settings, "LLM_PROVIDER", "openai"):
        res = query_llm("Original text", "Sys prompt", "User prompt")
        assert res == "This is rewritten text."
        
        # Verify request parameters
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.openai.com/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer test-key"
        assert kwargs["json"]["messages"][0]["content"] == "Sys prompt"


@patch("requests.post")
def test_llm_client_gemini_mock(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": "Gemini output text"}]}}
        ]
    }
    mock_post.return_value = mock_resp
    
    with patch.object(settings, "GEMINI_API_KEY", "gemini-key"), \
         patch.object(settings, "LLM_PROVIDER", "gemini"):
        res = query_llm("Original text", "Sys prompt", "User prompt")
        assert res == "Gemini output text"
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "v1beta/models" in args[0]
        assert "key=gemini-key" in args[0]
        assert kwargs["json"]["systemInstruction"]["parts"][0]["text"] == "Sys prompt"


@patch("requests.post")
def test_llm_client_claude_mock(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "content": [
            {"text": "Claude output text"}
        ]
    }
    mock_post.return_value = mock_resp
    
    with patch.object(settings, "ANTHROPIC_API_KEY", "claude-key"), \
         patch.object(settings, "LLM_PROVIDER", "anthropic"):
        res = query_llm("Original text", "Sys prompt", "User prompt")
        assert res == "Claude output text"
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "api.anthropic.com/v1/messages" in args[0]
        assert kwargs["headers"]["x-api-key"] == "claude-key"
        assert kwargs["json"]["system"] == "Sys prompt"


@patch("app.services.rewrite_engine.query_llm")
def test_rewrite_engine_llm_path(mock_query):
    def mock_query_fn(*args, **kwargs):
        user_prompt = kwargs.get("user_prompt") or args[2]
        tags = re.findall(r'⟦PROTECTED_[0-9A-F]{8}⟧', user_prompt)
        close_tag0 = tags[0].replace("PROTECTED", "/PROTECTED")
        close_tag1 = tags[1].replace("PROTECTED", "/PROTECTED")
        return f"Here is the model named {tags[0]}BERT{close_tag0} which is discussed in {tags[1]}[15]{close_tag1}."
        
    mock_query.side_effect = mock_query_fn
    
    config = {
        "mode_name": "Academic",
        "level": "Medium",
        "use_llm": True,
    }
    
    text = "This is a model named BERT discussed in [15]."
    
    # Run engine rewrite
    res = RewriteEngine.rewrite(text, config)
    
    assert res["rewritten_text"] == "Here is the model named BERT which is discussed in [15]."
    assert res["protected_entities_preserved_count"] == 2
    assert res["transformations_applied"] > 0
    assert res["sentences_modified"] == 1


@patch("app.services.rewrite_engine.query_llm")
def test_rewrite_engine_fallback(mock_query):
    # Setup LLM query to fail with an exception
    mock_query.side_effect = LLMClientError("Connection refused")
    
    config = {
        "mode_name": "Academic",
        "level": "Medium",
        "use_llm": True,
        "synonym_sample_rate": 0.20,
    }
    
    text = "We evaluated LIWC and the NRC Emotion Lexicon but the model lacks some specific structures."
    
    # The rewrite engine should intercept the error and fall back to local rule-based engine
    res = RewriteEngine.rewrite(text, config)
    
    # Local fallback should run and complete successfully without raising exception
    assert res["original_text"] == text
    assert "rewritten_text" in res
    assert res["similarity_percentage"] >= 50.0

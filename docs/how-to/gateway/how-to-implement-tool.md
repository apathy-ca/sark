# How to Implement an MCP Tool

This guide shows you how to implement, test, and deploy a production-ready MCP tool that works seamlessly with the SARK Gateway.

## Before You Begin

**Prerequisites:**
- MCP server framework installed (Python, TypeScript, or Go)
- Basic understanding of JSON Schema
- Familiarity with your chosen programming language
- SARK Gateway accessible for testing
- Development environment with testing tools

**What You'll Learn:**
- Design robust tool schemas
- Implement tools with proper validation
- Handle errors gracefully
- Test tools before deployment
- Version tools properly
- Deploy tools to production

## Tool Implementation Checklist

Before writing code, plan your tool:

- [ ] Define clear tool purpose and scope
- [ ] Design input schema with validation rules
- [ ] Design output schema
- [ ] List potential error conditions
- [ ] Plan authentication requirements
- [ ] Identify rate limiting needs
- [ ] Document expected behavior
- [ ] Create test cases

## Step 1: Design Your Tool Schema

### Define Tool Metadata

Create a tool specification document:

```yaml
# tool-spec.yaml
tool:
  name: analyze_sentiment
  version: 1.0.0
  description: |
    Analyzes the sentiment of provided text and returns a sentiment score
    between -1.0 (negative) and 1.0 (positive), along with confidence level
    and detected emotions.

  category: text-analysis
  tags:
    - nlp
    - sentiment
    - text

  input:
    type: object
    required:
      - text
    properties:
      text:
        type: string
        description: Text to analyze (max 10,000 characters)
        minLength: 1
        maxLength: 10000

      language:
        type: string
        description: Language code (ISO 639-1)
        default: en
        enum: [en, es, fr, de, it, pt, ja, zh]

      options:
        type: object
        properties:
          detect_emotions:
            type: boolean
            description: Include detailed emotion detection
            default: false

          include_phrases:
            type: boolean
            description: Return key phrases influencing sentiment
            default: false

  output:
    type: object
    required:
      - sentiment_score
      - confidence
    properties:
      sentiment_score:
        type: number
        description: Sentiment score from -1.0 to 1.0
        minimum: -1.0
        maximum: 1.0

      confidence:
        type: number
        description: Confidence level from 0.0 to 1.0
        minimum: 0.0
        maximum: 1.0

      label:
        type: string
        enum: [very_negative, negative, neutral, positive, very_positive]

      emotions:
        type: object
        description: Detected emotions (if requested)
        properties:
          joy: {type: number, minimum: 0, maximum: 1}
          sadness: {type: number, minimum: 0, maximum: 1}
          anger: {type: number, minimum: 0, maximum: 1}
          fear: {type: number, minimum: 0, maximum: 1}

      key_phrases:
        type: array
        description: Phrases influencing sentiment (if requested)
        items:
          type: object
          properties:
            phrase: {type: string}
            impact: {type: number}
            sentiment: {type: string}

  errors:
    - code: invalid_language
      message: Unsupported language code
      http_status: 400

    - code: text_too_long
      message: Text exceeds maximum length
      http_status: 400

    - code: analysis_failed
      message: Sentiment analysis engine error
      http_status: 500

    - code: rate_limit_exceeded
      message: Too many requests
      http_status: 429
```

**Expected Result:** A complete specification that serves as your implementation contract.

### Convert to JSON Schema

```bash
# Convert YAML spec to JSON Schema
yq eval -o=json tool-spec.yaml > tool-schema.json
```

**Expected Output:** `tool-schema.json` with proper JSON Schema format.

## Step 2: Implement the Tool (Python)

### Create Tool Implementation

Create `sentiment_analyzer.py`:

```python
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
from jsonschema import validate, ValidationError
import logging

logger = logging.getLogger(__name__)

@dataclass
class SentimentResult:
    """Result from sentiment analysis."""
    sentiment_score: float
    confidence: float
    label: str
    emotions: Optional[Dict[str, float]] = None
    key_phrases: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "sentiment_score": self.sentiment_score,
            "confidence": self.confidence,
            "label": self.label
        }
        if self.emotions:
            result["emotions"] = self.emotions
        if self.key_phrases:
            result["key_phrases"] = self.key_phrases
        return result


class SentimentAnalyzer:
    """MCP tool for sentiment analysis."""

    # Tool metadata
    NAME = "analyze_sentiment"
    VERSION = "1.0.0"

    # Input schema
    INPUT_SCHEMA = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {
                "type": "string",
                "minLength": 1,
                "maxLength": 10000,
                "description": "Text to analyze"
            },
            "language": {
                "type": "string",
                "default": "en",
                "enum": ["en", "es", "fr", "de", "it", "pt", "ja", "zh"],
                "description": "Language code (ISO 639-1)"
            },
            "options": {
                "type": "object",
                "properties": {
                    "detect_emotions": {
                        "type": "boolean",
                        "default": False
                    },
                    "include_phrases": {
                        "type": "boolean",
                        "default": False
                    }
                }
            }
        }
    }

    # Supported languages
    SUPPORTED_LANGUAGES = {"en", "es", "fr", "de", "it", "pt", "ja", "zh"}

    def __init__(self, model_path: Optional[str] = None):
        """Initialize the sentiment analyzer.

        Args:
            model_path: Path to sentiment analysis model
        """
        self.model = self._load_model(model_path)
        logger.info(f"SentimentAnalyzer initialized with model: {model_path}")

    def _load_model(self, model_path: Optional[str]):
        """Load sentiment analysis model."""
        # In production, load actual ML model
        # For this example, we'll simulate
        return {"type": "simulated", "path": model_path}

    def validate_input(self, arguments: Dict[str, Any]) -> None:
        """Validate input arguments against schema.

        Args:
            arguments: Tool input arguments

        Raises:
            ValidationError: If validation fails
        """
        try:
            validate(instance=arguments, schema=self.INPUT_SCHEMA)
        except ValidationError as e:
            logger.error(f"Input validation failed: {e.message}")
            raise

        # Additional custom validation
        text = arguments.get("text", "")
        if len(text) > 10000:
            raise ValueError("Text exceeds maximum length of 10,000 characters")

        language = arguments.get("language", "en")
        if language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")

    def analyze(
        self,
        text: str,
        language: str = "en",
        detect_emotions: bool = False,
        include_phrases: bool = False
    ) -> SentimentResult:
        """Perform sentiment analysis.

        Args:
            text: Text to analyze
            language: Language code
            detect_emotions: Whether to detect emotions
            include_phrases: Whether to extract key phrases

        Returns:
            SentimentResult with analysis
        """
        # In production, use actual ML model
        # This is a simplified simulation

        # Calculate sentiment score (-1.0 to 1.0)
        sentiment_score = self._calculate_sentiment(text, language)

        # Calculate confidence (0.0 to 1.0)
        confidence = self._calculate_confidence(text)

        # Determine label
        label = self._get_sentiment_label(sentiment_score)

        # Optional: detect emotions
        emotions = None
        if detect_emotions:
            emotions = self._detect_emotions(text, language)

        # Optional: extract key phrases
        key_phrases = None
        if include_phrases:
            key_phrases = self._extract_key_phrases(text, sentiment_score)

        return SentimentResult(
            sentiment_score=sentiment_score,
            confidence=confidence,
            label=label,
            emotions=emotions,
            key_phrases=key_phrases
        )

    def _calculate_sentiment(self, text: str, language: str) -> float:
        """Calculate sentiment score."""
        # Simplified example - replace with actual model
        positive_words = {"good", "great", "excellent", "amazing", "wonderful"}
        negative_words = {"bad", "terrible", "awful", "horrible", "poor"}

        words = text.lower().split()
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)

        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            return 0.0

        score = (positive_count - negative_count) / total_sentiment_words
        return max(-1.0, min(1.0, score))

    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence in the analysis."""
        # Simplified - longer text = higher confidence
        word_count = len(text.split())
        confidence = min(0.5 + (word_count / 100) * 0.5, 1.0)
        return round(confidence, 2)

    def _get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to label."""
        if score <= -0.6:
            return "very_negative"
        elif score <= -0.2:
            return "negative"
        elif score <= 0.2:
            return "neutral"
        elif score <= 0.6:
            return "positive"
        else:
            return "very_positive"

    def _detect_emotions(
        self,
        text: str,
        language: str
    ) -> Dict[str, float]:
        """Detect emotions in text."""
        # Simplified example
        text_lower = text.lower()

        emotions = {
            "joy": 0.0,
            "sadness": 0.0,
            "anger": 0.0,
            "fear": 0.0
        }

        # Simple keyword matching (replace with ML model)
        if any(word in text_lower for word in ["happy", "joy", "excited"]):
            emotions["joy"] = 0.75
        if any(word in text_lower for word in ["sad", "depressed", "unhappy"]):
            emotions["sadness"] = 0.70
        if any(word in text_lower for word in ["angry", "furious", "mad"]):
            emotions["anger"] = 0.65
        if any(word in text_lower for word in ["afraid", "scared", "worried"]):
            emotions["fear"] = 0.60

        return emotions

    def _extract_key_phrases(
        self,
        text: str,
        sentiment_score: float
    ) -> List[Dict[str, Any]]:
        """Extract key phrases influencing sentiment."""
        # Simplified example
        phrases = []

        sentences = text.split(".")
        for sentence in sentences[:3]:  # First 3 sentences
            if sentence.strip():
                phrases.append({
                    "phrase": sentence.strip(),
                    "impact": 0.3,
                    "sentiment": "positive" if sentiment_score > 0 else "negative"
                })

        return phrases

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments.

        This is the main entry point called by the MCP server.

        Args:
            arguments: Tool input arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: For invalid inputs
            RuntimeError: For execution errors
        """
        # Step 1: Validate input
        try:
            self.validate_input(arguments)
        except ValidationError as e:
            raise ValueError(f"Invalid input: {e.message}")

        # Step 2: Extract arguments with defaults
        text = arguments["text"]
        language = arguments.get("language", "en")
        options = arguments.get("options", {})
        detect_emotions = options.get("detect_emotions", False)
        include_phrases = options.get("include_phrases", False)

        # Step 3: Perform analysis
        try:
            result = self.analyze(
                text=text,
                language=language,
                detect_emotions=detect_emotions,
                include_phrases=include_phrases
            )
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}", exc_info=True)
            raise RuntimeError(f"Sentiment analysis failed: {str(e)}")

        # Step 4: Return result
        return result.to_dict()

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema for MCP discovery."""
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "description": "Analyzes sentiment of text and returns scores",
            "inputSchema": self.INPUT_SCHEMA
        }


# Example usage
if __name__ == "__main__":
    analyzer = SentimentAnalyzer()

    # Test with sample input
    result = analyzer.execute({
        "text": "This product is absolutely amazing! I love it.",
        "language": "en",
        "options": {
            "detect_emotions": True,
            "include_phrases": True
        }
    })

    print(json.dumps(result, indent=2))
```

**Expected Output:**
```json
{
  "sentiment_score": 1.0,
  "confidence": 0.55,
  "label": "very_positive",
  "emotions": {
    "joy": 0.0,
    "sadness": 0.0,
    "anger": 0.0,
    "fear": 0.0
  },
  "key_phrases": [
    {
      "phrase": "This product is absolutely amazing! I love it",
      "impact": 0.3,
      "sentiment": "positive"
    }
  ]
}
```

## Step 3: Add Parameter Validation Patterns

### Create Validation Utilities

Create `validation.py`:

```python
from typing import Any, Dict, List, Optional
from functools import wraps
import re

class ValidationError(Exception):
    """Custom validation error."""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


def validate_string_length(
    value: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    field_name: str = "field"
) -> None:
    """Validate string length."""
    if min_length and len(value) < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} characters",
            field=field_name
        )
    if max_length and len(value) > max_length:
        raise ValidationError(
            f"{field_name} must be at most {max_length} characters",
            field=field_name
        )


def validate_enum(
    value: Any,
    allowed_values: List[Any],
    field_name: str = "field"
) -> None:
    """Validate value is in allowed set."""
    if value not in allowed_values:
        raise ValidationError(
            f"{field_name} must be one of: {', '.join(map(str, allowed_values))}",
            field=field_name
        )


def validate_number_range(
    value: float,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
    field_name: str = "field"
) -> None:
    """Validate number is within range."""
    if minimum is not None and value < minimum:
        raise ValidationError(
            f"{field_name} must be at least {minimum}",
            field=field_name
        )
    if maximum is not None and value > maximum:
        raise ValidationError(
            f"{field_name} must be at most {maximum}",
            field=field_name
        )


def validate_pattern(
    value: str,
    pattern: str,
    field_name: str = "field",
    example: Optional[str] = None
) -> None:
    """Validate string matches regex pattern."""
    if not re.match(pattern, value):
        msg = f"{field_name} does not match required pattern"
        if example:
            msg += f". Example: {example}"
        raise ValidationError(msg, field=field_name)


def validate_required_fields(
    data: Dict[str, Any],
    required_fields: List[str]
) -> None:
    """Validate all required fields are present."""
    missing = [field for field in required_fields if field not in data]
    if missing:
        raise ValidationError(
            f"Missing required fields: {', '.join(missing)}"
        )


def sanitize_input(func):
    """Decorator to sanitize string inputs."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Sanitize string arguments
        sanitized_args = []
        for arg in args:
            if isinstance(arg, str):
                # Strip whitespace, remove null bytes
                arg = arg.strip().replace('\x00', '')
            sanitized_args.append(arg)

        sanitized_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                value = value.strip().replace('\x00', '')
            sanitized_kwargs[key] = value

        return func(*sanitized_args, **sanitized_kwargs)

    return wrapper
```

### Apply Validation to Tool

Update `sentiment_analyzer.py`:

```python
from validation import (
    validate_string_length,
    validate_enum,
    validate_required_fields,
    sanitize_input,
    ValidationError
)

class SentimentAnalyzer:
    # ... (previous code)

    @sanitize_input
    def validate_input(self, arguments: Dict[str, Any]) -> None:
        """Validate input with custom validators."""
        # Check required fields
        validate_required_fields(arguments, ["text"])

        # Validate text
        text = arguments["text"]
        validate_string_length(
            text,
            min_length=1,
            max_length=10000,
            field_name="text"
        )

        # Validate language if provided
        if "language" in arguments:
            validate_enum(
                arguments["language"],
                list(self.SUPPORTED_LANGUAGES),
                field_name="language"
            )
```

## Step 4: Implement Error Handling

### Create Error Classes

Create `errors.py`:

```python
from typing import Optional, Dict, Any
from enum import Enum

class ErrorCode(Enum):
    """Standard error codes."""
    INVALID_INPUT = "invalid_input"
    INVALID_LANGUAGE = "invalid_language"
    TEXT_TOO_LONG = "text_too_long"
    ANALYSIS_FAILED = "analysis_failed"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INTERNAL_ERROR = "internal_error"
    UNAUTHORIZED = "unauthorized"


class ToolError(Exception):
    """Base class for tool errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode,
        http_status: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.http_status = http_status
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON response."""
        error_dict = {
            "error": self.code.value,
            "message": self.message,
            "http_status": self.http_status
        }
        if self.details:
            error_dict["details"] = self.details
        return error_dict


class InvalidInputError(ToolError):
    """Invalid input provided."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_INPUT,
            http_status=400,
            details=details
        )


class RateLimitError(ToolError):
    """Rate limit exceeded."""
    def __init__(self, retry_after: int):
        super().__init__(
            message="Rate limit exceeded",
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            http_status=429,
            details={"retry_after_seconds": retry_after}
        )


class AnalysisError(ToolError):
    """Analysis failed."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.ANALYSIS_FAILED,
            http_status=500,
            details=details
        )
```

### Add Error Handling to Tool

```python
from errors import InvalidInputError, AnalysisError, ToolError
import traceback

class SentimentAnalyzer:
    # ... (previous code)

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute with comprehensive error handling."""
        try:
            # Validate input
            self.validate_input(arguments)

            # Extract arguments
            text = arguments["text"]
            language = arguments.get("language", "en")
            options = arguments.get("options", {})

            # Perform analysis
            result = self.analyze(
                text=text,
                language=language,
                detect_emotions=options.get("detect_emotions", False),
                include_phrases=options.get("include_phrases", False)
            )

            return result.to_dict()

        except ValidationError as e:
            # Input validation failed
            raise InvalidInputError(
                message=e.message,
                details={"field": e.field}
            )

        except ValueError as e:
            # Invalid value provided
            raise InvalidInputError(message=str(e))

        except Exception as e:
            # Unexpected error
            logger.error(
                f"Unexpected error in sentiment analysis: {str(e)}",
                exc_info=True
            )
            raise AnalysisError(
                message="Sentiment analysis failed",
                details={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc()
                }
            )
```

## Step 5: Test Tool Locally

### Create Unit Tests

Create `test_sentiment_analyzer.py`:

```python
import pytest
from sentiment_analyzer import SentimentAnalyzer
from errors import InvalidInputError, AnalysisError
from validation import ValidationError

@pytest.fixture
def analyzer():
    """Create analyzer instance for testing."""
    return SentimentAnalyzer()


class TestInputValidation:
    """Test input validation."""

    def test_valid_input(self, analyzer):
        """Test with valid input."""
        arguments = {
            "text": "This is a test",
            "language": "en"
        }
        analyzer.validate_input(arguments)  # Should not raise

    def test_missing_text(self, analyzer):
        """Test missing required field."""
        with pytest.raises(ValidationError):
            analyzer.validate_input({})

    def test_text_too_long(self, analyzer):
        """Test text exceeding max length."""
        arguments = {
            "text": "a" * 10001  # Over 10,000 chars
        }
        with pytest.raises(ValueError, match="exceeds maximum length"):
            analyzer.validate_input(arguments)

    def test_invalid_language(self, analyzer):
        """Test unsupported language."""
        arguments = {
            "text": "Hello",
            "language": "xx"  # Invalid
        }
        with pytest.raises(ValueError, match="Unsupported language"):
            analyzer.validate_input(arguments)


class TestSentimentAnalysis:
    """Test sentiment analysis functionality."""

    def test_positive_sentiment(self, analyzer):
        """Test positive text analysis."""
        result = analyzer.execute({
            "text": "This is great and wonderful!",
            "language": "en"
        })

        assert result["sentiment_score"] > 0
        assert result["label"] in ["positive", "very_positive"]
        assert 0 <= result["confidence"] <= 1

    def test_negative_sentiment(self, analyzer):
        """Test negative text analysis."""
        result = analyzer.execute({
            "text": "This is terrible and awful!",
            "language": "en"
        })

        assert result["sentiment_score"] < 0
        assert result["label"] in ["negative", "very_negative"]

    def test_neutral_sentiment(self, analyzer):
        """Test neutral text."""
        result = analyzer.execute({
            "text": "The sky is blue.",
            "language": "en"
        })

        assert -0.3 < result["sentiment_score"] < 0.3
        assert result["label"] == "neutral"

    def test_emotion_detection(self, analyzer):
        """Test emotion detection option."""
        result = analyzer.execute({
            "text": "I am so happy and joyful!",
            "language": "en",
            "options": {"detect_emotions": True}
        })

        assert "emotions" in result
        assert "joy" in result["emotions"]

    def test_phrase_extraction(self, analyzer):
        """Test key phrase extraction."""
        result = analyzer.execute({
            "text": "Great product. Amazing quality. Would buy again.",
            "language": "en",
            "options": {"include_phrases": True}
        })

        assert "key_phrases" in result
        assert len(result["key_phrases"]) > 0


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_input_error(self, analyzer):
        """Test invalid input raises proper error."""
        with pytest.raises(InvalidInputError):
            analyzer.execute({"text": ""})  # Empty text

    def test_error_structure(self, analyzer):
        """Test error has proper structure."""
        try:
            analyzer.execute({})
        except InvalidInputError as e:
            error_dict = e.to_dict()
            assert "error" in error_dict
            assert "message" in error_dict
            assert "http_status" in error_dict
            assert error_dict["http_status"] == 400


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Run Tests:**

```bash
pytest test_sentiment_analyzer.py -v
```

**Expected Output:**
```
test_sentiment_analyzer.py::TestInputValidation::test_valid_input PASSED
test_sentiment_analyzer.py::TestInputValidation::test_missing_text PASSED
test_sentiment_analyzer.py::TestInputValidation::test_text_too_long PASSED
test_sentiment_analyzer.py::TestInputValidation::test_invalid_language PASSED
test_sentiment_analyzer.py::TestSentimentAnalysis::test_positive_sentiment PASSED
test_sentiment_analyzer.py::TestSentimentAnalysis::test_negative_sentiment PASSED
test_sentiment_analyzer.py::TestSentimentAnalysis::test_neutral_sentiment PASSED
test_sentiment_analyzer.py::TestSentimentAnalysis::test_emotion_detection PASSED
test_sentiment_analyzer.py::TestSentimentAnalysis::test_phrase_extraction PASSED
test_sentiment_analyzer.py::TestErrorHandling::test_invalid_input_error PASSED
test_sentiment_analyzer.py::TestErrorHandling::test_error_structure PASSED

========================== 11 passed in 0.43s ===========================
```

### Create Integration Tests

Create `test_integration.py`:

```python
import requests
import pytest

# Assuming MCP server running on localhost:8000

BASE_URL = "http://localhost:8000"

def test_tool_discovery():
    """Test tool appears in discovery."""
    response = requests.get(f"{BASE_URL}/mcp/tools")
    assert response.status_code == 200

    tools = response.json()["tools"]
    tool_names = [t["name"] for t in tools]
    assert "analyze_sentiment" in tool_names


def test_tool_invocation():
    """Test tool can be invoked."""
    payload = {
        "tool": "analyze_sentiment",
        "arguments": {
            "text": "This is amazing!",
            "language": "en"
        }
    }

    response = requests.post(f"{BASE_URL}/mcp/tools/invoke", json=payload)
    assert response.status_code == 200

    result = response.json()
    assert "sentiment_score" in result
    assert "confidence" in result
    assert "label" in result


def test_error_response():
    """Test error handling in API."""
    payload = {
        "tool": "analyze_sentiment",
        "arguments": {
            "text": "",  # Invalid: empty
            "language": "en"
        }
    }

    response = requests.post(f"{BASE_URL}/mcp/tools/invoke", json=payload)
    assert response.status_code == 400

    error = response.json()
    assert "error" in error
    assert error["error"] == "invalid_input"
```

**Run Integration Tests:**

```bash
# Start MCP server first
python mcp_server.py &

# Run tests
pytest test_integration.py -v

# Stop server
kill %1
```

## Step 6: Version Your Tools

### Implement Versioning Strategy

Create `tool_versions.py`:

```python
from typing import Dict, Any
from abc import ABC, abstractmethod

class ToolVersion(ABC):
    """Base class for versioned tools."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Tool version."""
        pass

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool."""
        pass


class SentimentAnalyzerV1(ToolVersion):
    """Version 1.0.0 of sentiment analyzer."""

    @property
    def version(self) -> str:
        return "1.0.0"

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute v1 implementation."""
        # Original implementation
        pass


class SentimentAnalyzerV2(ToolVersion):
    """Version 2.0.0 with enhanced features."""

    @property
    def version(self) -> str:
        return "2.0.0"

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute v2 implementation with new features."""
        # Enhanced implementation with backward compatibility
        pass


class ToolRegistry:
    """Registry for managing tool versions."""

    def __init__(self):
        self._tools: Dict[str, Dict[str, ToolVersion]] = {}

    def register(self, name: str, tool: ToolVersion):
        """Register a tool version."""
        if name not in self._tools:
            self._tools[name] = {}
        self._tools[name][tool.version] = tool

    def get(self, name: str, version: str = "latest") -> ToolVersion:
        """Get specific tool version."""
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found")

        versions = self._tools[name]

        if version == "latest":
            # Get latest version
            latest_ver = max(versions.keys())
            return versions[latest_ver]

        if version not in versions:
            raise ValueError(f"Version '{version}' not found for tool '{name}'")

        return versions[version]


# Usage
registry = ToolRegistry()
registry.register("analyze_sentiment", SentimentAnalyzerV1())
registry.register("analyze_sentiment", SentimentAnalyzerV2())

# Get specific version
tool_v1 = registry.get("analyze_sentiment", "1.0.0")
tool_latest = registry.get("analyze_sentiment", "latest")
```

### Version Migration Guide

Create migration documentation:

```markdown
# Version Migration Guide

## Upgrading from v1.0.0 to v2.0.0

### Breaking Changes
- None (backward compatible)

### New Features
1. Enhanced emotion detection with 8 emotions (was 4)
2. Phrase extraction includes position information
3. Support for 5 additional languages

### Migration Steps

#### Step 1: Update Client Code
No changes required - v2 accepts all v1 inputs.

#### Step 2: Leverage New Features (Optional)
```python
# v1 usage (still works)
result = analyzer.execute({
    "text": "Sample text",
    "options": {"detect_emotions": True}
})

# v2 enhanced usage
result = analyzer.execute({
    "text": "Sample text",
    "options": {
        "detect_emotions": True,
        "emotion_granularity": "detailed"  # New in v2
    }
})
```

#### Step 3: Update Tests
Add tests for new features while keeping v1 tests.
```

## Step 7: Deploy Tool to Production

### Create Deployment Checklist

```markdown
# Tool Deployment Checklist

## Pre-Deployment
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Load tests completed
- [ ] Security review completed
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version bumped appropriately

## Deployment Steps
- [ ] Deploy to staging environment
- [ ] Run smoke tests in staging
- [ ] Update gateway configuration
- [ ] Deploy to production
- [ ] Verify health checks
- [ ] Monitor error rates
- [ ] Check performance metrics

## Post-Deployment
- [ ] Announce to users
- [ ] Monitor for 24 hours
- [ ] Review logs for errors
- [ ] Update runbook if needed
```

### Deploy to MCP Server

```bash
# Step 1: Build distribution package
python setup.py sdist bdist_wheel

# Step 2: Upload to package repository
twine upload dist/*

# Step 3: Update server dependencies
pip install --upgrade sentiment-analyzer-tool==2.0.0

# Step 4: Restart MCP server
systemctl restart mcp-server

# Step 5: Verify deployment
curl http://localhost:8000/mcp/tools | jq '.tools[] | select(.name=="analyze_sentiment")'
```

**Expected Output:**
```json
{
  "name": "analyze_sentiment",
  "version": "2.0.0",
  "description": "Analyzes sentiment of text and returns scores"
}
```

### Register with Gateway

```bash
sark-cli server register \
  --server-id sentiment-analysis-prod \
  --endpoint https://sentiment-api.example.com/mcp \
  --version 2.0.0
```

## Common Pitfalls

### Pitfall 1: Missing Input Validation

**Problem:** Tool crashes on unexpected input.

**Solution:** Always validate all inputs:
```python
def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    # Validate BEFORE processing
    self.validate_input(arguments)

    # Now safe to use
    text = arguments["text"]
```

### Pitfall 2: Not Handling Edge Cases

**Problem:** Tool fails on empty strings, special characters, etc.

**Solution:** Test edge cases:
```python
def test_edge_cases(self, analyzer):
    # Empty after whitespace strip
    result = analyzer.execute({"text": "   "})

    # Special characters
    result = analyzer.execute({"text": "Test 🎉 @#$%"})

    # Very long text
    result = analyzer.execute({"text": "word " * 5000})
```

### Pitfall 3: Poor Error Messages

**Problem:** Generic errors don't help users fix issues.

**Bad:**
```python
raise ValueError("Invalid input")
```

**Good:**
```python
raise InvalidInputError(
    message="Text exceeds maximum length of 10,000 characters",
    details={
        "field": "text",
        "provided_length": len(text),
        "max_length": 10000
    }
)
```

### Pitfall 4: Not Logging Errors

**Problem:** Hard to debug production issues.

**Solution:** Log comprehensively:
```python
try:
    result = self.analyze(text)
except Exception as e:
    logger.error(
        f"Analysis failed for text length {len(text)}",
        exc_info=True,
        extra={
            "language": language,
            "options": options,
            "text_preview": text[:100]
        }
    )
    raise
```

### Pitfall 5: Ignoring Performance

**Problem:** Tool times out under load.

**Solution:** Implement timeouts and optimize:
```python
import asyncio

async def analyze_with_timeout(self, text: str, timeout: int = 30):
    """Analyze with timeout."""
    try:
        return await asyncio.wait_for(
            self.analyze(text),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise AnalysisError(
            f"Analysis timed out after {timeout}s",
            details={"timeout_seconds": timeout}
        )
```

## Related Resources

- [MCP Protocol Specification](https://modelcontextprotocol.io/specification)
- [JSON Schema Guide](https://json-schema.org/learn/getting-started-step-by-step)
- [Error Handling Best Practices](../explanation/error-handling.md)
- [Testing MCP Tools](../tutorials/testing-mcp-tools.md)
- [How to Register Server](./how-to-register-server.md)
- [How to Monitor Gateway](./how-to-monitor-gateway.md)

## Next Steps

After implementing your tool:

1. **Write policies** to control access
   - See: [How to Write Policies](./how-to-write-policies.md)

2. **Set up monitoring** for tool performance
   - See: [How to Monitor Gateway](./how-to-monitor-gateway.md)

3. **Secure your tool** with authentication
   - See: [How to Secure Gateway](./how-to-secure-gateway.md)

4. **Troubleshoot issues** that arise
   - See: [How to Troubleshoot Tools](./how-to-troubleshoot-tools.md)

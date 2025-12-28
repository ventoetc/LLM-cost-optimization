"""
Input Processing Engine

Determines HOW to process user input based on:
- Clarity/ambiguity level
- Presence of context/attachments
- Query type (discrete task vs exploration)

Handles vague queries conversationally to help users refine.
"""
from typing import Optional, Dict, Any, List
from enum import Enum
import re

from app.services.decomposer import PromptDecomposer


class QueryType(str, Enum):
    """Type of user query"""
    CLEAR_TASK = "clear_task"  # Well-defined, ready to execute
    VAGUE_REQUEST = "vague_request"  # Needs clarification
    EXPLORATION = "exploration"  # User exploring problem space
    COMPARISON = "comparison"  # Comparing options
    DEBUGGING = "debugging"  # Troubleshooting issue
    IDEATION = "ideation"  # Brainstorming/planning


class ProcessingMode(str, Enum):
    """How to handle the input"""
    EXECUTE_DIRECTLY = "execute_directly"  # Clear enough, just run it
    CLARIFY_FIRST = "clarify_first"  # Too vague, ask questions
    GUIDED_EXPLORATION = "guided_exploration"  # Help them explore
    CONTEXT_NEEDED = "context_needed"  # Need attachments/more info


class InputAnalysis:
    """Analysis of user input"""
    def __init__(
        self,
        query_type: QueryType,
        processing_mode: ProcessingMode,
        ambiguity_score: float,
        clarity_score: float,
        detected_intent: str,
        missing_context: List[str],
        suggested_clarifications: List[str]
    ):
        self.query_type = query_type
        self.processing_mode = processing_mode
        self.ambiguity_score = ambiguity_score
        self.clarity_score = clarity_score
        self.detected_intent = detected_intent
        self.missing_context = missing_context
        self.suggested_clarifications = suggested_clarifications


class InputProcessor:
    """
    Pre-processing layer before orchestration

    Analyzes input and determines optimal processing strategy
    """

    def __init__(self):
        self.decomposer = PromptDecomposer()

        # Patterns for detecting query types
        self.vague_indicators = [
            r'\b(help|assist|need|want|looking for)\b',
            r'\b(something|anything|some|any)\b',
            r'\bhow do i\b',
            r'\bwhat should\b',
        ]

        self.exploration_indicators = [
            r'\b(explore|consider|think about|options|approaches)\b',
            r'\b(what are|what if|could i|should i)\b',
            r'\b(compare|versus|vs|or)\b',
        ]

        self.clear_task_indicators = [
            r'\b(analyze|calculate|generate|create|build|implement)\b',
            r'\b(show me|give me|provide|explain)\b.*\b(specific|exactly|precisely)\b',
        ]

    async def process_input(
        self,
        prompt: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Analyze input and determine processing strategy

        Returns either:
        - Clarifying questions (if vague)
        - Ready-to-execute enhanced request
        - Guided exploration prompts
        """

        # 1. Analyze the input
        analysis = self._analyze_input(prompt, attachments)

        # 2. Extract context from attachments if present
        attachment_context = None
        if attachments:
            attachment_context = await self._extract_attachment_context(attachments)

        # 3. Determine processing path
        if analysis.processing_mode == ProcessingMode.EXECUTE_DIRECTLY:
            # Input is clear enough - enhance and execute
            return {
                "mode": "execute",
                "enhanced_prompt": self._enhance_prompt(prompt, attachment_context),
                "analysis": analysis,
                "attachments_context": attachment_context
            }

        elif analysis.processing_mode == ProcessingMode.CLARIFY_FIRST:
            # Too vague - generate clarifying questions
            clarifications = await self._generate_clarifying_questions(
                prompt,
                analysis,
                attachment_context
            )
            return {
                "mode": "clarify",
                "original_prompt": prompt,
                "analysis": analysis,
                "clarifications": clarifications
            }

        elif analysis.processing_mode == ProcessingMode.GUIDED_EXPLORATION:
            # User exploring - provide guidance
            guidance = await self._generate_exploration_guidance(
                prompt,
                analysis,
                attachment_context
            )
            return {
                "mode": "explore",
                "original_prompt": prompt,
                "analysis": analysis,
                "guidance": guidance
            }

        else:  # CONTEXT_NEEDED
            # Need more context
            return {
                "mode": "context_needed",
                "original_prompt": prompt,
                "analysis": analysis,
                "missing_context": analysis.missing_context
            }

    def _analyze_input(
        self,
        prompt: str,
        attachments: Optional[List[Dict]] = None
    ) -> InputAnalysis:
        """Analyze input to determine query type and processing mode"""

        prompt_lower = prompt.lower()

        # Calculate ambiguity score
        ambiguity_score = self._calculate_ambiguity(prompt)

        # Calculate clarity score (inverse of ambiguity + specificity)
        clarity_score = self._calculate_clarity(prompt)

        # Detect query type
        query_type = self._detect_query_type(prompt_lower)

        # Detect intent
        intent = self._detect_intent(prompt_lower)

        # Identify missing context
        missing_context = self._identify_missing_context(prompt, attachments)

        # Determine processing mode
        processing_mode = self._determine_processing_mode(
            ambiguity_score,
            clarity_score,
            query_type,
            bool(attachments),
            missing_context
        )

        # Generate suggested clarifications
        clarifications = self._suggest_clarifications(
            prompt,
            query_type,
            missing_context
        )

        return InputAnalysis(
            query_type=query_type,
            processing_mode=processing_mode,
            ambiguity_score=ambiguity_score,
            clarity_score=clarity_score,
            detected_intent=intent,
            missing_context=missing_context,
            suggested_clarifications=clarifications
        )

    def _calculate_ambiguity(self, prompt: str) -> float:
        """
        Calculate ambiguity score (0.0 = clear, 1.0 = very vague)

        Indicators of ambiguity:
        - Vague language ("something", "help", etc.)
        - Short length without specifics
        - Multiple possible interpretations
        - Lack of concrete details
        """
        score = 0.0

        # Check for vague indicators
        for pattern in self.vague_indicators:
            if re.search(pattern, prompt.lower()):
                score += 0.2

        # Short prompts without specifics are often vague
        word_count = len(prompt.split())
        if word_count < 10:
            score += 0.3

        # Lack of specific nouns/details
        specific_patterns = r'\b[A-Z][a-z]+\b|\b\d+\b|[A-Za-z]+\.[A-Za-z]+'
        specifics = len(re.findall(specific_patterns, prompt))
        if specifics < 2:
            score += 0.2

        # Question words without clear object
        if re.search(r'\b(what|how|why)\b(?!.*\b(is|are|should|does)\s+\w+)', prompt.lower()):
            score += 0.15

        return min(score, 1.0)

    def _calculate_clarity(self, prompt: str) -> float:
        """
        Calculate clarity score (0.0 = unclear, 1.0 = very clear)

        Indicators of clarity:
        - Specific technical terms
        - Clear action verbs
        - Concrete details (numbers, names, etc.)
        - Well-structured question/request
        """
        score = 0.0

        # Specific action verbs
        action_verbs = r'\b(analyze|implement|calculate|optimize|compare|debug|refactor|design|build)\b'
        if re.search(action_verbs, prompt.lower()):
            score += 0.3

        # Technical terms or proper nouns
        technical_patterns = [
            r'\b[A-Z]{2,}\b',  # Acronyms (JWT, API, etc.)
            r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b',  # PascalCase
            r'\w+\.\w+',  # Dotted notation
            r'\b\d+[kmb]?\+?\b',  # Numbers with scale
        ]
        for pattern in technical_patterns:
            matches = len(re.findall(pattern, prompt))
            score += min(matches * 0.1, 0.2)

        # Concrete details
        if re.search(r'\b(for|in|with|using)\s+\w+', prompt.lower()):
            score += 0.2

        # Question structure
        if '?' in prompt and len(prompt.split()) > 8:
            score += 0.15

        # Sufficient length
        word_count = len(prompt.split())
        if word_count >= 15:
            score += 0.15

        return min(score, 1.0)

    def _detect_query_type(self, prompt_lower: str) -> QueryType:
        """Detect the type of query"""

        # Check for exploration
        for pattern in self.exploration_indicators:
            if re.search(pattern, prompt_lower):
                return QueryType.EXPLORATION

        # Check for comparison
        if re.search(r'\bvs\b|\bversus\b|\bor\b.*\bor\b|\bcompare\b', prompt_lower):
            return QueryType.COMPARISON

        # Check for debugging
        debug_patterns = [
            r'\b(error|bug|issue|problem|broken|not working|fails?)\b',
            r'\b(debug|fix|troubleshoot)\b',
            r'\bwhy (is|does|doesn\'t)\b'
        ]
        for pattern in debug_patterns:
            if re.search(pattern, prompt_lower):
                return QueryType.DEBUGGING

        # Check for ideation
        ideation_patterns = [
            r'\b(brainstorm|ideas|suggestions|possibilities)\b',
            r'\b(what (are|could be) (some|the))\b',
            r'\bhow (can|could|might) (i|we)\b'
        ]
        for pattern in ideation_patterns:
            if re.search(pattern, prompt_lower):
                return QueryType.IDEATION

        # Check for clear task
        for pattern in self.clear_task_indicators:
            if re.search(pattern, prompt_lower):
                return QueryType.CLEAR_TASK

        # Default: vague request
        return QueryType.VAGUE_REQUEST

    def _detect_intent(self, prompt_lower: str) -> str:
        """Extract the primary intent from prompt"""

        # Simple keyword-based intent detection
        intent_map = {
            'learn': r'\b(learn|understand|explain|what is|how does)\b',
            'implement': r'\b(implement|build|create|develop|code|write)\b',
            'analyze': r'\b(analyze|evaluate|assess|review|check)\b',
            'decide': r'\b(should|choose|decide|select|pick)\b',
            'optimize': r'\b(optimize|improve|faster|better|efficient)\b',
            'debug': r'\b(debug|fix|solve|error|problem)\b',
        }

        for intent, pattern in intent_map.items():
            if re.search(pattern, prompt_lower):
                return intent

        return 'general_inquiry'

    def _identify_missing_context(
        self,
        prompt: str,
        attachments: Optional[List[Dict]] = None
    ) -> List[str]:
        """Identify what context might be missing"""

        missing = []
        prompt_lower = prompt.lower()

        # Check for implementation questions without code context
        if re.search(r'\b(refactor|optimize|fix|debug|this code)\b', prompt_lower):
            if not attachments or not any(a.get('type') == 'code' for a in attachments):
                missing.append("code_to_analyze")

        # Check for UI/design questions without visual context
        if re.search(r'\b(ui|interface|design|layout|dashboard)\b', prompt_lower):
            if not attachments or not any(a.get('type') == 'image' for a in attachments):
                missing.append("visual_context")

        # Check for questions about "this" without clear referent
        if re.search(r'\b(this|these|that|those)\b', prompt_lower):
            if not attachments:
                missing.append("reference_context")

        # Check for scale-dependent questions
        if re.search(r'\b(scale|users|traffic|performance|load)\b', prompt_lower):
            if not re.search(r'\b\d+[kmb]?\b', prompt_lower):
                missing.append("scale_requirements")

        return missing

    def _determine_processing_mode(
        self,
        ambiguity_score: float,
        clarity_score: float,
        query_type: QueryType,
        has_attachments: bool,
        missing_context: List[str]
    ) -> ProcessingMode:
        """Determine how to process this input"""

        # Critical missing context
        if missing_context and 'code_to_analyze' in missing_context:
            return ProcessingMode.CONTEXT_NEEDED

        # High ambiguity = need clarification
        if ambiguity_score > 0.6:
            return ProcessingMode.CLARIFY_FIRST

        # Exploration/ideation queries
        if query_type in [QueryType.EXPLORATION, QueryType.IDEATION]:
            return ProcessingMode.GUIDED_EXPLORATION

        # Clear task with good clarity
        if clarity_score > 0.5 and query_type == QueryType.CLEAR_TASK:
            return ProcessingMode.EXECUTE_DIRECTLY

        # Comparison or debugging with some clarity
        if clarity_score > 0.4 and query_type in [QueryType.COMPARISON, QueryType.DEBUGGING]:
            if missing_context:
                return ProcessingMode.CONTEXT_NEEDED
            return ProcessingMode.EXECUTE_DIRECTLY

        # Default: clarify first
        return ProcessingMode.CLARIFY_FIRST

    def _suggest_clarifications(
        self,
        prompt: str,
        query_type: QueryType,
        missing_context: List[str]
    ) -> List[str]:
        """Generate suggested clarification questions"""

        clarifications = []

        # Context-specific clarifications
        if 'scale_requirements' in missing_context:
            clarifications.append("What scale are you targeting? (users, traffic volume, data size)")

        if 'code_to_analyze' in missing_context:
            clarifications.append("Can you share the code you're asking about?")

        if 'visual_context' in missing_context:
            clarifications.append("Can you share a screenshot or design mockup?")

        # Query-type specific
        if query_type == QueryType.VAGUE_REQUEST:
            clarifications.extend([
                "What are you trying to accomplish?",
                "What's the context or use case?",
                "Do you have any specific constraints or requirements?"
            ])

        elif query_type == QueryType.EXPLORATION:
            clarifications.extend([
                "What problem are you trying to solve?",
                "What approaches have you considered so far?"
            ])

        return clarifications[:5]  # Limit to 5 questions

    async def _extract_attachment_context(
        self,
        attachments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract context from attachments"""

        context = {
            "has_code": False,
            "has_images": False,
            "has_documents": False,
            "code_files": [],
            "image_descriptions": [],
            "document_summaries": []
        }

        for attachment in attachments:
            att_type = attachment.get('type', 'unknown')

            if att_type == 'code':
                context['has_code'] = True
                context['code_files'].append({
                    'filename': attachment.get('filename', 'code.txt'),
                    'language': attachment.get('language', 'unknown'),
                    'lines': len(attachment.get('content', '').split('\n'))
                })

            elif att_type == 'image':
                context['has_images'] = True
                # In real implementation, would use vision model
                context['image_descriptions'].append({
                    'filename': attachment.get('filename', 'image'),
                    'description': 'Image provided by user'
                })

            elif att_type in ['pdf', 'document', 'text']:
                context['has_documents'] = True
                # In real implementation, would extract/summarize
                context['document_summaries'].append({
                    'filename': attachment.get('filename', 'document'),
                    'type': att_type
                })

        return context

    def _enhance_prompt(
        self,
        prompt: str,
        attachment_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Enhance prompt with attachment context"""

        if not attachment_context:
            return prompt

        enhancements = []

        if attachment_context.get('has_code'):
            files = attachment_context['code_files']
            enhancements.append(
                f"User has provided {len(files)} code file(s) for analysis."
            )

        if attachment_context.get('has_images'):
            images = attachment_context['image_descriptions']
            enhancements.append(
                f"User has provided {len(images)} image(s) for visual context."
            )

        if attachment_context.get('has_documents'):
            docs = attachment_context['document_summaries']
            enhancements.append(
                f"User has provided {len(docs)} document(s) with additional context."
            )

        if enhancements:
            enhanced = f"{prompt}\n\nContext: {' '.join(enhancements)}"
            return enhanced

        return prompt

    async def _generate_clarifying_questions(
        self,
        prompt: str,
        analysis: InputAnalysis,
        attachment_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Generate conversational clarifying questions"""

        # Use cheap model to generate tailored questions
        clarification_prompt = f"""The user said: "{prompt}"

This is vague/ambiguous. Generate 3-5 clarifying questions to help them refine their request.

Focus on:
- What they're trying to accomplish
- Their specific context or constraints
- What they already have vs what they need

Make questions friendly and conversational, not interrogative.
"""

        # In real implementation, call cheap model here
        # For now, use suggested clarifications from analysis

        return {
            "message": "I'd like to help, but I need a bit more context. Let me ask a few quick questions:",
            "questions": analysis.suggested_clarifications,
            "quick_options": self._generate_quick_options(analysis.query_type)
        }

    async def _generate_exploration_guidance(
        self,
        prompt: str,
        analysis: InputAnalysis,
        attachment_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Generate guidance for exploration queries"""

        return {
            "message": f"It looks like you're exploring {analysis.detected_intent}. I can help you think through this.",
            "suggestions": [
                "Start with your goals and constraints",
                "Look at pros/cons of different approaches",
                "Consider what success looks like",
                "Think about potential risks or challenges"
            ],
            "next_steps": [
                "Tell me more about what you're trying to achieve",
                "Share any approaches you've already considered",
                "Let me know if there are specific options you want to compare"
            ]
        }

    def _generate_quick_options(self, query_type: QueryType) -> List[str]:
        """Generate quick response options for user"""

        options_map = {
            QueryType.VAGUE_REQUEST: [
                "I'm trying to build something new",
                "I'm debugging an existing issue",
                "I'm trying to learn/understand something",
                "I'm comparing different approaches"
            ],
            QueryType.EXPLORATION: [
                "Show me common approaches to this",
                "Help me think through tradeoffs",
                "I want to see examples"
            ],
            QueryType.IDEATION: [
                "Help me brainstorm ideas",
                "Show me what others have done",
                "I need to validate an idea"
            ]
        }

        return options_map.get(query_type, [])

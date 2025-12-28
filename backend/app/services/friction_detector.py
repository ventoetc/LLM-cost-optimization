"""
Friction Detection Service

Analyzes responses from different models to detect cognitive friction,
alignment patterns, and potential hallucinations. Uses model differences
as a proxy for diverse training perspectives.
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import re


class FrictionLevel(str, Enum):
    """Level of friction between model responses"""
    SMOOTH = "smooth"  # High alignment, confident
    MILD = "mild"  # Some differences, expected variance
    MODERATE = "moderate"  # Significant differences, needs attention
    SEVERE = "severe"  # Contradictory, investigation required
    SUSPICIOUS = "suspicious"  # Too smooth when friction expected (groupthink)


class VerificationFlag(str, Enum):
    """Basic verification checks"""
    FACTUAL_CONSISTENCY = "factual_consistency"
    LOGICAL_COHERENCE = "logical_coherence"
    SPECIFICITY = "specificity"  # Not vague/generic
    GROUNDING = "grounding"  # References concrete details vs fabrication
    CROSS_MODEL_AGREEMENT = "cross_model_agreement"


@dataclass
class FrictionPoint:
    """A point of friction between model responses"""
    location: str  # Where in the response
    description: str  # What the friction is about
    severity: FrictionLevel
    models_involved: List[str]
    reasoning_paths: List[str]  # Different approaches taken
    resolution_needed: bool


@dataclass
class VerificationResult:
    """Result of hallucination/error checking"""
    flag: VerificationFlag
    passed: bool
    confidence: float  # 0.0 to 1.0
    evidence: str
    models_checked: List[str]


@dataclass
class FrictionAnalysis:
    """Complete friction analysis of multi-model responses"""
    overall_friction: FrictionLevel
    friction_points: List[FrictionPoint]
    verification_results: List[VerificationResult]
    model_diversity_score: float  # How different were the models' approaches
    confidence_score: float  # Overall confidence in the response
    warnings: List[str]
    human_behavioral_patterns: Dict[str, bool]  # Natural patterns detected


class FrictionDetector:
    """
    Detects friction and validates responses across multi-vendor models

    Philosophy: Different models = different training = different cognitive paths
    Friction reveals where assumptions differ, alignment reveals confidence
    """

    def __init__(self):
        self.friction_threshold = {
            FrictionLevel.SMOOTH: 0.2,
            FrictionLevel.MILD: 0.4,
            FrictionLevel.MODERATE: 0.6,
            FrictionLevel.SEVERE: 0.8,
        }

    async def analyze_responses(
        self,
        responses: List[Dict[str, str]],  # [{model, response}, ...]
        task_context: str,
        expected_complexity: float
    ) -> FrictionAnalysis:
        """
        Analyze friction across model responses

        Args:
            responses: List of {model, response} dicts
            task_context: What the task was about
            expected_complexity: 0.0-1.0, higher = expect more friction
        """

        # Detect friction points
        friction_points = await self._detect_friction_points(responses, task_context)

        # Run verification checks
        verification_results = await self._run_verification_checks(responses)

        # Analyze model diversity
        diversity_score = self._calculate_diversity_score(responses)

        # Detect human behavioral patterns
        behavioral_patterns = self._detect_behavioral_patterns(
            friction_points,
            responses,
            expected_complexity
        )

        # Calculate overall friction level
        overall_friction = self._calculate_overall_friction(
            friction_points,
            expected_complexity,
            diversity_score
        )

        # Generate warnings
        warnings = self._generate_warnings(
            overall_friction,
            friction_points,
            verification_results,
            expected_complexity,
            behavioral_patterns
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            friction_points,
            verification_results,
            diversity_score
        )

        return FrictionAnalysis(
            overall_friction=overall_friction,
            friction_points=friction_points,
            verification_results=verification_results,
            model_diversity_score=diversity_score,
            confidence_score=confidence,
            warnings=warnings,
            human_behavioral_patterns=behavioral_patterns
        )

    async def _detect_friction_points(
        self,
        responses: List[Dict[str, str]],
        task_context: str
    ) -> List[FrictionPoint]:
        """
        Detect where models show friction in their reasoning

        Looks for:
        - Different approaches to same problem
        - Contradictory conclusions
        - Different assumptions revealed
        - Varying confidence levels
        """
        friction_points = []

        # Compare pairwise
        for i, resp_a in enumerate(responses):
            for resp_b in responses[i+1:]:
                # Detect semantic differences
                differences = self._find_semantic_differences(
                    resp_a['response'],
                    resp_b['response']
                )

                for diff in differences:
                    severity = self._assess_friction_severity(diff)

                    friction_point = FrictionPoint(
                        location=diff['location'],
                        description=diff['description'],
                        severity=severity,
                        models_involved=[resp_a['model'], resp_b['model']],
                        reasoning_paths=[
                            diff['approach_a'],
                            diff['approach_b']
                        ],
                        resolution_needed=severity in [
                            FrictionLevel.MODERATE,
                            FrictionLevel.SEVERE
                        ]
                    )
                    friction_points.append(friction_point)

        return friction_points

    def _find_semantic_differences(
        self,
        response_a: str,
        response_b: str
    ) -> List[Dict]:
        """
        Find meaningful semantic differences between responses

        This is a simplified implementation - in production, you'd use
        embedding similarity, semantic parsing, etc.
        """
        differences = []

        # Check for contradictory statements
        # Look for negations, opposing conclusions
        patterns = [
            (r'(is|are|was|were)\s+not', r'(is|are|was|were)\s+(?!not)'),
            (r'should\s+not', r'should\s+(?!not)'),
            (r'cannot', r'can\s+(?!not)'),
            (r'impossible', r'possible'),
            (r'always', r'never'),
        ]

        for neg_pattern, pos_pattern in patterns:
            neg_in_a = bool(re.search(neg_pattern, response_a, re.IGNORECASE))
            pos_in_a = bool(re.search(pos_pattern, response_a, re.IGNORECASE))
            neg_in_b = bool(re.search(neg_pattern, response_b, re.IGNORECASE))
            pos_in_b = bool(re.search(pos_pattern, response_b, re.IGNORECASE))

            if (neg_in_a and pos_in_b) or (pos_in_a and neg_in_b):
                differences.append({
                    'location': 'conclusion',
                    'description': 'Contradictory assertions detected',
                    'approach_a': 'Negative assertion' if neg_in_a else 'Positive assertion',
                    'approach_b': 'Negative assertion' if neg_in_b else 'Positive assertion',
                    'severity': 'high'
                })

        # Check for different methodologies mentioned
        method_keywords = ['approach', 'method', 'strategy', 'technique', 'way']
        methods_a = self._extract_methods(response_a, method_keywords)
        methods_b = self._extract_methods(response_b, method_keywords)

        if methods_a and methods_b and methods_a != methods_b:
            differences.append({
                'location': 'methodology',
                'description': 'Different approaches suggested',
                'approach_a': ', '.join(methods_a),
                'approach_b': ', '.join(methods_b),
                'severity': 'medium'
            })

        # Check for different levels of certainty
        confidence_a = self._extract_confidence_level(response_a)
        confidence_b = self._extract_confidence_level(response_b)

        if abs(confidence_a - confidence_b) > 0.3:
            differences.append({
                'location': 'confidence',
                'description': 'Significant difference in certainty',
                'approach_a': f'Confidence: {confidence_a:.2f}',
                'approach_b': f'Confidence: {confidence_b:.2f}',
                'severity': 'medium'
            })

        return differences

    def _extract_methods(self, text: str, keywords: List[str]) -> List[str]:
        """Extract mentioned methods/approaches from text"""
        methods = []
        for keyword in keywords:
            # Simple extraction - find sentences with method keywords
            pattern = rf'[^.]*{keyword}[^.]*\.'
            matches = re.findall(pattern, text, re.IGNORECASE)
            methods.extend(matches[:2])  # Limit to avoid noise
        return methods[:3]  # Max 3 methods

    def _extract_confidence_level(self, text: str) -> float:
        """
        Extract confidence level from text based on linguistic markers

        High confidence: definitely, certainly, always, must
        Medium: likely, probably, should, generally
        Low: might, could, possibly, maybe
        """
        high_confidence = len(re.findall(
            r'\b(definitely|certainly|always|must|clearly|obviously)\b',
            text, re.IGNORECASE
        ))
        medium_confidence = len(re.findall(
            r'\b(likely|probably|should|generally|typically)\b',
            text, re.IGNORECASE
        ))
        low_confidence = len(re.findall(
            r'\b(might|could|possibly|maybe|perhaps|potentially)\b',
            text, re.IGNORECASE
        ))

        total = high_confidence + medium_confidence + low_confidence
        if total == 0:
            return 0.5  # Neutral

        score = (high_confidence * 1.0 + medium_confidence * 0.5 + low_confidence * 0.2) / total
        return score

    def _assess_friction_severity(self, difference: Dict) -> FrictionLevel:
        """Assess severity of a detected difference"""
        severity_map = {
            'high': FrictionLevel.SEVERE,
            'medium': FrictionLevel.MODERATE,
            'low': FrictionLevel.MILD,
        }
        return severity_map.get(difference.get('severity', 'low'), FrictionLevel.MILD)

    async def _run_verification_checks(
        self,
        responses: List[Dict[str, str]]
    ) -> List[VerificationResult]:
        """
        Run basic hallucination and error checks

        These are fundamental checks to display to users
        """
        results = []

        # Check 1: Factual Consistency (do models agree on facts?)
        results.append(self._check_factual_consistency(responses))

        # Check 2: Logical Coherence (does reasoning make sense?)
        results.append(self._check_logical_coherence(responses))

        # Check 3: Specificity (not vague/generic hallucination)
        results.append(self._check_specificity(responses))

        # Check 4: Grounding (references to concrete details)
        results.append(self._check_grounding(responses))

        # Check 5: Cross-model agreement
        results.append(self._check_cross_model_agreement(responses))

        return results

    def _check_factual_consistency(
        self,
        responses: List[Dict[str, str]]
    ) -> VerificationResult:
        """Check if factual claims are consistent across models"""
        # Simplified: look for numbers, dates, names
        # In production: use NER and fact extraction

        models_checked = [r['model'] for r in responses]

        # Extract potential facts (numbers, dates, proper nouns)
        all_facts = []
        for resp in responses:
            text = resp['response']
            numbers = re.findall(r'\b\d+(?:\.\d+)?(?:\s*%|\s*percent)?\b', text)
            dates = re.findall(r'\b\d{4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}', text)
            all_facts.extend(numbers + dates)

        # If models mention different facts, might be inconsistent
        fact_variety = len(set(all_facts)) / max(len(all_facts), 1)

        passed = fact_variety < 0.7  # Less than 70% unique facts = good consistency
        confidence = 1.0 - fact_variety

        return VerificationResult(
            flag=VerificationFlag.FACTUAL_CONSISTENCY,
            passed=passed,
            confidence=confidence,
            evidence=f"Found {len(set(all_facts))} unique factual claims across {len(responses)} models",
            models_checked=models_checked
        )

    def _check_logical_coherence(
        self,
        responses: List[Dict[str, str]]
    ) -> VerificationResult:
        """Check for logical coherence in reasoning"""
        models_checked = [r['model'] for r in responses]

        # Look for logical connectors
        coherence_markers = [
            r'\btherefore\b', r'\bthus\b', r'\bhence\b', r'\bconsequently\b',
            r'\bbecause\b', r'\bsince\b', r'\bif\b.*\bthen\b', r'\bhowever\b',
            r'\balthough\b', r'\bwhile\b'
        ]

        coherence_scores = []
        for resp in responses:
            text = resp['response']
            markers_found = sum(
                len(re.findall(pattern, text, re.IGNORECASE))
                for pattern in coherence_markers
            )
            # Normalize by length
            score = min(markers_found / (len(text.split()) / 100), 1.0)
            coherence_scores.append(score)

        avg_coherence = sum(coherence_scores) / len(coherence_scores)
        passed = avg_coherence > 0.3

        return VerificationResult(
            flag=VerificationFlag.LOGICAL_COHERENCE,
            passed=passed,
            confidence=avg_coherence,
            evidence=f"Average logical coherence score: {avg_coherence:.2f}",
            models_checked=models_checked
        )

    def _check_specificity(
        self,
        responses: List[Dict[str, str]]
    ) -> VerificationResult:
        """Check that responses are specific, not vague hallucinations"""
        models_checked = [r['model'] for r in responses]

        # Vague phrases that might indicate hallucination
        vague_patterns = [
            r'\bsome\s+(?:people|experts|studies)\b',
            r'\bit\s+is\s+believed\b',
            r'\bmany\s+(?:believe|think|say)\b',
            r'\bgenerally\s+speaking\b',
            r'\bin\s+general\b',
        ]

        specificity_scores = []
        for resp in responses:
            text = resp['response']
            vague_count = sum(
                len(re.findall(pattern, text, re.IGNORECASE))
                for pattern in vague_patterns
            )
            # Lower vague count = higher specificity
            score = max(1.0 - (vague_count / 10), 0.0)
            specificity_scores.append(score)

        avg_specificity = sum(specificity_scores) / len(specificity_scores)
        passed = avg_specificity > 0.6

        return VerificationResult(
            flag=VerificationFlag.SPECIFICITY,
            passed=passed,
            confidence=avg_specificity,
            evidence=f"Specificity score: {avg_specificity:.2f}",
            models_checked=models_checked
        )

    def _check_grounding(
        self,
        responses: List[Dict[str, str]]
    ) -> VerificationResult:
        """Check for grounding in concrete details vs fabrication"""
        models_checked = [r['model'] for r in responses]

        # Look for concrete details: citations, specific names, technical terms
        grounding_indicators = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Proper names
            r'\b\d{4}\b',  # Years
            r'\baccording\s+to\b',
            r'\bstudy\b|\bresearch\b|\bpaper\b',
            r'\b[A-Z]{2,}\b',  # Acronyms
        ]

        grounding_scores = []
        for resp in responses:
            text = resp['response']
            indicators_found = sum(
                len(re.findall(pattern, text))
                for pattern in grounding_indicators
            )
            score = min(indicators_found / 5, 1.0)
            grounding_scores.append(score)

        avg_grounding = sum(grounding_scores) / len(grounding_scores)
        passed = avg_grounding > 0.3

        return VerificationResult(
            flag=VerificationFlag.GROUNDING,
            passed=passed,
            confidence=avg_grounding,
            evidence=f"Grounding score: {avg_grounding:.2f}",
            models_checked=models_checked
        )

    def _check_cross_model_agreement(
        self,
        responses: List[Dict[str, str]]
    ) -> VerificationResult:
        """Check agreement across different model vendors"""
        models_checked = [r['model'] for r in responses]

        # Simple similarity check (in production: use embeddings)
        # Count overlapping significant words
        all_words = []
        for resp in responses:
            words = set(re.findall(r'\b[a-z]{4,}\b', resp['response'].lower()))
            all_words.append(words)

        if len(all_words) < 2:
            return VerificationResult(
                flag=VerificationFlag.CROSS_MODEL_AGREEMENT,
                passed=True,
                confidence=1.0,
                evidence="Single model response",
                models_checked=models_checked
            )

        # Calculate Jaccard similarity
        intersection = set.intersection(*all_words)
        union = set.union(*all_words)
        similarity = len(intersection) / len(union) if union else 0

        passed = similarity > 0.2  # Some agreement expected

        return VerificationResult(
            flag=VerificationFlag.CROSS_MODEL_AGREEMENT,
            passed=passed,
            confidence=similarity,
            evidence=f"Model agreement: {similarity:.2%}",
            models_checked=models_checked
        )

    def _calculate_diversity_score(
        self,
        responses: List[Dict[str, str]]
    ) -> float:
        """
        Calculate how diverse the model responses are
        High diversity = different training/approaches surfaced
        """
        if len(responses) < 2:
            return 0.0

        # Check vendor diversity
        vendors = set(r['model'].split('/')[0] for r in responses)
        vendor_diversity = len(vendors) / len(responses)

        # Check response diversity (simple word overlap)
        word_sets = []
        for resp in responses:
            words = set(re.findall(r'\b[a-z]{4,}\b', resp['response'].lower()))
            word_sets.append(words)

        # Average pairwise Jaccard distance
        distances = []
        for i, ws_a in enumerate(word_sets):
            for ws_b in word_sets[i+1:]:
                intersection = len(ws_a & ws_b)
                union = len(ws_a | ws_b)
                distance = 1 - (intersection / union if union else 0)
                distances.append(distance)

        avg_distance = sum(distances) / len(distances) if distances else 0

        # Combine vendor and response diversity
        return (vendor_diversity + avg_distance) / 2

    def _detect_behavioral_patterns(
        self,
        friction_points: List[FrictionPoint],
        responses: List[Dict[str, str]],
        expected_complexity: float
    ) -> Dict[str, bool]:
        """
        Detect human-like behavioral patterns in the responses

        Natural patterns:
        - Healthy debate on complex issues
        - Quick alignment on simple facts
        - Exploration of edge cases
        - Acknowledgment of uncertainty
        """
        patterns = {}

        # Pattern 1: Healthy debate on complex issues
        if expected_complexity > 0.6:
            has_friction = len(friction_points) > 0
            patterns['healthy_debate'] = has_friction
        else:
            patterns['healthy_debate'] = True  # N/A for simple tasks

        # Pattern 2: Uncertainty acknowledgment
        uncertainty_markers = ['uncertain', 'unclear', 'depends', 'varies', 'might']
        has_uncertainty = any(
            any(marker in resp['response'].lower() for marker in uncertainty_markers)
            for resp in responses
        )
        patterns['acknowledges_uncertainty'] = has_uncertainty

        # Pattern 3: Explores alternatives
        alternative_markers = ['alternatively', 'another', 'also', 'additionally', 'however']
        explores_alternatives = any(
            sum(marker in resp['response'].lower() for marker in alternative_markers) > 2
            for resp in responses
        )
        patterns['explores_alternatives'] = explores_alternatives

        # Pattern 4: Shows reasoning process
        reasoning_markers = ['because', 'therefore', 'thus', 'hence', 'since']
        shows_reasoning = any(
            sum(marker in resp['response'].lower() for marker in reasoning_markers) > 2
            for resp in responses
        )
        patterns['shows_reasoning'] = shows_reasoning

        return patterns

    def _calculate_overall_friction(
        self,
        friction_points: List[FrictionPoint],
        expected_complexity: float,
        diversity_score: float
    ) -> FrictionLevel:
        """Calculate overall friction level"""
        if not friction_points:
            # No friction - is this suspicious?
            if expected_complexity > 0.7 and diversity_score > 0.5:
                # Expected friction but got none = suspicious
                return FrictionLevel.SUSPICIOUS
            return FrictionLevel.SMOOTH

        # Calculate weighted friction
        severity_weights = {
            FrictionLevel.MILD: 0.25,
            FrictionLevel.MODERATE: 0.5,
            FrictionLevel.SEVERE: 1.0,
        }

        total_friction = sum(
            severity_weights.get(fp.severity, 0.25)
            for fp in friction_points
        ) / len(friction_points)

        if total_friction < 0.3:
            return FrictionLevel.MILD
        elif total_friction < 0.6:
            return FrictionLevel.MODERATE
        else:
            return FrictionLevel.SEVERE

    def _generate_warnings(
        self,
        overall_friction: FrictionLevel,
        friction_points: List[FrictionPoint],
        verification_results: List[VerificationResult],
        expected_complexity: float,
        behavioral_patterns: Dict[str, bool]
    ) -> List[str]:
        """Generate warnings for the user"""
        warnings = []

        # Check for suspicious lack of friction
        if overall_friction == FrictionLevel.SUSPICIOUS:
            warnings.append(
                "⚠️ Suspiciously smooth agreement on complex task - "
                "models may be exhibiting groupthink or hallucinating similarly"
            )

        # Check for severe friction
        if overall_friction == FrictionLevel.SEVERE:
            warnings.append(
                "⚠️ Significant disagreement detected - "
                "manual review recommended to resolve conflicts"
            )

        # Check verification failures
        failed_checks = [vr for vr in verification_results if not vr.passed]
        if failed_checks:
            for check in failed_checks:
                warnings.append(
                    f"⚠️ Failed verification: {check.flag.value} - {check.evidence}"
                )

        # Check behavioral patterns
        if expected_complexity > 0.6 and not behavioral_patterns.get('healthy_debate'):
            warnings.append(
                "⚠️ Complex task but no healthy debate detected - "
                "consider additional validation"
            )

        if not behavioral_patterns.get('shows_reasoning'):
            warnings.append(
                "⚠️ Limited reasoning shown - responses may lack depth"
            )

        return warnings

    def _calculate_confidence(
        self,
        friction_points: List[FrictionPoint],
        verification_results: List[VerificationResult],
        diversity_score: float
    ) -> float:
        """Calculate overall confidence in the response"""
        # Start with verification scores
        verification_confidence = sum(
            vr.confidence for vr in verification_results
        ) / len(verification_results)

        # Adjust for friction (moderate friction is good, too much or too little is bad)
        friction_score = len(friction_points) / 5  # Normalize
        if 0.2 <= friction_score <= 0.6:
            friction_adjustment = 1.0
        else:
            friction_adjustment = 0.7

        # Diversity bonus (more diverse = more confident)
        diversity_bonus = diversity_score * 0.2

        confidence = (verification_confidence * 0.6 +
                     friction_adjustment * 0.3 +
                     diversity_bonus * 0.1)

        return min(max(confidence, 0.0), 1.0)

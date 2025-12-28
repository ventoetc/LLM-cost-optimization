"""
Emotional Friction Mapping

Maps AI model friction to human emotional/cognitive friction points.
The key insight: Where models struggle = where humans would feel frustrated.

By detecting model friction, we surface the micro-frustrations that accumulate
in human task execution - this is what we're using AI to help with.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class HumanEmotion(str, Enum):
    """Human emotions associated with task friction"""
    UNCERTAINTY = "uncertainty"  # "I'm not sure which approach is right"
    FRUSTRATION = "frustration"  # "This is harder than expected"
    CONFUSION = "confusion"  # "I don't understand what's being asked"
    OVERWHELM = "overwhelm"  # "Too many options/considerations"
    DOUBT = "doubt"  # "Am I doing this correctly?"
    ANXIETY = "anxiety"  # "What if I miss something important?"
    TEDIUM = "tedium"  # "This is repetitive and draining"


class CognitiveLoad(str, Enum):
    """Cognitive load levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXCESSIVE = "excessive"


@dataclass
class EmotionalFrictionPoint:
    """
    A point where both humans and AI experience difficulty

    This represents the micro-frustrations that accumulate during task execution.
    By detecting where AI models struggle, we surface where humans need help.
    """
    location: str  # Where in the task
    human_emotion: HumanEmotion  # What a human would feel
    ai_manifestation: str  # How AI models show this friction
    cognitive_load: CognitiveLoad
    help_needed: str  # What would reduce this friction
    model_signals: List[str]  # Specific signals from models
    severity: float  # 0.0 to 1.0


@dataclass
class TaskEmotionalProfile:
    """Complete emotional friction profile of a task"""
    friction_points: List[EmotionalFrictionPoint]
    overall_difficulty: CognitiveLoad
    primary_emotions: List[HumanEmotion]
    micro_frustrations: List[str]  # Specific small frustrations
    support_recommendations: List[str]  # How to help the user
    estimated_human_time_saved: float  # Hours saved by AI handling this


class EmotionalFrictionMapper:
    """
    Maps AI model friction to human emotional experience

    Philosophy: AI models experiencing difficulty = humans experiencing frustration
    By detecting AI friction, we predict where users need the most support
    """

    def map_ai_friction_to_human_emotion(
        self,
        ai_friction_points: List,  # From FrictionDetector
        task_context: str,
        user_history: Optional[Dict] = None
    ) -> TaskEmotionalProfile:
        """
        Convert AI friction signals into human emotional friction points

        This reveals the micro-frustrations humans would experience
        """
        emotional_points = []

        for ai_friction in ai_friction_points:
            # Map AI friction to human emotion
            emotional_point = self._translate_friction_to_emotion(
                ai_friction,
                task_context
            )
            emotional_points.append(emotional_point)

        # Identify primary emotional themes
        primary_emotions = self._identify_primary_emotions(emotional_points)

        # Extract micro-frustrations
        micro_frustrations = self._extract_micro_frustrations(
            emotional_points,
            task_context
        )

        # Calculate overall cognitive load
        overall_difficulty = self._calculate_cognitive_load(emotional_points)

        # Generate support recommendations
        support_recommendations = self._generate_support_recommendations(
            emotional_points,
            primary_emotions
        )

        # Estimate time saved
        time_saved = self._estimate_time_saved(
            overall_difficulty,
            len(micro_frustrations)
        )

        return TaskEmotionalProfile(
            friction_points=emotional_points,
            overall_difficulty=overall_difficulty,
            primary_emotions=primary_emotions,
            micro_frustrations=micro_frustrations,
            support_recommendations=support_recommendations,
            estimated_human_time_saved=time_saved
        )

    def _translate_friction_to_emotion(
        self,
        ai_friction,
        task_context: str
    ) -> EmotionalFrictionPoint:
        """
        Translate AI model friction into human emotional experience

        Key mappings:
        - Models disagree → Human uncertainty
        - Models use different approaches → Human confusion about best path
        - Models hedge/qualify → Human doubt
        - Models produce long responses → Human overwhelm
        - Models show low confidence → Human anxiety
        """
        # Analyze AI signals
        severity = getattr(ai_friction, 'severity', 'mild')
        description = getattr(ai_friction, 'description', '')
        models = getattr(ai_friction, 'models_involved', [])

        # Map to human emotion
        if 'contradictory' in description.lower():
            emotion = HumanEmotion.UNCERTAINTY
            manifestation = "Models can't agree on the right answer"
            help_needed = "Need clear validation or expert input"
            cognitive_load = CognitiveLoad.HIGH

        elif 'different approaches' in description.lower():
            emotion = HumanEmotion.CONFUSION
            manifestation = "Multiple valid paths, unclear which is best"
            help_needed = "Need decision criteria or guidance"
            cognitive_load = CognitiveLoad.MODERATE

        elif 'confidence' in description.lower():
            emotion = HumanEmotion.DOUBT
            manifestation = "Models are uncertain about correctness"
            help_needed = "Need additional validation or fact-checking"
            cognitive_load = CognitiveLoad.MODERATE

        elif 'methodology' in description.lower():
            emotion = HumanEmotion.OVERWHELM
            manifestation = "Too many possible approaches to consider"
            help_needed = "Need prioritization and simplification"
            cognitive_load = CognitiveLoad.HIGH

        else:
            emotion = HumanEmotion.FRUSTRATION
            manifestation = "Task is harder than it appears"
            help_needed = "Need step-by-step breakdown"
            cognitive_load = CognitiveLoad.MODERATE

        # Extract model signals
        model_signals = [f"{m} showed hesitation/variance" for m in models]

        return EmotionalFrictionPoint(
            location=getattr(ai_friction, 'location', 'general'),
            human_emotion=emotion,
            ai_manifestation=manifestation,
            cognitive_load=cognitive_load,
            help_needed=help_needed,
            model_signals=model_signals,
            severity=self._map_severity_to_float(severity)
        )

    def _map_severity_to_float(self, severity) -> float:
        """Map severity levels to 0-1 scale"""
        severity_map = {
            'mild': 0.3,
            'moderate': 0.6,
            'severe': 0.9,
            'suspicious': 0.8,
        }
        if hasattr(severity, 'value'):
            severity = severity.value
        return severity_map.get(str(severity).lower(), 0.5)

    def _identify_primary_emotions(
        self,
        emotional_points: List[EmotionalFrictionPoint]
    ) -> List[HumanEmotion]:
        """Identify the dominant emotional themes"""
        if not emotional_points:
            return []

        # Count emotion frequencies
        emotion_counts = {}
        for point in emotional_points:
            emotion_counts[point.human_emotion] = \
                emotion_counts.get(point.human_emotion, 0) + point.severity

        # Sort by weighted count
        sorted_emotions = sorted(
            emotion_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Return top 3 emotions
        return [emotion for emotion, _ in sorted_emotions[:3]]

    def _extract_micro_frustrations(
        self,
        emotional_points: List[EmotionalFrictionPoint],
        task_context: str
    ) -> List[str]:
        """
        Extract specific micro-frustrations

        These are the small annoyances that accumulate during task execution:
        - "Not sure if I'm doing this right"
        - "Too many options to consider"
        - "Might be missing something important"
        - "This is taking longer than expected"
        """
        frustrations = []

        emotion_to_micro_frustration = {
            HumanEmotion.UNCERTAINTY: [
                "Not confident in the chosen approach",
                "Multiple valid options, unclear which is best",
                "Worried about making the wrong choice"
            ],
            HumanEmotion.CONFUSION: [
                "The requirements aren't clear",
                "Too many variables to consider",
                "Don't know where to start"
            ],
            HumanEmotion.DOUBT: [
                "Not sure if this is correct",
                "Second-guessing the approach",
                "Might be missing edge cases"
            ],
            HumanEmotion.OVERWHELM: [
                "Too much information to process",
                "Can't keep track of all considerations",
                "Task is bigger than initially thought"
            ],
            HumanEmotion.ANXIETY: [
                "Worried about missing something critical",
                "Consequences of errors are significant",
                "Pressure to get this right"
            ],
            HumanEmotion.FRUSTRATION: [
                "This is harder than it should be",
                "Taking too long on small details",
                "Getting stuck on the same issues"
            ],
            HumanEmotion.TEDIUM: [
                "Repetitive steps are draining",
                "Losing focus on details",
                "Just want to get this done"
            ]
        }

        # Collect frustrations based on detected emotions
        seen_frustrations = set()
        for point in emotional_points:
            possible_frustrations = emotion_to_micro_frustration.get(
                point.human_emotion,
                ["Task complexity causing friction"]
            )

            # Weight by severity - more severe = more frustrations surface
            num_to_add = min(int(point.severity * 3), len(possible_frustrations))

            for frustration in possible_frustrations[:num_to_add]:
                if frustration not in seen_frustrations:
                    frustrations.append(frustration)
                    seen_frustrations.add(frustration)

        return frustrations[:7]  # Cap at 7 most significant

    def _calculate_cognitive_load(
        self,
        emotional_points: List[EmotionalFrictionPoint]
    ) -> CognitiveLoad:
        """Calculate overall cognitive load of the task"""
        if not emotional_points:
            return CognitiveLoad.LOW

        # Weight by severity
        load_values = {
            CognitiveLoad.LOW: 1,
            CognitiveLoad.MODERATE: 2,
            CognitiveLoad.HIGH: 3,
            CognitiveLoad.EXCESSIVE: 4
        }

        total_load = sum(
            load_values[point.cognitive_load] * point.severity
            for point in emotional_points
        )
        avg_load = total_load / len(emotional_points)

        if avg_load < 1.5:
            return CognitiveLoad.LOW
        elif avg_load < 2.5:
            return CognitiveLoad.MODERATE
        elif avg_load < 3.5:
            return CognitiveLoad.HIGH
        else:
            return CognitiveLoad.EXCESSIVE

    def _generate_support_recommendations(
        self,
        emotional_points: List[EmotionalFrictionPoint],
        primary_emotions: List[HumanEmotion]
    ) -> List[str]:
        """
        Generate recommendations for how to support the user

        Based on the emotional friction detected, suggest interventions
        """
        recommendations = []

        # Emotion-specific support
        support_map = {
            HumanEmotion.UNCERTAINTY:
                "Provide clear decision criteria and trade-off analysis",
            HumanEmotion.CONFUSION:
                "Break down into smaller, sequential steps",
            HumanEmotion.DOUBT:
                "Add validation checkpoints and confidence indicators",
            HumanEmotion.OVERWHELM:
                "Prioritize information and hide complexity initially",
            HumanEmotion.ANXIETY:
                "Highlight what's been validated and what's at risk",
            HumanEmotion.FRUSTRATION:
                "Automate repetitive parts and streamline workflow",
            HumanEmotion.TEDIUM:
                "Batch similar tasks and provide progress indicators"
        }

        for emotion in primary_emotions:
            rec = support_map.get(emotion)
            if rec and rec not in recommendations:
                recommendations.append(rec)

        # Add specific tactical recommendations
        high_severity_points = [p for p in emotional_points if p.severity > 0.6]

        if len(high_severity_points) > 3:
            recommendations.append(
                "Consider breaking this into multiple sessions to manage cognitive load"
            )

        if any(p.cognitive_load == CognitiveLoad.EXCESSIVE for p in emotional_points):
            recommendations.append(
                "High complexity detected - consider expert review or additional tooling"
            )

        # Always include the specific help needed from friction points
        for point in emotional_points[:3]:  # Top 3
            if point.help_needed not in recommendations:
                recommendations.append(point.help_needed)

        return recommendations

    def _estimate_time_saved(
        self,
        overall_difficulty: CognitiveLoad,
        num_micro_frustrations: int
    ) -> float:
        """
        Estimate hours saved by AI handling this task

        Based on:
        - Cognitive load (harder = more time)
        - Number of micro-frustrations (more = more delays)
        """
        base_time = {
            CognitiveLoad.LOW: 0.5,
            CognitiveLoad.MODERATE: 2.0,
            CognitiveLoad.HIGH: 5.0,
            CognitiveLoad.EXCESSIVE: 10.0
        }

        # Each micro-frustration adds 15-30 minutes of human time
        # (looking things up, second-guessing, revising)
        frustration_overhead = num_micro_frustrations * 0.25

        total_time = base_time[overall_difficulty] + frustration_overhead

        return round(total_time, 1)

    def format_for_user_display(
        self,
        profile: TaskEmotionalProfile
    ) -> Dict[str, any]:
        """
        Format emotional profile for user-friendly display

        Shows users what friction the AI is handling for them
        """
        return {
            "task_difficulty": profile.overall_difficulty.value,
            "time_saved_hours": profile.estimated_human_time_saved,
            "what_ai_is_handling": {
                "primary_challenges": [e.value for e in profile.primary_emotions],
                "micro_frustrations_addressed": profile.micro_frustrations,
                "friction_points_managed": len(profile.friction_points)
            },
            "support_provided": profile.support_recommendations,
            "user_message": self._generate_empathetic_message(profile)
        }

    def _generate_empathetic_message(
        self,
        profile: TaskEmotionalProfile
    ) -> str:
        """Generate an empathetic message about the task difficulty"""
        if profile.overall_difficulty == CognitiveLoad.LOW:
            return "This is a straightforward task - AI is handling the basics efficiently."

        if profile.overall_difficulty == CognitiveLoad.MODERATE:
            frustrations = ", ".join(profile.micro_frustrations[:2])
            return (
                f"This task has moderate complexity. The AI is managing challenges like: "
                f"{frustrations}. This would typically take "
                f"{profile.estimated_human_time_saved} hours of focused human effort."
            )

        if profile.overall_difficulty == CognitiveLoad.HIGH:
            return (
                f"This is a cognitively demanding task with {len(profile.friction_points)} "
                f"friction points detected. The AI is handling the mental load that would "
                f"typically cause {', '.join([e.value for e in profile.primary_emotions[:2]])}. "
                f"Estimated time saved: {profile.estimated_human_time_saved} hours."
            )

        # EXCESSIVE
        return (
            f"This is a highly complex task. The AI system detected {len(profile.micro_frustrations)} "
            f"micro-frustrations that would accumulate during human execution. "
            f"By distributing this across multiple specialized models, we're managing "
            f"the cognitive load that would take an expert {profile.estimated_human_time_saved}+ hours. "
            f"Processing time reflects the genuine difficulty of this request."
        )

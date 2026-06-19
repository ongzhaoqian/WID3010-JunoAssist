from src.core.models import EmotionState


class BreakRecommender:
    def recommend(self, emotion: EmotionState) -> str:
        if emotion == EmotionState.SADNESS:
            return "You seem a little low-energy or sad. I recommend a 5-minute reset before continuing."
        if emotion == EmotionState.FEAR:
            return "You seem stressed, worried, or under pressure. Let us prioritise the nearest deadline and start with a short study session."
        if emotion == EmotionState.ANGER:
            return "You seem angry or frustrated. Try pausing briefly, then break the task into smaller steps."
        if emotion == EmotionState.DISGUST:
            return "You seem uncomfortable with something. A short reset may help before returning to the task."
        if emotion == EmotionState.SURPRISE:
            return "You seem surprised. Take a moment to re-orient, then decide the next step calmly."
        if emotion == EmotionState.HAPPINESS:
            return "You seem to be doing well. This is a good time to continue your current task."
        if emotion == EmotionState.UNKNOWN:
            return "I cannot read a clear emotion yet. I can still help you check your schedule, set a timer, or plan your next task."
        return "You seem neutral. I can help you check your schedule, set a timer, or plan your next task."

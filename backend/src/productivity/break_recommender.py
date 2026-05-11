from src.core.models import EmotionState


class BreakRecommender:
    def recommend(self, emotion: EmotionState) -> str:
        if emotion == EmotionState.TIRED:
            return "You seem a little tired. I recommend a 5-minute break before continuing."
        if emotion == EmotionState.STRESSED:
            return "You seem a bit stressed. Let us prioritise the nearest deadline and start with a short study session."
        if emotion == EmotionState.FRUSTRATED:
            return "You seem frustrated. Try pausing briefly, then break the task into smaller steps."
        if emotion == EmotionState.HAPPY:
            return "You seem to be doing well. This is a good time to continue your current task."
        return "You seem neutral. I can help you check your schedule, set a timer, or plan your next task."

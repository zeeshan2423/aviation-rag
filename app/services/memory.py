class ChatMemory:
    def __init__(self, max_turns=3):
        self.history = []
        self.max_turns = max_turns

    def add(self, user_query, response):
        self.history.append({
            "user": user_query,
            # 🔥 compress response
            "assistant": response[:200]  # keep only key part
        })

        self.history = self.history[-self.max_turns:]

    def get_context(self):
        context = ""

        for turn in self.history:
            context += f"User: {turn['user']}\n"
            context += f"Assistant: {turn['assistant']}\n\n"

        return context.strip()
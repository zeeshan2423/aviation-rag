from app.services.memory import ChatMemory

memory_store = {}

def get_memory(session_id: str):
    if session_id not in memory_store:
        memory_store[session_id] = ChatMemory()
    return memory_store[session_id]
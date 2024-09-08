from uuid import uuid4

from chat_cli.utils.chat import ChatSession


class ChatSessionManager:
    def __init__(self):
        self.sessions = {}
        self.current_session = None

    def new_session(self) -> str:
        session_id = str(uuid4())
        self.sessions[session_id] = ChatSession()
        self.current_session = session_id
        return session_id

    def get_current_session(self) -> ChatSession | None:
        if self.current_session:
            return self.sessions[self.current_session]

    def list_sessions(self) -> list:
        return list(self.sessions.keys())

    def select_session(self, session_id) -> bool:
        if session_id in self.sessions:
            self.current_session = session_id
            return True
        return False

    def delete_session(self, session_id) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            if self.current_session == session_id:
                self.new_session()
            return True
        return False

    def toggle_tool(self) -> bool:
        current_session = self.get_current_session()
        if current_session:
            current_session.enable_tool = not current_session.enable_tool
            return current_session.enable_tool
        return False

    def change_model(self, model):
        current_session = self.get_current_session()
        if current_session:
            current_session.model = model

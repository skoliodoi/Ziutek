"""
Klasa ConversationData służy do zapisywania przez bota wybranych danych dotyczących użytkownika podczas tej rozmowy, w tym wypadku jego imienia
"""


class UserProfile:
    def __init__(self,
                 work_started: bool = False,
                 work_start_time: str = None,
                 work_stop_time: str = None,
                 name: str = None,
                 check_check: str = "",
                 project: str = None):
        self.work_started = work_started
        self.name = name
        self.project = project
        self.work_start_time = work_start_time
        self.work_stop_time = work_stop_time
        self.check_check = check_check

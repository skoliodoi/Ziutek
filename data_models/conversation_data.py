import datetime

"""
Klasa ConversationData służy do zapisywania szczegółów konwersacji podczas rozmowy
"""


class ConversationData:
    def __init__(
        self,
        timestamp: str = None,
        channel_id: str = None,
        asked_to_go_for_a_break: bool = False,
        asked_to_add_to_queue: bool = False,
        break_requested_at: datetime = None,
        went_on_a_break: bool = False,
        check: str = ''
    ):
        self.timestamp = timestamp
        self.channel_id = channel_id
        self.asked_to_go_for_a_break = asked_to_go_for_a_break
        self.asked_to_add_to_queue = asked_to_add_to_queue
        self.break_requested_at: break_requested_at
        self.went_on_a_break = went_on_a_break
        self.check = check

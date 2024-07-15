from config import DefaultConfig
from bots.bot_functions.helper_functions import check_kwarg_key
from responses.cards import text_block_template

config = DefaultConfig()


def send_to_break_card(data, name, was_asked_id):
    card_text = f"Ok, wygląda na to że możesz iść na przerwę na projekcie {name}!"
    card_actions = [
        {
            'type': "Action.Submit",
            "title": "Dobra, to idę!",
            "data": {
                "action": "go_on_break",
                "project_id": data['project'],
                "user_id": data['agent'],
                "was_asked_id": was_asked_id
            }
        },
        {
            'type': "Action.Submit",
            "title": "Muszę zrezygnować :(",
            "data": {
                "action": "decline_break",
                "user_declined": True,
                "project": data['project'],
                "agent": data['agent'],
                "was_asked_id": was_asked_id
            }
        },
    ]

    card = ({
        "$schema": config.CARD_SCHEMA,
        "version": config.CARD_VERSION,
        "type": "AdaptiveCard",
        "body": [
                text_block_template(card_text)
        ],
        "actions": card_actions
    })
    return card


def remove_from_queque_card():
    card_header = "Nie uzyskałem odpowiedzi na czas..."
    card_text = "Niestety muszę usunąć Cię z kolejki :("

    card = ({
        "$schema": config.CARD_SCHEMA,
        "version": config.CARD_VERSION,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_header),
            text_block_template(card_text)
        ],
    })
    return card


def i_told_on_you_card():
    card_text_primary = "Przykro mi, ale wciąż nie uzyskałem od Ciebie odpowiedzi, a inni mogą czekać na swoją kolej!"
    card_text_secondary = "W związku z tym musiałem powiadomić twojego lidera :("
    card_text_tertiary = "Wiem, wiem, zakaz sześćdziesiony, ale co ja mogę?"
    card = ({
            "$schema": config.CARD_SCHEMA,
            "version": config.CARD_VERSION,
            "type": "AdaptiveCard",
            "body": [
                text_block_template(card_text_primary),
                text_block_template(card_text_secondary, "medium"),
                text_block_template(card_text_tertiary, "small")
            ],
            })
    return card


def removed_remotely_card():
    card_text_primary = "Wygląda na to, że ktoś zdalnie usunął Cię z przerwy!"
    card_text_secondary = "Dla dobra nas wszystkich załóżmy że to Twój lider."
    card = ({
            "$schema": config.CARD_SCHEMA,
            "version": config.CARD_VERSION,
            "type": "AdaptiveCard",
            "body": [
                text_block_template(card_text_primary),
                text_block_template(card_text_secondary, "medium"),
            ],
            })
    return card


def break_end_reminder_card(project_id, was_reminded_id):
    card_text_primary = "Hej, według mojego zegara niestety skończył ci się czas przerwy!"
    card_text_secondary = "Z tego co widzę wyczerpałeś swój czas przerwy, a nie zalogowałeś się z powrotem do pracy. Zdarza się!"
    card_text_tertiary = "Chcesz to zrobić teraz?"

    actions = [
        {
            "type": "Action.Submit",
            "title": "Ups, faktycznie, wracam!",
            "data": {
                "action": 'return_from_break',
                'id': project_id,
                'quick_break': False,
                'was_reminded_id': was_reminded_id
            }
        }
    ]

    card = ({
            "$schema": config.CARD_SCHEMA,
            "version": config.CARD_VERSION,
            "type": "AdaptiveCard",
            "body": [
                text_block_template(card_text_primary),
                text_block_template(card_text_secondary, "medium"),
                text_block_template(card_text_tertiary, "medium"),
            ],
            "actions": actions
            })
    return card


def user_problem_card(recipient, problem_number, project_id, break_too_long_id, was_reminded_id, leader_asked_id):
    name = recipient['first_name']
    last_name = recipient['last_name']
    email = recipient['email']
    user_id = recipient['id']
    user_conversation_id = recipient['teams_conversation_id'] if recipient['teams_conversation_id'] else None
    reminded = was_reminded_id if was_reminded_id else None
    leader_asked = leader_asked_id if leader_asked_id else None
    break_too_long = break_too_long_id if break_too_long_id else None
    actions = [
        {
            'type': 'Action.Submit',
            'title': 'Usuń agenta z przerwy',
            'data': {
                'action': 'remove_from_break',
                'remote': True,
                'user_conversation_id': user_conversation_id,
                'user_id': user_id,
                'project_id': project_id,
                'first_name': name,
                "last_name": last_name,
                "reminded": reminded,
                "leader_asked": leader_asked,
                "break_too_long": break_too_long
            }
        },
        {
            'type': 'Action.Submit',
            'title': 'Nie rób nic',
            'data': {
                'action': 'decline_break',
                "reminded": reminded,
                "leader_asked": leader_asked,
                "break_too_long": break_too_long,
            }
        },
    ]
    card_text_primary = f"Nie mogę skontaktować się z użytkownikiem {name} {last_name} ({email})"
    card_text_tertiary = "W związku z tym usuwam go z kolejki, żeby nie zajmować miejsca innym."
    if problem_number == 1:
        card_text_primary = f"Nie mogę wysłać na przerwę użytkownika {name} {last_name} ({email})!"
        card_text_secondary = f"Powód jest prosty - według moich informacji, {name} już jest na przerwie!"
        actions = []
    if problem_number == 2:
        card_text_secondary = f"Powodem jest najpewniej błędne conversation ID - czy {name} na pewno mi się przedstawił zanim został dodany do kolejki?"
        actions = []
    if problem_number == 3:
        card_text_secondary = f"Powodem jest najpewniej błędne conversation ID - czy {name} na pewno mi się przedstawił zanim został wysłany na przerwę?"
        card_text_tertiary = "Co chcesz zrobić w związku z tym?"
    if problem_number == 4:
        card_text_primary = f"{name} {last_name} nie wrócił z przerwy!"
        card_text_secondary = f" Nie lubię donosić, ale niestety użytkownik {name} {last_name} ({email}) nie wrócił z przerwy"
        card_text_tertiary = "Co chcesz zrobić w związku z tym?"

    card = ({
        "$schema": config.CARD_SCHEMA,
        "version": config.CARD_VERSION,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_text_primary),
            text_block_template(card_text_secondary, "medium"),
            text_block_template(card_text_tertiary, "medium")
        ],
        "actions": actions
    })
    return card

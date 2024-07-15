from botbuilder.schema import HeroCard, CardImage
from botbuilder.core import CardFactory
from bots.bot_functions.helper_functions import check_kwarg_key
from config import DefaultConfig


config = DefaultConfig()
card_schema = config.CARD_SCHEMA
card_version = config.CARD_VERSION


def text_block_template(card_text, text_size="large", alignment="center"):
    return {
        "type": "TextBlock",
        "text": card_text,
        "wrap": True,
        "size": text_size,
        "horizontalAlignment": alignment
    }


def advice_card(text):
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(text, "medium")
        ],
    })
    return card


def already_card(info):
    card_text = f"Z tego co widzę jesteś już dodany do kolejki na przerwę na projekcie {info}! Trochę cierpliwości!"
    card_subtext = "Obiecuję, że dam znać kiedy tylko będzie Twoja kolej!"
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_text),
            text_block_template(card_subtext, "medium")
        ],
    })
    return card


def check_if_break_allowed_card(break_allowed, name, id, agent_id):
    if break_allowed:
        card_text = f"Ok, wygląda na to że możesz iść na przerwę na projekcie {name}!"
        card_actions = [
            {
                'type': "Action.Submit",
                "title": "Dobra, to idę!",
                "data": {
                    "action": "go_on_break",
                    "name": name,
                    "project_id": id
                }
            },
            {
                'type': "Action.Submit",
                "title": "Muszę zrezygnować :(",
                "data": {
                    "action": "decline_break",
                    "user_declined": True,
                    "project": id,
                    "agent": agent_id
                }
            },
        ]
    else:
        card_text = "Kurczę, wygląda na to że teraz nie możesz iść na przerwę!"
        card_actions = [
            {
                'type': "Action.Submit",
                "title": "W takim razie zapisz mnie w kolejce.",
                "data": {
                    "action": "add_to_queque",
                    "name": name,
                    "id": id
                }
            },
            {
                'type': "Action.Submit",
                "title": "W takim razie odpuszczam przerwę!",
                "data": {
                    "action": "decline_break"
                }
            },
        ]
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_text)
        ],
        "actions": card_actions
    })
    return card


def missing_data_card(missing_data, email=None):
    if missing_data == "no_email":
        card_title = f"Wygląda na to, że twój email {email} nie jest dodany do mojej bazy danych"
    else:
        card_title = "Wygląda na to, że nie jesteś dodany do żadnego projektu!"
    card_secondary = "W tej sytuacji raczej niewiele mogę dla ciebie zrobić :("
    card_tertiary = "Spróbuj porozmawiać z przełożonym i daj mu znać o tym problemie!"
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_title),
            text_block_template(card_secondary, "medium"),
            text_block_template(card_tertiary, "medium")
        ]
    })
    return card


def leader_card(initial, options, monitored_projects, username):
    card_text = "Co jeszcze mogę dla Ciebie zrobić?"
    card_body = [
        text_block_template(card_text)
    ]

    if initial:
        card_header = "Fiu fiu, widzę że mam  do czynienia z grubą szychą!"
        card_text = "Co mogę dla Ciebie zrobić?"
        card_body = [
            text_block_template(card_header),
            text_block_template(card_text, "medium")
        ]
    if options:
        card_text = f"Co mogę dla Ciebie zrobić, {username}?"
        card_body = [
            text_block_template(card_text)
        ]
    actions = [
        {
            "type": "Action.Submit",
            "title": "Monitoruj przerwy",
            "data": {
                "action": "monitorowanie"
            }
        },
        {
            "type": "Action.Submit",
            "title": "Pokaż mi kolejkę",
            "data": {
                "action": "check_queque"
            }
        },
        {
            "type": "Action.Submit",
            "title": "Pokaż mi aktywne przerwy",
            "data": {
                "action": "check_active_breaks"
            }
        },
        {
            "type": "Action.Submit",
            "title": "Pokaż status",
            "data": {
                "action": "show_status",
                "projects": monitored_projects
            }
        },
        {
            "type": "Action.Submit",
            "title": "Odśwież moje dane",
            "data": {
                "action": "refresh_data"
            }
        }
    ]

    if len(monitored_projects) > 0:
        actions.insert(1, {
            "type": "Action.Submit",
            "title": "Skończ monitorowanie",
            "data": {
                "action": "stop_monitorowanie",
                "projects": monitored_projects
            }
        })
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": card_body,
        "actions": actions
    })
    return card


def agent_options_card(initial, options, is_on_break, username, quick_breaks, queques, not_in_queque, user_id):
    card_text = "Co jeszcze mogę dla Ciebie zrobić?"
    if initial:
        card_text = "Co mogę dla Ciebie zrobić?"
    if options:
        card_text = f"Co mogę dla Ciebie zrobić, {username}?"
    card_body = [
        text_block_template(card_text)
    ]
    if is_on_break['is_on_break']:
        card_info_text = f"Według mojej wiedzy w tym momencie jesteś na przerwie na projekcie {is_on_break['project_name']}"
        card_body.append(
            text_block_template(card_info_text)
        )

        actions = [
            {
                'type': "Action.Submit",
                'title': "Wróć z przerwy",
                'data': {
                    'action': "return_from_break",
                    'id': is_on_break['project'],
                    'quick_break': False
                }
            }
        ]
        if is_on_break['quick_break']:
            actions[0]['data']['quick_break'] = True
        else:
            actions.append(
                {
                    'type': "Action.Submit",
                    'title': "Pokaż czas przerwy",
                    'data': {
                        'action': "show_my_break_time",
                        'project_id': is_on_break['project'],
                        'user_id': user_id,
                    }
                })

            if len(not_in_queque) > 0:
                actions.append({
                    'type': "Action.Submit",
                    'title': "Zapisz mnie w kolejce",
                    'data': {
                        'action': "add_to_queque",
                        'projects': not_in_queque
                    }
                })
            if len(queques) > 0:
                actions.append({
                    'type': "Action.Submit",
                    'title': "Wypisz mnie z kolejki",
                    'data': {
                        'action': "remove_from_queque",
                        'projects': queques
                    }
                },)
    else:
        actions = [
            {
                'type': "Action.Submit",
                'title': "Zapisz mnie w kolejce",
                'data': {
                    'action': "add_to_queque",
                    'projects': not_in_queque
                }
            },
            {
                'type': "Action.Submit",
                'title': "Sprawdź kolejkę na przerwę",
                'data': {
                    'action': "check_queque"
                }
            },
            {
                'type': "Action.Submit",
                'title': "Pokaż historię moich przerw z dzisiaj",
                'data': {
                    'action': "show_break_time"
                }
            },
            {
                "type": "Action.Submit",
                "title": "Odśwież moje dane",
                "data": {
                    "action": "refresh_data"
                }
            },
            # {
            #     'type': "Action.Submit",
            #     'title': "Chcę iść na dłuższą przerwę",
            #     'data': {
            #         'action': "requires_break"
            #     }
            # },
        ]

        if len(not_in_queque) < 1:
            for a in actions[:]:
                if a['data']['action'] == 'add_to_queque':
                    actions.remove(a)

        if len(queques) > 0:
            actions.insert(1, {
                'type': "Action.Submit",
                'title': "Wypisz mnie z kolejki",
                'data': {
                    'action': "remove_from_queque",
                    'projects': queques,
                }
            })

        if len(quick_breaks) > 0:
            actions.append({
                'type': "Action.Submit",
                'title': "Szybka przerwa raz, proszę!",
                'data': {
                    'action': "quick_break",
                    'quick_breaks': quick_breaks
                }
            })

    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": card_body,
        "actions": actions
    })
    return card


def break_history_card(data, name, is_leader):
    card_header = f"Wygląda na to, że dzisiaj nie byłeś jeszcze na żadnej przerwie na projekcie {name}!"
    card_text_body = "Może czas trochę odpocząć?"
    if len(data['details']) > 0:
        card_header = "Twój łączny czas przerw"
        if is_leader:
            card_header = "Łączny czas przerw użytkownika"
        card_header += f" na projekcie {name} z dzisiaj to {data['total']}"
        card_text_body = "Poniżej szczegóły wszystkich przerw: \n\n"
        detail_num = 0
        for b in data['details']:
            detail_num += 1
            card_text_body += f"{detail_num}) Początek przerwy: {b['start']}. Koniec przerwy: {b['end']}.\n\n- Czas tej przerwy: {b['duration_str']}\n\n"
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_header),
            text_block_template(
                card_text_body, text_size="medium", alignment="left")
        ]
    })
    return card


def check_queque_card(queque_data, project_id, is_leader, project_name):
    empty_queque = queque_data['queque_length'] == 0
    actions = []
    if empty_queque:
        card_header = f"W tym momencie kolejka na projekcie {project_name} jest pusta!"
    else:
        card_header = f"Liczba agentów w kolejce na projekcie {project_name}: {queque_data['queque_length']}"
    if is_leader:
        if empty_queque:
            card_text_body = "Twoje pracowite mrówki nawet nie myślą o przerwie! Nie wiem czy to zdrowo..."
        else:
            card_text_body = "Kolejka wygląda następująco: \n\n"
            for q in queque_data['queque_details']:
                card_text_body += f"Numer {q['order']} - {q['full_name']}\n\n"
            actions = [
                {
                    "type": "Action.Submit",
                    "title": "Chcę usunąć użytkownika z kolejki",
                    "data": {
                            'action': "remove_from_queque",
                            'projects': [project_id],
                            'agents': queque_data['queque_details']
                    }
                }
            ]
    else:
        if queque_data['place']:
            card_header = f"Długość kolejki na projekcie {project_name} wynosi: {queque_data['queque_length']}"
            card_text_body = f"Jesteś w tej kolejce. Numer Twojego miejsca: {queque_data['place']}"
        else:
            card_text_body = "Czy mam cię zapisać w kolejce na przerwę?"
            actions = [
                {
                    "type": "Action.Submit",
                    "title": "Tak, proszę!",
                    "data": {
                        'action': "add_to_queque",
                        'id': project_id
                    }
                },
                {
                    "type": "Action.Submit",
                    "title": "Nie trzeba, dziękuję",
                    "data": {
                        'action': "decline_break",
                    }
                },
            ]

    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_header),
            text_block_template(card_text_body, "medium"),
        ],
        "actions": actions
    })
    return card


def check_active_breaks_card(breaks):
    if breaks:
        breaks_length = len(breaks)
        card_header = f"Liczba osób na przerwie: {breaks_length}"
        card_text_body = "Są to: \n\n"
        detail_num = 0
        for b in breaks:
            detail_num += 1
            break_type = "szybka" if b['quick_break'] else "zwykła"
            card_text_body += f"{detail_num}) {b['full_name']}. Początek przerwy: {b['start_hour']}.\n\n - Rodzaj przerwy: {break_type}.\n\n"
    else:
        card_header = "W tym momencie nikogo nie ma na przerwie!"
        card_text_body = "Wszyscy ciężko pracują!"
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_header),
            text_block_template(card_text_body, "medium", "left")
        ]
    })
    return card


def confirmation_card(name, id, missing_users, too_many_users=False):
    card_header = "Z tego co widzę brakuje mi danych części uczestników projektu! Widocznie się ze mną nie przywitali :("
    card_text_body = "To znaczy, że kiedy nadejdzie ich kolej na przerwę nie będę mógł ich o tym poinformować!"
    card_text_question = "Czy mimo tego chcesz kontynuować?"
    if not too_many_users:
        missing_users_text = "Brakujący użytkownicy to: \n\n"
        for mu in missing_users:
            missing_users_text += f"{mu['first_name']} {mu['last_name']} ({mu['email']})\n\n"
    else:
        missing_users_text = "Brakujących użytkowników jest tak wielu, że nie zmieścili się w tej wiadomości!"
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_header),
            text_block_template(card_text_body, "medium"),
            text_block_template(missing_users_text, "medium"),
            text_block_template(card_text_question, "medium")
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "Tak, kontynuuj proszę",
                "data": {
                    "action": "confirm",
                    "confirmation_type": "monitorowanie",
                    "name": name,
                    "id": id
                }
            },
            {
                "type": "Action.Submit",
                "title": "Zaczekaj",
                "data": {
                    "action": "decline_break",
                    "confirmation_type": "monitorowanie"
                }
            }
        ]
    })
    return card


def response_card(project_name, is_leader=False):
    if is_leader:
        response_text = f"monitoruję przerwy na projekcie {project_name}"
    else:
        response_text = f"zapisuję cię w kolejce na przerwę na projekcie {project_name}"

    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(f"Zrozumiałem, {response_text}")
        ]
    })
    return card


def project_card(projects_to_check, **kwargs):
    break_answer = check_kwarg_key(kwargs, 'regular_break')
    quick_break_answer = check_kwarg_key(kwargs, 'quick_break')
    break_history_request_answer = check_kwarg_key(
        kwargs, 'break_history_request')
    remove_from_queque_answer = check_kwarg_key(kwargs, 'remove_from_queque')
    add_to_queque_answer = check_kwarg_key(kwargs, 'add_to_queque')
    queque_list_answer = check_kwarg_key(kwargs, 'check_queque')
    check_breaks_answer = check_kwarg_key(kwargs, 'check_breaks')
    check_active_breaks_answer = check_kwarg_key(kwargs, 'check_active_breaks')
    stop_checking_breaks_answer = check_kwarg_key(kwargs, 'stop_checking')
    card_text = "Na którym z projektów "
    if break_answer:
        card_text += "chcesz iść na przerwę?"

    if add_to_queque_answer:
        if kwargs['is_leader']:
            card_text += "chcesz dopisać użytkownika do kolejki?"
        else:
            card_text += "mam cię dopisać do kolejki?"

    if break_history_request_answer:
        card_text += "chcesz sprawdzić historię przerw?"

    if queque_list_answer:
        card_text += "chcesz sprawdzić kolejkę?"

    if remove_from_queque_answer:
        card_text += "chcesz się wypisać z kolejki?"

    if check_breaks_answer:
        card_text += "chcesz monitorować przerwy?"

    if check_active_breaks_answer:
        card_text += "chcesz sprawdzić aktywne przerwy?"

    if quick_break_answer:
        card_text += "chcesz szybko śmignąć na przerwę?"

    if stop_checking_breaks_answer:
        card_text += "mam przestać monitorować przerwy?"

    actions = [{
        "type": "Action.Submit",
        "title": p['name'],
        "data": {
            "action": "project_chosen",
            'name': p['name'],
            'id': p['id'],
            'break': break_answer,
            'quick_break': quick_break_answer,
            'add_to_queque': add_to_queque_answer,
            'remove_from_queque': remove_from_queque_answer,
            'break_history_request': break_history_request_answer,
            'queque_list': queque_list_answer,
            'check_breaks': check_breaks_answer,
            'check_active_breaks': check_active_breaks_answer,
            'stop_checking_breaks': stop_checking_breaks_answer
        }
    } for p in projects_to_check]

    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_text)
        ],
        "actions": actions
    })
    return card


def intro_card(user=None, initial=False):
    if user:
        intro_title = f"Cześć {user}!"
    else:
        intro_title = "Cześć, tajemniczy nieznajomy!"
    intro_text = "Daj mi chwilkę, żeby wszystko posprawdzać..."

    card = HeroCard(
        title=intro_title,
        text=intro_text,
        images=[CardImage(
            url="https://res.cloudinary.com/davhlcjqq/image/upload/v1702237739/ziutek/ziutek-hello_ssllti.png")]
    )

    return card


def break_card(project_id):
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            {
                "type": "Image",
                "url": "https://res.cloudinary.com/davhlcjqq/image/upload/v1702237757/ziutek/ziutek-beach_ndjfjb.png",
                "size": "stretch",
            },
            text_block_template("Ok, droga wolna!"),
            text_block_template("Baw się dobrze!", "medium")
        ],

    })
    return card


def queue_card(name, send_to_back):
    title = "Ok, zapisałem Cię w kolejce na przerwę "
    if send_to_back:
        title = "Ok, przesunąłem cię na koniec kolejki "
    title += f"na projekcie {name}."
    card = HeroCard(
        title=title,
        subtitle="Dam znać kiedy będzie Twoja kolej!",
        images=[CardImage(
            url="https://res.cloudinary.com/davhlcjqq/image/upload/v1702224522/ziutek/ziutek-queue_egad00.png")]
    )

    return card


def back_to_work_card():
    card = HeroCard(
        title="Przerwa skończona",
        subtitle="Owocnej pracy!",
        images=[CardImage(
            url="https://res.cloudinary.com/davhlcjqq/image/upload/v1702224521/ziutek/ziutek-desk_qupfit.png")]
    )

    return card


def remote_break_end_card(name, last_name, gender):
    card_text = f"Użytkownik {name} {last_name} został wypisany z przerwy."
    if gender == 'F':
        card_text = f"Użytkowniczka {name} {last_name} została wypisana z przerwy."
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_text)
        ],

    })
    return card


def back_to_queque_card(name, id, queque_data, break_data, skip_project_check):
    card_header = f"Czy chcesz od razu zapisać się ponownie w kolejce na przerwę na projekcie {name}?"
    if queque_data['queque_length'] == 0:
        card_text = "W tym momencie kolejka jest pusta!"
    else:
        card_text = f"Liczba agentów w kolejce: {queque_data['queque_length']}"
    end_hour = break_data['range_details']['end_hour']
    card_footer = f"Przerwa jest dostępna do {end_hour}"
    actions = [
        {
            "type": "Action.Submit",
            "title": "Tak, zapisz mnie ponownie",
            "data": {
                "action": "add_to_queque",
                "id": id
            }
        },
        {
            "type": "Action.Submit",
            "title": "Nie trzeba, dzięki",
            "data": {
                "action": "decline_break"
            }
        }
    ]

    if not skip_project_check:
        actions.append({
            "type": "Action.Submit",
            "title": "Nie, ale zapisz mnie w kolejce na innym projekcie",
            "data": {
                "action": "add_to_queque",
                "exclude_id": id
            }
        })
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_header),
            text_block_template(card_text),
            text_block_template(card_footer)
        ],
        "actions": actions

    })
    return card


def error_card(main_text, secondary_text):
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(main_text),
            text_block_template(secondary_text, "medium")
        ],
    })
    return card


def user_problem_card(name, last_name, email, problem_number):
    if problem_number == 1:
        card_text_primary = f"Nie mogę wysłać na przerwę użytkownika {name} {last_name} ({email})!"
        card_text_secondary = f"Powód jest prosty - według moich informacji, {name} już jest na przerwie!"
    if problem_number == 2:
        card_text_primary = f"Nie mogę skontaktować się z użytkownikiem {name} {last_name} ({email})"
        card_text_secondary = f"Powodem jest najpewniej błędne conversation ID - czy {name} na pewno mi się przedstawił zanim został dodany do kolejki?"
    card_text_tertiary = "W związku z tym usuwam go z kolejki, żeby nie zajmować miejsca innym."
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_text_primary),
            text_block_template(card_text_secondary, "medium"),
            text_block_template(card_text_tertiary, "medium"),
        ],
    })
    return card


def data_saved_card():
    card_header = "Twoje dane zostały zapisane po stronie serwera."
    card_text = "Wydaje się, że możesz teraz bez przeszkód korzystać z moich usług żeby pójść na przerwę!"
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_header),
            text_block_template(card_text, "medium")
        ],
    })
    return card


def removed_from_queque_card(project_name, agent_name, agent_gender, multiple, not_in_queque):
    card_text = "Zrozumiano, usunąłem Cię z kolejki na przerwę"
    if not_in_queque:
        card_text = "Zabawne, tak naprawdę to nie było Cię w kolejce"
    if multiple:
        card_text = "Agenci zostali usunięci z kolejki"
    if agent_name and agent_gender:
        is_male = agent_gender == 'M'
        card_text = f"{agent_name} {'został' if is_male else 'została'} usunięt{'y' if is_male else 'a'} z kolejki"
    card_text += f" na projekcie {project_name}!"
    if not_in_queque:
        card_text += " W takim razie umówmy się że wypisałem Cię zgodnie z oczekiwaniami ;)"
    card = CardFactory.adaptive_card({
        "$schema": card_schema,
        "version": card_version,
        "type": "AdaptiveCard",
        "body": [
            text_block_template(card_text)
        ],
    })
    return card


def agents_choice_card(agents, project):
    choices = [{'title': a['full_name'],
                'value': f"{str(a['agent_id'])};{a['full_name']};{a['gender']}"} for a in agents]
    card = CardFactory.adaptive_card({
        "type": "AdaptiveCard",
        "version": card_version,
        "$schema": card_schema,
        "body": [
            {
                "type": "TextBlock",
                "size": "Medium",
                "weight": "Bolder",
                "text": "Kogo chcesz usunąć?"
            },
            {
                "type": "Input.ChoiceSet",
                "choices": choices,
                "id": "people-picker",
                "isMultiSelect": True
            }
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "Zatwierdź wybór",
                "data": {
                    'action': 'agents_chosen',
                    "people-picker": "{people-picker}",
                    'project': project
                }
            }
        ],

    })
    return card


def decline_break_choice_card(data):
    actions = [
        {
            'type': "Action.Submit",
            'title': "Usuń mnie z kolejki",
            'data': {
                'action': 'remove_from_queque',
                'delete_completely': True,
                'user_data': data
            }
        },
        {
            'type': "Action.Submit",
            'title': "Przesuń mnie na koniec kolejki!",
            'data': {
                'action': 'remove_from_queque',
                'delete_completely': False,
                'user_data': data
            }
        },
    ]
    card = CardFactory.adaptive_card({
        "type": "AdaptiveCard",
        "version": card_version,
        "$schema": card_schema,
        "body": [
            text_block_template("Jasna sprawa!"),
            text_block_template(
                "Mam cię przesunąć na koniec kolejki czy usunąć Cię całkowicie?", "medium"),
        ],
        "actions": actions

    })
    return card


def check_current_break_card(break_time, more_than_allowed, project_id):
    card_header = f"Czas twojej obecnej przerwy to {break_time['duration_str']}"
    if more_than_allowed:
        card_body = "Niestety, dozwolony czas trwania przerwy został przekroczony! Na Twoim miejscu wracałbym do pracy!"
    else:
        card_body = "Na luzie, masz jeszcze trochę czasu dla siebie :)"
    actions = [
        {
            'type': "Action.Submit",
            'title': "Wracam do pracy",
            'data': {
                    'action': 'return_from_break',
                    'id': project_id,
                    'quick_break': False,
            }
        }
    ]
    card = CardFactory.adaptive_card({
        "type": "AdaptiveCard",
        "version": card_version,
        "$schema": card_schema,
        "body": [
            text_block_template(card_header),
            text_block_template(card_body, "medium"),
        ],
        "actions": actions

    })
    return card


def timer_stopped_card(name):
    card_header = f"Dobra, skończyłem monitorowanie przerw na projekcie {name}!"
    card_text = "W sumie i dobrze, zaczynałem się już robić zmęczony :)"
    card = CardFactory.adaptive_card({
        "type": "AdaptiveCard",
        "version": card_version,
        "$schema": card_schema,
        "body": [
                text_block_template(card_header),
                text_block_template(card_text),
        ],
    })
    return card


def maruda_card():
    card_header = "A kto to przyszedł?"
    card_text = "Pan maruda, niszczyciel dobrej zabawy, pogromca uśmiechów dzieci!"
    card = CardFactory.adaptive_card({
        "type": "AdaptiveCard",
        "version": card_version,
        "$schema": card_schema,
        "body": [
            text_block_template(card_header),
            text_block_template(card_text),
        ],
    })
    return card


def monitoring_status_card(projects, gender='M'):
    alignment = "center"
    if len(projects) == 0:
        card_header = "W tym momencie nie monitoruję żadnych przerw!"
        card_text = "Odpoczywam sobie, pełen chill :)"
    else:
        card_recipient = "Kierowniczko kochana" if gender == 'F' else "Kierowniku złoty"
        card_header = f"{card_recipient}, ciężko pracuję!"
        if len(projects) == 1:
            card_text = f"Monitoruję przerwy na projekcie {projects[0]}"
        if len(projects) > 1:
            alignment = "left"
            card_text = "Mam ręce pełne roboty, monitoruję przerwy na następujących projektach: \n\n"
            detail_num = 0
            for p in projects:
                detail_num += 1
                card_text += f"{detail_num}) {p}\n\n"

    card = CardFactory.adaptive_card({
        "type": "AdaptiveCard",
        "version": card_version,
        "$schema": card_schema,
        "body": [
            text_block_template(card_header),
            text_block_template(card_text, "medium", alignment),
        ],
    })
    return card

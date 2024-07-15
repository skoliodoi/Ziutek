from botbuilder.core import MessageFactory, CardFactory
from responses.cards import maruda_card, monitoring_status_card, check_queque_card, queue_card, project_card, leader_card, confirmation_card, response_card, missing_data_card, agent_options_card, check_if_break_allowed_card, already_card, break_card, error_card, back_to_work_card, intro_card, user_problem_card, data_saved_card, break_history_card, back_to_queque_card, check_active_breaks_card, agents_choice_card, remote_break_end_card, decline_break_choice_card, check_current_break_card, removed_from_queque_card, advice_card, timer_stopped_card
from bots.bot_functions.api_calls import check_queque, check_break_range, get_projects, get_project_details, get_user, check_if_on_break, check_break_availability, add_agent_to_break_queue, check_if_in_queque, handle_break, get_project_name, check_agent, check_active_breaks
from bots.bot_functions.helper_functions import assume_gender, calculate_time_difference, check_if_too_long
from datetime import datetime
import pytz


def welcome_message(user_name):
    message = MessageFactory.attachment(
        CardFactory.hero_card(intro_card(user=user_name)))
    return message


def maruda_message():
    card = maruda_card()
    message = MessageFactory.attachment(card)
    return message


async def monitoring_status_message(projects, user):
    gender = assume_gender(user)
    project_names = []
    for project in projects:
        project_names.append(await get_project_name(project))
    card = monitoring_status_card(project_names, gender)
    message = MessageFactory.attachment(card)
    return message


async def options_message(scheduler, initial, options, is_leader, user_name, agent_data, user_projects):
    if is_leader:
        message = leader_options_message(
            scheduler, user_projects, initial, options, user_name)
    else:
        message = await agent_options_message(initial, options, user_name, agent_data, user_projects)
    return message


def leader_options_message(scheduler, projects, initial, options, username):
    monitored_projects = []
    for p in projects:
        if p in scheduler.keys():
            monitored_projects.append(p)
    card = leader_card(initial, options, monitored_projects, username=username)
    message = MessageFactory.attachment(card)
    return message


async def agent_options_message(initial, options, username, agent_data, projects):
    short_breaks = []
    queques = []
    for p in projects:
        check_queque = await check_if_in_queque({'agent': agent_data['user_api_id'], 'project': p})
        if check_queque:
            queques.append(p)
        project = await get_project_details(p)
        if project['quick_break_allowed']:
            short_breaks.append(project['id'])
    is_on_break = await check_if_on_break(agent_data)
    not_in_queque = list(
        set(projects) - set(queques))
    if is_on_break['is_on_break']:
        is_on_break['project_name'] = await get_project_name(is_on_break['project'])
        if not is_on_break['quick_break']:
            not_in_queque.remove(is_on_break['project'])
    card = agent_options_card(initial, options, is_on_break, username,
                              short_breaks, queques, not_in_queque, agent_data['user_api_id'])
    message = MessageFactory.attachment(card)
    return message


async def check_queque_message(data):
    project_details = await get_project_details(data['project'])
    check = await check_queque(data)
    for q in check['queque_details']:
        agent_details = await check_agent(None, q['agent_id'])
        if agent_details:
            q['gender'] = assume_gender(agent_details['first_name'])
            q['full_name'] = f"{agent_details['first_name']} {agent_details['last_name']}"
    card = check_queque_card(
        check, data['project'], data['leader'], project_details['name'])
    message = MessageFactory.attachment(card)
    return message


async def add_to_break_queque_message(data, send_to_back=False):
    project_details = await get_project_details(data['project'])
    in_queque = await check_if_in_queque(data)
    if not in_queque:
        await add_agent_to_break_queue(data)
        message = MessageFactory.attachment(
            CardFactory.hero_card(queue_card(project_details['name'], send_to_back)))
    else:
        message = MessageFactory.attachment(
            already_card(project_details['name']))
    return message


async def check_if_break_allowed_message(project_id, agent_id, name, from_loop=False):
    break_allowed = await check_break_availability(project_id, agent_id)
    card = check_if_break_allowed_card(
        break_allowed, name, project_id, agent_id)
    message = MessageFactory.attachment(card)
    if from_loop:
        return card
    return message


def missing_data_message(missing_data, email):
    card = missing_data_card(missing_data, email)
    message = MessageFactory.attachment(card)
    return message


async def project_message(**kwargs):
    projects_from_api = await get_projects()
    projects_to_check = [
        p for p in projects_from_api if p['id'] in kwargs['projects']]
    card = project_card(projects_to_check, **kwargs)
    message = MessageFactory.attachment(card)
    return message


async def confirmation_message(project_id, missing_users, too_many_users=False):
    project_name = await get_project_name(project_id)
    card = confirmation_card(project_name, project_id,
                             missing_users, too_many_users)
    message = MessageFactory.attachment(card)
    return message


def response_message(project_name, is_leader):
    card = response_card(project_name, is_leader)
    message = MessageFactory.attachment(card)
    return message


async def back_to_queque_message(project_id, agent_id, skip_project_check, is_leader):
    project_name = await get_project_name(project_id)
    data = {'project': project_id, 'agent': agent_id, 'leader': is_leader}
    check = await check_queque(data)
    break_details = await check_break_range(project_id)
    card = back_to_queque_card(
        project_name, project_id, check, break_details, skip_project_check)
    message = MessageFactory.attachment(card)
    return message


def error_message(main, sec):
    card = error_card(main, sec)
    message = MessageFactory.attachment(card)
    return message


async def break_confirmation_message(project_id, agent_id, action, quick_break=False):
    if action == 'start':
        card = break_card(project_id)
    if action == 'end':
        card = back_to_work_card()
    if await handle_break({'project': project_id, 'agent': agent_id}, action, quick_break):
        if action == 'start':
            message = MessageFactory.attachment(card)
        else:
            message = MessageFactory.attachment(
                CardFactory.hero_card(card))
    else:
        error_main = "Coś poszło nie tak, nie mogę zapisać cię na przerwę :("
        error_secondary = "Proszę, powiadom przełożonego że coś jest nie tak!"
        message = error_message(error_main, error_secondary)
    return message


async def remote_break_end_message(data):
    if await handle_break({'project': data['project_id'], 'agent': data['user_id']}, 'end'):
        gender = assume_gender(data['first_name'])
        card = remote_break_end_card(
            data['first_name'], data['last_name'], gender)
        message = MessageFactory.attachment(card)
        status = "success"
    else:
        error_main = "Nie udało mi się usunąć użytkownika z przerwy!"
        error_secondary = "Coś poszło straszliwie nie tak!"
        message = error_message(error_main, error_secondary)
        status = "error"
    return {
        'status': status,
        'message': message
    }


async def user_problem_message(id, problem_number):
    user = await get_user(id)
    card = user_problem_card(
        user['first_name'], user['last_name'], user['email'], problem_number)
    message = MessageFactory.attachment(card)
    return message


def data_saved_message():
    card = data_saved_card()
    message = MessageFactory.attachment(card)
    return message


def break_history_message(break_details, project_name, is_leader=False):
    card = break_history_card(break_details, project_name, is_leader)
    message = MessageFactory.attachment(card)
    return message


async def check_current_break_message(data):
    breaks = await check_active_breaks(data['project_id'])
    if breaks:
        my_break = next(
            (b for b in breaks if b['agent'] == data['user_id']), None)
    if my_break:
        break_time = calculate_time_difference(
            start=my_break['start_datetime'])
        break_range = await check_break_range(data['project_id'])
        more_than_allowed = check_if_too_long(
            my_break['start_datetime'], break_range)
        card = check_current_break_card(
            break_time, more_than_allowed, data['project_id'])
        message = MessageFactory.attachment(card)
        return message


async def check_active_breaks_message(id):
    breaks = await check_active_breaks(id)
    if breaks:
        for b in breaks:
            agent_details = await check_agent(None, b['agent'])
            if agent_details:
                timezone = 'Europe/Warsaw'
                dt = datetime.fromisoformat(b['start_datetime'][:-6])
                dt = pytz.timezone(timezone).localize(dt)
                b['start_hour'] = dt.time()
                b['full_name'] = f"{agent_details['first_name']} {agent_details['last_name']}"
    card = check_active_breaks_card(breaks)
    message = MessageFactory.attachment(card)
    return message


def agents_choice_message(agents, project):
    card = agents_choice_card(agents, project)
    message = MessageFactory.attachment(card)
    return message


def decline_break_choice_message(data):
    card = decline_break_choice_card(data)
    message = MessageFactory.attachment(card)
    return message


async def removed_from_queque_message(project_id, agent_name=None, agent_gender=None, multiple=False, not_in_queque=False):
    project_name = await get_project_name(project_id)
    card = removed_from_queque_card(
        project_name, agent_name, agent_gender, multiple, not_in_queque)
    message = MessageFactory.attachment(card)
    return message


def advice_message(text):
    card = advice_card(text)
    message = MessageFactory.attachment(card)
    return message


async def timer_stopped_message(project_id):
    project_name = await get_project_name(project_id)
    card = timer_stopped_card(project_name)
    message = MessageFactory.attachment(card)
    return message

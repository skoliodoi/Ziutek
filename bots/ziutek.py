# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from botbuilder.core import TurnContext, UserState, ConversationState, MessageFactory, CardFactory, BotFrameworkAdapter, BotFrameworkAdapterSettings, MemoryStorage
from botbuilder.core.teams import TeamsActivityHandler, TeamsInfo
from botbuilder.schema.teams import TeamsChannelAccount
from botbuilder.schema import Activity, ActivityTypes
from responses.proactive_cards import send_to_break_card, user_problem_card, remove_from_queque_card, break_end_reminder_card, i_told_on_you_card, removed_remotely_card
from responses.messages import maruda_message, monitoring_status_message, welcome_message, project_message, options_message, confirmation_message, response_message, missing_data_message, check_if_break_allowed_message, add_to_break_queque_message, break_confirmation_message, error_message, user_problem_message, data_saved_message, break_history_message, check_queque_message, back_to_queque_message, check_active_breaks_message, agents_choice_message, remote_break_end_message, decline_break_choice_message, check_current_break_message, removed_from_queque_message, advice_message, timer_stopped_message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from .bot_functions.api_calls import create_conversation_id, get_leaders, get_project_name, create_token, check_active_breaks, get_project_breaks, get_user, update_user, check_if_all_agents_are_introduced, check_agent, check_break_range, remove_from_queue, get_project_details, check_if_on_break
from .bot_functions.helper_functions import extract_agent_data
from apscheduler.schedulers import SchedulerAlreadyRunningError
from config import DefaultConfig
import requests
import json
import pytz

ADAPTIVECARDTEMPLATE = "resources/TestCard.json"
TIMEZONE = 'Europe/Warsaw'
config = DefaultConfig()


class Ziutek(TeamsActivityHandler):
    def __init__(self, conversation_state: ConversationState, user_state: UserState):
        print("Bot instance initialized.")
        if conversation_state is None:
            raise TypeError(
                "[StateManagementBot]: Missing parameter. conversation_state is required but None was given"
            )
        if user_state is None:
            raise TypeError(
                "[StateManagementBot]: Missing parameter. user_state is required but None was given"
            )
        adapter_settings = BotFrameworkAdapterSettings(
            app_id=config.APP_ID, app_password=config.APP_PASSWORD)
        self.adapter = BotFrameworkAdapter(adapter_settings)
        self.memory = MemoryStorage()

        self.conversation_state = conversation_state
        self.user_state = user_state
        self.agent = None
        self.break_asked = []
        self.leader_asked = []
        self.questioning_dict = {}
        self.project_schedulers = {}
        self.scheduler_job_ids = {}
        self.conversation_data_accessor = self.conversation_state.create_property(
            "ConversationData"
        )
        self.user_profile_accessor = self.user_state.create_property(
            "UserProfile")

    def add_was_asked(self, id):
        self.break_asked.append({
            'id': id,
            'asked_time': datetime.now(tz=pytz.timezone('Europe/Warsaw'))
        })

    def check_was_asked(self, id):
        was_asked = next(
            (ba['asked_time'] for ba in self.break_asked if ba['id'] == id), None)
        return was_asked

    def delete_was_asked(self, id):
        for item in self.break_asked[:]:
            if item['id'] == id:
                self.break_asked.remove(item)

    async def send_proactive_message(self, card, headers, conversation_id):
        send_message_url = f"https://smba.trafficmanager.net/emea/v3/conversations/{conversation_id}/activities"
        message_data = {
            "type": "message",
            "from": {"id": config.APP_ID},
            "attachments": [
                {"contentType": "application/vnd.microsoft.card.adaptive", "content": card}
            ]
        }
        response = requests.post(
            send_message_url, headers=headers, data=json.dumps(message_data))
        # Check if the message was sent successfully
        print(response.status_code)

    async def tell_the_leaders(self, project_id, headers, problem_number, recipient, break_too_long_id, was_reminded_id):
        leaders = await get_leaders(project_id)
        for leader in leaders:
            if leader['teams_conversation_id']:
                was_asked_id = f"{leader['teams_conversation_id']}_{project_id}_{recipient['id']}"
                card = user_problem_card(
                    recipient, problem_number, project_id, break_too_long_id, was_reminded_id, was_asked_id)
                if not self.check_was_asked(was_asked_id):
                    await self.send_proactive_message(
                        card=card, headers=headers, conversation_id=leader['teams_conversation_id'])
                    self.add_was_asked(was_asked_id)
                else:
                    print("Już wysłałem wiadomość, czekam na odpowiedź")

    async def create_ms_token(self):
        token_endpoint = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
        token_data = {
            "grant_type": "client_credentials",
            "client_id": config.APP_ID,
            "client_secret": config.APP_PASSWORD,
            "scope": "https://api.botframework.com/.default"
        }
        response = requests.post(token_endpoint, data=token_data)
        access_token = response.json().get("access_token")
        headers = {
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/json"
        }
        return headers

    async def create_proactive_message(self, turn_context: TurnContext, recipient, project_id, break_message):
        bot_data = turn_context.activity.recipient
        print("Sprawdzam usera: ", recipient)
        recipient_teams_id = recipient['teams_user_id']
        recipient_conversation_id = recipient['teams_conversation_id']

        def time_finished(time_asked, minutes_to_respond):
            now = datetime.now(tz=pytz.timezone('Europe/Warsaw'))
            diff = now - time_asked
            minutes_difference = diff.total_seconds() / 60
            if minutes_difference > minutes_to_respond:
                return True
            return False

        # token_endpoint = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
        # token_data = {
        #     "grant_type": "client_credentials",
        #     "client_id": config.APP_ID,
        #     "client_secret": config.APP_PASSWORD,
        #     "scope": "https://api.botframework.com/.default"
        # }
        # response = requests.post(token_endpoint, data=token_data)
        # access_token = response.json().get("access_token")
        # headers = {
        #     "Authorization": "Bearer " + access_token,
        #     "Content-Type": "application/json"
        # }

        headers = await self.create_ms_token()

        if recipient_conversation_id:
            conversation_id = recipient_conversation_id
        else:
            try:
                conversation_id = await create_conversation_id(
                    bot_id=bot_data.id, recipient_teams_id=recipient_teams_id, headers=headers)
            except Exception:
                problem_number = None
                if break_message:
                    problem_number = 3
                else:
                    problem_number = 2
                await self.tell_the_leaders(project_id, headers, problem_number, recipient)
                if not break_message:
                    await remove_from_queue({'agent': recipient['id'], 'project': project_id})
                return
        project_details = await get_project_details(project_id)
        minutes_to_respond = project_details['time_to_respond_in_minutes']
        if not break_message:
            was_asked_id = f"{conversation_id}_{project_id}_{recipient['id']}_break_send"
            was_asked = self.check_was_asked(was_asked_id)
            data = {
                'project': project_id,
                'agent': recipient['id']
            }
            if was_asked:
                if time_finished(was_asked, minutes_to_respond):
                    card = remove_from_queque_card()
                    await self.send_proactive_message(
                        card=card, headers=headers, conversation_id=conversation_id)

                    await remove_from_queue(data)
                    self.delete_was_asked(was_asked_id)
            else:
                self.add_was_asked(was_asked_id)
                project_name = await get_project_name(project_id)
                card = send_to_break_card(data, project_name, was_asked_id)
                await self.send_proactive_message(card=card, headers=headers, conversation_id=conversation_id)
        else:
            was_asked_id = f"{conversation_id}_{project_id}_{recipient['id']}_break_too_long"
            was_asked = self.check_was_asked(was_asked_id)
            if was_asked:
                if time_finished(was_asked, minutes_to_respond):
                    was_reminded_id = f"{conversation_id}_{project_id}_{recipient['id']}_told_on"
                    was_reminded = self.check_was_asked(was_reminded_id)
                    if was_reminded:
                        print(
                            f"{was_reminded_id} - Nie trzeba powtarzać!")
                    else:
                        card = i_told_on_you_card()
                        await self.send_proactive_message(card=card, headers=headers, conversation_id=conversation_id)
                        await self.tell_the_leaders(project_id, headers, 4, recipient, was_asked_id, was_reminded_id)
                        self.add_was_asked(was_reminded_id)
            else:
                self.add_was_asked(was_asked_id)
                card = break_end_reminder_card(project_id, was_asked_id)
                await self.send_proactive_message(card=card, headers=headers, conversation_id=conversation_id)

    async def get_initial_data(self, turn_context: TurnContext, activity):
        try:
            activity = turn_context.activity
            teams_id = activity.from_property.id
            user_info = await TeamsInfo.get_member(turn_context, teams_id)
            # user_id = user_info.additional_properties['aadObjectId']
            user_id = user_info.aad_object_id
            user_email = user_info.email
            user_name = user_info.given_name
            conversation_id = activity.conversation.id
        except Exception as ex:
            print(f"Error getting member information: {ex}")
        try:
            current_agent = await check_agent(email=user_email)
            user = {
                "projects": current_agent['projects'],
                "is_leader": current_agent['is_leader'],
                "user_api_id": current_agent['user_api_id'],
                "teams_id": teams_id,
                "user_id": user_id,
                "conversation_id": conversation_id,
                'mail': user_email,
                "user_name": current_agent['user_name']
            }
            obj = {
                teams_id: user
            }
            await self.memory.write(obj)
            return user
        except ValueError as e:
            if str(e) == "no_email" or str(e) == "no_projects":
                await turn_context.send_activity(welcome_message(user_name))
                await turn_context.send_activity(missing_data_message(str(e), user_email))
                return
            else:
                return await turn_context.send_activity("Oops! Wygląda na to że się zepsułem! Coś nie działa jak należy! :(")

    async def on_message_activity(self, turn_context: TurnContext):
        await create_token()
        try:
            activity = turn_context.activity
            user_id = activity.from_property.id
        except Exception as ex:
            print(f"Error getting member information: {ex}")

        async def typing():
            await turn_context.send_activity(Activity(
                type=ActivityTypes.typing,
            ))
        # check_user = await self.memory.read([f"{user_id}"])
        # if not check_user:
        current_user = await self.get_initial_data(turn_context, activity)
        # else:
        #     current_user = check_user[user_id]
        if not current_user:
            return

        async def send_message(message):
            if message:
                await typing()
                await turn_context.send_activity(message)

        async def break_request(project_id):
            project_details = await get_project_details(project_id)
            project_name = project_details['name']
            return await check_if_break_allowed_message(project_id, current_user['user_api_id'], project_name)

        async def break_history_request(project_id, user_id=current_user['user_api_id'], is_leader=current_user['is_leader']):
            project_name = await get_project_name(project_id)
            break_details = await get_project_breaks(user_id, project_id)
            return break_history_message(break_details, project_name, is_leader)

        async def break_monitoring_request(turn_context: TurnContext, project_id):
            project_details = await get_project_details(project_id)
            project_name = project_details['name']
            try:
                await self.set_timer(turn_context, project_id=project_id)
                message = response_message(
                    project_name, current_user['is_leader'])

            except SchedulerAlreadyRunningError:
                message = error_message(main="Halo halo, wstrzymaj konie!",
                                        sec=f"Przecież ja już monitoruję przerwy na projekcie {project_name}!")
            return message

        async def show_options(initial=False, options=False):
            message = await options_message(self.scheduler_job_ids, initial, options, user_name=current_user['user_name'], is_leader=current_user['is_leader'], agent_data=current_user, user_projects=current_user['projects'])
            return message
        if activity.conversation.conversation_type == 'personal':
            if current_user:
                try:
                    await update_user(teams_user_id=current_user['user_id'],
                                      conversation_id=current_user['conversation_id'], is_leader=current_user['is_leader'], mail=current_user['mail'])
                except Exception:
                    main = "Coś poszło nie tak podczas próby zapisania Cię w mojej bazie danych!"
                    secondary = "Daj znać przełożonemu!"
                    return await turn_context.send_activity(error_message(main, secondary))
            if activity.value is not None:
                user_message = ''
                a_v = activity.value
                print(a_v)
                skip_project_check = len(current_user['projects']) == 1
                if skip_project_check:
                    single_project_id = current_user['projects'][0]
                first_message = None
                second_message = None
                third_message = None
                fourth_message = None
                await typing()
                match a_v['action']:
                    case "monitorowanie":
                        if skip_project_check:
                            introduced_agents_missing = await check_if_all_agents_are_introduced(single_project_id)
                            if len(introduced_agents_missing) > 0:
                                try:
                                    first_message = await confirmation_message(
                                        single_project_id, introduced_agents_missing)
                                except Exception as e:
                                    if "MessageSizeTooBig" in str(e):
                                        first_message = await confirmation_message(
                                            single_project_id, [], True)
                            else:
                                first_message = await break_monitoring_request(turn_context, single_project_id)
                                second_message = await show_options()
                        else:
                            first_message = await project_message(is_leader=current_user['is_leader'], projects=current_user['projects'], check_breaks=True)
                    case "stop_monitorowanie":
                        if skip_project_check:
                            try:
                                await self.stop_timer(single_project_id)
                                first_message = await timer_stopped_message(single_project_id)
                                second_message = await show_options()
                            except Exception:
                                main = "Coś poszło nie tak!"
                                secondary = "Nie udało mi się przerwać monitorowania na tym projekcie!"
                                advice = "Może inny lider wyłączył je przed tobą?"
                                first_message = error_message(main, secondary)
                                second_message = advice_message(advice)
                                third_message = await show_options()

                        else:
                            first_message = await project_message(is_leader=current_user['is_leader'], projects=current_user['projects'], stop_checking=True)
                    case "show_status":
                        first_message = await monitoring_status_message(a_v['projects'], current_user['user_name'])
                        second_message = await show_options()
                    case "agents_chosen":
                        no_choice_made = a_v['people-picker'] == '{people-picker}'
                        if no_choice_made:
                            first_message = "Nie został wybrany nikt do usunięcia, więc nikogo nie usuwam!"
                            second_message = await show_options()
                        else:
                            agents_list = a_v['people-picker'].split(',')
                            agents_details = extract_agent_data(
                                agents=agents_list)
                            if len(agents_details) == 0:
                                first_message = "Nie został wybrany nikt do usunięcia, więc nikogo nie usuwam!"
                            elif len(agents_details) == 1:
                                agent = agents_details[0]
                                await remove_from_queue(
                                    {'agent': agent['id'], 'project': a_v['project']})
                                first_message = await removed_from_queque_message(project_id=a_v['project'],
                                                                                  agent_name=agent['full_name'], agent_gender=agent['gender'])
                            else:
                                for a in agents_details:
                                    await remove_from_queue(
                                        {'agent': a['id'], 'project': a_v['project']})
                                first_message = await removed_from_queque_message(project_id=a_v['project'],
                                                                                  multiple=True)
                            second_message = await check_queque_message({'project': a_v['project'], 'agent': current_user['user_api_id'], 'leader': current_user['is_leader']})
                            third_message = await show_options()
                    case "remove_from_break":
                        removed_user_conversation_id = None
                        if "remote" in a_v.keys():
                            removed_user_conversation_id = a_v['user_conversation_id']
                            if self.check_was_asked(a_v['reminded']):
                                self.delete_was_asked(a_v['reminded'])
                            if self.check_was_asked(a_v['leader_asked']):
                                self.delete_was_asked(a_v['leader_asked'])
                            if self.check_was_asked(a_v['break_too_long']):
                                self.delete_was_asked(a_v['break_too_long'])
                        # if 'user_conversation_id' in a_v.keys():
                        #     if a_v['user_conversation_id']:
                        #         check_id = f"{a_v['user_conversation_id']}_{a_v['project_id']}_{a_v['user_id']}"
                        #         first_check = check_id+"_break_too_long"
                        #         second_check = check_id+"_told_on"
                        #         if self.check_was_asked(first_check):
                        #             self.delete_was_asked(first_check)
                        #         if self.check_was_asked(second_check):
                        #             self.delete_was_asked(second_check)
                        check = await remote_break_end_message(a_v)
                        first_message = check['message']
                        if check['status'] == 'success':
                            second_message = await break_history_request(a_v['project_id'], user_id=a_v['user_id'])
                            if removed_user_conversation_id:
                                card = removed_remotely_card()
                                headers = await self.create_ms_token()
                                await self.send_proactive_message(card=card, headers=headers, conversation_id=removed_user_conversation_id)
                        else:
                            advice = "Sprawdź jeszcze raz czy użytkownik dalej jest na przerwie. Być może w międzyczasie zdążył wrócić, albo usunął go inny lider?"
                            second_message = advice_message(advice)
                        third_message = await show_options()
                        # return
                    case "requires_break":
                        # Przycisk "chcę iśc na dłuższą przerwę" (tylko do testów, tylko dla agenta)
                        if skip_project_check:
                            # jeśli agent jest na tylko jednym projekcie pomijamy wybór projektów
                            first_message = await break_request(single_project_id)
                        else:
                            # jeśli agent jest na większej ilości projektów wyświetlamy mu kartę wyboru projektów
                            first_message = await project_message(is_leader=current_user['is_leader'], projects=current_user['projects'], regular_break=True)
                    case "go_on_break":
                        # Przycisk "Dobra, to idę!", wysyłający agenta na przerwę (tylko dla agenta)
                        first_message = await break_confirmation_message(
                            a_v['project_id'], current_user['user_api_id'], 'start')
                        # Wiadomość potwierdzająca start przerwy lub informująca o problemach
                        if self.check_was_asked(a_v['was_asked_id']):
                            self.delete_was_asked(a_v['was_asked_id'])
                        second_message = await show_options()
                        # Wiadomość pokazująca dodatkowe opcje
                        # return await turn_context.send_activity(message)
                    # wysyłane w przypadku gdy użytkownik chce odświeżyć swoje dane (projekty, do których jest przypisany, status lidera itp)
                    case "refresh_data":
                        await self.get_initial_data(turn_context, activity)
                        first_message = "Ok, odświeżyłem Twoje dane, sprawdź wszystko jeszcze raz!"
                        second_message = await show_options()
                    case "project_chosen":
                        # Wiadomość pojawia się w przypadku gdy agent lub lider są przypisani do więcej niż jednego projektu
                        # Po wyborze projektu w zależnosci od tego jaka czynność została wybrana (informacja przekazana w wiadomości), pojawiają się różne karty
                        await turn_context.send_activity(f"Jasne, poczekaj aż sprawdzę wszystkie detale dla projektu {a_v['name']}...")
                        if current_user['is_leader']:
                            if a_v['stop_checking_breaks']:
                                try:
                                    await self.stop_timer(a_v['id'])
                                    first_message = await timer_stopped_message(
                                        a_v['id'])
                                except Exception as e:
                                    main = "Coś poszło nie tak!"
                                    secondary = str(e)
                                    first_message = error_message(
                                        main, secondary)
                                second_message = await show_options()
                            if a_v['queque_list']:
                                first_message = await check_queque_message({'project': a_v['id'], 'agent': current_user['user_api_id'], 'leader': current_user['is_leader']})

                            if a_v['check_active_breaks']:
                                first_message = await check_active_breaks_message(a_v['id'])
                                second_message = await show_options()

                            if a_v['check_breaks']:
                                introduced_agents_missing = await check_if_all_agents_are_introduced(a_v['id'])
                                if len(introduced_agents_missing) > 0:
                                    try:
                                        first_message = await confirmation_message(a_v['id'], introduced_agents_missing)
                                        # return await turn_context.send_activity(confirmation_message(a_v['name'], a_v['id'], introduced_agents_missing))
                                    except Exception as e:
                                        if "MessageSizeTooBig" in str(e):
                                            first_message = await confirmation_message(a_v['id'], [], True)
                                            # return await turn_context.send_activity(confirmation_message(a_v['name'], a_v['id'], [], True))
                                else:
                                    first_message = await break_monitoring_request(
                                        turn_context, a_v['id'])
                                    second_message = await show_options()
                        else:
                            if a_v['break']:
                                first_message = await break_request(a_v['id'])
                            if a_v['quick_break']:
                                first_message = await break_confirmation_message(
                                    a_v['id'], current_user['user_api_id'], 'start', True)
                                second_message = await show_options()
                            if a_v['break_history_request']:
                                first_message = await break_history_request(a_v['id'])
                                second_message = await show_options()
                            if a_v['queque_list']:
                                first_message = await check_queque_message({'project': a_v['id'], 'agent': current_user['user_api_id'], 'leader': current_user['is_leader']})
                            if a_v['add_to_queque']:
                                # jeśli użytkownik wybrał projekt żeby dodać się do kolejki
                                first_message = await add_to_break_queque_message(
                                    {'project': a_v['id'], 'agent': current_user['user_api_id']})
                                second_message = await show_options()
                            if a_v['remove_from_queque']:
                                data = {
                                    'project': a_v['id'],
                                    'agent': current_user['user_api_id']
                                }
                                await remove_from_queue(data)
                                first_message = await removed_from_queque_message(
                                    project_id=a_v['id'])
                                second_message = await show_options()
                    case "confirm":
                        if current_user['is_leader']:
                            first_message = await break_monitoring_request(turn_context, a_v['id'])
                            second_message = await show_options()
                    case "show_break_time":
                        # Przycisk "Pokaż historię moich przerw z dzisiaj" (tylko dla agenta)
                        if skip_project_check:
                            # Jeśli agent jest na jednym projekcie sprawdzamy historię przerw tylko na tym projekcie, wyświetlamy tę historię i pokazujemy znowu opcje do wyboru
                            first_message = await break_history_request(single_project_id)
                            second_message = await show_options()
                        else:
                            # Jeśli agent jest na więcej niż jednym projekcie wyświetlamy mu kartę wyboru projektu do sprawdzenia
                            first_message = await project_message(is_leader=current_user['is_leader'], projects=current_user['projects'], break_history_request=True)
                    case "check_queque":
                        if skip_project_check:
                            first_message = await check_queque_message({'project': single_project_id, 'agent': current_user['user_api_id'], 'leader': current_user['is_leader']})
                        else:
                            first_message = await project_message(projects=current_user['projects'], is_leader=current_user['is_leader'], check_queque=True)
                    case "add_to_queque":
                        if 'exclude_id' in a_v.keys():
                            projects = current_user['projects']
                            projects.remove(a_v['exclude_id'])
                            if len(projects) > 1:
                                first_message = await project_message(is_leader=current_user['is_leader'], projects=projects, add_to_queque=True)
                            else:
                                single_project_id = projects[0]
                                first_message = await add_to_break_queque_message(
                                    {'project': single_project_id, 'agent': current_user['user_api_id']})
                        elif 'id' in a_v.keys():
                            # Przycisk "Tak, zapisz mnie ponownie", id projektu jest od razu przesłane w treści wiadomości i nie trzeba nic sprawdzać, od razu zapisujemy w kolejce
                            first_message = await add_to_break_queque_message(
                                {'project': a_v['id'], 'agent': current_user['user_api_id']})
                            second_message = await show_options()
                        else:
                            # Przycisk "Zapisz mnie w kolejce" (tylko dla agenta)
                            if skip_project_check:
                                # Jeśli agent jest zapisany do tylko jednego projektu nie wyświetlamy listy projektów tylko od razu zapisujemy w kolejce
                                first_message = await add_to_break_queque_message(
                                    {'project': single_project_id, 'agent': current_user['user_api_id']})
                                second_message = await show_options()
                            else:
                                if len(a_v['projects']) > 1:
                                    first_message = await project_message(is_leader=current_user['is_leader'], projects=a_v['projects'], add_to_queque=True)
                                else:
                                    project_id = a_v['projects'][0]
                                    first_message = await add_to_break_queque_message(
                                        {'project': project_id, 'agent': current_user['user_api_id']})
                                    second_message = await show_options()
                        # return await turn_context.send_activity(message)
                    case "remove_from_queque":
                        data = {
                            'agent': current_user['user_api_id'],
                            'project': None
                        }
                        if 'user_data' in a_v.keys():
                            # Sprawdzamy czy użytkownik był zapytany o pójście na przerwę
                            data = a_v['user_data']
                            # Pobieramy dane użytkownika z przesłanej odpowiedzi
                            check_id = f"{current_user['conversation_id']}_{data['project']}_{data['agent']}_break_send"
                            await remove_from_queue(data)
                            if a_v['delete_completely']:
                                # Przycisk "Usuń mnie z kolejki" (tylko dla agenta)
                                first_message = await removed_from_queque_message(
                                    project_id=data['project'])
                            else:
                                first_message = await add_to_break_queque_message(data, True)
                            second_message = await show_options()
                            if self.check_was_asked(check_id):
                                self.delete_was_asked(check_id)
                        else:
                            if current_user['is_leader']:
                                if len(a_v['agents']) > 1:
                                    first_message = agents_choice_message(
                                        a_v['agents'], a_v['projects'][0])
                                else:
                                    agent_to_remove = a_v['agents'][0]
                                    full_name = agent_to_remove['full_name']
                                    data['agent'] = agent_to_remove['agent_id']
                                    data['project'] = a_v['projects'][0]
                                    await remove_from_queue(data)
                                    first_message = await removed_from_queque_message(
                                        a_v['projects'][0], agent_name=full_name, agent_gender=agent_to_remove['gender'])
                                    second_message = await check_queque_message({'project': a_v['projects'][0], 'agent': current_user['user_api_id'], 'leader': True})
                                    third_message = await show_options()
                            else:
                                # Przycisk "Wypisz mnie z kolejki" (tylko dla agenta)
                                if len(a_v['projects']) > 1:
                                    # Jeśli agent jest w kolejce na większej ilości projektów niż jeden, pytamy go o to z którego projektu ma zostać wypisany
                                    first_message = await project_message(is_leader=current_user['is_leader'], projects=a_v['projects'], remove_from_queque=True)
                                else:
                                    # Jeśli jest w kolejce do tylko jednego projektu wywalamy go z niej od razu
                                    data['project'] = a_v['projects'][0]
                                    first_message = await removed_from_queque_message(
                                        project_id=data['project'])
                                    await remove_from_queue(data)
                                    second_message = await show_options()
                    case "quick_break":
                        if len(a_v['quick_breaks']) > 1:
                            first_message = await project_message(
                                quick_break=True, is_leader=current_user['is_leader'], projects=a_v['quick_breaks'])
                        else:
                            single_project_id = a_v['quick_breaks'][0]
                            first_message = await break_confirmation_message(
                                single_project_id, current_user['user_api_id'], 'start', True)
                            second_message = await show_options()
                    case "return_from_break":
                        if 'was_asked_id' in a_v.keys():
                            if self.check_was_asked(a_v['was_asked_id']):
                                self.delete_was_asked(a_v['was_asked_id'])
                        if 'was_reminded_id' in a_v.keys():
                            if self.check_was_asked(a_v['was_reminded_id']):
                                self.delete_was_asked(a_v['was_reminded_id'])
                        user_id = current_user['user_api_id']
                        first_message = await break_confirmation_message(
                            a_v['id'], user_id, 'end')
                        second_message = await break_history_request(a_v['id'], user_id)
                        if a_v['quick_break']:
                            third_message = await show_options()
                        else:
                            third_message = await back_to_queque_message(a_v['id'], user_id, skip_project_check, current_user['is_leader'])
                    case "decline_break":
                        if 'user_declined' in a_v.keys():
                            # Przycisk "muszę zrezygnować", kiedy użytkownik sam rezygnuje z przerwy
                            first_message = decline_break_choice_message(a_v)
                            if self.check_was_asked(a_v['was_asked_id']):
                                self.delete_was_asked(a_v['was_asked_id'])
                            # Ziutek zwraca mu wtedy wiadomośc wyboru - całkowite usunięcie z kolejki albo przesunięcie na sam koniec kolejki
                        elif 'remote' in a_v.keys():
                            if self.check_was_asked(a_v['break_too_long']):
                                self.delete_was_asked(a_v['break_too_long'])
                            if self.check_was_asked(a_v['reminded']):
                                self.delete_was_asked(a_v['reminded'])
                            if self.check_was_asked(a_v['leader_asked']):
                                self.delete_was_asked(a_v['leader_asked'])
                        else:
                            # Przycisk "Nie trzeba, dzięki"
                            first_message = "Jak sobie chcesz, w przeciwieństwie do mnie (jeszcze) masz wolną wolę :)"
                            second_message = await show_options()
                    case "show_my_break_time":
                        first_message = await check_current_break_message(a_v)
                    case "check_active_breaks":
                        if skip_project_check:
                            first_message = await check_active_breaks_message(single_project_id)
                            second_message = await show_options()
                        else:
                            first_message = await project_message(is_leader=current_user['is_leader'], projects=current_user['projects'], check_active_breaks=True)
                await send_message(first_message)
                await send_message(second_message)
                await send_message(third_message)
                await send_message(fourth_message)
                return
            else:
                await typing()
                user_message = turn_context.activity.text.lower().strip()
            if current_user:
                match user_message:
                    case "cześć ziutek":
                        await typing()
                        options = await show_options(initial=True)
                        if current_user['mail'] == 'tomasz.rabiczko@oex-vcc.com':
                            await turn_context.send_activity(maruda_message())
                        else:
                            await turn_context.send_activity(welcome_message(current_user['user_name']))
                        await turn_context.send_activity(options)
                        return
                    case "pokaż opcje":
                        options = await show_options(options=True)
                        await typing()
                        await turn_context.send_activity("Ślimak, ślimak, pokaż rogi...")
                        await turn_context.send_activity(options)
                        return

    async def check_channel_name(self, turn_context: TurnContext):
        activity = turn_context.activity
        team = await TeamsInfo.get_team_details(turn_context)
        team_name = f"{team.name}"
        current_channel_name = activity.conversation.name if activity.conversation.name else team_name
        return current_channel_name

    async def on_teams_members_added(self, teams_members_added: TeamsChannelAccount, team_info: TeamsInfo, turn_context: TurnContext):
        await create_token()

        async def show_options(initial=False, options=False):
            message = await options_message(self.scheduler_job_ids, initial, options, user_name=current_user['user_name'], is_leader=current_user['is_leader'], agent_data=current_user, user_projects=current_user['projects'])
            return message
        activity = turn_context.activity
        if activity.conversation.conversation_type == 'personal':
            member = await TeamsInfo.get_member(turn_context, turn_context.activity.from_property.id)
            if member.id != turn_context.activity.recipient.id:
                current_user = await self.get_initial_data(turn_context, activity)
                if current_user:
                    options = await show_options()
                    await turn_context.send_activity(welcome_message(current_user['user_name']))
                    await update_user(teams_user_id=current_user['user_id'],
                                      conversation_id=current_user['conversation_id'], mail=current_user['mail'], is_leader=current_user['is_leader'])
                    await turn_context.send_activity(data_saved_message())
                    await turn_context.send_activity(options)
                    return
        else:
            try:
                for member in teams_members_added:
                    if member.id != turn_context.activity.recipient.id:
                        print(member)
                    else:
                        print("Dane zespołu:", team_info)
                        print("Dane kanału:", activity.channel_data)
                        print("Ziutek dodany do zespołu!")
            except Exception as e:
                print(e)
        return

    async def set_timer(self, turn_context, project_id):
        async def break_wrapper():
            await self.break_inspector(turn_context, project_id)
        print(f"Schedulers running: {self.project_schedulers}")
        print(f"Job IDs: {self.scheduler_job_ids}")
        if project_id not in self.project_schedulers:
            scheduler = AsyncIOScheduler()
            self.project_schedulers[project_id] = scheduler
        else:
            raise SchedulerAlreadyRunningError()

        job_scheduler = self.project_schedulers[project_id]
        break_job = job_scheduler.add_job(
            break_wrapper, trigger=IntervalTrigger(seconds=60))
        job_scheduler.start()
        self.scheduler_job_ids[project_id] = break_job.id
        print(f"Schedulers running after start: {self.project_schedulers}")
        print(f"Job IDs after start: {self.scheduler_job_ids}")
        return

    async def stop_timer(self, project_id):
        if project_id in self.project_schedulers:
            job_id = self.scheduler_job_ids[project_id]
            job_scheduler = self.project_schedulers[project_id]
            job_scheduler.remove_job(job_id)
            del (self.project_schedulers[project_id])
            del (self.scheduler_job_ids[project_id])
            print(
                f"Stopped scheduler for project {project_id}, job id {job_id}")
            print(f"Schedulers running after stop: {self.project_schedulers}")
            print(f"Job IDs after stop: {self.scheduler_job_ids}")
        else:
            raise Exception(
                "W tej chwili nie monitoruję przerw na tym projekcie. Na pewno o niego Ci chodziło?")

    async def break_inspector(self, turn_context: TurnContext, project_id):
        await create_token()
        print("Jo sem jest kłekłe inspektor, hej")
        now = datetime.now(tz=pytz.timezone('Europe/Warsaw'))
        now = now.astimezone(pytz.timezone('Europe/Warsaw'))
        project_name = await get_project_name(project_id)
        break_range = await check_break_range(
            project_id=project_id)
        if break_range:
            break_range_details = break_range['range_details']
            allowed_break_time = break_range_details['time_limit_in_minutes']
            if len(break_range['queque']) > 0:
                for b in break_range['queque']:
                    data = {
                        'project': project_id,
                        'agent': b['agent_id']
                    }
                    user_break_status = await check_if_on_break({'projects': [project_id], 'user_api_id': b['agent_id']})
                    if user_break_status['is_on_break']:
                        message = await (user_problem_message(b['agent_id'], 1))
                        await turn_context.send_activity(message)
                        await remove_from_queue(data)
                    else:
                        agent = await get_user(b['agent_id'])
                        # if agent['teams_conversation_id'] != "":
                        try:
                            # agent['teams_conversation_id'] = ''
                            await self.create_proactive_message(turn_context, recipient=agent, project_id=project_id, break_message=False)
                        except Exception as e:
                            if "Bad format of conversation ID" in str(e):
                                message = await user_problem_message(b['agent_id'], 2)
                                await turn_context.send_activity(message)
                                await remove_from_queue(data)

            else:
                print(
                    f"{datetime.now(tz=pytz.timezone('Europe/Warsaw'))} - nie ma nikogo w kolejce na projekcie {project_name}")
        else:
            allowed_break_time = 0
            print(
                f"Projekt {project_name} obecnie nie ma aktywnego zakresu przerw!")
        print("Jo sem jest brejk inspektor, hej")
        active_breaks = await check_active_breaks(project_id)
        if active_breaks and len(active_breaks) > 0:
            for ab in active_breaks:
                break_time = allowed_break_time if not ab['quick_break'] else 3
                print(
                    f"Quick break? {ab['quick_break']}. Allowed break time in minutes: {break_time}")
                break_minutes = break_time * 60
                break_start = datetime.fromisoformat(ab['start_datetime'][:-6])
                break_start = pytz.timezone(
                    'Europe/Warsaw').localize(break_start)
                time_diff = now - break_start
                more_than_allowed = time_diff.total_seconds() > break_minutes
                if more_than_allowed:
                    agent = await get_user(ab['agent'])
                    await self.create_proactive_message(turn_context, recipient=agent, project_id=project_id, break_message=True)
        else:
            print(
                f"{datetime.now(tz=pytz.timezone('Europe/Warsaw'))} - nie ma aktywnych przerw na projekcie {project_name}")

    async def on_turn(self, turn_context: TurnContext):
        await super().on_turn(turn_context)

        await self.user_state.save_changes(turn_context)
        await self.conversation_state.save_changes(turn_context)

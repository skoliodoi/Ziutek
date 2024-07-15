import requests
import json
from config import DefaultConfig
from botbuilder.core import ActivityHandler, TurnContext, StoreItem, MemoryStorage
from datetime import datetime, timedelta
from .helper_functions import calculate_time_difference, format_time


config = DefaultConfig()
storage = MemoryStorage()
username = config.API_USERNAME
password = config.API_PASSWORD

BASE_URL = config.API_BASE_URL


async def create_token():
    data = {"username": username,
            "password": password
            }
    req = requests.post(BASE_URL + '/token/', data=data).json()
    res = {
        'name': 'ziutoken',
        'access': req['access'],
        'refresh': req['refresh']
    }
    # query = {"name": 'ziutoken'}
    # db_tokens.update_one(query, {"$set": res}, upsert=True)
    access_token = res['access']
    refresh_token = res['refresh']
    changes = {'access_token': access_token, 'refresh_token': refresh_token}
    await storage.write(changes)
    return


async def refresh_token():
    refresh_token = await storage.read(["refresh_token"])
    data = {"refresh": refresh_token['refresh_token']}
    res = requests.post(BASE_URL + '/token/refresh/', data=data).json()
    new_access_token = res['access']
    changes = {'access_token': new_access_token,
               'refresh_token': refresh_token}
    await storage.write(changes)
    return


async def get_authorization():
    storage_info = await storage.read(["access_token"])
    authorization_headers = {
        'Authorization': f"Bearer {storage_info['access_token']}"
    }
    return authorization_headers


async def get_project_details(id):
    headers = await get_authorization()
    response = requests.get(
        BASE_URL + f"/api/projects/{id}/detail/", headers=headers)
    if response.ok:
        return response.json()
    else:
        print(response)
        raise Exception


async def get_project_name(id):
    project_details = await get_project_details(id)
    return project_details['name']


async def get_project_breaks(agent_id, project_id):
    headers = await get_authorization()
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    r = requests.get(
        BASE_URL + f"/api/break/list?agent_id={agent_id}&start_date={today}&end_date={tomorrow}", headers=headers).json()
    project_breaks = [
        item for item in r if item['project']['id'] == project_id]
    time_table = []
    total_time = 0
    total_formatted_time = "00:00:00"
    if len(project_breaks) > 0:
        for b in project_breaks:
            time_diff = calculate_time_difference(
                b['start_datetime'], b['end_datetime'])
            total_time += time_diff['duration']
            time_table.append(time_diff)
        total_formatted_time = format_time(total_time)

    return {
        'total': total_formatted_time,
        'details': time_table
    }


async def check_if_all_agents_are_introduced(id):
    headers = await get_authorization()
    project_details = await get_project_details(id)
    agents_in_project = project_details['agents']
    projects_from_api = await get_projects()
    this_project = next((p for p in projects_from_api if p['id'] == id), None)
    api_persons = requests.get(BASE_URL + '/api/persons/',
                               headers=headers).json()
    introduced = [ap['id'] for ap in api_persons if ap['id'] in this_project['agents'] and ap['teams_user_id'] and ap['teams_conversation_id']]
    not_introduced = [ap for ap in api_persons if ap['id']
                      in this_project['agents'] and ap['id'] not in introduced]
    all_agents_introduced = len(agents_in_project) == len(introduced)
    if all_agents_introduced:
        response = []
    else:
        response = not_introduced
    return response


async def get_user(id):
    headers = await get_authorization()
    persons = requests.get(BASE_URL + '/api/persons/',
                           headers=headers).json()
    user_api_email = next(
        (p['email'] for p in persons if p['id'] == id), None)
    user = requests.get(BASE_URL + f'/api/persons/{user_api_email}/',
                        headers=headers).json()
    return user


async def update_user(teams_user_id, conversation_id, is_leader, mail):
    headers = await get_authorization()
    data = {
        "teams_user_id": teams_user_id,
        "teams_conversation_id": conversation_id,
        "is_leader": is_leader
    }
    response = requests.put(BASE_URL + f'/api/persons/{mail}/',
                            headers=headers, data=data)
    if response.ok:
        print("User poprawnie zaktualizowany!")
    else:
        error = response.json()
        print(error)
        raise Exception("Aktualizacja użytkownika nieudana!")


async def get_projects():
    headers = await get_authorization()
    projects = requests.get(BASE_URL + '/api/projects/',
                            headers=headers).json()
    project_details = list(
        {'name': pr['name'], 'id': pr['id'], 'leaders': pr['leaders'], 'agents': pr['agents']} for pr in projects)
    return project_details


async def get_leaders(project_id):
    headers = await get_authorization()
    r = requests.get(BASE_URL + f'/api/projects/{project_id}/leaders',
                     headers=headers).json()
    return r


async def check_leader(email, projects):
    is_leader = False
    leader_id = None
    lead_projects = []
    leader_name = 'Gall Anonim'
    if email:
        for project in projects:
            # Używamy id projektu żeby zrobić poprawne zapytanie do API o liderów dla każdego z projektów
            project_id = project['id']
            response = await get_leaders(project_id)
            # Jeśli request zwraca poprawne wartości, sprawdzamy czy email przekazany jako atrybut funkcji znajduje się w odpowiedzi zwróconej przez request.
            # Jeśli tak jest, to oznacza że dany użytkownik jest liderem, a my dodajemy ID tego projektu do listy zarządzanych przez niego projektów
            if response:
                for r in response:
                    if email == r['email']:
                        is_leader = True
                        leader_id = r['id']
                        leader_name = r['first_name']
                        lead_projects.append(project['id'])
    return {
        'is_leader': is_leader,
        'leader_id': leader_id,
        'lead_projects': lead_projects,
        'leader_name': leader_name
    }


async def check_agent(email, agent_id=None):
    headers = await get_authorization()
    # Najpierw pobieramy listę wszystkich projektów
    projects_from_api = requests.get(BASE_URL + '/api/projects/',
                                     headers=headers).json()

    leader_check = await check_leader(email, projects_from_api)

    # Jeśli po sprawdzeniu okazuje się że użytkownik jest liderem to przypisujemy jego id i projekty którymi zarządza do wartościom, które potem zwróci funkcja do zapisu w bazie danych
    if leader_check['is_leader']:
        projects = leader_check['lead_projects']
        user_api_id = leader_check['leader_id']
        user_first_name = leader_check['leader_name']
    # Jeśli użytkownik nie jest liderem, sprawdzamy listę wszystkich użytkowników
    else:
        persons = requests.get(BASE_URL + '/api/persons/',
                               headers=headers).json()
        if agent_id:
            agent_data = next(
                (p for p in persons if p['id'] == agent_id), None)
            return agent_data
        # Wyszukujemy email użytkownika w liście użytkowników i pobieramy jego id
        user = next(
            (p for p in persons if p['email'] == email.lower()), None)
        if user:
            print('Juzer:', user)
            user_api_id = user['id']
            user_first_name = user['first_name']
        # Jeśli użytkownik nie zostanie znaleziony, zwracamy błąd (DO USPRAWNIENIA, sam błąd wywala po prostu Ziutka na ryj)
        else:
            raise ValueError("no_email")
        # W liście projektów z API sprawdzamy wszystkie projekty które mają id obecnego użytkownika w liście agentów
        projects = list(pr['id']
                        for pr in projects_from_api if user_api_id in pr['agents'])
        # Jeśli się nie znajdzie id użytkownika, to znaczy że nie jest przypisany do żadnego projektu, co również zwraca błąd (to też DO USPRAWNIENIA, błąd wywalający Ziutka na ryj)
        if len(projects) == 0:
            raise ValueError("no_projects")
    # Zwracamy uzyskane w ten sposób dane, do zapisu w bazie danych w celu dalszego użycia ich przez Ziutka
    return {
        "is_leader": leader_check['is_leader'],
        "projects": projects,
        "user_api_id": user_api_id,
        "user_name": user_first_name
    }


async def check_queque(agent_data):
    headers = await get_authorization()
    data = {"project": agent_data['project']}
    place_in_queque = None
    queque_details = []
    r = requests.get(BASE_URL + "/api/queue/get_all_positions/",
                     data=data, headers=headers)
    response_body = r.json()
    if agent_data['leader']:
        queque_details = response_body
    else:
        place_in_queque = next(
            (q['order'] for q in response_body if q['agent_id'] == agent_data['agent']), None)
    if r.status_code // 100 == 2:
        return {
            'queque_details': queque_details,
            'queque_length': len(response_body),
            'place': place_in_queque
        }
    else:
        return None


async def check_break_availability(project_id, agent_id):
    headers = await get_authorization()
    data = {"project": project_id}
    response = requests.get(
        BASE_URL + '/api/queue/get_next_agents/', data=data, headers=headers)
    response_body = response.json()
    if response.status_code // 100 == 2:
        if len(response_body['queque']) == 0 or len(response_body['queque']) < response_body['range_details']['people_limit']:
            return True
        can_go_to_break = next(
            (q for q in response_body['queque'] if q['agent_id'] == agent_id), None)
        if can_go_to_break:
            return True
        else:
            return False
    else:
        return False


async def check_break_range(project_id):
    headers = await get_authorization()
    data = {"project": project_id}
    response = requests.get(
        BASE_URL + '/api/queue/get_next_agents/', data=data, headers=headers)
    response_body = response.json()
    if response.status_code // 100 == 2:
        return response_body
    else:
        print(response)
        return []


async def check_if_in_queque(agent_data):
    headers = await get_authorization()
    response = requests.get(
        BASE_URL + "/api/queue/get_agent_positions/", data=agent_data, headers=headers)
    response_body = response.json()
    if response.status_code // 100 == 2:
        return response_body
    else:
        return None


async def check_active_breaks(project):
    headers = await get_authorization()
    breaks = requests.get(
        BASE_URL + "/api/queue/get_active_breakes/", data={'project': project}, headers=headers)
    if breaks.status_code // 100 == 2:
        return breaks.json()
    else:
        return None


async def add_agent_to_break_queue(data):
    headers = await get_authorization()
    response = requests.post(
        BASE_URL + "/api/queue/add_agent/", data=data, headers=headers)
    response_body = response.json()
    if response.status_code // 100 == 2:
        return response_body['message']
    else:
        return response_body['error']


async def check_if_on_break(agent_data):
    for ap in agent_data['projects']:
        breaks = await check_active_breaks(ap)
        if breaks:
            user_break = next(
                (b for b in breaks if b['agent'] == agent_data['user_api_id']), None)
            return {'is_on_break': True, 'project': user_break['project'], 'quick_break': user_break['quick_break']} if user_break else {'is_on_break': False, 'project': None, 'quick_break': False}

    return {'is_on_break': False, 'project': None, 'quick_break': False}


async def handle_break(agent_data, action, quick_break=False):
    headers = await get_authorization()
    request_address = f"{BASE_URL}/api/break/{action}/"
    if action == 'start':
        if quick_break:
            agent_data['quick_break'] = True
        response = requests.post(
            request_address, data=agent_data, headers=headers)
    if action == 'end':
        response = requests.put(
            request_address, data=agent_data, headers=headers)
    if response.status_code // 100 == 2:
        if quick_break or action == 'end':
            return True
        if action == 'start':
            in_queque = await check_if_in_queque(agent_data=agent_data)
            if in_queque:
                return await remove_from_queue(agent_data=agent_data)
            else:
                return True
    else:
        print('Error: ', response)
        return False


async def remove_from_queue(agent_data):
    headers = await get_authorization()
    delete = requests.delete(
        BASE_URL + "/api/queue/remove_agent/", data=agent_data, headers=headers)
    # db_test.update_one({"id_in_project": agent_data['agent']}, {
    #                    "$unset": {"sent_to_break": 1}})
    return True if delete.status_code // 100 == 2 else False


async def get_graph_token():
    CLIENT_ID = config.CLIENT_ID
    CLIENT_SECRET = config.CLIENT_SECRET
    TENANT_ID = config.TENANT_ID
    # Scope for accessing Microsoft Graph API
    SCOPE = ['https://graph.microsoft.com/.default']

    # Define the URL for token endpoint
    TOKEN_ENDPOINT = f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token'

    # Function to authenticate and obtain access token
    token_data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': ' '.join(SCOPE),
        'grant_type': 'client_credentials'
    }
    response = requests.post(TOKEN_ENDPOINT, data=token_data)
    access_token = response.json().get('access_token')
    return access_token


# async def send_graph_request():
#     # Define the URL for Microsoft Graph API
#     GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
#     request_body = {
#         "chatType": "oneOnOne",
#         "members": [
#             {
#                 "@odata.type": "#microsoft.graph.aadUserConversationMember",
#                 "roles": ["owner"],
#                 "user@odata.bind": "https://graph.microsoft.com/v1.0/users('de650dc0-c698-4ab2-9f0e-3f8021f132f7')"
#             },
#             {
#                 "@odata.type": "#microsoft.graph.aadUserConversationMember",
#                 "roles": ["owner"],
#                 "user@odata.bind": "https://graph.microsoft.com/v1.0/users('a2eb7e8f-a9fd-45ea-80ab-77d6df131260')"
#             }
#         ]
#     }

#   # Authenticate and obtain access token
#     # access_token = await get_graph_token()
#     email = '4KapustaAd@projekty.voicecc.pl'
#     access_token = 'eyJ0eXAiOiJKV1QiLCJub25jZSI6IldQdmxoUmgxNm5qdnFWSGZ0V0ljMnpNeFZmNzF5M1NqNDJBZVNJNV9PRTQiLCJhbGciOiJSUzI1NiIsIng1dCI6IkwxS2ZLRklfam5YYndXYzIyeFp4dzFzVUhIMCIsImtpZCI6IkwxS2ZLRklfam5YYndXYzIyeFp4dzFzVUhIMCJ9.eyJhdWQiOiIwMDAwMDAwMy0wMDAwLTAwMDAtYzAwMC0wMDAwMDAwMDAwMDAiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC8wMWY1NmY3ZC1jMjk4LTRlYTMtODFkZC05YTlhY2JhMzc1NmIvIiwiaWF0IjoxNzE0Mzk0OTk5LCJuYmYiOjE3MTQzOTQ5OTksImV4cCI6MTcxNDQ4MTY5OSwiYWNjdCI6MCwiYWNyIjoiMSIsImFpbyI6IkFUUUF5LzhXQUFBQS9IeHBOaHp0S2RBSnlqdytBOTJESjRGdW41NkFZZFJERzRIYmFlL2ttV2xqUFk3RmVmd0pHaUZJS0hqVDhPQmMiLCJhbXIiOlsicHdkIl0sImFwcF9kaXNwbGF5bmFtZSI6IkdyYXBoIEV4cGxvcmVyIiwiYXBwaWQiOiJkZThiYzhiNS1kOWY5LTQ4YjEtYThhZC1iNzQ4ZGE3MjUwNjQiLCJhcHBpZGFjciI6IjAiLCJmYW1pbHlfbmFtZSI6IlXFgmFub3dza2kiLCJnaXZlbl9uYW1lIjoiU3p5bW9uIiwiaWR0eXAiOiJ1c2VyIiwiaXBhZGRyIjoiMTA5LjIzMy44OC4zOCIsIm5hbWUiOiJTenltb24gVcWCYW5vd3NraSIsIm9pZCI6ImRlNjUwZGMwLWM2OTgtNGFiMi05ZjBlLTNmODAyMWYxMzJmNyIsInBsYXRmIjoiMyIsInB1aWQiOiIxMDAzMjAwMTRCNTQwNzRGIiwicmgiOiIwLkFWOEFmV18xQVpqQ28wNkIzWnFheTZOMWF3TUFBQUFBQUFBQXdBQUFBQUFBQUFBUEFVNC4iLCJzY3AiOiJDaGFubmVsTWVzc2FnZS5SZWFkLkFsbCBDaGF0LkNyZWF0ZSBDaGF0LlJlYWQgQ2hhdC5SZWFkV3JpdGUgR3JvdXAuUmVhZC5BbGwgb3BlbmlkIHByb2ZpbGUgVXNlci5SZWFkIFVzZXIuUmVhZC5BbGwgZW1haWwiLCJzaWduaW5fc3RhdGUiOlsia21zaSJdLCJzdWIiOiIwakxJd1hzeWltRlN5MFV1cmtLLTFsY3p4OVZlb3g1Wko0SEpXVVZrQWRzIiwidGVuYW50X3JlZ2lvbl9zY29wZSI6IkVVIiwidGlkIjoiMDFmNTZmN2QtYzI5OC00ZWEzLTgxZGQtOWE5YWNiYTM3NTZiIiwidW5pcXVlX25hbWUiOiJzenltb24udWxhbm93c2tpQG9leC12Y2MuY29tIiwidXBuIjoic3p5bW9uLnVsYW5vd3NraUBvZXgtdmNjLmNvbSIsInV0aSI6IjktYU16SGdCQmtpZGxBOFdNTG9CQUEiLCJ2ZXIiOiIxLjAiLCJ3aWRzIjpbIjliODk1ZDkyLTJjZDMtNDRjNy05ZDAyLWE2YWMyZDVlYTVjMyIsIjE1OGMwNDdhLWM5MDctNDU1Ni1iN2VmLTQ0NjU1MWE2YjVmNyIsImI3OWZiZjRkLTNlZjktNDY4OS04MTQzLTc2YjE5NGU4NTUwOSJdLCJ4bXNfY2MiOlsiQ1AxIl0sInhtc19zc20iOiIxIiwieG1zX3N0Ijp7InN1YiI6ImJuNkFld3pMUjhGUUQzeVpGRV9FS1lDUExvdFJXV3dGZ1o0NEpXVnhiUTAifSwieG1zX3RjZHQiOjE1MTQ0MDA2NjgsInhtc190ZGJyIjoiRVUifQ.Q2nCUJTK2U8s922n9R-TphPVUATLgc1p8eQr4dai4IslS0dpkTM3wLSQswVVFXPGhO976KTFDFmuJcaQdfyUnytSMb8A_1JET7u5bXyj1K_CybJBGeYFKL3k9Vj4i9Yu6GM23CGzynZt0i3UNq6JrxhwlZCxTVotsoVrRtKNGjrEfuNRhdcvUhzAEE_v0BRYdL_WnpBs0BM0PuvBiyTFD848dpa3f8xhjrslukoZsKaVcOeC513wvzwDFSQBiABKwaTq6t797Wp3_XHOTtTnzUZb5EFBgfS_fXMuwIepdsyw3pECzJmZ3gXbr1RR81cmTmgGlO2cajGL8wBAPrnpgw'
#     # Define headers with access token
#     headers = {
#         'Authorization': 'Bearer ' + str(access_token),
#         'Content-Type': 'application/json'
#     }

#     # Make a POST request to create a chat
#     response = requests.get(f'{GRAPH_API_ENDPOINT}/users/{email}',
#                             headers=headers, json=request_body)

#     # Print the response
#     print('Response:', response.json())


async def create_conversation_id(recipient_teams_id, bot_id, headers):
    TENANT_ID = config.TENANT_ID
    # Replace with the user's Teams ID
    user_teams_id = recipient_teams_id
    # Create a conversation
    create_conversation_url = "https://smba.trafficmanager.net/teams/v3/conversations"

    conversation_parameters = {
        'bot': {
            "id": bot_id,
            "name": "Ziutek",
            "role": "bot"
        },
        "members": [{"id": user_teams_id}],
        'tenantId': TENANT_ID
    }
    response = requests.post(create_conversation_url,
                             headers=headers, data=json.dumps(conversation_parameters))
    # Check the status code
    if response.ok:
        conversation_id = response.json().get("id")
        return conversation_id
    else:
        error = response.json()
        error_msg = error['error']['message']
        raise Exception(error_msg)
        # Access the message from the JSON
        # print(error_message)
    # Send a proactive message

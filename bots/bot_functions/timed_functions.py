import asyncio
from botbuilder.core import TurnContext
from data_models.conversation_data import ConversationData
from .api_calls import check_break_availability


def _timer_func_wrapper(func):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(func)


# async def _wait_for_break(data, turn_context: TurnContext, convo_accessor, conversation_data, scheduler):
#     break_time = check_break_availability(data)
#     if break_time['break_allowed']:
#         message = 'Czas na przerwę!'
#         conversation_data.asked_to_go_for_a_break = True
#         # user_profile.check_check = 'test'
#         await convo_accessor.set(turn_context, conversation_data)
#         # await user_accesor.set(turn_context, user_profile)
#         if (hasattr, conversation_data, 'job_id'):
#             scheduler.remove_job(conversation_data.job_id)
#         # return 'Czas na przerwę!'
#     else:
#         message = 'Jeszcze nie czas na przerwę! :('
#     await turn_context.send_activity(message)

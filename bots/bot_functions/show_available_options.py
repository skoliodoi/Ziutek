from botbuilder.core import TurnContext
from responses.cards import create_adaptive_card


async def _show_available_options(turn_context: TurnContext, action, commands, returns_from_break=False):
    show_additional_message = False
    message = "Wybierz co mogę dla ciebie zrobić z listy komend dostępnych poniżej:"
    if action == 'queue':
        message = 'Zapisać się ponownie w kolejce?' if returns_from_break else 'Zapisać cię w kolejce na przerwę?'
        show_additional_message = True
    card = create_adaptive_card(message, commands)
    if show_additional_message and not returns_from_break:
        await turn_context.send_activity("Kurczę, wygląda na to, że teraz nie możesz iść na przerwę :/")
    await turn_context.send_activity(card)
    return

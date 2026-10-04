import pytest

from tests.helpers import make_game
from twilight_cards import GameCards
from twilight_enums import Side, CardAction


SCORING_CARDS = [name for name, card in GameCards().ALL.items() if card.card_type == 'Scoring']


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('card', SCORING_CARDS)
@pytest.mark.parametrize('optional_round', [False, True])
def test_scoring_actions_offer_only_event_even_with_modifiers_and_optional_round(side, card, optional_round):
    game = make_game()
    game.turn_track, game.ar_track = 4, 8 if optional_round else 1
    game.ars_by_turn[side][4] = 8
    game.basket[side].append('Brezhnev_Doctrine' if side == Side.USSR else 'Containment')
    game.select_action(side, card)
    assert list(game.input_state.legal_options) == [CardAction.PLAY_EVENT.name]
    for action in CardAction:
        if action != CardAction.PLAY_EVENT:
            assert game.input_state.recv(action.name) is False
    assert game.input_state.reps == 1 and game.stage_list == []


@pytest.mark.parametrize('actor', [Side.USSR, Side.US])
@pytest.mark.parametrize('scoring', ['Asia_Scoring', 'Africa_Scoring'])
def test_grain_received_scoring_can_only_score_and_settles_once(actor, scoring):
    game = make_game()
    game.ar_side = actor
    game.hand[Side.USSR] = [scoring]
    expected = make_game()
    expected.cards[scoring].use_event(expected, Side.US)
    game.cards['Grain_Sales_to_Soviets'].use_event(game, actor)
    assert game.input_state.recv(scoring) is True
    game.stage_complete()
    assert game.input_state.recv('Use card normally') is True
    assert list(game.input_state.legal_options) == [CardAction.PLAY_EVENT.name]
    assert game.input_state.recv(CardAction.PLAY_EVENT.name) is True
    while game.stage_list:
        game.stage_complete()
    assert game.vp_track == expected.vp_track
    assert game.cards[scoring].event_occurred
    assert scoring not in game.hand[Side.US]
    assert game.discard_pile.count(scoring) == 1


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('card', ['Blank_2_Op_Card', 'Blank_4_Op_Card'])
def test_ordinary_cards_keep_their_ops_choices(side, card):
    game = make_game()
    game.select_action(side, card)
    assert {CardAction.INFLUENCE.name, CardAction.COUP.name, CardAction.REALIGNMENT.name} <= set(game.input_state.legal_options)

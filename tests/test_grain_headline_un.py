from copy import deepcopy

import pytest

from tests.helpers import make_game
from twilight_enums import Side, InputType, CardAction


@pytest.mark.parametrize('actor', [Side.USSR, Side.US])
@pytest.mark.parametrize('ar', [0, 1])
@pytest.mark.parametrize('draw', ['UN_Intervention', 'Fidel'])
@pytest.mark.parametrize('cloned', [False, True])
def test_grain_received_card_respects_headline_un_ban_and_return(actor, ar, draw, cloned):
    game = make_game()
    game.ar_side, game.ar_track = actor, ar
    game.hand[Side.USSR] = [draw]
    game.hand[Side.US] = ['Fidel'] if draw == 'UN_Intervention' else ['UN_Intervention']
    game.cards['Grain_Sales_to_Soviets'].use_event(game, actor)
    assert game.input_state.recv(draw) is True
    assert draw in game.hand[Side.US] and draw not in game.hand[Side.USSR]
    source = game
    if cloned:
        game = deepcopy(game)
    game.stage_complete()
    expected = ['Return card to USSR'] if ar == 0 and draw == 'UN_Intervention' else [
        'Use card normally', 'Return card to USSR']
    if ar > 0 and draw == 'Fidel':
        expected.append('Use card with UN Intervention')
    inp = game.input_state
    assert list(inp.legal_options) == expected
    if ar == 0:
        for invalid in ['Use card with UN Intervention'] + (
                ['Use card normally'] if draw == 'UN_Intervention' else []):
            assert inp.recv(invalid) is False
            assert inp.reps == 1 and game.stage_list == []
            assert draw in game.hand[Side.US]
    assert inp.recv('Return card to USSR') is True
    assert game.hand[Side.USSR] == [draw]
    assert draw not in game.hand[Side.US]
    assert game.discard_pile == [] and game.removed_pile == []
    assert game.input_state.state == InputType.SELECT_CARD_ACTION
    assert game.input_state.side == Side.US
    assert game.input_state.context['source_card'] == 'Blank_2_Op_Card'
    assert game.input_state.context['is_event_resolved']
    assert CardAction.INFLUENCE.name in game.input_state.legal_options
    if cloned:
        assert draw in source.hand[Side.US] and source.hand[Side.USSR] == []
        assert source.input_state.complete and len(source.stage_list) == 1


@pytest.mark.parametrize('actor', [Side.USSR, Side.US])
@pytest.mark.parametrize('cloned', [False, True])
def test_grain_ordinary_round_preserves_legal_un_pairing(actor, cloned):
    game = make_game()
    game.ar_side = actor
    game.hand[Side.USSR] = ['Fidel']
    game.hand[Side.US] = ['UN_Intervention']
    game.cards['Grain_Sales_to_Soviets'].use_event(game, actor)
    assert game.input_state.recv('Fidel') is True
    game.stage_complete()
    source = game
    if cloned:
        game = deepcopy(game)
    assert game.input_state.recv('Use card with UN Intervention') is True
    assert game.input_state.state == InputType.SELECT_CARD_ACTION
    assert game.input_state.context['source_card'] == 'Fidel'
    assert game.input_state.context['un_intervention']
    assert CardAction.PLAY_EVENT.name not in game.input_state.legal_options
    assert CardAction.RESOLVE_EVENT_FIRST.name not in game.input_state.legal_options
    assert CardAction.INFLUENCE.name in game.input_state.legal_options
    assert game.hand[Side.US] == ['UN_Intervention', 'Fidel']
    assert not game.cards['Fidel'].event_occurred
    if cloned:
        assert source.input_state.state == InputType.SELECT_MULTIPLE
        assert source.stage_list == []


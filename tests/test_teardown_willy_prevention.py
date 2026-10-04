"""The real Tear Down This Wall event must prevent future Willy Brandt events."""

from copy import deepcopy

import pytest

from tests.helpers import make_game
from twilight_enums import CardAction, Side


@pytest.mark.parametrize('trigger', [Side.US, Side.USSR])
@pytest.mark.parametrize('willy_active', [False, True])
@pytest.mark.parametrize('on_clone', [False, True])
def test_teardown_prevents_willy_after_real_event_and_turn_cleanup(
        trigger, willy_active, on_clone):
    original = make_game()
    original.turn_track = 7
    original.basket[Side.US].append('NATO')
    original.map['West_Germany'].set_influence(0, 5)
    if willy_active:
        original.trigger_event(Side.USSR, 'Willy_Brandt')
    assert original.map.can_coup(
        original, 'West_Germany', Side.USSR) is willy_active
    game = deepcopy(original) if on_clone else original
    game.add_turn_effect(Side.US, 'Containment')
    game.hand[trigger].append('Tear_Down_This_Wall')
    game.trigger_event(trigger, 'Tear_Down_This_Wall')
    assert game.basket[Side.US].count('Tear_Down_This_Wall') == 1
    assert 'Willy_Brandt' not in game.basket[Side.USSR]
    assert game.map['East_Germany'].influence[Side.US] == 3
    assert 'West_Germany' in game.calculate_nato_countries()
    assert not game.map.can_coup(game, 'West_Germany', Side.USSR)
    assert not game.map.can_realignment(game, 'West_Germany', Side.USSR)
    game.cards['Tear_Down_This_Wall'].dispose(game, trigger)
    assert game.removed_pile.count('Tear_Down_This_Wall') == 1

    # Advance a real turn with enough ordinary cards to avoid a shuffle prompt.
    game.input_state = None
    game.draw_pile = [n for n, c in game.cards.ALL.items()
                      if c.info.card_type != 'Scoring'
                      and n not in ('The_China_Card', 'Tear_Down_This_Wall')][:20]
    game.end_of_turn()
    assert game.turn_track == 8 and not game.terminated
    assert 'Containment' not in game.basket[Side.US]
    assert game.basket[Side.US].count('Tear_Down_This_Wall') == 1
    before = (game.vp_track, list(game.map['West_Germany'].influence))
    for side in (Side.USSR, Side.US):
        assert not game.cards['Willy_Brandt'].can_event(game, side)
        game.trigger_event(side, 'Willy_Brandt')
        assert (game.vp_track, game.map['West_Germany'].influence) == before
        game.select_action(side, 'Willy_Brandt')
        assert CardAction.PLAY_EVENT.name not in game.input_state.legal_options
        assert CardAction.RESOLVE_EVENT_FIRST.name not in game.input_state.legal_options
        assert CardAction.INFLUENCE.name in game.input_state.legal_options
    assert 'Willy_Brandt' not in game.basket[Side.USSR]
    if on_clone:
        assert 'Tear_Down_This_Wall' not in original.basket[Side.US]
        assert ('Willy_Brandt' in original.basket[Side.USSR]) is willy_active
        assert original.turn_track == 7

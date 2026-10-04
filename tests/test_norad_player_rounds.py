from copy import deepcopy

import pytest

from tests.helpers import make_game
from twilight_enums import Side, InputType


@pytest.mark.parametrize('actor,turn,ar,rounds,last', [
    (Side.USSR, 1, 1, (6, 6), False), (Side.US, 1, 1, (6, 6), False),
    (Side.USSR, 1, 6, (6, 6), False), (Side.US, 1, 6, (6, 6), True),
    (Side.USSR, 4, 7, (7, 7), False), (Side.US, 4, 7, (7, 7), True),
    (Side.USSR, 4, 8, (8, 7), True), (Side.US, 4, 8, (7, 8), True),
])
@pytest.mark.parametrize('cloned', [False, True])
def test_norad_resolves_before_advancing_each_player_round(actor, turn, ar, rounds, last, cloned):
    game = make_game()
    game.turn_track, game.ar_track, game.ar_side = turn, ar, actor
    for side in (Side.USSR, Side.US):
        game.ars_by_turn[side][turn] = rounds[side]
    game.ar_side_done = [actor == Side.US, actor == Side.USSR and ar > rounds[Side.US]]
    game.basket[Side.US].append('NORAD')
    game.map['Canada'].set_influence(0, 4)
    game.map['South_Korea'].set_influence(0, 1)
    game.defcon_track = 3
    game.change_defcon(-1)
    source = game
    if cloned:
        game = deepcopy(game)
    game.ar_complete()
    inp = game.input_state
    assert inp is not None and inp.prompt == 'Place NORAD influence.'
    assert game.ar_side == actor and game.ar_track == ar
    assert not game.defcon_reached_two_this_ar
    assert inp.side == Side.US and inp.state == InputType.SELECT_COUNTRY
    assert inp.context['source_card'] == 'NORAD'
    assert all(game.map[n].influence[Side.US] > 0 for n in inp.legal_options)
    assert inp.recv('South_Korea') is True
    assert game.map['South_Korea'].influence[Side.US] == 2
    game.stage_complete()  # Resume the same AR end, without a second NORAD reward.
    assert game.input_state is None and not game.defcon_reached_two_this_ar
    if last:
        assert game.stage_list[-1].__name__ == 'end_of_turn'
    elif actor == Side.USSR:
        assert game.ar_side == Side.US and game.ar_track == ar
    else:
        assert game.ar_side == Side.USSR and game.ar_track == ar + 1
    if cloned:
        assert source.ar_side == actor and source.ar_track == ar
        assert source.defcon_reached_two_this_ar and source.input_state is None
        assert source.map['South_Korea'].influence[Side.US] == 1
        assert source.stage_list == []


@pytest.mark.parametrize('actor', [Side.USSR, Side.US])
@pytest.mark.parametrize('reason', ['headline', 'no_drop', 'inactive', 'no_canada', 'quagmire'])
def test_norad_does_not_leak_an_ineligible_rounds_trigger(actor, reason):
    game = make_game()
    game.ar_side = actor
    game.basket[Side.US].append('NORAD')
    game.map['Canada'].set_influence(0, 4)
    game.defcon_track = 3
    if reason == 'headline':
        game.ar_track = 0
    if reason != 'no_drop':
        game.change_defcon(-1)
    if reason == 'inactive':
        game.basket[Side.US].remove('NORAD')
    elif reason == 'no_canada':
        game.map['Canada'].set_influence(0, 0)
    elif reason == 'quagmire':
        game.cards['Quagmire'].use_event(game, Side.USSR)
    before = game.map['South_Korea'].influence[Side.US]
    game.ar_complete()
    assert game.input_state is None
    assert not game.defcon_reached_two_this_ar
    assert game.map['South_Korea'].influence[Side.US] == before


def test_norad_can_reward_both_players_rounds_in_the_same_numbered_pair():
    game = make_game()
    game.basket[Side.US].append('NORAD')
    game.map['Canada'].set_influence(0, 4)
    game.map['South_Korea'].set_influence(0, 1)
    for actor in (Side.USSR, Side.US):
        assert game.ar_side == actor and game.ar_track == 1
        game.defcon_track = 3
        game.change_defcon(-1)
        game.ar_complete()
        assert game.input_state.recv('South_Korea') is True
        game.stage_complete()
        game.stage_list.clear()
    assert game.map['South_Korea'].influence[Side.US] == 3
    assert game.ar_side == Side.USSR and game.ar_track == 2


@pytest.mark.parametrize('actor', [Side.USSR, Side.US])
def test_norad_cannot_revive_a_terminated_game(actor):
    game = make_game()
    game.ar_side = actor
    game.basket[Side.US].append('NORAD')
    game.map['Canada'].set_influence(0, 4)
    game.defcon_track = 3
    game.change_defcon(-1)
    game.change_defcon(-1)
    assert game.terminated
    game.ar_complete()
    assert game.input_state is None and game.stage_list == []
    assert game.ar_side == actor and game.ar_track == 1

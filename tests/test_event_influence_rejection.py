from copy import deepcopy

import pytest

from tests.helpers import make_game
from twilight_enums import Side
from twilight_map import Country


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('operation', [Country.decrement_influence, Country.remove_influence])
def test_rejected_influence_mutation_does_not_spend_repetitions(side, operation):
    game = make_game()
    game.map['Iran'].influence[side] = 0
    game.map['Cuba'].influence[side] = 1
    game.event_place_influence(side, operation, side, ('Iran', 'Cuba'), 'Remove influence.', reps=2)
    inp = game.input_state
    assert inp.recv('Iran') is False
    assert inp.reps == 2 and inp.selection['Iran'] == 0
    assert inp.recv('Cuba') is True
    assert inp.reps == 1 and game.map['Cuba'].influence[side] == 0
    game.map['Iran'].influence[side] = 1
    assert inp.recv('Iran') is True
    assert inp.complete and game.map['Iran'].influence[side] == 0


@pytest.mark.parametrize('actor', [Side.USSR, Side.US])
def test_destalinization_does_not_relocate_a_rejected_removal(actor):
    game = make_game()
    for country in game.map.ALL.values():
        country.influence[Side.USSR] = 0
    for name in ('Iran', 'Cuba'):
        game.map[name].influence[Side.USSR] = 2
    game.cards['De_Stalinization'].use_event(game, actor)
    inp = game.input_state
    game.map['Iran'].influence[Side.USSR] = 0
    assert inp.recv('Iran') is False
    assert inp.reps == 4 and inp.option_stop_early == 'Move no influence.'
    assert inp.selection['Iran'] == 0
    assert inp.recv('Cuba') is True
    assert inp.recv('Cuba') is True
    assert inp.recv('Move 2 influence.') is True
    assert game.input_state.reps == 2
    assert game.input_state.recv('Iran') is True
    assert game.input_state.recv('Iran') is True
    assert game.input_state.complete
    assert game.map['Iran'].influence[Side.USSR] == 2


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('remaining', [0, 1, 2, 3])
def test_cmc_rechecks_its_full_two_marker_cost(side, remaining):
    game = make_game()
    country = 'Cuba' if side == Side.USSR else 'Turkey'
    game.map[country].influence[side] = 3
    game.basket[side.opp].append('Cuban_Missile_Crisis')
    assert game.cards['Cuban_Missile_Crisis'].cuban_missile_remove(game, side) is True
    inp = game.input_state
    game.map[country].influence[side] = remaining
    if remaining < 2:
        assert inp.recv(country) is False
        assert inp.reps == 1 and inp.selection[country] == 0
        assert game.map[country].influence[side] == remaining
        assert 'Cuban_Missile_Crisis' in game.basket[side.opp]
        assert inp.recv('Do not remove influence.') is True
        assert 'Cuban_Missile_Crisis' in game.basket[side.opp]
    else:
        assert inp.recv(country) is True
        assert game.map[country].influence[side] == remaining - 2
        assert 'Cuban_Missile_Crisis' not in game.basket[side.opp]
    assert inp.complete


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
def test_cmc_removal_callback_still_rebinds_to_the_cloned_game(side):
    game = make_game()
    country = 'Cuba' if side == Side.USSR else 'Turkey'
    game.map[country].influence[side] = 3
    game.basket[side.opp].append('Cuban_Missile_Crisis')
    game.cards['Cuban_Missile_Crisis'].cuban_missile_remove(game, side)
    clone = deepcopy(game)
    assert clone.input_state.recv(country) is True
    assert clone.map[country].influence[side] == 1
    assert game.map[country].influence[side] == 3 and game.input_state.reps == 1
    assert 'Cuban_Missile_Crisis' in game.basket[side.opp]

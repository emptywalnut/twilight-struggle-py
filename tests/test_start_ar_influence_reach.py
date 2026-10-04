from copy import deepcopy

import pytest

from tests.helpers import make_game
from twilight_enums import Side
from twilight_map import Country


def empty_map():
    game = make_game()
    for country in game.map.ALL.values():
        if not country.info.superpower:
            country.set_influence(0, 0)
    return game


def begin_round(game):
    game.ar_track = 0
    game.ar_complete()
    game.stage_list.clear()


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('round_started', [False, True])
@pytest.mark.parametrize('cloned', [False, True])
def test_ops_cannot_chain_through_a_marker_just_placed(side, round_started, cloned):
    game = empty_map()
    game.map['Nicaragua'].influence[side] = 1
    if round_started:
        begin_round(game)
    game.card_operation_influence(side, 'Blank_4_Op_Card')
    source = game
    if cloned:
        game = deepcopy(game)
    inp = game.input_state
    assert 'Costa_Rica' in inp.legal_options and 'Panama' not in inp.legal_options
    assert inp.recv('Costa_Rica') is True
    assert 'Panama' not in inp.legal_options
    before, reps = list(game.map['Panama'].influence), inp.reps
    assert inp.recv('Panama') is False
    assert game.map['Panama'].influence == before and inp.reps == reps
    assert inp.recv('Costa_Rica') is True
    if cloned:
        assert source.map['Costa_Rica'].influence[side] == 0
        assert source.input_state.reps == 4


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
def test_reach_is_refreshed_for_the_next_players_round(side):
    game = empty_map()
    game.map['Nicaragua'].influence[side] = 1
    begin_round(game)
    game.card_operation_influence(side, 'Blank_4_Op_Card')
    assert game.input_state.recv('Costa_Rica') is True
    assert 'Panama' not in game.input_state.legal_options
    game.input_state = None
    game.ar_complete()  # US starts its own AR, not a new numbered pair.
    game.stage_list.clear()
    assert game.ar_side == Side.US and game.ar_track == 1
    assert game.map.can_place_influence(game, 'Panama', side, 4)
    game.card_operation_influence(side, 'Blank_4_Op_Card')
    assert game.input_state.recv('Panama') is True


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('cloned', [False, True])
def test_removing_a_starting_marker_does_not_shrink_frozen_reach(side, cloned):
    game = empty_map()
    game.map['Finland'].influence[side] = 1
    begin_round(game)
    source = game
    if cloned:
        game = deepcopy(game)
    game.event_place_influence(side.opp, Country.remove_influence, side, ['Finland'], 'Remove influence.', reps=1)
    assert game.input_state.recv('Finland') is True
    assert game.map['Finland'].influence[side] == 0
    assert game.map.can_place_influence(game, 'Sweden', side, 4)
    game.card_operation_influence(side, 'Blank_4_Op_Card')
    assert game.input_state.recv('Sweden') is True
    if cloned:
        assert source.map['Finland'].influence[side] == 1
        assert source.map['Sweden'].influence[side] == 0


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('round_started', [False, True])
@pytest.mark.parametrize('cloned', [False, True])
def test_control_cost_changes_live_without_expanding_reach(side, round_started, cloned):
    game = empty_map()
    game.map['West_Germany'].influence[side] = 1
    game.map['France'].influence[side.opp] = 3
    if round_started:
        begin_round(game)
    game.card_operation_influence(side, 'Blank_4_Op_Card')
    source = game
    if cloned:
        game = deepcopy(game)
    inp = game.input_state
    assert inp.recv('France') is True and inp.reps == 2
    assert game.map['France'].control != side.opp
    assert 'Algeria' not in inp.legal_options
    assert inp.recv('France') is True and inp.reps == 1
    assert inp.recv('France') is True and inp.complete
    if cloned:
        assert source.map['France'].influence[side] == 0
        assert source.input_state.reps == 4


@pytest.mark.parametrize('phasing', [Side.USSR, Side.US])
@pytest.mark.parametrize('cloned', [False, True])
def test_event_placed_influence_does_not_expand_same_round_ops_reach(phasing, cloned):
    game = empty_map()
    begin_round(game)
    if phasing == Side.US:
        game.ar_complete()
        game.stage_list.clear()
    assert not game.map.can_place_influence(game, 'Haiti', Side.USSR, 4)
    source = game
    if cloned:
        game = deepcopy(game)
    game.cards['Fidel'].use_event(game, Side.US)
    assert game.map['Cuba'].influence[Side.USSR] == 3
    assert not game.map.can_place_influence(game, 'Haiti', Side.USSR, 4)
    game.card_operation_influence(Side.USSR, 'Blank_4_Op_Card')
    assert 'Haiti' not in game.input_state.legal_options
    if cloned:
        assert source.map['Cuba'].influence[Side.USSR] == 0


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
def test_headline_ops_do_not_use_a_previous_round_reach_snapshot(side):
    game = empty_map()
    begin_round(game)
    game.ar_track = 0
    game.map['Finland'].influence[side] = 1
    assert game.map.can_place_influence(game, 'Sweden', side, 4)
    game.card_operation_influence(side, 'Blank_4_Op_Card')
    assert game.input_state.recv('Sweden') is True

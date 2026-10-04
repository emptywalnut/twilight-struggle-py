from copy import deepcopy
from functools import partial

import pytest

from tests.helpers import make_game
from twilight_enums import Side, InputType


def coup_game(side):
    game = make_game()
    game.map['Cuba'].set_influence(0, 2) if side == Side.USSR else game.map['Cuba'].set_influence(2, 0)
    for country in ['West_Germany', 'Turkey']:
        game.map[country].influence[side] = 0
    game.basket[Side.US].append('Nuclear_Subs')
    game.basket[Side.USSR].append('Yuri_and_Samantha')
    return game


def board(game):
    return {name: tuple(country.influence) for name, country in game.map.ALL.items()}


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('off_turn', [False, True])
@pytest.mark.parametrize('free', [False, True])
@pytest.mark.parametrize('path', ['map', 'stage', 'selected'])
@pytest.mark.parametrize('cloned', [False, True])
def test_cmc_coup_ends_before_dice_or_influence_changes(side, off_turn, free, path, cloned):
    game = coup_game(side)
    game.ar_side = side.opp if off_turn else side
    # Exercise a target input that became CMC-prohibited after it was created.
    if path == 'selected':
        game.card_operation_coup(side, 'Blank_4_Op_Card', restricted_list=['Cuba'], free=free)
        game.stage_complete()
        assert list(game.input_state.legal_options) == ['Cuba']
    game.basket[side.opp].append('Cuban_Missile_Crisis')
    game.stage_list.append(partial(game.select_card, side))
    initial_board, initial_hands = board(game), deepcopy(game.hand)
    initial_vp, initial_milops = game.vp_track, list(game.milops_track)
    source = game
    if cloned:
        game = deepcopy(game)
    if path == 'map':
        game.map.coup(game, 'Cuba', side, 4, 6, free=free)
    elif path == 'stage':
        game.card_operation_coup(side, 'Blank_4_Op_Card', restricted_list=['Cuba'], free=free)
        assert game.input_state is None  # Neither side can afford cancellation.
        game.stage_complete()
    else:
        assert game.input_state.recv('Cuba') is True
    assert game.terminated
    assert game.termination_winner == side.opp
    assert game.termination_reason == 'thermonuclear_war'
    assert game.termination_context == {
        'defcon': 1, 'cause': 'Cuban_Missile_Crisis', 'loser': side.toStr()}
    assert game.defcon_track == 1
    assert board(game) == initial_board and game.hand == initial_hands
    assert game.vp_track == initial_vp and game.milops_track == initial_milops
    assert game.input_state is None and game.stage_list == []
    if cloned:
        assert not source.terminated and source.defcon_track == 5
        assert board(source) == initial_board and source.hand == initial_hands
        assert len(source.stage_list) == 1
        if path == 'selected':
            assert source.input_state.reps == 1


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('cancel', [False, True])
def test_existing_cmc_cancellation_precedes_coup_loss(side, cancel):
    game = coup_game(side)
    country = 'Cuba' if side == Side.USSR else 'Turkey'
    game.map[country].influence[side] = 2
    game.basket[side.opp].append('Cuban_Missile_Crisis')
    game.card_operation_coup(side, 'Blank_4_Op_Card', restricted_list=['Cuba'])
    inp = game.input_state
    assert 'Cuban Missile Crisis' in inp.prompt
    assert inp.recv(country if cancel else inp.option_stop_early) is True
    before = board(game)
    game.stage_complete()
    if not cancel:
        assert game.terminated and game.termination_winner == side.opp
        assert board(game) == before and not game.stage_list
        return
    assert not game.terminated and 'Cuban_Missile_Crisis' not in game.basket[side.opp]
    assert game.map[country].influence[side] == 0
    assert game.input_state.recv('Cuba') is True
    assert not game.terminated and board(game) == before
    game.stage_complete()
    assert game.input_state.state == InputType.ROLL_DICE
    assert game.input_state.recv('6') is True
    assert not game.terminated and board(game) != before
    assert game.milops_track[side] == 4


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
def test_targetless_free_coup_is_not_a_cmc_attempt(side):
    game = coup_game(side)
    game.basket[side.opp].append('Cuban_Missile_Crisis')
    game.card_operation_coup(side, 'Blank_4_Op_Card', restricted_list=[], free=True)
    game.stage_complete()
    assert not game.terminated and game.defcon_track == 5
    assert game.input_state.complete and game.stage_list == []
    assert game.milops_track == [0, 0]


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('off_turn', [False, True])
def test_junta_free_coup_uses_actual_coup_side_for_cmc_loss(side, off_turn):
    game = coup_game(side)
    game.ar_side = side.opp if off_turn else side
    game.basket[side.opp].append('Cuban_Missile_Crisis')
    game.cards['Junta'].stage_2(game, side, ['Cuba'])
    before = board(game)
    assert game.input_state.recv('Free coup attempt') is True
    assert game.input_state.reps == 0
    game.stage_complete()
    assert game.terminated and game.termination_winner == side.opp
    assert board(game) == before and game.milops_track == [0, 0]
    assert game.input_state is None and game.stage_list == []


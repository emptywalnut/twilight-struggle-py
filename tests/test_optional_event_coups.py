"""Che and Ortega offer coups; opening the offer is not an attempt."""

from copy import deepcopy

import pytest

from tests.helpers import make_game
from twilight_enums import InputType, Side

EVENTS = [('Che', 'Skip Che coup.'),
          ('Ortega_Elected_in_Nicaragua', 'Skip Ortega coup.')]


def board(game):
    return {n: tuple(c.influence) for n, c in game.map.ALL.items()}


def open_event(card, actor, cmc=False, targets=True):
    game = make_game()
    game.ar_side, game.defcon_track = actor, 2
    for country in game.map.ALL.values():
        if not country.info.superpower:
            country.set_influence(0, 0)
    game.map['Cuba'].set_influence(3, 0)
    game.map['Nicaragua'].set_influence(0, 4)
    if targets:
        game.map['Honduras'].set_influence(0, 3)
        game.map['Uruguay'].set_influence(0, 3)
    if cmc:
        game.basket[Side.US].append('Cuban_Missile_Crisis')
    game.cards[card].use_event(game, actor)
    return game


@pytest.mark.parametrize('card,stop', EVENTS)
@pytest.mark.parametrize('actor', [Side.US, Side.USSR])
@pytest.mark.parametrize('choice', ['skip', 'cancel', 'attempt'])
@pytest.mark.parametrize('cloned', [False, True])
def test_cmc_offer_can_skip_cancel_or_lose_before_dice(card, stop, actor, choice, cloned):
    game = open_event(card, actor, cmc=True)
    # Native UI retains its existing pre-coup cancellation prompt.
    assert game.input_state.recv('Cuba' if choice == 'cancel'
                                 else game.input_state.option_stop_early)
    game.stage_complete()
    assert not game.terminated
    assert {'Honduras', stop} <= set(game.input_state.legal_options)
    original = game
    before = board(game)
    if cloned:
        game = deepcopy(game)
    assert game.input_state.recv(stop if choice == 'skip' else 'Honduras')
    if choice == 'attempt':
        assert game.terminated and game.termination_winner == Side.US
        assert game.defcon_track == 1 and game.stage_list == []
        assert game.input_state is None and board(game) == before
        assert game.milops_track == [0, 0]
    elif choice == 'skip':
        assert not game.terminated and game.input_state.complete
        assert not game.stage_list and board(game) == before
        assert 'Cuban_Missile_Crisis' in game.basket[Side.US]
        assert game.milops_track == [0, 0]
    else:
        assert not game.terminated and game.map['Cuba'].influence[Side.USSR] == 1
        assert 'Cuban_Missile_Crisis' not in game.basket[Side.US]
        game.stage_complete()
        assert game.input_state.state == InputType.ROLL_DICE
        assert game.input_state.recv('6')
        assert not game.terminated and board(game) != before
        assert game.milops_track[Side.USSR] == (3 if card == 'Che' else 0)
    if cloned:
        assert not original.terminated and board(original) == before
        assert original.input_state.reps == 1 and not original.stage_list


@pytest.mark.parametrize('second', ['skip', 'attempt'])
@pytest.mark.parametrize('cloned', [False, True])
def test_che_second_coup_is_optional_and_never_grants_a_third(second, cloned):
    game = open_event('Che', Side.USSR)
    game.stage_complete()
    assert game.input_state.recv('Uruguay')
    game.stage_complete()
    assert game.input_state.recv('6')
    game.stage_complete()
    assert 'Uruguay' not in game.input_state.legal_options
    assert {'Honduras', 'Skip Che coup.'} <= set(game.input_state.legal_options)
    original = game
    if cloned:
        game = deepcopy(game)
    assert game.input_state.recv('Skip Che coup.' if second == 'skip' else 'Honduras')
    if second == 'attempt':
        game.stage_complete()
        assert game.input_state.recv('6')
    assert not game.stage_list
    assert game.milops_track[Side.USSR] == (3 if second == 'skip' else 5)
    if cloned:
        assert original.input_state.reps == 1
        assert original.map['Honduras'].influence[Side.US] == 3
        assert original.milops_track[Side.USSR] == 3


@pytest.mark.parametrize('card,stop', EVENTS)
def test_targetless_optional_event_is_not_a_cmc_attempt(card, stop):
    game = open_event(card, Side.USSR, cmc=True, targets=False)
    # Che can target Nicaragua, so remove it for the targetless fixture.
    game.map['Nicaragua'].set_influence(0, 0)
    assert game.input_state.recv(game.input_state.option_stop_early)
    game.stage_complete()
    assert not game.terminated and game.defcon_track == 2
    assert game.input_state.complete and not game.stage_list
    assert game.milops_track == [0, 0]

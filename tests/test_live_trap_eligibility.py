"""One live predicate for trap menus, trial hands and consuming callbacks."""
from copy import deepcopy
from functools import partial

import pytest
from tests.helpers import make_game
from twilight_enums import Side

SCORING = ['Asia_Scoring', 'Middle_East_Scoring']


def trapped(side, hand, ar=1):
    game = make_game()
    game.ar_side, game.ar_track = side, ar
    trap = 'Quagmire' if side == Side.US else 'Bear_Trap'
    game.basket[side].append(trap)
    game.hand[side] = list(hand)
    return game, trap


@pytest.mark.parametrize('side', [Side.US, Side.USSR])
@pytest.mark.parametrize('hand,ar,forced,purged,pending,mode,options', [
    (['The_China_Card'], 1, False, False, None, 'skip', []),
    (['Asia_Scoring'], 1, False, False, None, 'scoring', ['Asia_Scoring']),
    (SCORING + ['NATO'], 6, False, False, None, 'scoring', SCORING),
    (['Asia_Scoring', 'Fidel'], 5, False, False, None, 'discard', ['Fidel']),
    (['Asia_Scoring', 'Fidel'], 6, False, False, None, 'scoring', ['Asia_Scoring']),
    (['Missile_Envy', 'NATO'], 1, True, False, None, 'discard', ['Missile_Envy']),
    (['Missile_Envy', 'NATO'], 1, True, True, None, 'discard', ['NATO']),
    (['Missile_Envy', 'NATO'], 1, False, False, None, 'discard', ['Missile_Envy', 'NATO']),
    (['NATO', 'Fidel'], 1, False, False, 'NATO', 'discard', ['Fidel']),
    (['Missile_Envy', 'NATO'], 1, True, False, 'Missile_Envy', 'discard', ['NATO']),
    (['Asia_Scoring', 'NATO'], 6, False, False, 'Asia_Scoring', 'discard', ['NATO']),
    (['Fidel'], 1, False, True, None, 'skip', []),
])
def test_trap_menu_and_trial_hand_use_same_eligibility(side, hand, ar, forced, purged, pending, mode, options):
    game, trap = trapped(side, hand, ar)
    if forced:
        game.basket[side].append('Missile_Envy')
    if purged:
        game.basket[side.opp].append('Red_Scare_Purge')
    if pending:
        game.stage_list.append(partial(game.cards[pending].dispose, game, side))
    game.qbt_discard(side, trap)
    actual = [] if game.input_state is None else list(game.input_state.legal_options)
    assert actual == options
    assert game.qbt_options(side) == (mode, options)
    assert game.qbt_options(side, hand=list(hand)) == (mode, options)
    assert game.hand[side] == hand
    if mode != 'skip':
        assert game.input_state.context['trap_mode'] == mode


@pytest.mark.parametrize('side', [Side.US, Side.USSR])
@pytest.mark.parametrize('change', ['missing', 'ops', 'pending', 'forced_envy', 'scoring_priority', 'trap_ended'])
@pytest.mark.parametrize('cloned', [False, True])
def test_stale_trap_discard_rejects_before_reps_piles_or_dice_queue(side, change, cloned):
    game, trap = trapped(side, ['Fidel', 'Nuclear_Test_Ban'])
    game.qbt_discard(side, trap)
    if cloned:
        game = deepcopy(game)
    inp = game.input_state
    if change == 'missing':
        game.hand[side].remove('Fidel')
    elif change == 'ops':
        game.basket[side.opp].append('Red_Scare_Purge')
    elif change == 'pending':
        game.stage_list.append(partial(game.cards['Fidel'].dispose, game, side))
    elif change == 'forced_envy':
        game.basket[side].append('Missile_Envy')
        game.hand[side].append('Missile_Envy')
    elif change == 'scoring_priority':
        game.ar_track = 6
        game.hand[side].append('Asia_Scoring')
    else:
        game.basket[side].remove(trap)
    hands, discards, stages = [list(h) for h in game.hand], list(game.discard_pile), list(game.stage_list)
    reps, selection = inp.reps, dict(inp.selection)
    assert inp.recv('Fidel') is False
    assert game.hand == hands and game.discard_pile == discards and game.stage_list == stages
    assert game.input_state is inp and inp.reps == reps and inp.selection == selection


@pytest.mark.parametrize('side', [Side.US, Side.USSR])
@pytest.mark.parametrize('change', ['missing', 'new_ops', 'trap_ended'])
@pytest.mark.parametrize('cloned', [False, True])
def test_stale_trap_scoring_rejects_before_consuming_choice(side, change, cloned):
    game, trap = trapped(side, ['Asia_Scoring'])
    game.qbt_discard(side, trap)
    if cloned:
        game = deepcopy(game)
    inp = game.input_state
    if change == 'missing':
        game.hand[side].clear()
    elif change == 'new_ops':
        game.hand[side].append('Fidel')
    else:
        game.basket[side].remove(trap)
    hands, stages = [list(h) for h in game.hand], list(game.stage_list)
    assert inp.recv('Asia_Scoring') is False
    assert game.hand == hands and game.stage_list == stages and inp.reps == 1
    assert game.input_state is inp and not game.discard_pile


@pytest.mark.parametrize('side', [Side.US, Side.USSR])
@pytest.mark.parametrize('roll', ['1', '6'])
def test_valid_forced_envy_discard_and_escape_roll_still_complete(side, roll):
    game, trap = trapped(side, ['Missile_Envy', 'NATO'])
    game.basket[side].append('Missile_Envy')
    game.cards['Missile_Envy'].event_occurred = game.cards['Missile_Envy'].exchange = True
    game.qbt_discard(side, trap)
    assert game.input_state.recv('Missile_Envy') is True
    assert game.discard_pile == ['Missile_Envy'] and game.hand[side] == ['NATO']
    assert 'Missile_Envy' not in game.basket[side]
    assert not game.cards['Missile_Envy'].event_occurred and not game.cards['Missile_Envy'].exchange
    game.stage_complete()
    assert game.input_state.recv(roll) is True
    assert game.input_state.complete and (trap in game.basket[side]) is (roll == '6')


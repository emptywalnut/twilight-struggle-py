"""Nonrandom hand choices must not reuse pending cards or accept stale choices."""
from copy import deepcopy
from functools import partial

import pytest

from tests.helpers import make_game
from twilight_enums import Side

EVENTS = (
    'UN_Intervention', 'Missile_Envy', 'Blockade',
    'Latin_American_Debt_Crisis', 'Ask_Not_What_Your_Country_Can_Do_For_You',
    'Aldrich_Ames_Remix',
)


def setup(event, actor=Side.US):
    game = make_game()
    game.ar_side = actor
    victim = actor if event == 'UN_Intervention' else actor.opp if event == 'Missile_Envy' else Side.US
    pending = 'Marshall_Plan' if victim == Side.US else 'Brezhnev_Doctrine'
    alternate = 'NATO' if victim == Side.US else 'COMECON'
    if event == 'Missile_Envy':
        pending, alternate = 'Nuclear_Test_Ban', 'Fidel'
    if event == 'UN_Intervention':
        pending, alternate = ('Brezhnev_Doctrine', 'Nasser') if actor == Side.US else ('Marshall_Plan', 'CIA_Created')
    game.hand[victim] = ['The_China_Card', pending, alternate]
    return game, victim, pending, alternate


@pytest.mark.parametrize('event', EVENTS)
@pytest.mark.parametrize('settlement', ['dispose', 'event_first'])
@pytest.mark.parametrize('cloned', [False, True])
def test_nonrandom_menus_exclude_pending_physical_cards(event, settlement, cloned):
    game, victim, pending, alternate = setup(event)
    if settlement == 'dispose':
        game.stage_list.append(partial(game.cards[pending].dispose, game, victim))
    else:
        game.stage_list.append(partial(game.select_action, victim, pending, is_event_resolved=True))
    source = game
    if cloned:
        game = deepcopy(game)
    game.cards[event].use_event(game, Side.US)
    options = list(game.input_state.legal_options)
    assert pending not in options and 'The_China_Card' not in options
    assert alternate in options
    assert pending in game.hand[victim]
    assert game.input_state.recv(alternate) is True
    assert pending in game.hand[victim]
    if cloned:
        assert alternate in source.hand[victim] and source.input_state is None


@pytest.mark.parametrize('event', EVENTS)
@pytest.mark.parametrize('change', ['removed', 'pending'])
def test_stale_nonrandom_callbacks_reject_without_mutation(event, change):
    game, victim, pending, alternate = setup(event)
    game.cards[event].use_event(game, Side.US)
    inp = game.input_state
    assert pending in list(inp.legal_options)
    if change == 'removed':
        game.hand[victim].remove(pending)
        game.discard_pile.append(pending)
    else:
        game.stage_list.append(partial(game.cards[pending].dispose, game, victim))
    hands = [list(h) for h in game.hand]
    discards, stages = list(game.discard_pile), list(game.stage_list)
    reps, selection = inp.reps, dict(inp.selection)
    assert inp.recv(pending) is False
    assert game.hand == hands and game.discard_pile == discards
    assert game.stage_list == stages and game.input_state is inp
    assert inp.reps == reps and inp.selection == selection


@pytest.mark.parametrize('actor', [Side.US, Side.USSR])
def test_un_intervention_cannot_pair_an_already_played_opponent_card(actor):
    game, victim, pending, alternate = setup('UN_Intervention', actor)
    game.hand[victim] = [pending]
    game.stage_list.append(partial(game.cards[pending].dispose, game, victim))
    assert game.cards['UN_Intervention'].can_event(game, actor) is False
    game.cards['UN_Intervention'].use_event(game, actor)
    assert list(game.input_state.legal_options) == []


@pytest.mark.parametrize('event', ['Blockade', 'Latin_American_Debt_Crisis'])
def test_ops_discard_rechecks_modifiers_before_consuming_choice(event):
    game, victim, pending, alternate = setup(event)
    alternate = 'De_Stalinization'
    game.hand[victim] = ['The_China_Card', alternate]
    game.cards[event].use_event(game, Side.US)
    inp = game.input_state
    assert alternate in list(inp.legal_options)
    game.basket[Side.USSR].append('Red_Scare_Purge')
    assert game.get_global_effective_ops(Side.US, game.cards[alternate].ops) == 2
    hands = [list(h) for h in game.hand]
    assert inp.recv(alternate) is False
    assert inp.reps == 1 and game.hand == hands and not game.discard_pile


@pytest.mark.parametrize('actor', [Side.US, Side.USSR])
def test_missile_exchange_rechecks_highest_available_ops(actor):
    game, victim, pending, alternate = setup('Missile_Envy', actor)
    game.hand[victim] = [alternate]
    game.cards['Missile_Envy'].use_event(game, actor)
    inp = game.input_state
    assert alternate in list(inp.legal_options)
    game.hand[victim].append(pending)
    hands = [list(h) for h in game.hand]
    assert inp.recv(alternate) is False
    assert inp.reps == 1 and game.hand == hands
    assert not game.cards['Missile_Envy'].exchange


@pytest.mark.parametrize('actor', [Side.US, Side.USSR])
def test_un_callback_rechecks_current_card_owner(actor):
    game, victim, pending, alternate = setup('UN_Intervention', actor)
    game.cards['UN_Intervention'].use_event(game, actor)
    inp = game.input_state
    game.cards[pending].owner = actor
    assert inp.recv(pending) is False
    assert inp.reps == 1 and game.input_state is inp


@pytest.mark.parametrize('event', EVENTS)
def test_original_eligible_choices_still_work(event):
    game, victim, pending, alternate = setup(event)
    game.cards[event].use_event(game, Side.US)
    inp = game.input_state
    assert pending in list(inp.legal_options)
    assert inp.recv(pending) is True

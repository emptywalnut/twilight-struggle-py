"""Missile Envy must spend an opponent-associated borrowed card only as Ops."""

from copy import deepcopy

import pytest

from tests.helpers import make_game
from twilight_enums import CardAction, Side


@pytest.mark.parametrize('actor', [Side.US, Side.USSR])
@pytest.mark.parametrize('phase', ['headline', 'ordinary_ar', 'optional_ar'])
@pytest.mark.parametrize('space', ['available', 'attempt_used', 'finished'])
def test_missile_borrowed_opponent_event_cannot_space_or_skip(actor, phase, space):
    game = make_game()
    game.turn_track, game.ar_side = 7, actor
    game.ar_track = {'headline': 0, 'ordinary_ar': 1, 'optional_ar': 8}[phase]
    if phase == 'optional_ar':
        game.ars_by_turn[actor][7] = 8
    if space == 'attempt_used':
        game.spaced_turns[actor] = 1
    elif space == 'finished':
        game.space_track[actor] = 8
    borrowed = 'Brezhnev_Doctrine' if actor == Side.US else 'Containment'
    game.hand[actor] = ['Missile_Envy']
    game.hand[actor.opp] = [borrowed, 'The_China_Card']
    assert game.can_space(actor, borrowed) is (space == 'available')
    game.cards['Missile_Envy'].use_event(game, actor)
    assert list(game.input_state.legal_options) == [borrowed]
    assert game.input_state.recv(borrowed)
    expected = {CardAction.INFLUENCE.name}
    if game.can_coup_at_all(actor):
        expected.add(CardAction.COUP.name)
    if game.can_realign_at_all(actor):
        expected.add(CardAction.REALIGNMENT.name)
    assert set(game.input_state.legal_options) == expected
    for action in (CardAction.SPACE, CardAction.PLAY_EVENT,
                   CardAction.RESOLVE_EVENT_FIRST, CardAction.SKIP_OPTIONAL_AR):
        assert not game.input_state.recv(action.name)
    assert game.input_state.reps == 1 and not game.stage_list
    assert not game.cards[borrowed].event_occurred

    clone = deepcopy(game)
    assert clone.input_state.recv(CardAction.INFLUENCE.name)
    clone.stage_complete()
    clone.stage_complete()
    country = 'Canada' if actor == Side.US else 'Finland'
    before = clone.map[country].influence[actor]
    budget = clone.get_global_effective_ops(actor, clone.cards[borrowed].info.ops)
    for _ in range(budget):
        assert clone.input_state.recv(country)
    assert clone.input_state.complete
    clone.stage_complete()
    assert clone.map[country].influence[actor] == before + budget
    assert borrowed not in clone.hand[actor]
    assert clone.discard_pile.count(borrowed) == 1
    assert borrowed not in clone.removed_pile
    assert not clone.cards[borrowed].event_occurred
    assert clone.vp_track == 0 and clone.milops_track == [0, 0]
    assert clone.spaced_turns == game.spaced_turns
    assert clone.space_track == game.space_track
    assert game.input_state.reps == 1 and not game.stage_list
    assert borrowed in game.hand[actor] and borrowed not in game.discard_pile

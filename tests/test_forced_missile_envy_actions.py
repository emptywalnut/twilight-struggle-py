"""Forced Missile Envy plays allow only Ops and the legal scoring/UN exceptions."""

from copy import deepcopy

import pytest

from tests.helpers import make_game
from twilight_enums import CardAction, Side


def exchange_to(recipient, extra):
    game = make_game()
    game.turn_track, game.ar_side = 7, recipient.opp
    incoming = 'Marshall_Plan' if recipient == Side.US else 'The_Reformer'
    game.hand[recipient.opp] = ['Missile_Envy']
    game.hand[recipient] = [incoming, *extra]
    game.select_card(recipient.opp)
    assert game.input_state.recv('Missile_Envy')
    game.stage_complete()
    assert game.input_state.recv(CardAction.PLAY_EVENT.name)
    game.stage_complete()
    game.stage_complete()
    assert game.input_state.recv(incoming)
    assert game.input_state.recv(CardAction.INFLUENCE.name)
    game.stage_complete()
    game.stage_complete()
    target = 'Finland' if recipient == Side.US else 'Canada'
    budget = game.get_global_effective_ops(recipient.opp, game.cards[incoming].info.ops)
    for _ in range(budget):
        assert game.input_state.recv(target)
    game.stage_complete()  # Incoming card settles.
    game.stage_complete()  # Missile Envy transfers, leaving its obligation.
    assert not game.stage_list
    assert 'Missile_Envy' in game.hand[recipient]
    assert 'Missile_Envy' in game.basket[recipient]
    assert incoming in game.discard_pile
    return game


def enable_extra_round(game, recipient):
    if recipient == Side.US:
        game.cards['North_Sea_Oil'].use_event(game, recipient)
    else:
        game.space_track[recipient] = 7
        game.change_space(recipient, 1)


@pytest.mark.parametrize('recipient', [Side.US, Side.USSR])
@pytest.mark.parametrize('rounds', [7, 8])
@pytest.mark.parametrize('mode', [
    'plain', 'purged', 'un_invalid', 'un_valid',
    'scoring_urgent', 'scoring_early', 'un_valid_scoring_urgent',
])
def test_real_forced_recipient_plays_ops_or_legal_exception(recipient, rounds, mode):
    extra = []
    paired = 'Fidel' if recipient == Side.US else 'Containment'
    if mode.startswith('un_'):
        extra.append('UN_Intervention')
    if mode.startswith('un_valid'):
        extra.append(paired)
    if 'scoring' in mode:
        extra.append('Asia_Scoring')
    game = exchange_to(recipient, extra)
    game.ar_side = recipient
    if rounds == 8:
        enable_extra_round(game, recipient)
    game.ar_track = 1 if mode in ('un_invalid', 'scoring_early') else rounds
    if mode == 'purged':
        game.basket[recipient.opp].append('Red_Scare_Purge')
    clone = deepcopy(game)
    clone.select_card(recipient)
    scoring = 'scoring' in mode and mode != 'scoring_early'
    expected = {'Asia_Scoring'} if scoring else {'Missile_Envy'}
    if mode == 'un_valid':
        expected.add('UN_Intervention')
    assert set(clone.input_state.legal_options) == expected
    if scoring:
        assert not clone.input_state.recv('Missile_Envy')
        assert clone.input_state.recv('Asia_Scoring')
        while 'Asia_Scoring' in clone.hand[recipient]:
            if clone.input_state is not None and not clone.input_state.complete:
                assert clone.input_state.recv(CardAction.PLAY_EVENT.name)
            assert clone.stage_list
            clone.stage_complete()
        assert 'Asia_Scoring' in clone.discard_pile
        assert 'Missile_Envy' in clone.hand[recipient]
        assert 'Missile_Envy' in clone.basket[recipient]
    else:
        selected = 'UN_Intervention' if mode == 'un_valid' else 'Missile_Envy'
        assert clone.input_state.recv(selected)
        clone.stage_complete()
        if selected == 'UN_Intervention':
            assert set(clone.input_state.legal_options) == {CardAction.PLAY_EVENT.name}
            for action in (CardAction.INFLUENCE, CardAction.COUP, CardAction.REALIGNMENT):
                assert not clone.input_state.recv(action.name)
        else:
            for action in (CardAction.SPACE, CardAction.SKIP_OPTIONAL_AR, CardAction.PLAY_EVENT):
                assert not clone.input_state.recv(action.name)
            assert clone.input_state.recv(CardAction.INFLUENCE.name)
            clone.stage_complete()
            clone.stage_complete()
            budget = 1 if mode == 'purged' else 2
            target = 'Canada' if recipient == Side.US else 'Finland'
            for _ in range(budget):
                assert clone.input_state.recv(target)
            assert clone.input_state.complete
            clone.stage_complete()
            assert 'Missile_Envy' not in clone.hand[recipient]
            assert 'Missile_Envy' not in clone.basket[recipient]
            assert clone.discard_pile.count('Missile_Envy') == 1
            assert not clone.cards['Missile_Envy'].event_occurred
            assert clone.spaced_turns == game.spaced_turns
    assert 'Missile_Envy' in game.hand[recipient]
    assert 'Missile_Envy' in game.basket[recipient]
    assert not game.stage_list and game.input_state is None


@pytest.mark.parametrize('recipient', [Side.US, Side.USSR])
@pytest.mark.parametrize('ar', [1, 8])
def test_unforced_missile_envy_keeps_normal_space_and_optional_skip(recipient, ar):
    game = make_game()
    game.turn_track, game.ar_track = 7, ar
    if ar == 8:
        enable_extra_round(game, recipient)
    game.hand[recipient] = ['Missile_Envy']
    game.basket[recipient.opp].append('Missile_Envy')
    game.select_action(recipient, 'Missile_Envy')
    assert (CardAction.SPACE.name in game.input_state.legal_options) == game.can_space(recipient, 'Missile_Envy')
    assert (CardAction.SKIP_OPTIONAL_AR.name in game.input_state.legal_options) == (ar == 8)

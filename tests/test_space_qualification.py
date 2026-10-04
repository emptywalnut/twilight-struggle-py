import pytest

from tests.helpers import make_game
from twilight_enums import Side, CardAction


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('level,minimum', enumerate((2, 2, 2, 2, 3, 3, 3, 4, None)))
@pytest.mark.parametrize('ops', [1, 2, 3, 4])
def test_space_checks_the_target_box_and_action_menu(side, level, minimum, ops):
    game = make_game()
    game.space_track[side] = level
    card = f'Blank_{ops}_Op_Card'
    expected = minimum is not None and ops >= minimum
    assert game.can_space(side, card) is expected
    game.select_action(side, card)
    assert (CardAction.SPACE.name in game.input_state.legal_options) is expected


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('level,opponent,used,expected', [
    (0, 0, 0, True), (0, 0, 1, False),
    (2, 1, 1, True), (2, 1, 2, False), (2, 1, 3, False),
    (2, 2, 1, False), (7, 1, 1, True), (8, 1, 0, False),
])
def test_space_attempt_limit_and_privilege_cancellation(side, level, opponent, used, expected):
    game = make_game()
    game.space_track[side], game.space_track[side.opp] = level, opponent
    game.spaced_turns[side] = used
    assert game.can_space(side, 'Blank_4_Op_Card') is expected


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('level,ops,purge,bonus,expected', [
    (4, 2, False, True, True), (4, 3, True, False, False),
    (7, 4, True, False, False), (7, 4, True, True, True),
    (0, 1, False, True, True),
])
def test_space_uses_only_global_effective_ops(side, level, ops, purge, bonus, expected):
    game = make_game()
    game.space_track[side] = level
    if purge:
        game.basket[side.opp].append('Red_Scare_Purge')
    if bonus:
        game.basket[side].append('Brezhnev_Doctrine' if side == Side.USSR else 'Containment')
    assert game.can_space(side, f'Blank_{ops}_Op_Card') is expected

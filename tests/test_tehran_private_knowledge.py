"""The Tehran peek is private evidence that cards are not in the USSR hand."""

from copy import deepcopy

import pytest

from tests.helpers import make_game
from twilight_enums import Side
from twilight_playerview import PlayerView

PEEK = ['Fidel', 'NATO', 'CIA_Created', 'Duck_and_Cover', 'Suez_Crisis']


@pytest.mark.parametrize('count', [0, 1, 5])
@pytest.mark.parametrize('cloned', [False, True])
def test_tehran_records_only_us_private_exclusions_at_enemy_draw_epoch(count, cloned):
    original = make_game()
    original.players = [PlayerView(Side.USSR), PlayerView(Side.US)]
    original.unknown_hand_draws = [9, 4]
    original.hand[Side.NEUTRAL] = PEEK[:count]
    original.hand[Side.USSR] = ['The_China_Card', 'Korean_War']
    original.players[Side.US].update_opp_hand(['Korean_War'])
    game = deepcopy(original) if cloned else original
    hands, draw_epochs = deepcopy(game.hand), list(game.unknown_hand_draws)
    game.cards['Our_Man_In_Tehran'].stage_1(game)
    view = game.players[Side.US]
    assert view.opp_hand_excluded_at == dict.fromkeys(PEEK[:count], 9)
    assert view.opp_hand == ['Korean_War']
    assert game.players[Side.USSR].opp_hand_excluded_at == {}
    assert game.hand == hands and game.unknown_hand_draws == draw_epochs
    assert view.opp_hand_revision == (2 if count else 1)
    if count:
        assert set(game.input_state.available_options) == set(PEEK[:count])
        assert game.input_state.recv(game.input_state.option_stop_early)
        game.stage_complete()
        assert view.opp_hand_excluded_at == dict.fromkeys(PEEK[:count], 9)
        assert game.unknown_hand_draws == draw_epochs
    else:
        assert game.input_state is None
    if cloned:
        assert original.players[Side.US].opp_hand_excluded_at == {}
        assert original.hand == hands and not original.stage_list


def test_tehran_without_player_view_still_runs_for_rule_only_consumers():
    game = make_game()
    game.hand[Side.NEUTRAL] = PEEK[:1]
    game.cards['Our_Man_In_Tehran'].stage_1(game)
    assert list(game.input_state.available_options) == PEEK[:1]

import pytest

from tests.helpers import make_game
from twilight_enums import Side, CardAction
from twilight_playerview import PlayerView
from ts_save import position_snapshot
from twilight_ui import UI


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('acquired_turn', [1, 4])
def test_station_rounds_persist_and_cancel_after_catchup(side, acquired_turn):
    game = make_game()
    game.turn_track = acquired_turn
    game.ar_track = 6
    game.space_track[side] = 7
    game.change_space(side, 1)
    assert game.ars_remaining(side) == 3
    for turn in (acquired_turn, 5, 8, 10):
        game.turn_track = turn
        game.ar_track = 8
        assert game.ars_remaining(side) == 1
        assert game.ars_remaining(side.opp) == 0
        view = PlayerView(side)
        view.update(game, side)
        assert view.ars_by_turn[side][turn] == 8
        assert position_snapshot(game)['ars_by_turn'][side.name][turn] == 8
        assert game.ars_by_turn[side][turn] == game.Default.ARS_BY_TURN[turn]
        game.select_action(side, 'Blank_2_Op_Card')
        assert CardAction.SKIP_OPTIONAL_AR.name in game.input_state.legal_options
    game.turn_track = acquired_turn
    game.change_space(side.opp, 8)
    for turn in (acquired_turn, 5, 8, 10):
        game.turn_track = turn
        assert game.ars_remaining(side) == game.ars_remaining(side.opp) == 0
        view.update(game, side)
        assert view.ars_by_turn[side][turn] == game.Default.ARS_BY_TURN[turn]
        assert position_snapshot(game)['ars_by_turn'][side.name][turn] == game.Default.ARS_BY_TURN[turn]
        game.select_action(side, 'Blank_2_Op_Card')
        assert CardAction.SKIP_OPTIONAL_AR.name not in game.input_state.legal_options


@pytest.mark.parametrize('station_side', [Side.USSR, Side.US])
def test_station_cancellation_preserves_north_sea_oil_this_turn(station_side):
    game = make_game()
    game.turn_track, game.ar_track = 4, 8
    game.space_track[station_side] = 7
    game.change_space(station_side, 1)
    game.cards['North_Sea_Oil'].use_event(game, Side.US)
    game.change_space(station_side.opp, 8)
    assert game.ars_remaining(Side.US) == 1
    assert game.ars_remaining(Side.USSR) == 0
    game.turn_track = 5
    assert game.ars_remaining(Side.US) == game.ars_remaining(Side.USSR) == 0


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
def test_stage_machine_reaches_the_station_owners_future_eighth_round(side):
    game = make_game()
    game.turn_track = 4
    game.space_track[side] = 7
    game.change_space(side, 1)
    game.turn_track, game.ar_track, game.ar_side = 5, 7, Side.US
    game.ar_side_done = [True, False]
    game.hand[side] = ['Blank_2_Op_Card']
    game.ar_complete()
    assert game.ar_track == 8 and game.ar_side == side
    assert game.ar_side_done[side] is False
    game.stage_complete()
    assert game.input_state.side == side
    assert game.input_state.recv('Blank_2_Op_Card') is True
    game.stage_complete()
    assert CardAction.SKIP_OPTIONAL_AR.name in game.input_state.legal_options


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
def test_ui_displays_the_live_station_round_limit(side, capsys):
    game = make_game()
    game.turn_track = 5
    game.space_track[side] = 8
    ui = UI()
    ui.game, ui.game_in_progress = game, True
    ui.parse_state('')
    expected = (8, 7) if side == Side.USSR else (7, 8)
    assert f'ARs this turn {expected}' in capsys.readouterr().out


def test_round_projections_still_work_after_final_scoring():
    game = make_game()
    game.turn_track = 10
    game.milops_track = [5, 5]
    game.space_track = [8, 8]
    game.end_of_turn()
    assert game.terminated and game.turn_track == 11
    view = PlayerView(Side.US)
    view.update(game, Side.US)
    assert view.ars_by_turn == game.ars_by_turn
    assert position_snapshot(game)['ars_by_turn']['US'] == game.ars_by_turn[Side.US]

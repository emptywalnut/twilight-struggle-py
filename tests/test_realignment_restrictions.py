import pytest

from tests.helpers import make_game
from twilight_enums import Side, MapRegion
from twilight_map import CountryInfo


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
def test_junta_keeps_the_american_restriction_after_its_first_roll(side):
    game = make_game()
    for name in ('Panama', 'Brazil', 'Iran'):
        game.map[name].set_influence(5, 5)
    game.cards['Junta'].use_event(game, side)
    assert game.input_state.recv('Brazil') is True
    game.stage_complete()
    assert game.input_state.recv('Free realignment rolls') is True
    assert 'Iran' not in game.input_state.legal_options
    assert game.input_state.recv('Panama') is True
    game.stage_complete()
    assert game.input_state.recv((3, 3)) is True
    game.stage_complete()
    allowed = CountryInfo.REGION_ALL[MapRegion.CENTRAL_AMERICA] | CountryInfo.REGION_ALL[MapRegion.SOUTH_AMERICA]
    assert set(game.input_state.context['restricted_countries']) == allowed
    assert 'Iran' not in game.input_state.legal_options
    assert 'Brazil' in game.input_state.legal_options
    assert game.input_state.recv('Stop realignments.') is True


def test_tear_down_keeps_europe_and_defcon_bypass_on_every_roll():
    game = make_game()
    game.defcon_track = 2
    for name in ('France', 'Italy', 'Iran'):
        game.map[name].set_influence(5, 5)
    game.cards['Tear_Down_This_Wall'].use_event(game, Side.US)
    assert game.input_state.recv('Free realignment rolls') is True
    for index, name in enumerate(('France', 'Italy', 'France')):
        assert 'Iran' not in game.input_state.legal_options
        assert game.input_state.context['ignore_defcon'] is True
        assert game.input_state.recv(name) is True
        game.stage_complete()
        assert game.input_state.recv((3, 3)) is True
        if index < 2:
            game.stage_complete()


def test_region_bonus_intersects_instead_of_widening_an_event_restriction():
    game = make_game()
    for name in ('Thailand', 'Laos_Cambodia', 'Japan'):
        game.map[name].set_influence(5, 5)
    game.basket[Side.USSR].append('Vietnam_Revolts')
    game.card_operation_realignment(
        Side.USSR, 'Blank_2_Op_Card', reps=2,
        restricted_list=('Thailand',), free=True,
    )
    for _ in range(2):
        assert game.input_state.recv('Thailand') is True
        game.stage_complete()
        assert game.input_state.recv((3, 3)) is True
        game.stage_complete()
        assert tuple(game.input_state.context['restricted_countries']) == ('Thailand',)
        assert 'Laos_Cambodia' not in game.input_state.legal_options

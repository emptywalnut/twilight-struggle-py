"""Optional event operations must remain playable without a legal target."""

from copy import deepcopy

import pytest

from tests.helpers import make_game
from twilight_enums import MapRegion, Side
from twilight_map import CountryInfo

DECLINE = 'Do not conduct free operations.'
COUP = 'Free coup attempt'
REALIGN = 'Free realignment rolls'
EVENTS = [('Junta', Side.US), ('Junta', Side.USSR),
          ('Tear_Down_This_Wall', Side.USSR)]


def open_event(card, trigger, *, target=True, cmc=False, defcon=5):
    game = make_game()
    game.defcon_track = defcon
    actor = trigger if card == 'Junta' else Side.US
    for country in game.map.ALL.values():
        if not country.info.superpower:
            country.set_influence(0, 0)
    name = 'Nicaragua' if card == 'Junta' else 'Spain_Portugal'
    if target:
        game.map[name].influence[actor.opp] = 1
    if cmc:
        game.basket[actor.opp].append('Cuban_Missile_Crisis')
    game.cards[card].use_event(game, trigger)
    if card == 'Junta':
        assert game.input_state.recv('Venezuela')
        game.stage_complete()
        assert game.map['Venezuela'].influence[actor] == 2
    else:
        assert game.map['East_Germany'].influence[Side.US] == 3
    return game, actor, name


@pytest.mark.parametrize('card,trigger', EVENTS)
@pytest.mark.parametrize('target', [False, True])
@pytest.mark.parametrize('cmc', [False, True])
def test_optional_offer_can_decline_without_attempt(card, trigger, target, cmc):
    game, actor, _ = open_event(card, trigger, target=target, cmc=cmc)
    expected = {DECLINE, COUP, REALIGN} if target else {DECLINE}
    assert set(game.input_state.legal_options) == expected
    assert game.input_state.side == actor
    influence = [tuple(c.influence) for c in game.map.ALL.values()]
    basket = deepcopy(game.basket)
    assert game.input_state.recv(DECLINE)
    assert game.input_state.complete
    assert not game.stage_list and not game.terminated
    assert game.defcon_track == 5 and game.milops_track == [0, 0]
    assert game.basket == basket
    assert [tuple(c.influence) for c in game.map.ALL.values()] == influence


@pytest.mark.parametrize('card,trigger', EVENTS)
@pytest.mark.parametrize('choice', [COUP, REALIGN])
@pytest.mark.parametrize('defcon', [2, 5])
def test_free_operation_modes_preserve_rules_and_clone_isolation(
        card, trigger, choice, defcon):
    original, actor, target = open_event(card, trigger, defcon=defcon)
    original_options = set(original.input_state.legal_options)
    game = deepcopy(original)
    assert game.input_state.recv(choice)
    if choice == COUP:
        game.stage_complete()
    assert game.input_state.side == actor
    assert set(game.input_state.legal_options) == {target}
    if choice == REALIGN:
        assert game.input_state.context['free']
        assert game.input_state.context['ignore_defcon'] == (card != 'Junta')
    assert game.input_state.recv(target)
    game.stage_complete()
    assert game.input_state.recv('6' if choice == COUP else (6, 1))
    assert game.defcon_track == defcon and game.milops_track == [0, 0]
    assert not game.terminated
    assert set(original.input_state.legal_options) == original_options
    assert original.input_state.reps == 1 and not original.stage_list
    assert original.map[target].influence[actor.opp] == 1


@pytest.mark.parametrize('ignore_defcon,reformer,expected', [
    (False, False, {DECLINE}),
    (True, False, {DECLINE, COUP, REALIGN}),
    (True, True, {DECLINE, REALIGN}),
])
def test_shared_offer_uses_each_modes_target_predicate(
        ignore_defcon, reformer, expected):
    game = make_game()
    game.defcon_track = 4
    game.map['France'].set_influence(0, 3)
    if reformer:
        game.basket[Side.USSR].append('The_Reformer')
    countries = CountryInfo.REGION_ALL[MapRegion.EUROPE]
    game.select_free_operations(Side.USSR, 'Junta', countries,
                                'Optional operations', ignore_defcon=ignore_defcon)
    assert set(game.input_state.legal_options) == expected

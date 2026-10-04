"""GMT FAQ #50: WWBY applies to the next real US AR, not a delegated/headline play."""
from copy import deepcopy
from functools import partial
import pytest

from tests.helpers import make_game
from twilight_enums import Side, CardAction

NAME = 'We_Will_Bury_You'


def pending(actor=Side.USSR, ar=2, turn=5):
    game = make_game()
    game.turn_track, game.ar_track, game.ar_side = turn, ar, actor
    game.milops_track = [5, 5]
    game.cards[NAME].use_event(game, actor)
    return game


@pytest.mark.parametrize('activation', [(Side.USSR, 2), (Side.US, 2), (Side.USSR, 0), (Side.US, 0)])
@pytest.mark.parametrize('current', [(5, 0, Side.US, False, False), (5, 2, Side.USSR, False, False),
                                    (5, 2, Side.US, False, False), (5, 3, Side.US, False, False),
                                    (6, 1, Side.US, False, False), (5, 3, Side.US, True, False),
                                    (10, 7, Side.US, False, True)])
def test_activation_clock_and_clone_only_settle_next_real_us_ar(activation, current):
    actor, ar = activation
    game = pending(actor, ar)
    source = game
    game = deepcopy(game)
    game.turn_track, game.ar_track, game.ar_side, game.ar_side_done[Side.US], game.final_scoring_active = current
    game.hand[Side.US] = ['Duck_and_Cover']
    game.resolve_card_action(Side.US, 'Duck_and_Cover', CardAction.PLAY_EVENT.name)
    turn, now_ar, side, done, final = current
    eligible = now_ar > 0 and side == Side.US and not done and not final and (turn, now_ar, side) > (5, ar, actor)
    assert game.vp_track == (3 if eligible else 0)
    assert (NAME in game.basket[Side.USSR]) is not eligible
    assert source.vp_track == 0 and NAME in source.basket[Side.USSR]


@pytest.mark.parametrize('method', ['direct_un', 'star_wars_un', 'missile_un', 'grain_pair'])
@pytest.mark.parametrize('phasing', [Side.US, Side.USSR])
def test_delegated_un_cancels_only_on_actual_us_ar(method, phasing):
    game = pending(Side.USSR, 2)
    game.ar_track, game.ar_side = 3, phasing
    game.hand[Side.US] = ['Fidel', 'UN_Intervention']
    if method == 'direct_un':
        game.resolve_card_action(Side.US, 'UN_Intervention', CardAction.PLAY_EVENT.name)
    elif method == 'grain_pair':
        game.resolve_card_action(Side.US, 'Grain_Sales_to_Soviets', CardAction.PLAY_EVENT.name)
        assert game.vp_track == 0 and NAME in game.basket[Side.USSR]
        game.cards['Grain_Sales_to_Soviets'].use_un_intervention(game, 'Fidel')
    else:
        outer = 'Star_Wars' if method == 'star_wars_un' else 'Missile_Envy'
        game.resolve_card_action(Side.US, outer, CardAction.PLAY_EVENT.name)
        assert game.vp_track == 0 and NAME in game.basket[Side.USSR]
        game.stage_list = []
        game.trigger_event(Side.US, 'UN_Intervention')
    assert game.vp_track == 0
    assert (NAME in game.basket[Side.USSR]) is (phasing == Side.USSR)


@pytest.mark.parametrize('vp', [0, 17])
@pytest.mark.parametrize('entry', ['vp_award', 'card_choice', 'trigger_event', 'trap', 'ar_end'])
def test_award_precedes_us_vp_or_mutation_and_only_once(vp, entry):
    game = pending()
    game.ar_track, game.ar_side, game.vp_track = 3, Side.US, vp
    game.hand[Side.US] = ['Duck_and_Cover']
    if entry == 'vp_award':
        game.change_vp(-2)
        expected = 20 if vp == 17 else 1
    elif entry == 'card_choice':
        game.select_card(Side.US)
        assert game.input_state.recv('Duck_and_Cover')
        expected = vp + 3
        if vp == 17:
            assert not game.stage_list
    elif entry == 'trigger_event':
        game.trigger_event(Side.US, 'Duck_and_Cover')
        expected = 20 if vp == 17 else 1
        if vp == 17:
            assert not game.cards['Duck_and_Cover'].event_occurred
            assert game.defcon_track == 4
    elif entry == 'trap':
        game.basket[Side.US].append('Quagmire')
        game.qbt_discard(Side.US, 'Quagmire')
        expected = vp + 3
    else:
        game.ar_complete()
        expected = vp + 3
    assert game.vp_track == expected and NAME not in game.basket[Side.USSR]
    assert game.terminated is (vp == 17)
    before = game.vp_track
    if not game.terminated:
        game.resolve_card_action(Side.US, 'Nuclear_Test_Ban', CardAction.INFLUENCE.name)
        assert game.vp_track == before


@pytest.mark.parametrize('retriever', ['Grain_Sales_to_Soviets', 'Star_Wars', 'Missile_Envy'])
def test_retriever_only_defers_for_event_and_us_award_forces_settlement(retriever):
    game = pending()
    game.ar_track, game.ar_side = 3, Side.US
    game.resolve_card_action(Side.US, retriever, CardAction.PLAY_EVENT.name)
    assert game.vp_track == 0 and NAME in game.basket[Side.USSR]
    game.change_vp(-1)
    assert game.vp_track == 2 and NAME not in game.basket[Side.USSR]
    other = pending()
    other.ar_track, other.ar_side = 3, Side.US
    other.resolve_card_action(Side.US, retriever, CardAction.INFLUENCE.name)
    assert other.vp_track == 3 and NAME not in other.basket[Side.USSR]


@pytest.mark.parametrize('held', [False, True])
def test_retrieved_un_needs_an_opponent_event(held):
    game = pending()
    game.ar_track, game.ar_side = 3, Side.US
    game.hand[Side.US] = ['UN_Intervention'] + (['Fidel'] if held else [])
    game.trigger_event(Side.US, 'UN_Intervention')
    assert game.vp_track == (0 if held else 3)
    assert NAME not in game.basket[Side.USSR]


def test_optional_us_ar_skip_does_not_consume_effect():
    game = pending(Side.US, 7)
    game.ar_track = 8
    game.ars_by_turn[Side.US][5] = 8
    game.hand[Side.US] = ['Nuclear_Test_Ban']
    game.select_card(Side.US)
    assert game.input_state.recv('Nuclear_Test_Ban')
    assert game.vp_track == 0
    game.stage_complete()
    assert game.input_state.recv(CardAction.SKIP_OPTIONAL_AR.name)
    game.stage_complete()
    assert game.ar_side_done[Side.US]
    game.ar_complete()
    assert game.vp_track == 0 and NAME in game.basket[Side.USSR]


def test_final_defcon_loss_prevents_activation():
    game = make_game()
    game.defcon_track = 2
    game.cards[NAME].use_event(game, Side.USSR)
    assert game.terminated and NAME not in game.basket[Side.USSR]

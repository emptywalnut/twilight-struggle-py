import pytest
from copy import deepcopy
from functools import partial

from tests.helpers import make_game
from twilight_enums import Side, InputType


@pytest.mark.parametrize('actor', [Side.USSR, Side.US])
@pytest.mark.parametrize('hand', [
    (), ('The_China_Card',), ('Grain_Sales_to_Soviets',),
    ('Grain_Sales_to_Soviets', 'The_China_Card'),
    ('The_China_Card', 'Fidel'),
    ('Grain_Sales_to_Soviets', 'The_China_Card', 'Nasser'),
])
def test_grain_draw_pool_and_empty_branch_use_the_same_eligible_hand(actor, hand):
    game = make_game()
    game.ar_side = actor
    game.hand[Side.USSR] = list(hand)
    expected = [n for n in hand if n not in ('The_China_Card', 'Grain_Sales_to_Soviets')]
    game.cards['Grain_Sales_to_Soviets'].use_event(game, actor)
    if expected:
        assert game.input_state.side == Side.NEUTRAL
        assert list(game.input_state.legal_options) == expected
        assert game.input_state.recv(expected[0]) is True
        assert expected[0] in game.hand[Side.US]
    else:
        assert game.input_state.side == Side.US
        assert game.input_state.state == InputType.SELECT_CARD_ACTION
        assert game.input_state.context['source_card'] == 'Blank_2_Op_Card'
        assert game.hand[Side.USSR] == list(hand)
    assert ('The_China_Card' in game.hand[Side.USSR]) == ('The_China_Card' in hand)
    assert 'The_China_Card' not in game.hand[Side.US]


@pytest.mark.parametrize('event', ['Five_Year_Plan', 'Grain_Sales_to_Soviets', 'Terrorism'])
@pytest.mark.parametrize('actor', [Side.USSR, Side.US])
@pytest.mark.parametrize('kind', ['china', 'source', 'stale'])
def test_random_hand_callbacks_reject_disallowed_and_stale_cards(event, actor, kind):
    game = make_game()
    victim = actor.opp if event == 'Terrorism' else Side.USSR
    game.hand[victim] = ['The_China_Card', event, 'Nasser', 'Nuclear_Test_Ban']
    game.cards[event].use_event(game, actor)
    inp = game.input_state
    card = {'china': 'The_China_Card', 'source': event, 'stale': 'Nasser'}[kind]
    if kind == 'stale':
        game.hand[victim].remove(card)
        game.discard_pile.append(card)
    hands = [list(h) for h in game.hand]
    discards, stages = list(game.discard_pile), list(game.stage_list)
    reps, selection = inp.reps, dict(inp.selection)
    receive = inp.recv if kind == 'stale' else inp.callback
    assert receive(card) is False
    assert game.hand == hands and game.discard_pile == discards
    assert game.stage_list == stages and game.input_state is inp
    assert inp.reps == reps and inp.selection == selection


@pytest.mark.parametrize('actor', [Side.USSR, Side.US])
@pytest.mark.parametrize('hostages', [False, True])
def test_terrorism_keeps_legal_discards_and_hostage_bonus(actor, hostages):
    game = make_game()
    victim = actor.opp
    game.hand[actor] = ['Terrorism']
    game.hand[victim] = ['The_China_Card', 'Nasser', 'Nuclear_Test_Ban']
    if hostages:
        game.basket[Side.USSR].append('Iranian_Hostage_Crisis')
    game.cards['Terrorism'].use_event(game, actor)
    reps = 2 if hostages and actor == Side.USSR else 1
    assert game.input_state.reps == reps
    for card in ('Nasser', 'Nuclear_Test_Ban')[:reps]:
        assert game.input_state.recv(card) is True
        assert card not in game.hand[victim] and card in game.discard_pile
        assert not game.cards[card].event_occurred
    assert game.input_state.complete
    assert 'The_China_Card' in game.hand[victim]


@pytest.mark.parametrize('event', ['Five_Year_Plan', 'Grain_Sales_to_Soviets', 'Terrorism'])
@pytest.mark.parametrize('actor', [Side.USSR, Side.US])
@pytest.mark.parametrize('settlement', ['dispose', 'event_first'])
@pytest.mark.parametrize('cloned', [False, True])
def test_random_hand_choices_exclude_queued_plays_without_moving_physical_cards(event, actor, settlement, cloned):
    game = make_game()
    victim = actor.opp if event == 'Terrorism' else Side.USSR
    game.hand[victim] = ['The_China_Card', event, 'Nasser', 'Nuclear_Test_Ban']
    if settlement == 'dispose':
        game.stage_list.append(partial(game.cards['Nasser'].dispose, game, victim))
    else:
        game.stage_list.append(partial(game.select_action, victim, 'Nasser', is_event_resolved=True))
    source = game
    if cloned:
        game = deepcopy(game)
    game.cards[event].use_event(game, actor)
    assert list(game.input_state.legal_options) == ['Nuclear_Test_Ban']
    assert 'Nasser' in game.hand[victim]
    assert game.input_state.recv('Nuclear_Test_Ban') is True
    assert 'Nasser' in game.hand[victim]
    if cloned:
        assert 'Nuclear_Test_Ban' in source.hand[victim]
        assert source.input_state is None


@pytest.mark.parametrize('side', [Side.USSR, Side.US])
@pytest.mark.parametrize('un_intervention', [False, True])
def test_resolved_or_un_ops_input_keeps_its_physical_source_out_of_the_pool(side, un_intervention):
    game = make_game()
    game.hand[side] = ['The_China_Card', 'Nasser', 'Nuclear_Test_Ban']
    game.select_action(side, 'Nasser', is_event_resolved=not un_intervention, un_intervention=un_intervention)
    assert game.pending_hand_cards(side) == {'Nasser'}
    assert game.random_hand_cards(side) == ['Nuclear_Test_Ban']
    assert game.hand[side] == ['The_China_Card', 'Nasser', 'Nuclear_Test_Ban']

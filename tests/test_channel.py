import time
from itertools import zip_longest
from unittest.mock import Mock

import pytest

import pyartnet
from .conftest import PatchedArtNetNode


@pytest.mark.asyncio
async def test_channel_single_step(running_artnet_node: PatchedArtNetNode):

    universe = running_artnet_node.add_universe(0)
    channel = universe.add_channel(1, 1)

    channel.add_fade([255], 0)
    await channel.wait_till_fade_complete()
    assert channel.get_channel_values() == [255]

    channel.add_fade([0], 0)
    await channel.wait_till_fade_complete()
    assert channel.get_channel_values() == [0]

    assert running_artnet_node.values == [[255, 0], [0, 0]]


@pytest.mark.asyncio
async def test_channel_double_step(running_artnet_node: PatchedArtNetNode):

    universe = running_artnet_node.add_universe(0)
    channel = universe.add_channel(1, 1)

    channel.add_fade([255], 2)
    await channel.wait_till_fade_complete()
    assert channel.get_channel_values() == [255]

    channel.add_fade([0], 2)
    await channel.wait_till_fade_complete()
    assert channel.get_channel_values() == [0]

    assert running_artnet_node.values == [[128, 0], [255, 0], [128, 0], [0, 0]]


@pytest.mark.asyncio
async def test_channel_with_3(running_artnet_node: PatchedArtNetNode):

    universe = running_artnet_node.add_universe(0)
    channel = universe.add_channel(1, 3)

    channel.add_fade([100, 150, 200], 5)
    await channel.wait_till_fade_complete()
    assert channel.get_channel_values() == [100, 150, 200]

    assert running_artnet_node.values == [
        [20, 30, 40, 0], [40, 60, 80, 0], [60, 90, 120, 0], [80, 120, 160, 0], [100, 150, 200, 0]
    ]
    running_artnet_node.values.clear()

    channel.add_fade([0, 0, 0], 2)
    await channel.wait_till_fade_complete()
    assert channel.get_channel_values() == [0, 0, 0]

    assert running_artnet_node.values == [[50, 75, 100, 0], [0, 0, 0, 0]]


@pytest.mark.asyncio
async def test_channel_cb(running_artnet_node: PatchedArtNetNode):
    universe = running_artnet_node.add_universe(0)
    channel = universe.add_channel(1, 1)

    channel.callback_fade_finished = cb_f = Mock()
    channel.callback_value_changed = cb_v = Mock()

    channel.add_fade([100], 5)
    await channel.wait_till_fade_complete()

    assert cb_f.call_count == 1
    assert cb_v.call_count == 5


@pytest.mark.asyncio
async def test_channel_wait_till_complete(running_artnet_node: PatchedArtNetNode):
    # under windows we can't use the quick ms sleeps
    running_artnet_node.sleep_time = 0.05

    universe = running_artnet_node.add_universe(0)
    channel = universe.add_channel(1, 1)

    channel.add_fade([255], 500)

    start = time.time()
    await channel.wait_till_fade_complete()
    duration = time.time() - start

    assert channel.get_channel_values() == [255]
    assert 0.4 <= duration <= 0.6


@pytest.mark.asyncio
async def test_byte_iterator(running_artnet_node: PatchedArtNetNode):

    universe = running_artnet_node.add_universe(0)

    for i, obj in enumerate(([10], [20, 30], [255, 254, 253, 252, 251])):
        channel = universe.add_channel(5 * i + 1, len(obj))
        channel.add_fade(obj, 0)
        await channel.wait_till_fade_complete()
        assert channel.get_channel_values() == obj
        for soll, ist in zip_longest(obj, channel.get_bytes()):
            assert soll == ist

    target_vals = [[254 * 255], [253 * 255, 252 * 255], [251 * 255, 250 * 255, 249 * 250]]
    target_bytes = []
    for val in target_vals:
        b = []
        for obj in val:
            b.append(obj >> 8)
            b.append(obj & 255)
        target_bytes.append(b)

    for i, obj in enumerate(target_vals):
        channel = universe.add_channel(10 * i + 50, len(obj), channel_type=pyartnet.DmxChannel16Bit)
        channel.add_fade(obj, 0)
        await channel.wait_till_fade_complete()
        assert channel.get_channel_values() == obj
        for soll, ist in zip_longest(target_bytes[i], list(channel.get_bytes())):
            assert soll == ist


def test_channel_boundaries():
    node = pyartnet.ArtNetNode(host='')
    univ = pyartnet.DmxUniverse(node)

    with pytest.raises(pyartnet.errors.ChannelOutOfUniverseError) as r:
        pyartnet.DmxChannel(univ, 0, 1)
    assert str(r.value) == 'Start position of channel out of universe (1..512): 0'
    pyartnet.DmxChannel(univ, 1, 1)

    with pytest.raises(pyartnet.errors.ChannelOutOfUniverseError) as r:
        pyartnet.DmxChannel(univ, 513, 1)
    assert str(r.value) == 'Start position of channel out of universe (1..512): 513'
    pyartnet.DmxChannel(univ, 512, 1)

    with pytest.raises(pyartnet.errors.ChannelOutOfUniverseError) as r:
        pyartnet.DmxChannel(univ, 512, 2)
    assert str(r.value) == 'End position of channel out of universe (1..512): start: 512 width: 2 * 2bytes -> 513'
    pyartnet.DmxChannel(univ, 511, 2)

    # 16 Bit Channels
    with pytest.raises(pyartnet.errors.ChannelOutOfUniverseError) as r:
        pyartnet.DmxChannel16Bit(univ, 512, 1)
    assert str(r.value) == 'End position of channel out of universe (1..512): start: 512 width: 1 * 2bytes -> 513'
    pyartnet.DmxChannel16Bit(univ, 511, 1)

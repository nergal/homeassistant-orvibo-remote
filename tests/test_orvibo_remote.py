import pytest
from unittest.mock import MagicMock
from custom_components.orvibo_remote.orvibo.orvibo import Orvibo
from custom_components.orvibo_remote.remote import OrviboRemote


class TestArguments:
    @pytest.mark.asyncio
    async def test_async_send_command_none(self):
        mocked_name = "Test intance"
        mocked_device = Orvibo(ip="127.0.0.1", mac="F2FFFFFFFFFF", type=Orvibo.TYPE_IRDA)
        mocked_device.emit_ir = MagicMock(return_value=b"any")

        mocked_command = []

        instance = OrviboRemote(mocked_name, mocked_device)
        await instance.async_send_command(command=mocked_command)

        mocked_device.emit_ir.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_send_command_single(self):
        mocked_name = "Test intance"
        mocked_device = Orvibo(ip="127.0.0.1", mac="F2FFFFFFFFFF", type=Orvibo.TYPE_IRDA)
        mocked_device.emit_ir = MagicMock(return_value=b"any")

        mocked_command = [
            "b64:dGVzdDE=",
        ]
        expected_result = b"test1"

        instance = OrviboRemote(mocked_name, mocked_device)
        await instance.async_send_command(command=mocked_command)

        mocked_device.emit_ir.assert_called_once_with(expected_result)

    @pytest.mark.asyncio
    async def test_async_send_command_few_commands(self):
        mocked_name = "Test intance"
        mocked_device = Orvibo(ip="127.0.0.1", mac="F2FFFFFFFFFF", type=Orvibo.TYPE_IRDA)
        mocked_device.emit_ir = MagicMock(return_value=b"any")

        mocked_command = [
            "b64:dGVzdDE=",
            "b64:dGVzdDI=",
            "b64:dGVzdDM=",
        ]
        expected_results = [
            b"test1",
            b"test2",
            b"test3",
        ]

        instance = OrviboRemote(mocked_name, mocked_device)
        await instance.async_send_command(command=mocked_command)

        assert len(mocked_command) == mocked_device.emit_ir.call_count
        for expected_result in expected_results:
            mocked_device.emit_ir.assert_any_call(expected_result)


class TestFormats:
    @pytest.mark.asyncio
    async def test_boardlink_format(self):
        mocked_name = "Test intance"
        mocked_device = Orvibo(ip="127.0.0.1", mac="F2FFFFFFFFFF", type=Orvibo.TYPE_IRDA)
        mocked_device.emit_ir = MagicMock(return_value=b"any")

        mocked_command = [
            "b64:iAAAAAAAiAAAAAAAAAAAAHgAViH6D90BEwa4ATYCzgEiAs0BIgK4ASkGzgEhAs4" +
            "BIQLOASQCtQEsBs0BzwX8ATcCzQEhAs8BIQK4ATgCtgE4As0BIQLNASICzQElArcBNQ" +
            "LNASICzgEhAs0BFga3ATYCzQEWBrcBNwLNASICzAEjAs4BEwbOAQAA"
        ]
        expected_result = bytes.fromhex(
            '8800 0000 0000 8800 0000 0000 0000 0000 7800 5621 fa0f dd01 1306 ' +
            'b801 3602 ce01 2202 cd01 2202 b801 2906 ce01 2102 ce01 2102 ce01 ' +
            '2402 b501 2c06 cd01 cf05 fc01 3702 cd01 2102 cf01 2102 b801 3802 ' +
            'b601 3802 cd01 2102 cd01 2202 cd01 2502 b701 3502 cd01 2202 ce01 ' +
            '2102 cd01 1606 b701 3602 cd01 1606 b701 3702 cd01 2202 cc01 2302 ' +
            'ce01 1306 ce01 0000'
        )

        instance = OrviboRemote(mocked_name, mocked_device)
        await instance.async_send_command(command=mocked_command)

        mocked_device.emit_ir.assert_called_once_with(expected_result)

    @pytest.mark.asyncio
    async def test_raw(self):
        mocked_name = "Test intance"
        mocked_device = Orvibo(ip="127.0.0.1", mac="F2FFFFFFFFFF", type=Orvibo.TYPE_IRDA)
        mocked_device.emit_ir = MagicMock(return_value=b"any")

        expected_result = bytes.fromhex(
            '8800 0000 0000 8800 0000 0000 0000 0000 7800 5621 fa0f dd01 1306 ' +
            'b801 3602 ce01 2202 cd01 2202 b801 2906 ce01 2102 ce01 2102 ce01 ' +
            '2402 b501 2c06 cd01 cf05 fc01 3702 cd01 2102 cf01 2102 b801 3802 ' +
            'b601 3802 cd01 2102 cd01 2202 cd01 2502 b701 3502 cd01 2202 ce01 ' +
            '2102 cd01 1606 b701 3602 cd01 1606 b701 3702 cd01 2202 cc01 2302 ' +
            'ce01 1306 ce01 0000'
        )

        instance = OrviboRemote(mocked_name, mocked_device)
        await instance.async_send_command(command=[expected_result])

        mocked_device.emit_ir.assert_called_once_with(expected_result)

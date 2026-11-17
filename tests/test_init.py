"""Integration tests for Energy Tracker."""

from datetime import date, timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_tracker.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations."""
    return


@pytest.fixture
async def entry(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> MockConfigEntry:
    """Set up the integration."""
    freezer.move_to("2025-07-01 12:00:00+00:00")
    await hass.config.async_set_time_zone("UTC")
    assert await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(domain=DOMAIN, options={"show_panel": True, "panel_title": "Energie"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _ws(client, msg_type: str, **data):
    await client.send_json_auto_id({"type": f"{DOMAIN}/{msg_type}", **data})
    return await client.receive_json()


async def test_full_flow(hass: HomeAssistant, entry, hass_ws_client) -> None:
    """Create a meter, readings and a contract and check results."""
    client = await hass_ws_client(hass)

    msg = await _ws(client, "meter/save", name="Strom", meter_type="electricity", unit="kWh")
    assert msg["success"], msg
    meter_id = msg["result"]["id"]
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    reading_entity = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{meter_id}_reading")
    assert reading_entity == "sensor.strom_meter_reading"

    start = date(2024, 12, 31)
    for offset, value in ((0, 1000), (90, 1600), (181, 2200)):
        msg = await _ws(
            client,
            "reading/save",
            meter_id=meter_id,
            date=(start + timedelta(days=offset)).isoformat(),
            value=value,
        )
        assert msg["success"], msg

    # Plausibility check: lower than previous reading
    msg = await _ws(client, "reading/save", meter_id=meter_id, date="2025-07-01", value=10)
    assert not msg["success"]
    assert msg["error"]["code"] == "value_too_low"

    msg = await _ws(
        client,
        "contract/save",
        meter_id=meter_id,
        provider="Stadtwerke",
        start_date="2025-01-01",
        unit_price=0.3,
        base_price=10,
        advance_payment=80,
    )
    assert msg["success"], msg
    assert msg["result"]["payments_per_year"] == 12
    await hass.async_block_till_done()

    state = hass.states.get(reading_entity)
    assert float(state.state) == 2200
    assert state.attributes["device_class"] == "energy"
    # must not be selectable as energy dashboard source (see energy_stats)
    assert "state_class" not in state.attributes

    msg = await _ws(
        client,
        "statistics",
        meter_id=meter_id,
        start="2025-01-01",
        end="2025-12-31",
        granularity="month",
        compare_start="2024-01-01",
        compare_end="2024-12-31",
    )
    assert msg["success"], msg
    result = msg["result"]
    assert len(result["buckets"]) == 12
    assert result["summary"]["measured"] == pytest.approx(1200)
    assert result["buckets"][0]["cost"] is not None
    assert len(result["compare"]["buckets"]) == 12

    msg = await _ws(client, "billing", meter_id=meter_id)
    assert msg["success"], msg
    billing = msg["result"]["selected"]
    # billing date 30.09. (default), independent of the contract start
    assert (billing["start"], billing["end"], billing["label"]) == ("2024-10-01", "2025-09-30", "2024/25")
    # contract from 01.01.2025: 9 payments of 80 € until September
    assert billing["advance_total"] == pytest.approx(9 * 80)
    assert billing["cost_coverage"] == pytest.approx(273 / 365)
    # the measurement starts with the contract: no days without tariff
    assert msg["result"]["tariff_gaps"] == {"gaps": [], "before": None, "after": None}

    # a bill of the utility for the period 2024/25
    msg = await _ws(
        client,
        "bill/save",
        meter_id=meter_id,
        start_date="2024-10-01",
        end_date="2025-09-30",
        consumption=2500,
        total_cost=900,
        advances_paid=720,
        new_advance=95,
        new_advance_from="2025-10-01",
    )
    assert msg["success"], msg
    bill_id = msg["result"]["id"]
    await hass.async_block_till_done()
    last_bill = hass.states.get("sensor.strom_last_bill_refund_additional_payment")
    assert float(last_bill.state) == pytest.approx(-180)
    assert last_bill.attributes["billing_year"] == "2024/25"
    assert last_bill.attributes["advances_paid"] == 720
    msg = await _ws(client, "billing", meter_id=meter_id)
    assert msg["result"]["bill"]["bill"]["id"] == bill_id
    assert msg["result"]["periods"][-1]["bill_id"] == bill_id
    assert msg["result"]["bill"]["comparison"]["consumption"]["bill"] == 2500
    msg = await _ws(client, "bill/delete", bill_id=bill_id)
    assert msg["success"], msg

    balance = hass.states.get("sensor.strom_expected_refund_additional_payment")
    assert balance is not None
    assert float(balance.state) == pytest.approx(round(billing["balance"], 2))

    msg = await _ws(client, "overview")
    assert msg["success"], msg
    assert msg["result"][0]["quality"] == "good"
    assert msg["result"][0]["billing"]["label"] == "2024/25"
    assert msg["result"][0]["last_bill"] is None

    # Service with meter name
    response = await hass.services.async_call(
        DOMAIN,
        "add_reading",
        {"meter": "strom", "value": 2210, "date": "2025-07-01"},
        blocking=True,
        return_response=True,
    )
    assert response["reading"]["value"] == 2210
    await hass.async_block_till_done()
    assert float(hass.states.get(reading_entity).state) == 2210

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "add_reading", {"meter": "unknown", "value": 1}, blocking=True)

    msg = await _ws(client, "meter/delete", meter_id=meter_id)
    assert msg["success"], msg
    await hass.async_block_till_done()
    assert ent_reg.async_get_entity_id("sensor", DOMAIN, f"{meter_id}_reading") is None
    assert hass.states.get(reading_entity) is None


async def test_import_and_unload(hass: HomeAssistant, entry, hass_ws_client) -> None:
    """Bulk import readings and unload the entry."""
    client = await hass_ws_client(hass)
    msg = await _ws(client, "meter/save", name="Wasser", meter_type="water", unit="m³")
    meter_id = msg["result"]["id"]
    msg = await _ws(
        client,
        "reading/import",
        meter_id=meter_id,
        readings=[
            {"date": "2025-01-01", "value": 10},
            {"date": "2025-02-01", "value": 17},
            {"date": "2025-02-01", "value": 17},
        ],
    )
    assert msg["result"] == {"added": 2, "skipped": 1}
    msg = await _ws(client, "data")
    assert len(msg["result"]["readings"]) == 2

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    msg = await _ws(client, "data")
    assert not msg["success"]


async def test_config_flow(hass: HomeAssistant) -> None:
    """Test the config flow."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == "form"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"show_panel": False, "panel_title": "Verbrauch"}
    )
    assert result["type"] == "create_entry"
    assert result["options"] == {"show_panel": False, "panel_title": "Verbrauch"}


async def test_write_commands_need_admin(
    hass: HomeAssistant, entry, hass_ws_client, hass_read_only_access_token: str
) -> None:
    """Users without admin rights can read but not change data."""
    admin = await hass_ws_client(hass)
    msg = await _ws(admin, "meter/save", name="Strom", meter_type="electricity", unit="kWh")
    meter_id = msg["result"]["id"]
    msg = await _ws(admin, "reading/save", meter_id=meter_id, date="2025-01-01", value=1)
    reading_id = msg["result"]["id"]

    client = await hass_ws_client(hass, hass_read_only_access_token)
    for msg_type, data in (
        ("meter/save", {"name": "X", "meter_type": "gas", "unit": "m³"}),
        ("meter/delete", {"meter_id": meter_id}),
        ("reading/save", {"meter_id": meter_id, "date": "2025-02-01", "value": 2}),
        ("reading/import", {"meter_id": meter_id, "readings": [{"date": "2025-02-01", "value": 2}]}),
        ("reading/delete", {"reading_id": reading_id}),
        ("contract/save", {"meter_id": meter_id, "start_date": "2025-01-01"}),
        ("contract/delete", {"contract_id": "x"}),
        ("photo/discard", {"photo_id": "a" * 32 + ".jpg"}),
    ):
        msg = await _ws(client, msg_type, **data)
        assert not msg["success"], msg_type
        assert msg["error"]["code"] == "unauthorized", msg_type

    for msg_type, data in (
        ("data", {}),
        ("overview", {}),
        (
            "statistics",
            {"meter_id": meter_id, "start": "2025-01-01", "end": "2025-01-31", "granularity": "day"},
        ),
    ):
        msg = await _ws(client, msg_type, **data)
        assert msg["success"], msg_type
    assert len(hass.data[DOMAIN].readings) == 1


async def test_remove_entry_deletes_storage(hass: HomeAssistant, entry, hass_ws_client, hass_storage) -> None:
    """Removing the integration deletes the stored data."""
    client = await hass_ws_client(hass)
    await _ws(client, "meter/save", name="Strom", meter_type="electricity", unit="kWh")
    await hass.data[DOMAIN].async_flush()
    assert f"{DOMAIN}.data" in hass_storage

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert f"{DOMAIN}.data" not in hass_storage


@pytest.fixture
def frozen_2026(freezer: FrozenDateTimeFactory) -> None:
    """Freeze the time before the websocket client (and its token) is created."""
    freezer.move_to("2026-11-17 12:00:00+00:00")


async def test_storage_migration(hass: HomeAssistant, hass_storage, frozen_2026, hass_ws_client) -> None:
    """Data of version 1 is migrated when the integration is loaded."""
    hass_storage[f"{DOMAIN}.data"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"{DOMAIN}.data",
        "data": {
            "meters": [{"id": "m1", "name": "Gas", "type": "gas", "unit": "m³", "profile": "auto"}],
            "readings": [
                {"id": "r1", "meter_id": "m1", "date": "2025-09-08", "value": 10147.79, "reset": False},
                {"id": "r2", "meter_id": "m1", "date": "2026-09-07", "value": 10874.85, "reset": False},
            ],
            "contracts": [
                {
                    "id": "c1",
                    "meter_id": "m1",
                    "start_date": "2026-10-01",
                    "unit_price": 0.11,
                    "base_price": 15.5,
                    "advance_payment": 95,
                    "conversion_factor": 10.4,
                    "billing_months": 12,
                }
            ],
        },
    }
    assert await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(domain=DOMAIN, options={"show_panel": False})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    store = hass.data[DOMAIN]
    assert (store.meters["m1"]["billing_day"], store.meters["m1"]["billing_month"]) == (30, 9)
    contract = store.contracts["c1"]
    assert (contract["unit_price"], contract["advance_payment"], contract["conversion_factor"]) == (
        0.11,
        95,
        10.4,
    )
    assert contract["payments_per_year"] == 12
    assert store.bills == {}

    client = await hass_ws_client(hass)
    msg = await _ws(client, "billing", meter_id="m1")
    result = msg["result"]
    # the measurement starts on 09.09.2025, still in the billing year 2024/25
    assert [p["label"] for p in result["periods"]] == ["2024/25", "2025/26", "2026/27"]
    assert result["selected"]["label"] == "2026/27"
    assert result["selected"]["advance_total"] == pytest.approx(12 * 95)
    # readings since 08.09.2025, contract only from 01.10.2026
    assert result["tariff_gaps"]["before"] == {"start": "2025-09-09", "end": "2026-09-30"}

    msg = await _ws(client, "billing", meter_id="m1", period_index=1)
    previous = msg["result"]["selected"]
    assert previous["result"] == "no_tariff"
    assert previous["cost_coverage"] == 0
    await store.async_flush()
    assert hass_storage[f"{DOMAIN}.data"]["version"] == 3
    assert hass_storage[f"{DOMAIN}.data"]["data"]["contracts"][0]["price_changes"] == []


async def test_tariff_gaps_and_meter_fields(hass: HomeAssistant, entry, hass_ws_client) -> None:
    """Gaps between contracts are reported, billing date and method can be set."""
    client = await hass_ws_client(hass)
    msg = await _ws(
        client,
        "meter/save",
        name="Strom",
        meter_type="electricity",
        unit="kWh",
        billing_day=31,
        billing_month=12,
        forecast_method="average",
    )
    meter = msg["result"]
    assert (meter["billing_day"], meter["billing_month"], meter["forecast_method"]) == (31, 12, "average")
    msg = await _ws(client, "meter/save", name="X", meter_type="gas", unit="m³", billing_month=13)
    assert not msg["success"]

    for start, end in (("2024-01-01", "2024-06-30"), ("2024-08-01", None)):
        msg = await _ws(
            client,
            "contract/save",
            meter_id=meter["id"],
            start_date=start,
            end_date=end,
            unit_price=0.3,
            advance_payment=50,
            payments_per_year=11,
            payment_day=15,
            advance_changes=[{"date": "2025-03-01", "amount": 60}],
        )
        assert msg["success"], msg
    assert msg["result"]["advance_changes"] == [{"date": "2025-03-01", "amount": 60.0}]
    msg = await _ws(
        client, "contract/save", meter_id=meter["id"], start_date="2024-01-01", payments_per_year=10
    )
    assert not msg["success"]

    msg = await _ws(client, "billing", meter_id=meter["id"])
    result = msg["result"]
    assert result["tariff_gaps"]["gaps"] == [{"start": "2024-07-01", "end": "2024-07-31"}]
    # calendar year as billing period
    assert (result["selected"]["start"], result["selected"]["label"]) == ("2025-01-01", "2025")
    assert result["selected"]["payments_per_year"] == 11

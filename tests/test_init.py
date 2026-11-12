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
    contract_id = msg["result"]["id"]
    await hass.async_block_till_done()

    state = hass.states.get(reading_entity)
    assert float(state.state) == 2200
    assert state.attributes["device_class"] == "energy"

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

    msg = await _ws(client, "billing", contract_id=contract_id)
    assert msg["success"], msg
    billing = msg["result"]["selected"]
    assert billing["start"] == "2025-01-01"
    assert billing["advance_total"] == pytest.approx(960)

    balance = hass.states.get("sensor.strom_expected_refund_additional_payment")
    assert balance is not None
    assert float(balance.state) == pytest.approx(round(billing["balance"], 2))

    msg = await _ws(client, "overview")
    assert msg["success"], msg
    assert msg["result"][0]["quality"] == "good"

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

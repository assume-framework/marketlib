# SPDX-FileCopyrightText: Florian Maurer
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from datetime import datetime, timedelta
from pprint import pprint

import pandas as pd
from assume import World
from assume.common.forecasts import NaiveForecast
from assume.common.market_objects import MarketConfig, MarketProduct
from dateutil import rrule as rr

from emarketlib.assume import clearing_mechanisms
from emarketlib.example_eu import eu_market_design

log = logging.getLogger(__name__)

pprint(eu_market_design)


if __name__ == "__main__":
    db_uri = "postgresql://assume:assume@localhost:5432/assume"
    world = World(database_uri=db_uri)
    start = datetime(2019, 1, 1)
    end = datetime(2019, 3, 1)
    index = pd.date_range(
        start=start,
        end=end + timedelta(hours=24),
        freq="h",
    )
    sim_id = "world_script_simulation"

    world.setup(
        start=start,
        end=end,
        save_frequency_hours=48,
        simulation_id=sim_id,
        index=index,
    )

    marketdesign = [
        MarketConfig(
            market_id="EOM",
            opening_hours=rr.rrule(rr.HOURLY, interval=1, dtstart=start, until=end),
            opening_duration=timedelta(hours=1),
            market_mechanism="pay_as_clear",
            market_products=[MarketProduct(timedelta(hours=1), 1, timedelta(hours=1))],
            additional_fields=["block_id", "link", "exclusive_id"],
        )
    ]
    world.clearing_mechanisms.update(clearing_mechanisms)

    mo_id = "market_operator"
    world.add_market_operator(id=mo_id)
    for market_config in marketdesign:
        world.add_market(mo_id, market_config)

    world.add_unit_operator("my_demand")
    world.add_unit(
        "demand1",
        "demand",
        "my_demand",
        # the unit_params have no hints
        {
            "min_power": 0,
            "max_power": 1000,
            "bidding_strategies": {"EOM": "naive_eom"},
            "technology": "demand",
        },
        NaiveForecast(index, demand=1000),
    )

    nuclear_forecast = NaiveForecast(index, availability=1, fuel_price=3, co2_price=0.1)
    n = 1
    for i in range(n):
        world.add_unit_operator(f"my_operator{i}")
        world.add_unit(
            f"nuclear{i}",
            "power_plant",
            f"my_operator{i}",
            {
                "min_power": 200 / n,
                "max_power": 1000 / n,
                "bidding_strategies": {"EOM": "naive_eom"},
                "technology": "nuclear",
            },
            nuclear_forecast,
        )
    world.run()
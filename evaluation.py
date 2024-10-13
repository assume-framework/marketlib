# SPDX-FileCopyrightText: ASSUME Developers
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import copy
from datetime import datetime, timedelta

from dateutil import rrule as rr
from dateutil.relativedelta import relativedelta as rd

from emarketpy.clearing_algorithms import PayAsClearRole, clearing_mechanisms
from emarketpy.market_objects import MarketConfig, MarketProduct
from emarketpy.utils import get_available_products, plot_orderbook

from tests.utils import create_orderbook, extend_orderbook

simple_dayahead_auction_config = MarketConfig(
    market_id="simple_dayahead_auction",
    market_products=[MarketProduct(rd(hours=+1), 1, rd(hours=1))],
    additional_fields=["node"],
    opening_hours=rr.rrule(
        rr.HOURLY,
        dtstart=datetime(2005, 6, 1),
        cache=True,
    ),
    opening_duration=timedelta(hours=1),
    volume_unit="MW",
    volume_tick=0.1,
    price_unit="€/MW",
    market_mechanism="pay_as_clear",
)

next_opening = simple_dayahead_auction_config.opening_hours.after(datetime.now())
products = get_available_products(
    simple_dayahead_auction_config.market_products, next_opening
)

"""
Create Orderbook with constant order volumes and prices:
    - dem1: volume = -1000, price = 3000
    - gen1: volume = 1000, price = 100
    - gen2: volume = 900, price = 50
"""

orderbook = extend_orderbook(products, -1000, 200)
orderbook = extend_orderbook(products, -800, 20, orderbook)
orderbook = extend_orderbook(products, 1000, 100, orderbook)
orderbook = extend_orderbook(products, 900, 50, orderbook)

mr = PayAsClearRole(simple_dayahead_auction_config)
accepted, rejected, meta = mr.clear(orderbook, products)

plot_orderbook(accepted, meta)
assert meta[0]["demand_volume"] > 0
assert meta[0]["price"] > 0
import pandas as pd

print(pd.DataFrame(mr.all_orders))
print(pd.DataFrame(accepted))
print(meta)



# SPDX-FileCopyrightText: ASSUME Developers
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta

from dateutil import rrule as rr
from dateutil.relativedelta import relativedelta as rd

from emarketpy.clearing_algorithms.simple import PayAsClearRole
from emarketpy.market_objects import MarketConfig, MarketProduct
from emarketpy.utils import (
    get_available_products,
    plot_orderbook,
)
from tests.utils import extend_orderbook

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

# vertical down
orderbook = extend_orderbook(products, -100, 100)
orderbook = extend_orderbook(products, -100, 50, orderbook)
orderbook = extend_orderbook(products, 100, 70, orderbook)
orderbook = extend_orderbook(products, 100, 80, orderbook)

mr = PayAsClearRole(simple_dayahead_auction_config)
accepted, rejected, meta = mr.clear(orderbook, products)

all_orders = []
all_orders.extend(accepted)
all_orders.extend(rejected)
plot_orderbook(all_orders, meta, "vertical overlap", show_text=False)

### intersect demand change
orderbook = extend_orderbook(products, -100, 100)
orderbook = extend_orderbook(products, -100, 10, orderbook)
orderbook = extend_orderbook(products, 80, 120, orderbook)
orderbook = extend_orderbook(products, 120, 80, orderbook)

mr = PayAsClearRole(simple_dayahead_auction_config)
accepted, rejected, meta = mr.clear(orderbook, products)

all_orders = []
all_orders.extend(accepted)
all_orders.extend(rejected)
plot_orderbook(all_orders, meta, "intersection demand change", show_text=False)


### intersect supply change
orderbook = extend_orderbook(products, -100, 100)
orderbook = extend_orderbook(products, -100, 10, orderbook)
orderbook = extend_orderbook(products, 50, 50, orderbook)
orderbook = extend_orderbook(products, 150, 80, orderbook)

mr = PayAsClearRole(simple_dayahead_auction_config)
accepted, rejected, meta = mr.clear(orderbook, products)

all_orders = []
all_orders.extend(accepted)
all_orders.extend(rejected)
plot_orderbook(all_orders, meta, "intersection supply change", show_text=False)

### intersect more expensive price
orderbook = extend_orderbook(products, -100, 100)
orderbook = extend_orderbook(products, -90, 50, orderbook)
orderbook = extend_orderbook(products, -100, 3, orderbook)
orderbook = extend_orderbook(products, 100, 3, orderbook)
orderbook = extend_orderbook(products, 100, 50, orderbook)
orderbook = extend_orderbook(products, 100, 100, orderbook)

mr = PayAsClearRole(simple_dayahead_auction_config)
accepted, rejected, meta = mr.clear(orderbook, products)

all_orders = []
all_orders.extend(accepted)
all_orders.extend(rejected)
plot_orderbook(all_orders, meta, "horizontal overlap", show_text=False)

assert meta[0]["demand_volume"] > 0
assert meta[0]["price"] > 0

import pandas as pd

print(pd.DataFrame(all_orders))
print(pd.DataFrame(accepted))
print(meta)



# SPDX-FileCopyrightText: ASSUME Developers
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta

import matplotlib.pyplot as plt
from dateutil import rrule as rr
from dateutil.relativedelta import relativedelta as rd

from emarketlib.clearing_algorithms.simple import PayAsClearRole
from emarketlib.market_objects import MarketConfig, MarketProduct
from emarketlib.utils import (
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
orderbook = extend_orderbook(products, -100, 100, node="1")
orderbook = extend_orderbook(products, -100, 50, orderbook, node="1")
orderbook = extend_orderbook(products, 100, 70, orderbook, node="1")
orderbook = extend_orderbook(products, 100, 80, orderbook, node="1")

mr = PayAsClearRole(simple_dayahead_auction_config)
accepted, rejected, meta, _ = mr.clear(orderbook, products)

all_orders = []
metas = []
metas.extend(meta)
all_orders.extend(accepted)
all_orders.extend(rejected)


#plot_orderbook(all_orders, meta, "vertical overlap", show_text=False)

### intersect demand change
orderbook = extend_orderbook(products, -100, 100, node="2")
orderbook = extend_orderbook(products, -100, 10, orderbook, node="2")
orderbook = extend_orderbook(products, 80, 120, orderbook, node="2")
orderbook = extend_orderbook(products, 120, 80, orderbook, node="2")

mr = PayAsClearRole(simple_dayahead_auction_config)
accepted, rejected, meta, _ = mr.clear(orderbook, products)

all_orders.extend(accepted)
all_orders.extend(rejected)
metas.extend(meta)

### intersect supply change
orderbook = extend_orderbook(products, -100, 100, node="3")
orderbook = extend_orderbook(products, -100, 10, orderbook, node="3")
orderbook = extend_orderbook(products, 50, 50, orderbook, node="3")
orderbook = extend_orderbook(products, 150, 80, orderbook, node="3")

mr = PayAsClearRole(simple_dayahead_auction_config)
accepted, rejected, meta, _ = mr.clear(orderbook, products)

all_orders.extend(accepted)
all_orders.extend(rejected)
metas.extend(meta)

### intersect more expensive price
orderbook = extend_orderbook(products, -100, 100, node="4")
orderbook = extend_orderbook(products, -90, 50, orderbook, node="4")
orderbook = extend_orderbook(products, -100, 3, orderbook, node="4")
orderbook = extend_orderbook(products, 100, 3, orderbook, node="4")
orderbook = extend_orderbook(products, 100, 50, orderbook, node="4")
orderbook = extend_orderbook(products, 100, 100, orderbook, node="4")

mr = PayAsClearRole(simple_dayahead_auction_config)
accepted, rejected, meta, _ = mr.clear(orderbook, products)

all_orders.extend(accepted)
all_orders.extend(rejected)
metas.extend(meta)
plot_orderbook(all_orders, metas, ["vertical overlap", "intersection demand change","intersection supply change", "horizontal overlap"], show_text=False, rowcount=2, figsize=(8,6))

plt.savefig("intersection-bids.svg")

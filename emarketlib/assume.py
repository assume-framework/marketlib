# SPDX-FileCopyrightText: Florian Maurer
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from assume.markets.base_market import MarketRole

from .clearing_algorithms.all_or_nothing import PayAsBidAonRole, PayAsClearAonRole
from .clearing_algorithms.contracts import PayAsBidContractRole
from .clearing_algorithms.simple import (
    AverageMechanismRole,
    McAfeeRole,
    PayAsBidRole,
    PayAsClearRole,
    VCGAuctionRole,
)


class PayAsBidContractMarketRole(MarketRole, PayAsBidContractRole):
    pass


class PayAsBidAonMarketRole(MarketRole, PayAsBidAonRole):
    pass


class PayAsClearAonMarketRole(MarketRole, PayAsClearAonRole):
    pass


class VCGMarketRole(MarketRole, VCGAuctionRole):
    pass


class AverageMechanismMarketRole(MarketRole, AverageMechanismRole):
    pass


class PayAsBidMarketRole(MarketRole, PayAsBidRole):
    pass


class PayAsClearMarketRole(MarketRole, PayAsClearRole):
    pass


class McAffeeMarketRole(MarketRole, McAfeeRole):
    pass


clearing_mechanisms: dict[str, MarketRole] = {
    "pay_as_clear": PayAsClearMarketRole,
    "pay_as_bid": PayAsBidMarketRole,
    "pay_as_bid_aon": PayAsBidAonRole,
    "pay_as_clear_aon": PayAsClearAonMarketRole,
    "pay_as_bid_contract": PayAsBidContractMarketRole,
    "mc_affee": McAffeeMarketRole,
    "average_mech": AverageMechanismMarketRole,
    "vcg": VCGMarketRole,
}

# try importing pypsa if it is installed
try:
    from .clearing_algorithms.nodal_pricing import NodalRole
    from .clearing_algorithms.redispatch import RedispatchRole

    class NodalMarketRole(MarketRole, NodalRole):
        pass

    class RedispatchMarketRole(MarketRole, RedispatchRole):
        pass

    clearing_mechanisms["redispatch"] = RedispatchMarketRole
    clearing_mechanisms["nodal"] = NodalMarketRole

except ImportError:
    pass

# try importing pyomo if it is installed
try:
    from .clearing_algorithms.complex_clearing import ComplexClearingRole
    from .clearing_algorithms.complex_clearing_dmas import ComplexDmasClearingRole

    class ComplexDmasClearingMarketRole(MarketRole, ComplexDmasClearingRole):
        pass

    class ComplexClearingMarketRole(MarketRole, ComplexClearingRole):
        pass

    clearing_mechanisms["pay_as_clear_complex"] = ComplexClearingMarketRole
    clearing_mechanisms["pay_as_clear_complex_dmas"] = ComplexDmasClearingMarketRole
except ImportError:
    pass


if __name__ == "__main__":
    from datetime import datetime, timedelta

    from dateutil import rrule as rr
    from dateutil.relativedelta import relativedelta as rd

    from ..utils import MarketProduct, get_available_products
    from .market_objects import MarketConfig, Orderbook

    simple_dayahead_auction_config = MarketConfig(
        "simple_dayahead_auction",
        market_products=[MarketProduct(rd(hours=+1), 1, rd(hours=1))],
        opening_hours=rr.rrule(
            rr.HOURLY,
            dtstart=datetime(2005, 6, 1),
            cache=True,
        ),
        opening_duration=timedelta(hours=1),
        amount_unit="MW",
        amount_tick=0.1,
        price_unit="€/MW",
        market_mechanism="pay_as_clear",
    )

    mr = MarketRole(simple_dayahead_auction_config)
    next_opening = simple_dayahead_auction_config.opening_hours.after(datetime.now())
    products = get_available_products(
        simple_dayahead_auction_config.market_products, next_opening
    )
    assert len(products) == 1

    print(products)
    start = products[0][0]
    end = products[0][1]
    only_hours = products[0][2]

    orderbook: Orderbook = [
        {
            "start_time": start,
            "end_time": end,
            "volume": 120,
            "price": 120,
            "agent_id": "gen1",
            "only_hours": None,
        },
        {
            "start_time": start,
            "end_time": end,
            "volume": 80,
            "price": 58,
            "agent_id": "gen1",
            "only_hours": None,
        },
        {
            "start_time": start,
            "end_time": end,
            "volume": 100,
            "price": 53,
            "agent_id": "gen1",
            "only_hours": None,
        },
        {
            "start_time": start,
            "end_time": end,
            "volume": -180,
            "price": 70,
            "agent_id": "dem1",
            "only_hours": None,
        },
    ]
    simple_dayahead_auction_config.market_mechanism = clearing_mechanisms[
        simple_dayahead_auction_config.market_mechanism
    ]
    mr.all_orders = orderbook
    clearing_result, meta = simple_dayahead_auction_config.market_mechanism(
        mr, products
    )
    import pandas as pd

    print(pd.DataFrame.from_dict(mr.all_orders))
    print(pd.DataFrame.from_dict(clearing_result))
    print(meta)

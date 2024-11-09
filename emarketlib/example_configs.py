# SPDX-FileCopyrightText: ASSUME Developers
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta

from dateutil import rrule as rr
from dateutil.relativedelta import relativedelta as rd

from emarketlib.market_objects import MarketConfig, MarketProduct

today = datetime.today()
CLEARING_FREQ_MINUTES = 5

p2p_trading_config = MarketConfig(
    "p2p_trading",
    today,
    additional_fields=["sender_id", "receiver_id"],
    market_products=[
        MarketProduct("quarter-hourly", 96),
        MarketProduct("half-hourly", 48),
        MarketProduct("hourly", 24),
    ],
    supports_get_unmatched=True,
    volume_unit="kWh",
    price_unit="€/kWh",
    price_tick=0.01,
    maximum_bid_price=9999,
    minimum_bid_price=-9999,
    market_mechanism="pay_as_bid_contract",
)


policy_trading_config = MarketConfig(
    "contract_trading",
    additional_fields=[
        "sender_id",
        "eligible_lambda",
        "contract",
        "evaluation_frequency",
    ],
    market_products=[
        MarketProduct(rd(months=+1, day=1, hour=0), 12, rd(days=2)),
        MarketProduct(
            rr.rrule(rr.MONTHLY, bymonth=(1, 4, 7, 10), bymonthday=1, byhour=0),
            11,
            first_delivery=rd(days=2),
        ),
        MarketProduct(rd(years=+1, yearday=1, hour=0), 10, rd(days=2)),
    ],
    opening_hours=rr.rrule(
        rr.MINUTELY,
        interval=CLEARING_FREQ_MINUTES,
        dtstart=datetime(2023, 1, 1),
        until=datetime(2023, 12, 31),
    ),
    opening_duration=timedelta(minutes=CLEARING_FREQ_MINUTES),
    supports_get_unmatched=True,
    volume_unit="MW",
    price_unit="€/MWh",
    price_tick=0.01,
    maximum_bid_price=9999,
    minimum_bid_price=-9999,
    market_mechanism="pay_as_bid_contract",
    # laufzeit vs abrechnungszeitraum
)

# eligible_lambda is a lambda to check if an agent is eligible to receive a policy (must have solar...)
# Control Reserve market
# control reserve can be bid for 7 days (überschneidende Gebots-Zeiträume)?
# FCR
market_start = today - timedelta(days=7) + timedelta(hours=10)
control_reserve_trading_config = MarketConfig(
    today,
    additional_fields=["eligible_lambda"],  # eligible_lambda
    market_products=[
        MarketProduct(rd(hours=+4), 6 * 7, rd(days=+1)),
    ],
    opening_hours=rr.rrule(rr.DAILY, market_start),
    opening_duration=timedelta(days=7),
    volume_unit="MW",
    volume_tick=0.1,
    price_unit="€/MW",
    price_tick=0.01,
    maximum_bid_price=9999,
    minimum_bid_price=-9999,
)  # pay-as-bid/merit-order one sided

# RAM Regelarbeitsmarkt - Control Reserve
market_start = today - timedelta(days=2) + timedelta(hours=12)
control_work_trading_config = MarketConfig(
    today,
    additional_fields=["eligible_lambda"],
    market_products=[
        MarketProduct("quarter-hourly", 96),
    ],
    opening_hours=rr.rrule(rr.DAILY, market_start),
    opening_duration=timedelta(days=1),
    volume_unit="MW",
    volume_tick=0.1,
    price_unit="€/MW",
    price_tick=0.01,
    maximum_bid_price=9999,
    minimum_bid_price=-9999,
    # obligation = innerhalb von 1 minute reagieren kann
)  # pay-as-bid/merit-order

# MISO Nodal market
# https://help.misoenergy.org/knowledgebase/article/KA-01024/en-us
market_start = today - timedelta(days=14) + timedelta(hours=10, minutes=30)
# 05.2010
miso_day_ahead_config = MarketConfig(
    today,
    additional_fields=["node_id"],
    market_products=[
        MarketProduct("hourly", 24),
    ],
    opening_hours=rr.rrule(rr.DAILY, market_start),
    opening_duration=timedelta(days=1),
    volume_unit="MW",
    price_unit="$/MW",
    price_tick=0.01,
    maximum_bid_price=9999,
    minimum_bid_price=-9999,
    eligible_obligations_lambda=lambda agent: agent.location,
)  # pay-as-bid/merit-order

# ISO gibt spezifisches Marktergebnis welches nicht teil des Angebots war

# Contour Map
# https://www.misoenergy.org/markets-and-operations/real-time--market-data/markets-displays/
# Realtime Data API
# https://www.misoenergy.org/markets-and-operations/RTDataAPIs/
# SCED
# https://help.misoenergy.org/knowledgebase/article/KA-01112/en-us
# Market Closure Table (unclear)
# https://help.misoenergy.org/knowledgebase/article/KA-01163/en-us
# Metrics:
# https://cdn.misoenergy.org/202211%20Markets%20and%20Operations%20Report627372.pdf (p. 60-63)
# Start 12.2009
countrylist = ["BW"]
miso_real_time_config = MarketConfig(
    today,
    additional_fields=["node_id"],
    market_products=[
        MarketProduct("5minutes", 12),
        # unclear how many slots can be traded?
        # at least the current hour
    ],
    opening_hours=rr.rrule(rr.MINUTELY, interval=5, dtstart=today - timedelta(hours=1)),
    opening_duration=timedelta(hours=1),
    volume_unit="MW",
    price_unit="$/MW",
    price_tick=0.01,
    maximum_bid_price=9999,
    minimum_bid_price=-9999,
    eligible_obligations_lambda=lambda agent: agent.location in countrylist,
    market_mechanism="pay_as_clear",
)


# result_bids = clearing(self, input_bids)
# asymmetrical auction
# one sided acution

# GME market - italian
# which market products exist?
# 11.2007


# PJM: https://pjm.com/markets-and-operations/energy/real-time/historical-bid-data/unit-bid.aspx
# DataMiner: https://dataminer2.pjm.com/feed/da_hrl_lmps/definition
# ContourMap: https://pjm.com/markets-and-operations/interregional-map.aspx

# TODO: ISO NE, ERCOT, CAISO

## Agenten müssen ihren Verpflichtungen nachkommen
## TODO: geographische Voraussetzungen - wer darf was - Marktbeitrittsbedingungen

# LMP Markt:
# https://www.e-education.psu.edu/eme801/node/498
# All Constraints and marginal Costs are collected in the LMP market
# Markt dispatched kosten an Demand nach Stability constrained Merit-Order
# participants are paid only the marginal cost
# difference is congestion revenue -> is kept by TSO?

# All operating facilities in the U.S. devote the first portion of their revenues to the maintenance and operations of the priced lanes.
# The traffic monitoring, tolling, enforcement, incident management, administration, and routine maintenance costs can be significant,
# https://www.cmap.illinois.gov/updates/all/-/asset_publisher/UIMfSLnFfMB6/content/examples-of-how-congestion-pricing-revenues-are-used-elsewhere-in-the-u-s-


# Virtual profitability Index:
# sum of all profits (transactions settled above price) / Total traded MWh


### Auswertung Index - Benchmark
# ID3
# https://www.eex.com/fileadmin/EEX/Downloads/Trading/Specifications/Indices/DE/20200131-indexbeschreibung-v009b-d-final-track-changes-data.pdf
# https://www.epexspot.com/en/indices#auction-price-indices


# 1. multi-stage market -> clears locally, rejected_bids are pushed up a layer
# 2. nodal pricing -> centralized market which handles different node_ids different - can also be used for country coupling
# 3. nodal limited market -> clear by node_id, select cheapest generation orders from surrounding area up to max_capacity, clear market
# 4. one sided market? - fixed demand as special case of two sided market
# 5.

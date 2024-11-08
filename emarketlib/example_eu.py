# SPDX-FileCopyrightText: ASSUME Developers
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta

from dateutil import rrule as rr
from dateutil.relativedelta import relativedelta as rd

from emarketlib.market_objects import MarketConfig, MarketProduct

# relevant information
# https://www.next-kraftwerke.de/wissen/spotmarkt-epex-spot
# https://www.epexspot.com/sites/default/files/2023-01/22-10-25_TradingBrochure.pdf

# EPEX DayAhead-Auction:
# https://www.epexspot.com/en/tradingproducts#day-ahead-trading
# 45 days ahead (5 weeks)
# https://www.epexspot.com/sites/default/files/download_center_files/EPEX%20SPOT%20Market%20Rules_0_0.zip

epex_dayahead_auction_config = MarketConfig(
    "epex_dayahead_auction",
    additional_fields=["link", "offer_id"],
    market_products=[MarketProduct(rd(hours=+1), 24 * 45, rd(days=2, hour=0))],
    supports_get_unmatched=False,  # orders persist between clearings - shorter intervals
    opening_hours=rr.rrule(
        rr.DAILY, byhour=12, dtstart=datetime(2005, 6, 1), until=datetime(2030, 12, 31)
    ),
    opening_duration=timedelta(days=1),
    maximum_gradient=0.1,  # can only change 10% between hours - should be more generic
    volume_unit="MWh",
    volume_tick=0.1,
    price_unit="€/MW",
    market_mechanism="pay_as_clear",
)

# EPEX Intraday-Auction:
# https://www.epexspot.com/en/tradingproducts#intraday-trading
# closes/opens at 15:00 every day
epex_intraday_auction_config = MarketConfig(
    "epex_intraday_auction",
    market_products=[
        MarketProduct(
            duration=rd(minutes=+15),
            count=96,
            first_delivery=rd(days=2, hour=0),
        )
    ],
    supports_get_unmatched=False,
    opening_hours=rr.rrule(
        rr.DAILY,
        byhour=15,
        dtstart=datetime(2011, 12, 15),
        until=datetime(2023, 12, 31),
    ),
    opening_duration=timedelta(days=1),
    volume_unit="MWh",
    volume_tick=0.1,
    price_unit="€/MWh",
    price_tick=0.01,
    maximum_bid_price=4000,
    minimum_bid_price=-3000,
    market_mechanism="pay_as_clear",
)

# EPEX IntraDay-Trading:
# https://www.epexspot.com/en/tradingproducts#intraday-trading
# Price list 2019: https://www.coursehero.com/file/43528280/Price-listpdf/
# 25000€ Entry fee
# DAM + IDM 10000€/a
# IDM only 5000€/a
# 15m IDM auction 5000€/a
# https://www.epexspot.com/en/downloads#rules-fees-processes


# Trading should start at 15:00
def dynamic_end(current_time: datetime):
    if current_time.hour < 15:
        # if the new auction day did not start- only the rest of today can be traded
        return rd(days=+1, hour=0)
    else:
        # after 15:00 the next day can be traded too
        return rd(days=+2, hour=0)


# eligible_lambda for marketproducts (also see RAM)
# 60 minutes before for xbid
# 30 minutes before in DE
# 5 minutes before in same TSO area
# TODO: area specific dependencies
CLEARING_FREQ_MINUTES = 5
epex_intraday_trading_config = MarketConfig(
    market_id="epex_intraday_trading",
    opening_hours=rr.rrule(
        rr.MINUTELY,
        interval=CLEARING_FREQ_MINUTES,
        dtstart=datetime(2013, 11, 1),
        until=datetime(2023, 12, 31),
    ),
    opening_duration=timedelta(minutes=CLEARING_FREQ_MINUTES),
    market_products=[
        MarketProduct(rd(minutes=+15), dynamic_end, rd(minutes=+5)),
        MarketProduct(rd(minutes=+30), dynamic_end, rd(minutes=30)),
        MarketProduct(rd(hours=+1), dynamic_end, rd(minutes=30)),
    ],
    eligible_obligations_lambda=lambda agent, market: agent.aid in market.participants
    and agent.payed > 10000,  # per year + 25k once
    market_mechanism="pay_as_bid",  # TODO remove orders from same agent when setting for same product
    volume_unit="MWh",
    volume_tick=0.1,
    price_unit="€/MWh",
    price_tick=0.01,
    maximum_bid_price=9999,
    minimum_bid_price=-9999,
)
# pay as bid
# publishes market results to TSO every 15 minutes
# matching findet nur in eigener Regelzone für die letzen 15 Minuten statt - sonst mindestens 30 Minuten vorher

workdays = (rr.MO, rr.TU, rr.WE, rr.TH, rr.FR)

# TerminHandel:
# https://www.eex.com/en/markets/power/power-futures
# Price List: https://www.eex.com/fileadmin/EEX/Downloads/Trading/Price_Lists/20230123_Price_List_EEX_AG_0107a_E_FINAL.pdf
# Transaktionsentgelt: 0,0075 €/MWh (TODO)
# 22000€ Teilnahme pro Jahr
# open from 8:00 to 18:00 on workdays
# https://www.eex.com/en/markets/power/power-futures
# continuous clearing - approximated through 5 minute intervals
# trading structure:
# https://www.eex.com/en/markets/trading-ressources/rules-and-regulations
CLEARING_FREQ_MINUTES = 5
two_days_after_start = rd(days=2, hour=0)
eex_future_trading_config = MarketConfig(
    market_id="eex_future_trading",
    additional_fields=["link", "offer_id"],
    opening_hours=rr.rrule(
        rr.MINUTELY,
        interval=CLEARING_FREQ_MINUTES,
        byhour=range(8, 18),
        byweekday=workdays,
        dtstart=datetime(2002, 1, 1),
        until=datetime(2023, 12, 31),
    ),
    opening_duration=timedelta(minutes=CLEARING_FREQ_MINUTES),
    market_products=[
        MarketProduct(rd(days=+1, hour=0), 7, two_days_after_start),
        MarketProduct(rd(weeks=+1, weekday=0, hour=0), 4, two_days_after_start),
        MarketProduct(rd(months=+1, day=1, hour=0), 9, two_days_after_start),
        MarketProduct(
            rr.rrule(rr.MONTHLY, bymonth=(1, 4, 7, 10), bymonthday=1, byhour=0),
            11,
            two_days_after_start,
        ),
        MarketProduct(rd(years=+1, yearday=1, hour=0), 10, two_days_after_start),
    ],
    maximum_bid_price=9999,
    minimum_bid_price=-9999,
    volume_unit="MW",  # offer volume is in MW for whole product duration
    volume_tick=0.1,
    price_unit="€/MWh",  # cost is given in €/MWh - total product cost results in price*amount/(duration in hours)
    price_tick=0.01,
    eligible_obligations_lambda=lambda agent, market: agent.aid in market.participants
    and agent.payed > 22000,  # per year
    market_mechanism="pay_as_bid",
)


# AfterMarket:
# https://www.epexspot.com/en/tradingproducts#after-market-trading
# Trading end should be 12:30 day after delivery (D+1) - dynamic repetition makes it possible
def dynamic_repetition(current_time):
    if current_time.hour < 13:
        return +(24 + current_time.hour)
    else:
        return +(current_time.hour)


epex_aftermarket_trading_config = MarketConfig(
    "epex_aftermarket",
    additional_fields=["link", "offer_id"],
    market_products=[
        # negative duration, to go back in time
        MarketProduct(rd(hours=-1), dynamic_repetition, timedelta()),
    ],
    opening_hours=rr.rrule(
        rr.MINUTELY,
        interval=CLEARING_FREQ_MINUTES,
        byhour=range(8, 18),
        byweekday=workdays,
        dtstart=datetime(2023, 1, 1),
        until=datetime(2023, 12, 31),
    ),
    opening_duration=timedelta(minutes=CLEARING_FREQ_MINUTES),
    volume_unit="MWh",
    volume_tick=0.1,
    price_unit="€/MWh",
    price_tick=0.01,
    supports_get_unmatched=True,
    maximum_bid_price=9999,
    minimum_bid_price=-9999,
    market_mechanism="pay_as_bid",
)

# EPEX Emissionsmarkt Spot:
# EU Allowance (EUA)
# https://www.eex.com/de/maerkte/umweltprodukte/eu-ets-auktionen
# https://www.eex.com/de/maerkte/umweltprodukte/eu-ets-spot-futures-options
# https://www.eex.com/fileadmin/EEX/Markets/Environmental_markets/Emissions_Spot__Futures___Options/20200619-EUA_specifications_v2.pdf

epex_emission_trading_config = MarketConfig(
    "epex_emission_trading",
    market_products=[
        MarketProduct("yearly", 10),
    ],
    supports_get_unmatched=True,
    volume_unit="t CO2",
    volume_tick=1,
    price_unit="€/t",
    price_tick=5,  # only 5 tons can be bought together
)

eu_market_design = [
    epex_dayahead_auction_config,
    epex_intraday_auction_config,
    epex_intraday_trading_config,
    eex_future_trading_config,
]

eu_full_market_design = [epex_aftermarket_trading_config, epex_emission_trading_config]
eu_full_market_design.extend(eu_market_design)

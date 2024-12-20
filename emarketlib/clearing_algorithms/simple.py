# SPDX-FileCopyrightText: Florian Maurer, ASSUME Developers
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import random
from datetime import timedelta
from itertools import groupby
from operator import itemgetter

from ..base_market import MarketMechanism
from ..market_objects import MarketConfig, MarketProduct, Orderbook

log = logging.getLogger(__name__)


def max_map(column, iterable):
    return max([0, *map(itemgetter(column), iterable)])


def min_map(column, iterable):
    return max([0, *map(itemgetter(column), iterable)])


def calculate_meta(accepted_supply_orders, accepted_demand_orders, product):
    supply_volume = sum(map(itemgetter("accepted_volume"), accepted_supply_orders))
    demand_volume = -sum(map(itemgetter("accepted_volume"), accepted_demand_orders))
    prices = list(
        map(
            itemgetter("accepted_price"),
            (accepted_demand_orders + accepted_supply_orders),
        )
    ) or [0]
    # can also be self.marketconfig.maximum_bid..?
    duration_hours = (product[1] - product[0]) / timedelta(hours=1)
    avg_price = 0
    if supply_volume:
        weighted_price = [
            order["accepted_volume"] * order["accepted_price"]
            for order in accepted_supply_orders
        ]
        avg_price = sum(weighted_price) / supply_volume
    return {
        "supply_volume": supply_volume,
        "demand_volume": demand_volume,
        "demand_volume_energy": demand_volume * duration_hours,
        "supply_volume_energy": supply_volume * duration_hours,
        "price": avg_price,
        "max_price": max(prices),
        "min_price": min(prices),
        "node": None,
        "product_start": product[0],
        "product_end": product[1],
        "only_hours": product[2],
    }


class QuasiUniformPricingRole(MarketMechanism):
    def __init__(self, marketconfig: MarketConfig):
        super().__init__(marketconfig)

    def clear(
        self, orderbook: Orderbook, market_products
    ) -> (Orderbook, Orderbook, list[dict]):
        """
        Performs electricity market clearing using a pay-as-clear mechanism. This means that the clearing price is the
        highest price that is still accepted. The clearing price is the same for all accepted orders.

        Args:
            orderbook (Orderbook): the orders to be cleared as an orderbook
            market_products (list[MarketProduct]): the list of products which are cleared in this clearing

        Returns:
            tuple: accepted orderbook, rejected orderbook and clearing meta data
        """
        market_getter = itemgetter("start_time", "end_time", "only_hours")
        accepted_orders: Orderbook = []
        rejected_orders: Orderbook = []
        clear_price = 0
        meta = []
        orderbook.sort(key=market_getter)
        for product, product_orders in groupby(orderbook, market_getter):
            accepted_demand_orders: Orderbook = []
            accepted_supply_orders: Orderbook = []
            product_orders = list(product_orders)
            if product not in market_products:
                rejected_orders.extend(product_orders)
                # log.debug(f'found unwanted bids for {product} should be {market_products}')
                continue

            supply_orders = [x for x in product_orders if x["volume"] > 0]
            demand_orders = [x for x in product_orders if x["volume"] < 0]
            # volume 0 is ignored/invalid

            # Sort supply orders by price with randomness for tie-breaking
            supply_orders.sort(key=lambda x: (x["price"], random.random()))

            # Sort demand orders by price in descending order with randomness for tie-breaking
            demand_orders.sort(
                key=lambda x: (x["price"], random.random()), reverse=True
            )

            dem_vol, gen_vol = 0, 0
            # the following algorithm is inspired by one bar for generation and one for demand
            # add generation for currents demand price, until it matches demand
            # generation above it has to be sold for the lower price (or not at all)
            for demand_order in demand_orders:
                if not supply_orders:
                    # if no more generation - continue
                    # reject left over demand at the end
                    continue

                # assert dem_vol == gen_vol
                # now add the next demand order
                dem_vol += -demand_order["volume"]
                demand_order["accepted_volume"] = demand_order["volume"]
                # and add supply until the demand order is matched
                while supply_orders and gen_vol < dem_vol:
                    supply_order = supply_orders.pop(0)
                    if supply_order["price"] <= demand_order["price"]:
                        added = supply_order["volume"] - supply_order.get(
                            "accepted_volume", 0
                        )
                        should_insert = not supply_order.get("accepted_volume")
                        supply_order["accepted_volume"] = supply_order["volume"]
                        if should_insert:
                            accepted_supply_orders.append(supply_order)
                        gen_vol += added
                    # if supply is not partially accepted before, reject it
                    elif not supply_order.get("accepted_volume"):
                        rejected_orders.append(supply_order)
                # now we know which orders we need
                # we only need to see how to arrange it.

                diff = gen_vol - dem_vol

                if diff < 0:
                    # gen < dem
                    # generation is not enough - accept partially
                    demand_order["accepted_volume"] = demand_order["volume"] - diff
                elif diff > 0:
                    # generation left over - accept generation bid partially
                    supply_order = accepted_supply_orders[-1]
                    supply_order["accepted_volume"] = supply_order["volume"] - diff

                    # changed supply_order is still part of to_commit and will be added
                    # only volume-diff can be sold for current price
                    gen_vol -= diff

                    # add left over to supply_orders again
                    supply_orders.insert(0, supply_order)
                    demand_order["accepted_volume"] = demand_order["volume"]
                else:
                    demand_order["accepted_volume"] = demand_order["volume"]

                if demand_order["accepted_volume"]:
                    accepted_demand_orders.append(demand_order)

            # if demand is fulfilled, we do have some additional supply orders
            # these will be rejected
            for order in supply_orders:
                # if the order was not accepted partially, it is rejected
                if not order.get("accepted_volume"):
                    rejected_orders.append(order)

            for order in demand_orders:
                # if the order was not accepted partially, it is rejected
                if not order.get("accepted_volume"):
                    rejected_orders.append(order)

            # set clearing price - merit order - uniform pricing
            if accepted_supply_orders:
                clear_price = float(max_map("price", accepted_supply_orders))
            else:
                clear_price = 0

            accepted_product_orders = self.set_pricing(
                market_products,
                accepted_supply_orders,
                accepted_demand_orders,
                clear_price,
                rejected_orders,
            )

            accepted_orders.extend(accepted_product_orders)

            meta.append(
                calculate_meta(
                    accepted_supply_orders,
                    accepted_demand_orders,
                    product,
                )
            )

        return accepted_orders, rejected_orders, meta, {}


class PayAsClearRole(QuasiUniformPricingRole):
    def set_pricing(
        self,
        market_products: list[MarketProduct],
        accepted_supply_orders: list[dict],
        accepted_demand_orders: Orderbook,
        clear_price: float,
        rejected_orders: Orderbook,
    ) -> Orderbook:
        """
        Sets the pricing for the accepted orders.
        """
        accepted_product_orders = accepted_demand_orders + accepted_supply_orders
        for order in accepted_product_orders:
            order["accepted_price"] = clear_price

        return accepted_product_orders


class AverageMechanismRole(QuasiUniformPricingRole):
    """
    Average double auction mechanism
    * IR
    * not IC - strategic bidding is helpful
    """

    def set_pricing(
        self,
        market_products: list[MarketProduct],
        accepted_supply_orders: Orderbook,
        accepted_demand_orders: Orderbook,
        clear_price: float,
        rejected_orders: Orderbook,
    ) -> Orderbook:
        sell_price = max_map("price", accepted_supply_orders)
        buy_price = min_map("price", accepted_demand_orders)
        p = sell_price + buy_price / 2
        for order in accepted_demand_orders + accepted_supply_orders:
            order["accepted_price"] = p
        return accepted_demand_orders + accepted_supply_orders


class TradeReductionRole(QuasiUniformPricingRole):
    """
    * IR
    * IC
    * not SBB - auctioneer has surplus
    * not EE - the last trade does not take place

    The last trade does not take place, which makes this mechanism not efficient.

    """

    def set_pricing(
        self,
        market_products: list[MarketProduct],
        accepted_supply_orders: Orderbook,
        accepted_demand_orders: Orderbook,
        clear_price: float,
        rejected_orders: Orderbook,
    ) -> Orderbook:
        """
        Sets the pricing for the accepted orders.
        """
        sell_price = max_map("price", accepted_supply_orders)

        # remove last trade
        accepted_supply_orders.sort(key=lambda x: x["price"])
        accepted_demand_orders.sort(key=lambda x: x["price"], reverse=True)
        reduced_supply = accepted_supply_orders.pop(-1)
        reduced_demand = accepted_demand_orders.pop(-1)
        if reduced_demand["accepted_volume"] == reduced_supply["accepted_volume"]:
            rejected_orders.append(reduced_supply)
            rejected_orders.append(reduced_demand)
        if reduced_demand["accepted_volume"] > reduced_supply["accepted_volume"]:
            reduced_demand["accepted_volume"] -= reduced_supply["accepted_volume"]
            rejected_orders.append(reduced_supply)
        else:
            reduced_supply["accepted_volume"] -= reduced_demand["accepted_volume"]
            rejected_orders.append(reduced_demand)

        # continue clearing
        for order in accepted_supply_orders:
            order["accepted_price"] = sell_price

        buy_price = min_map("price", accepted_demand_orders)

        for order in accepted_demand_orders:
            order["accepted_price"] = buy_price

        accepted_product_orders = accepted_demand_orders + accepted_supply_orders
        return accepted_product_orders


class McAfeeRole(QuasiUniformPricingRole):
    """
    * IR - buyer pays less than his value, seller receives more
    * IC - truthful bidding is optimal
    * WBB but not SBB - auctioneer has surplus
    * not EE - the last trade does not take place if b < p or p < s
    """

    def set_pricing(
        self,
        market_products: list[MarketProduct],
        accepted_supply_orders: Orderbook,
        accepted_demand_orders: Orderbook,
        clear_price: float,
        rejected_orders: Orderbook,
    ) -> Orderbook:
        """
        Sets the pricing for the accepted orders.
        """
        sell_price = max_map("price", accepted_supply_orders)
        buy_price = min_map("price", accepted_demand_orders)
        rejected_supply_orders = [x for x in rejected_orders if x["volume"] > 0]
        rejected_demand_orders = [x for x in rejected_orders if x["volume"] < 0]
        next_sell_price = min_map("price", rejected_supply_orders)
        next_buy_price = max_map("price", rejected_demand_orders)

        p = (next_sell_price + next_buy_price) / 2

        if buy_price >= p >= sell_price:
            sell_price = p
            buy_price = p

        for order in accepted_supply_orders:
            order["accepted_price"] = sell_price

        for order in accepted_demand_orders:
            order["accepted_price"] = buy_price

        return accepted_demand_orders + accepted_supply_orders


class VCGAuctionRole(QuasiUniformPricingRole):
    """
    Vickrey-Clarke-Groves double auction mechanism
    * IR - buyer pays less than his value, seller receives more
    * IC - truthful bidding is optimal
    * not Balanced Budget - difference has to be paid by the auctioneer
    * EE - efficient as all trades take place

    """

    def set_pricing(
        self,
        market_products: list[MarketProduct],
        accepted_supply_orders: Orderbook,
        accepted_demand_orders: Orderbook,
        clear_price: float,
        rejected_orders: Orderbook,
    ) -> Orderbook:
        """
        Sets the pricing for the accepted orders.
        """
        sell_price = max_map("price", accepted_supply_orders)
        buy_price = min_map("price", accepted_demand_orders)
        rejected_supply_orders = [x for x in rejected_orders if x["volume"] > 0]
        rejected_demand_orders = [x for x in rejected_orders if x["volume"] < 0]
        next_sell_price = min_map("price", rejected_supply_orders)
        next_buy_price = max_map("price", rejected_demand_orders)

        if next_sell_price > buy_price:
            if next_buy_price < sell_price:
                sell_price, buy_price = buy_price, sell_price
            else:
                sell_price = buy_price
                buy_price = next_buy_price
        else:
            if next_buy_price < sell_price:
                sell_price = next_buy_price
                buy_price = sell_price
            else:
                sell_price = next_sell_price
                buy_price = next_buy_price

        for order in accepted_supply_orders:
            order["accepted_price"] = sell_price

        for order in accepted_demand_orders:
            order["accepted_price"] = buy_price

        # calculate payment which the auctioneer has to pay
        total_payment = 0
        for order in accepted_demand_orders:
            total_payment += order["accepted_price"] * order["accepted_volume"]
        for order in accepted_supply_orders:
            total_payment -= order["accepted_price"] * order["accepted_volume"]

        return accepted_demand_orders + accepted_supply_orders


class PayAsBidRole(MarketMechanism):
    def __init__(self, marketconfig: MarketConfig):
        super().__init__(marketconfig)

    def clear(
        self, orderbook: Orderbook, market_products: list[MarketProduct]
    ) -> (Orderbook, Orderbook, list[dict]):
        """
        Simulates electricity market clearing using a pay-as-bid mechanism.

        Args:
            orderbook (Orderbook): the orders to be cleared as an orderbook
            market_products (list[MarketProduct]): the list of products which are cleared in this clearing

        Returns:
            tuple[Orderbook, Orderbook, list[dict]]: accepted orderbook, rejected orderbook and clearing meta data
        """

        market_getter = itemgetter("start_time", "end_time", "only_hours")
        accepted_orders: Orderbook = []
        rejected_orders: Orderbook = []
        meta = []
        orderbook.sort(key=market_getter)
        for product, product_orders in groupby(orderbook, market_getter):
            accepted_demand_orders: Orderbook = []
            accepted_supply_orders: Orderbook = []
            if product not in market_products:
                rejected_orders.extend(product_orders)
                # log.debug(f'found unwanted bids for {product} should be {market_products}')
                continue

            product_orders = list(product_orders)
            supply_orders = [x for x in product_orders if x["volume"] > 0]
            demand_orders = [x for x in product_orders if x["volume"] < 0]
            # volume 0 is ignored/invalid

            # Sort supply orders by price with randomness for tie-breaking
            supply_orders.sort(key=lambda i: (i["price"], random.random()))
            # Sort demand orders by price in descending order with randomness for tie-breaking
            demand_orders.sort(
                key=lambda i: (i["price"], random.random()), reverse=True
            )

            dem_vol, gen_vol = 0, 0
            # the following algorithm is inspired by one bar for generation and one for demand
            # add generation for currents demand price, until it matches demand
            # generation above it has to be sold for the lower price (or not at all)
            for demand_order in demand_orders:
                if not supply_orders:
                    # if no more generation - continue
                    # reject left over demand at the end
                    continue

                dem_vol += -demand_order["volume"]
                to_commit: Orderbook = []

                while supply_orders and gen_vol < dem_vol:
                    supply_order = supply_orders.pop(0)
                    if supply_order["price"] <= demand_order["price"]:
                        supply_order["accepted_volume"] = supply_order["volume"]
                        to_commit.append(supply_order)
                        gen_vol += supply_order["volume"]
                    # if supply is not partially accepted before, reject it
                    elif not supply_order.get("accepted_volume"):
                        rejected_orders.append(supply_order)
                # now we know which orders we need
                # we only need to see how to arrange it.

                diff = gen_vol - dem_vol

                if diff < 0:
                    print("mydiff", diff)
                    # gen < dem
                    demand_order["accepted_volume"] = demand_order["volume"] - diff
                elif diff > 0:
                    # generation left over - split generation
                    supply_order = to_commit[-1]
                    split_supply_order = supply_order.copy()
                    split_supply_order["volume"] = diff
                    supply_order["accepted_volume"] = supply_order["volume"] - diff
                    # only volume-diff can be sold for current price
                    # add left over to supply_orders again
                    gen_vol -= diff

                    supply_orders.insert(0, split_supply_order)
                    demand_order["accepted_volume"] = demand_order["volume"]
                else:
                    # diff == 0 perfect match
                    demand_order["accepted_volume"] = demand_order["volume"]

                if demand_order["accepted_volume"]:
                    accepted_demand_orders.append(demand_order)
                # pay as bid
                for supply_order in to_commit:
                    supply_order["accepted_price"] = supply_order["price"]

                    demand_order["accepted_price"] = supply_order["price"]
                accepted_supply_orders.extend(to_commit)

            # if demand is fulfilled, we do have some additional supply orders
            # these will be rejected
            for order in supply_orders:
                # if the order was not accepted partially, it is rejected
                if not order.get("accepted_volume"):
                    rejected_orders.append(order)

            for order in demand_orders:
                # if the order was not accepted partially, it is rejected
                if not order.get("accepted_volume"):
                    rejected_orders.append(order)

            accepted_product_orders = accepted_demand_orders + accepted_supply_orders

            accepted_orders.extend(accepted_product_orders)
            meta.append(
                calculate_meta(
                    accepted_supply_orders,
                    accepted_demand_orders,
                    product,
                )
            )
        return accepted_orders, rejected_orders, meta, {}

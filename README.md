<!--
SPDX-FileCopyrightText: Florian Maurer

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# emarketlib

A Python library for simulating electricity markets and market mechanisms.

## Features

- Base market implementation with configurable market mechanisms
- Multiple clearing algorithms:
  - Pay-as-clear (uniform pricing)
  - Pay-as-bid
  - Average mechanism
  - Trade reduction mechanism
  - McAfee mechanism
  - VCG auction mechanism
- Support for:
  - Market registration and validation
  - Order book handling
  - Market clearing
  - Result storage and querying
  - Grid topology data

## Market Mechanisms

### Pay-as-clear (Uniform Pricing)
- All accepted orders receive the same clearing price
- Clearing price determined by highest accepted supply order
- Merit order based clearing with random tie-breaking

### Pay-as-bid
- Each accepted order is settled at its bid price
- Merit order based clearing with random tie-breaking

### Average Mechanism
- Clearing price is average of highest accepted supply and lowest accepted demand price
- Not incentive compatible but individually rational

### Trade Reduction
- Removes last matched trade to achieve incentive compatibility
- Not efficient but individually rational
- Budget balanced but not strongly budget balanced

### McAfee Mechanism
- Incentive compatible and individually rational
- Weakly budget balanced
- Not efficient when price conditions not met

### VCG Auction
- Incentive compatible and individually rational
- Efficient but not budget balanced
- Auctioneer must subsidize difference

## Usage

```python
from emarketlib import MarketConfig
from emarketlib.clearing_algorithms.simple import PayAsClearRole

# Create market config
config = MarketConfig(
    market_id="day_ahead",
    # Add configuration parameters
)

# Initialize market with clearing mechanism
market = PayAsClearRole(config)
```


## Installation


`pip install emarketlib`

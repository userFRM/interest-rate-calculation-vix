# US Treasury Yield Curve Processor

[![Python CI](https://github.com/yourusername/treasury-rates-processor/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/treasury-rates-processor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

A Python tool that fetches US Treasury yield curve data and calculates risk-free rates for VIX-style volatility calculations. This implementation follows the Cboe VIX Mathematics Methodology for interest rate calculations.

## Features

- 🏦 Fetches daily treasury yield curve data from the US Treasury website
- 📊 Performs linear interpolation for missing maturities
- 🔄 Converts Bond Equivalent Yields (BEY) to continuously compounded APY rates
- 📈 Calculates near-term and next-term rates for VIX calculations
- 🦀 Generates Rust code snippets for direct integration
- 🐳 Docker support for easy deployment
- 📝 Zero external dependencies (uses only Python standard library)

## VIX Methodology Support

This processor implements the interest rate calculation methodology from the Cboe VIX Mathematics Methodology document:

- **BEY to APY conversion**: `APY = (1 + BEY/2)^2 - 1`
- **Continuous rate conversion**: `r_t = ln(1 + APY)`
- **Near-term and next-term rate extraction** for option pricing

## Installation

### Local Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/treasury-rates-processor.git
cd treasury-rates-processor

# No dependencies to install! Uses only Python standard library

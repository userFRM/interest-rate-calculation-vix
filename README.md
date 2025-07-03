# US Treasury Yield Curve Processor

[![Python CI](https://github.com/userFRM/interest-rate-calculation-vix/actions/workflows/ci.yml/badge.svg)](https://github.com/userFRM/interest-rate-calculation-vix/actions/workflows/ci.yml)
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
git clone https://github.com/userFRM/interest-rate-calculation-vix.git
cd interest-rate-calculation-vix

# No dependencies to install! Uses only Python standard library
```

### Docker Installation

```bash
# Build the Docker image
docker build -t treasury-rates .

# Or pull from Docker Hub
docker pull userFRM/treasury-rates:latest
```

## Usage

### Command Line

```bash
# Use default VIX terms (30 and 60 days)
python src/treasury_rates.py

# Specify custom terms
python src/treasury_rates.py --near 23 --next 30

# Use specific year
python src/treasury_rates.py --year 2024

# JSON output only (for piping to other programs)
python src/treasury_rates.py --json-only

# Include Rust code output
python src/treasury_rates.py --rust-output

# Full example with all options
python src/treasury_rates.py --near 23 --next 30 --year 2024 --rust-output --verbose
```

### Docker

```bash
# Run with default settings
docker run treasury-rates

# Run with custom parameters
docker run treasury-rates --near 23 --next 30

# Save output to host machine
docker run -v $(pwd):/data treasury-rates --output-file /data/rates.json

# Run as a service
docker-compose up -d
```

### Python API

```python
import asyncio
from treasury_rates import YieldCurveProcessor, YieldCurveConfig

async def get_rates():
    # Create processor with custom configuration
    config = YieldCurveConfig(year=2024)
    processor = YieldCurveProcessor(config)

    # Fetch and process data
    xml_content = await processor.fetch_data()
    processed_data = processor.process(xml_content)

    # Get latest rates
    date, rates = processor.get_latest_rates(processed_data)

    # Get VIX-style term rates
    vix_rates = processor.get_vix_term_rates(rates, near_term_days=23, next_term_days=30)

    return vix_rates

# Run
rates = asyncio.run(get_rates())
print(f"Near-term rate: {rates['near_term_rate']:.4%}")
print(f"Next-term rate: {rates['next_term_rate']:.4%}")
```

## Output Formats

### Standard Output

```
Latest Date: 2024-07-02T00:00:00
----------------------------------------
Maturity:    30 days, r_t: 0.042838
Maturity:    60 days, r_t: 0.043817
...

============================================================
VIX-Style Term Rates (Continuously Compounded APY):
============================================================
Near-term rate (30 days): 0.042838 (4.28%)
Next-term rate (60 days): 0.043817 (4.38%)
```

### JSON Output

```json
{
  "date": "2024-07-02T00:00:00",
  "year": 2024,
  "vix_term_rates": {
    "near_term_rate": 0.042838,
    "next_term_rate": 0.043817,
    "near_term_days": 30,
    "next_term_days": 60
  },
  "full_rates": {
    "30": 0.042838,
    "60": 0.043817,
    ...
  }
}
```

### Rust Code Output

```rust
// Risk-free rates for VIX calculation
let risk_free_rates = RiskFreeRates {
    near_term_rate: 0.042838,  // 4.28% annualized (30 days)
    next_term_rate: 0.043817,  // 4.38% annualized (60 days)
    timestamp: chrono::Utc::now(),  // Latest data from: 2024-07-02T00:00:00
};
```

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=src tests/

# Run specific test
python -m pytest tests/test_treasury_rates.py::test_rate_interpolation
```

### Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## CI/CD

This project uses GitHub Actions for continuous integration:

- ✅ Automated testing on Python 3.8, 3.9, 3.10, 3.11, and 3.12
- ✅ Code style checking with pylint
- ✅ Type checking with mypy
- ✅ Security scanning
- ✅ Docker image building and publishing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- US Treasury for providing public yield curve data
- Cboe for the VIX Mathematics Methodology documentation
- The Python community for the excellent standard library

## Support

- 🐛 Issues: [GitHub Issues](https://github.com/userFRM/interest-rate-calculation-vix/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/userFRM/interest-rate-calculation-vix/discussions)
```

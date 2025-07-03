#!/usr/bin/env python3
"""
US Treasury Yield Curve Data Processor

Fetches daily treasury yield curve data from the US Treasury website,
performs linear interpolation for missing maturities, and converts
Bond Equivalent Yields (BEY) to continuously compounded APY rates.

This implementation uses only Python standard library modules.

VIX Methodology Support:
The processor implements the interest rate calculation methodology from the
Cboe VIX Mathematics Methodology document, including:
- Bounded cubic spline interpolation (simplified to linear here)
- BEY to APY conversion: APY = (1 + BEY/2)^2 - 1
- Continuous rate conversion: r_t = ln(1 + APY)
- Near-term and next-term rate extraction for option pricing
"""

import argparse
import asyncio
import json
import logging
import math
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class YieldCurveConfig:
    """Configuration for yield curve processing."""
    url_template: str = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xmlview?data=daily_treasury_yield_curve&field_tdr_date_value={year}"
    year: int = datetime.now().year  # Dynamic year
    maturities: Tuple[int, ...] = (30, 60, 91, 182, 365, 730, 1095, 1825, 2555, 3650, 7300, 10950)
    timeout: int = 30

    @property
    def url(self) -> str:
        """Generate URL with the specified year."""
        return self.url_template.format(year=self.year)


class MaturityMapper:
    """Maps CMT field names to day counts."""

    FIELD_TO_DAYS: Dict[str, int] = {
        "BC_1MONTH": 30,
        "BC_2MONTH": 60,
        "BC_3MONTH": 91,
        "BC_4MONTH": 120,
        "BC_6MONTH": 182,
        "BC_1YEAR": 365,
        "BC_2YEAR": 730,
        "BC_3YEAR": 1095,
        "BC_5YEAR": 1825,
        "BC_7YEAR": 2555,
        "BC_10YEAR": 3650,
        "BC_20YEAR": 7300,
        "BC_30YEAR": 10950,
    }

    @classmethod
    def get_days(cls, field: str) -> Optional[int]:
        """Convert field name to days."""
        return cls.FIELD_TO_DAYS.get(field)


class RateInterpolator:
    """Performs linear interpolation for missing maturities."""

    def __init__(self, target_maturities: Tuple[int, ...]):
        self.target_maturities = target_maturities

    def interpolate(self, raw_rates: Dict[int, float]) -> Optional[Dict[int, float]]:
        """
        Perform linear interpolation for missing maturities.

        Args:
            raw_rates: Dictionary mapping days to rates

        Returns:
            Dictionary with interpolated rates for all target maturities
        """
        if not raw_rates:
            return None

        sorted_maturities = sorted(raw_rates.keys())
        interpolated = {}

        for target in self.target_maturities:
            if target in raw_rates:
                interpolated[target] = raw_rates[target]
            else:
                lower = self._find_bound(sorted_maturities, target, upper=False)
                upper = self._find_bound(sorted_maturities, target, upper=True)

                if lower is None or upper is None:
                    logger.warning(f"Cannot interpolate for {target} days")
                    continue

                rate = self._linear_interpolate(
                    lower, upper, target,
                    raw_rates[lower], raw_rates[upper]
                )
                interpolated[target] = rate

        return interpolated

    @staticmethod
    def _find_bound(sorted_list: List[int], target: int, upper: bool) -> Optional[int]:
        """Find lower or upper bound for interpolation."""
        if upper:
            for val in sorted_list:
                if val > target:
                    return val
        else:
            for val in reversed(sorted_list):
                if val < target:
                    return val
        return None

    @staticmethod
    def _linear_interpolate(x1: int, x2: int, x: int, y1: float, y2: float) -> float:
        """Perform linear interpolation."""
        return y1 + (y2 - y1) * ((x - x1) / (x2 - x1))


class RateConverter:
    """Converts Bond Equivalent Yields to continuous APY rates."""

    @staticmethod
    def to_continuous(rates: Dict[int, float]) -> Dict[int, float]:
        """
        Convert BEY to continuous APY rate using Cboe methodology.

        Args:
            rates: Dictionary mapping days to BEY rates

        Returns:
            Dictionary mapping days to continuous rates
        """
        continuous_rates = {}

        for days, bey in rates.items():
            # APY = (1 + BEY/2)^2 - 1
            apy = (1.0 + bey / 200.0) ** 2 - 1.0
            # r_t = ln(1 + APY)
            continuous_rates[days] = math.log(1.0 + apy)

        return continuous_rates


class TreasuryXMLParser:
    """Parses Treasury XML data."""

    def __init__(self):
        self.maturity_mapper = MaturityMapper()

    def parse(self, xml_content: str) -> Dict[str, Dict[int, float]]:
        """
        Parse XML content and extract yield curve data.

        Args:
            xml_content: XML string from Treasury API

        Returns:
            Dictionary mapping dates to rate dictionaries
        """
        # Remove namespaces for simpler parsing
        xml_content = self._strip_namespaces(xml_content)

        root = ET.fromstring(xml_content)
        rates_by_date = {}

        for entry in root.findall('.//entry'):
            date, raw_rates = self._parse_entry(entry)
            if date and raw_rates:
                rates_by_date[date] = raw_rates

        return rates_by_date

    def _parse_entry(self, entry: ET.Element) -> Tuple[Optional[str], Dict[int, float]]:
        """Parse a single entry element."""
        properties = entry.find('content/properties')
        if properties is None:
            return None, {}

        date = None
        raw_rates = {}

        for prop in properties:
            if prop.tag == 'NEW_DATE' and prop.text:
                date = prop.text.strip()
            elif prop.tag.startswith('BC_') and prop.text:
                days = self.maturity_mapper.get_days(prop.tag)
                if days:
                    try:
                        rate = float(prop.text.strip())
                        raw_rates[days] = rate
                    except ValueError:
                        logger.warning(f"Invalid rate value for {prop.tag}: {prop.text}")

        return date, raw_rates

    @staticmethod
    def _strip_namespaces(xml_content: str) -> str:
        """Remove namespace declarations from XML."""
        replacements = [
            ('xmlns="http://www.w3.org/2005/Atom"', ''),
            ('xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"', ''),
            ('xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"', ''),
            ('m:', ''),
            ('d:', ''),
        ]

        for old, new in replacements:
            xml_content = xml_content.replace(old, new)

        return xml_content


class HTTPClient:
    """Simple HTTP client using urllib."""

    @staticmethod
    async def fetch(url: str, timeout: int = 30) -> str:
        """
        Fetch content from URL using urllib.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Response text content

        Raises:
            urllib.error.URLError: On network errors
            urllib.error.HTTPError: On HTTP errors
        """
        loop = asyncio.get_event_loop()

        def _fetch_sync():
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Python Treasury Yield Processor/1.0'
                }
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode('utf-8')

        # Run synchronous urllib in executor to avoid blocking
        return await loop.run_in_executor(None, _fetch_sync)


class YieldCurveProcessor:
    """Main processor for Treasury yield curve data."""

    def __init__(self, config: Optional[YieldCurveConfig] = None):
        self.config = config or YieldCurveConfig()
        self.parser = TreasuryXMLParser()
        self.interpolator = RateInterpolator(self.config.maturities)
        self.converter = RateConverter()
        self.http_client = HTTPClient()

    async def fetch_data(self) -> str:
        """Fetch XML data from Treasury API."""
        try:
            return await self.http_client.fetch(self.config.url, self.config.timeout)
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error {e.code}: {e.reason}")
            raise
        except urllib.error.URLError as e:
            logger.error(f"URL error: {e.reason}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            raise

    def process(self, xml_content: str) -> Dict[str, Dict[int, float]]:
        """
        Process XML content to extract and convert yield curve data.

        Args:
            xml_content: Raw XML string

        Returns:
            Dictionary mapping dates to continuous rate curves
        """
        # Parse XML
        rates_by_date = self.parser.parse(xml_content)

        # Process each date
        processed_data = {}
        for date, raw_rates in rates_by_date.items():
            # Interpolate missing maturities
            interpolated = self.interpolator.interpolate(raw_rates)
            if interpolated:
                # Convert to continuous rates
                continuous = self.converter.to_continuous(interpolated)
                processed_data[date] = continuous

        return processed_data

    def get_latest_rates(self, processed_data: Dict[str, Dict[int, float]]) -> Optional[Tuple[str, Dict[int, float]]]:
        """Get the latest date's rates."""
        if not processed_data:
            return None

        latest_date = max(processed_data.keys())
        return latest_date, processed_data[latest_date]

    def get_rate_for_days(self, rates: Dict[int, float], target_days: int) -> float:
        """
        Get interpolated rate for specific number of days.

        Args:
            rates: Dictionary of rates by days
            target_days: Target number of days

        Returns:
            Interpolated rate for target days
        """
        # If exact match exists, return it
        if target_days in rates:
            return rates[target_days]

        # Find surrounding points for interpolation
        sorted_days = sorted(rates.keys())
        lower_days = None
        upper_days = None

        for days in sorted_days:
            if days < target_days:
                lower_days = days
            elif days > target_days and upper_days is None:
                upper_days = days
                break

        # Interpolate if we have both bounds
        if lower_days is not None and upper_days is not None:
            lower_rate = rates[lower_days]
            upper_rate = rates[upper_days]
            # Linear interpolation
            weight = (target_days - lower_days) / (upper_days - lower_days)
            return lower_rate + weight * (upper_rate - lower_rate)

        # Extrapolate if needed (using nearest point)
        if lower_days is None:
            return rates[sorted_days[0]]
        if upper_days is None:
            return rates[sorted_days[-1]]

    def get_vix_term_rates(self, rates: Dict[int, float], near_term_days: int = 23, next_term_days: int = 30) -> Dict[str, float]:
        """
        Get near-term and next-term rates for VIX-style calculations.

        Args:
            rates: Dictionary of continuous rates by days
            near_term_days: Days to expiration for near-term (default: 23)
            next_term_days: Days to expiration for next-term (default: 30)

        Returns:
            Dictionary with near_term_rate and next_term_rate
        """
        near_term_rate = self.get_rate_for_days(rates, near_term_days)
        next_term_rate = self.get_rate_for_days(rates, next_term_days)

        return {
            'near_term_rate': near_term_rate,
            'next_term_rate': next_term_rate,
            'near_term_days': near_term_days,
            'next_term_days': next_term_days
        }

    def format_output(self, date: str, rates: Dict[int, float]) -> str:
        """Format rates for display."""
        lines = [
            f"Latest Date: {date}",
            "-" * 40
        ]

        for maturity in sorted(rates.keys()):
            rate = rates[maturity]
            lines.append(f"Maturity: {maturity:5d} days, r_t: {rate:.6f}")

        return "\n".join(lines)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='US Treasury Yield Curve Processor for VIX Calculations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default VIX terms (30 and 60 days)
  python treasury_rates.py

  # Specify custom terms
  python treasury_rates.py --near 23 --next 30

  # Use specific year
  python treasury_rates.py --year 2024

  # JSON output only
  python treasury_rates.py --json-only
        """
    )

    parser.add_argument(
        '--near',
        type=int,
        default=30,
        help='Near-term days to expiration (default: 30)'
    )

    parser.add_argument(
        '--next',
        type=int,
        default=60,
        help='Next-term days to expiration (default: 60)'
    )

    parser.add_argument(
        '--year',
        type=int,
        default=datetime.now().year,
        help=f'Year for treasury data (default: {datetime.now().year})'
    )

    parser.add_argument(
        '--json-only',
        action='store_true',
        help='Output JSON only (no text output)'
    )

    parser.add_argument(
        '--output-file',
        type=str,
        default='latest_yield_curve.json',
        help='Output JSON file name (default: latest_yield_curve.json)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_arguments()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create configuration with specified year
    config = YieldCurveConfig(year=args.year)
    processor = YieldCurveProcessor(config)

    try:
        # Fetch data
        if not args.json_only:
            logger.info(f"Fetching Treasury yield curve data for year {args.year}...")
        xml_content = await processor.fetch_data()

        # Process data
        if not args.json_only:
            logger.info("Processing yield curve data...")
        processed_data = processor.process(xml_content)

        # Get latest rates
        result = processor.get_latest_rates(processed_data)
        if result:
            latest_date, latest_rates = result

            # Calculate VIX-style near-term and next-term rates
            vix_rates = processor.get_vix_term_rates(latest_rates, args.near, args.next)

            if args.json_only:
                # JSON output only
                output_data = {
                    "date": latest_date,
                    "year": args.year,
                    "vix_term_rates": vix_rates,
                    "full_rates": {str(k): v for k, v in latest_rates.items()}
                }
                print(json.dumps(output_data, indent=2))
            else:
                # Display full yield curve
                output = processor.format_output(latest_date, latest_rates)
                print(f"\n{output}")

                # Display VIX term rates
                print("\n" + "="*60)
                print("VIX-Style Term Rates (Continuously Compounded APY):")
                print("="*60)
                print(f"Near-term rate ({vix_rates['near_term_days']} days): {vix_rates['near_term_rate']:.6f} ({vix_rates['near_term_rate']*100:.2f}%)")
                print(f"Next-term rate ({vix_rates['next_term_days']} days): {vix_rates['next_term_rate']:.6f} ({vix_rates['next_term_rate']*100:.2f}%)")

            # Save to JSON file
            output_data = {
                "date": latest_date,
                "year": args.year,
                "full_rates": {str(k): v for k, v in latest_rates.items()},
                "vix_term_rates": vix_rates
            }
            with open(args.output_file, "w") as f:
                json.dump(output_data, f, indent=2)
                if not args.json_only:
                    logger.info(f"Saved latest rates to {args.output_file}")
        else:
            if args.json_only:
                print(json.dumps({"error": "No data found"}, indent=2))
            else:
                logger.error("No data found")
            sys.exit(1)

    except Exception as e:
        if args.json_only:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            logger.error(f"Error processing yield curve data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

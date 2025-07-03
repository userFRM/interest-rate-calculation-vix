import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Import from src
import sys
sys.path.insert(0, 'src')
from treasury_rates import (
    YieldCurveConfig, MaturityMapper, RateInterpolator,
    RateConverter, YieldCurveProcessor
)


class TestMaturityMapper:
    def test_get_days_valid_field(self):
        assert MaturityMapper.get_days("BC_1MONTH") == 30
        assert MaturityMapper.get_days("BC_1YEAR") == 365
        assert MaturityMapper.get_days("BC_30YEAR") == 10950

    def test_get_days_invalid_field(self):
        assert MaturityMapper.get_days("INVALID") is None
        assert MaturityMapper.get_days("") is None


class TestRateInterpolator:
    def setup_method(self):
        self.interpolator = RateInterpolator((30, 60, 90, 180, 365))

    def test_interpolate_exact_match(self):
        rates = {30: 0.04, 60: 0.045, 365: 0.05}
        result = self.interpolator.interpolate(rates)
        assert result[30] == 0.04
        assert result[60] == 0.045
        assert result[365] == 0.05

    def test_interpolate_between_points(self):
        rates = {30: 0.04, 365: 0.05}
        result = self.interpolator.interpolate(rates)
        # Linear interpolation for 90 days
        expected_90 = 0.04 + (0.05 - 0.04) * ((90 - 30) / (365 - 30))
        assert abs(result[90] - expected_90) < 0.0001

    def test_interpolate_empty_rates(self):
        result = self.interpolator.interpolate({})
        assert result is None


class TestRateConverter:
    def test_to_continuous(self):
        # Test BEY to continuous rate conversion
        rates = {30: 4.0, 365: 5.0}  # 4% and 5% BEY
        result = RateConverter.to_continuous(rates)

        # For 4% BEY: APY = (1 + 0.04/2)^2 - 1 = 0.0404
        # r_t = ln(1.0404) ≈ 0.03961
        assert abs(result[30] - 0.03961) < 0.0001

        # For 5% BEY: APY = (1 + 0.05/2)^2 - 1 = 0.050625
        # r_t = ln(1.050625) ≈ 0.04939
        assert abs(result[365] - 0.04939) < 0.0001


class TestYieldCurveProcessor:
    @pytest.fixture
    def processor(self):
        return YieldCurveProcessor()

    def test_get_rate_for_days_exact(self, processor):
        rates = {30: 0.04, 60: 0.045, 365: 0.05}
        assert processor.get_rate_for_days(rates, 30) == 0.04
        assert processor.get_rate_for_days(rates, 365) == 0.05

    def test_get_rate_for_days_interpolate(self, processor):
        rates = {30: 0.04, 60: 0.045}
        # Interpolate for 45 days
        result = processor.get_rate_for_days(rates, 45)
        expected = 0.04 + (0.045 - 0.04) * ((45 - 30) / (60 - 30))
        assert abs(result - expected) < 0.0001

    def test_get_vix_term_rates(self, processor):
        rates = {i: 0.04 + i * 0.00001 for i in range(1, 366)}
        result = processor.get_vix_term_rates(rates, 23, 30)

        assert result['near_term_days'] == 23
        assert result['next_term_days'] == 30
        assert 'near_term_rate' in result
        assert 'next_term_rate' in result
        assert result['near_term_rate'] < result['next_term_rate']


@pytest.mark.asyncio
class TestIntegration:
    async def test_config_default_year(self):
        config = YieldCurveConfig()
        assert config.year == datetime.now().year

    async def test_config_custom_year(self):
        config = YieldCurveConfig(year=2023)
        assert config.year == 2023
        assert "2023" in config.url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

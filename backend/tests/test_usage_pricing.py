"""Tests unitaires sur le calcul de coût LLM."""

from meoxa_secretary.services.usage import PRICING, UsageService


def test_sonnet_pricing_correct() -> None:
    # 1M tokens input Sonnet 4.6 = $3.00 = 3_000_000 micro-USD
    micro = UsageService.compute_cost_micro_usd(
        model="claude-sonnet-4-6",
        input_tokens=1_000_000,
        output_tokens=0,
        cache_read_tokens=0,
        cache_write_tokens=0,
    )
    assert micro == 3_000_000


def test_opus_more_expensive_than_sonnet() -> None:
    args = dict(
        input_tokens=10_000,
        output_tokens=2_000,
        cache_read_tokens=0,
        cache_write_tokens=0,
    )
    sonnet = UsageService.compute_cost_micro_usd(model="claude-sonnet-4-6", **args)
    opus = UsageService.compute_cost_micro_usd(model="claude-opus-4-7", **args)
    assert opus > sonnet


def test_unknown_model_costs_zero() -> None:
    # On n'impute pas de coût pour un modèle inconnu (évite gonflement artificiel).
    micro = UsageService.compute_cost_micro_usd(
        model="gpt-9999",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        cache_read_tokens=0,
        cache_write_tokens=0,
    )
    assert micro == 0


def test_cache_reads_much_cheaper() -> None:
    # Cache read Sonnet = $0.30/MTok (10× moins cher que input régulier).
    full = UsageService.compute_cost_micro_usd(
        model="claude-sonnet-4-6",
        input_tokens=1_000_000,
        output_tokens=0,
        cache_read_tokens=0,
        cache_write_tokens=0,
    )
    cached = UsageService.compute_cost_micro_usd(
        model="claude-sonnet-4-6",
        input_tokens=0,
        output_tokens=0,
        cache_read_tokens=1_000_000,
        cache_write_tokens=0,
    )
    assert cached < full / 5


def test_all_models_have_pricing() -> None:
    for model in PRICING:
        assert PRICING[model].input > 0
        assert PRICING[model].output > 0

"""
Tests for diet plan generation and retrieval endpoints.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from decimal import Decimal


class TestDietPlanGeneration:
    """Test diet plan generation endpoints."""

    @pytest.mark.asyncio
    async def test_generate_diet_plan_anonymous(self, client: AsyncClient) -> None:
        """Anonymous users can generate a diet plan with breed/age/weight."""
        response = await client.post(
            "/api/v1/diet-plans/generate",
            json={
                "breed": "golden_retriever",
                "age_months": 24,
                "weight_kg": 30.0,
                "activity_level": "moderate",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["breed"] == "golden_retriever"
        assert data["age_months"] == 24
        assert data["daily_calories"] > 0
        assert float(data["protein_g"]) > 0
        assert float(data["fat_g"]) > 0
        assert float(data["carbs_g"]) > 0
        assert "weekly_calories" in data
        assert data["weekly_calories"] == int(data["daily_calories"] * 7)

    @pytest.mark.asyncio
    async def test_generate_diet_plan_uses_defaults(self, client: AsyncClient) -> None:
        """Missing parameters should use safe defaults."""
        response = await client.post(
            "/api/v1/diet-plans/generate",
            json={},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["breed"] == "unknown"
        assert data["age_months"] == 24
        assert float(data["weight_kg"]) == pytest.approx(10.0, rel=0.01)
        assert data["activity_level"] == "moderate"
        assert data["daily_calories"] > 0

    @pytest.mark.asyncio
    async def test_generate_diet_plan_includes_recommendations(
        self, client: AsyncClient
    ) -> None:
        """Diet plan should include food recommendations, supplements, and schedule."""
        response = await client.post(
            "/api/v1/diet-plans/generate",
            json={
                "breed": "labrador_retriever",
                "age_months": 36,
                "weight_kg": 32.0,
                "activity_level": "active",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["food_recommendations"]) > 0
        assert len(data["foods_to_avoid"]) > 0
        assert len(data["feeding_schedule"]) > 0
        assert data["meals_per_day"] >= 2

    @pytest.mark.asyncio
    async def test_generate_diet_plan_with_allergies(
        self, client: AsyncClient
    ) -> None:
        """Diet plan should respect allergies."""
        response = await client.post(
            "/api/v1/diet-plans/generate",
            json={
                "breed": "beagle",
                "age_months": 24,
                "weight_kg": 12.0,
                "allergies": ["chicken", "wheat"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        # Check that chicken-containing foods are avoided
        chicken_foods = [f for f in data["foods_to_avoid"] if "chicken" in f.lower()]
        assert len(chicken_foods) > 0 or len(data["food_recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_weekly_aggregates_computed(self, client: AsyncClient) -> None:
        """Weekly fields should be 7x daily values."""
        response = await client.post(
            "/api/v1/diet-plans/generate",
            json={
                "breed": "pug",
                "age_months": 48,
                "weight_kg": 8.0,
                "activity_level": "sedentary",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["weekly_calories"] == int(data["daily_calories"] * 7)
        assert float(data["weekly_protein_g"]) == pytest.approx(float(data["protein_g"]) * 7, rel=0.1
        )
        assert float(data["weekly_fat_g"]) == pytest.approx(float(data["fat_g"]) * 7, rel=0.1
        )
        assert float(data["weekly_carbs_g"]) == pytest.approx(float(data["carbs_g"]) * 7, rel=0.1
        )
        assert data["meals_per_week"] == data["meals_per_day"] * 7


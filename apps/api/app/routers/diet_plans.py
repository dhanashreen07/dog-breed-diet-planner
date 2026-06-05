from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import APIBaseModel, PaginatedResponse
from app.schemas.diet_plan import (
    DietPlanPublic,
    FoodRecommendation,
    FeedingScheduleItem,
)
from app.services.diet_engine import diet_engine
from app.middleware.auth import ANONYMOUS_USER_ID, get_optional_user

router = APIRouter()


class AnonDietPlanRequest(APIBaseModel):
    """Anonymous diet-plan request — optional `pet_id` allowed for authenticated users."""
    pet_id: uuid.UUID | None = None
    breed: str | None = None
    age_months: Annotated[int | None, Field(ge=0, le=360)] = None
    weight_kg: Annotated[Decimal | None, Field(ge=Decimal("0.1"), le=Decimal("200"))] = None
    activity_level: str | None = None
    is_neutered: bool = True
    sex: str = "male"
    allergies: list[str] = []
    health_conditions: list[str] = []


@router.post("/generate", response_model=DietPlanPublic, status_code=status.HTTP_201_CREATED)
async def generate_diet_plan(
    request: AnonDietPlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_optional_user),
) -> DietPlanPublic:
    """Generate a diet plan in-memory (no persistence). If `pet_id` is provided, the pet must belong to the authenticated user."""
    # If pet_id provided, fetch pet profile (requires auth)
    if request.pet_id:
        if current_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required to generate from a saved pet")
        from app.services.pet_service import pet_service
        pet = await pet_service.get_by_id(db, request.pet_id, current_user.id)
        if not pet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
        breed = pet.breed or "unknown"
        age_months = pet.age_months or 24
        weight_kg = float(pet.weight_kg or 10.0)
        activity_level = pet.activity_level or "moderate"
        allergies = list(pet.allergies)
        health_conditions = list(pet.health_conditions)
        is_neutered = pet.is_neutered
        sex = pet.sex or "male"
    else:
        breed = request.breed or "unknown"
        age_months = request.age_months if request.age_months is not None else 24
        weight_kg = float(request.weight_kg) if request.weight_kg is not None else 10.0
        activity_level = request.activity_level or "moderate"
        allergies = request.allergies
        health_conditions = request.health_conditions
        is_neutered = request.is_neutered
        sex = request.sex

    result = diet_engine.generate(
        breed=breed,
        age_months=age_months,
        weight_kg=weight_kg,
        activity_level=activity_level,
        is_neutered=is_neutered,
        sex=sex,
        allergies=allergies,
        health_conditions=health_conditions,
    )

    now = datetime.now(timezone.utc)
    # Compute weekly fields (non-persistent)
    weekly_calories = int(result.daily_calories * 7)
    weekly_protein = float(result.protein_g) * 7
    weekly_fat = float(result.fat_g) * 7
    weekly_carbs = float(result.carbs_g) * 7
    meals_per_week = int(result.meals_per_day * 7)

    return DietPlanPublic(
        id=uuid.uuid4(),
        pet_id=request.pet_id or uuid.uuid4(),
        user_id=getattr(current_user, "id", ANONYMOUS_USER_ID),
        prediction_id=None,
        breed=result.breed,
        age_months=result.age_months,
        weight_kg=Decimal(str(result.weight_kg)),
        activity_level=result.activity_level,
        daily_calories=result.daily_calories,
        protein_g=Decimal(str(result.protein_g)),
        fat_g=Decimal(str(result.fat_g)),
        carbs_g=Decimal(str(result.carbs_g)),
        meals_per_day=result.meals_per_day,
        food_recommendations=[FoodRecommendation(**f) for f in result.food_recommendations],
        foods_to_avoid=result.foods_to_avoid,
        supplement_flags=result.supplement_flags,
        feeding_schedule=[FeedingScheduleItem(**s) for s in result.feeding_schedule],
        notes=result.notes,
        engine_version=result.engine_version,
        ai_insights=None,
        ai_provider_used=None,
        created_at=now,
        updated_at=now,
        weekly_calories=weekly_calories,
        weekly_protein_g=Decimal(str(round(weekly_protein, 2))),
        weekly_fat_g=Decimal(str(round(weekly_fat, 2))),
        weekly_carbs_g=Decimal(str(round(weekly_carbs, 2))),
        meals_per_week=meals_per_week,
    )


@router.get("/{plan_id}", response_model=DietPlanPublic)
async def get_diet_plan(plan_id: uuid.UUID) -> DietPlanPublic:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Diet plans are not persisted in anonymous mode.",
    )


@router.get("", response_model=PaginatedResponse)
async def list_diet_plans(
    pet_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
) -> PaginatedResponse:
    return PaginatedResponse(items=[], total=0, page=page, page_size=page_size, pages=0)

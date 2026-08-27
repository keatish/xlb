from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Ingredient(Base):
    __tablename__ = "ingredient"

    id: Mapped[int] = mapped_column(primary_key=True)
    inci_name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    common_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    function: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_irritant: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    comedogenic_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_group: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    products: Mapped[list[ProductIngredient]] = relationship(back_populates="ingredient")


class ProductIngredient(Base):
    """Link table. `position` is the INCI list index — order approximates concentration."""

    __tablename__ = "product_ingredient"
    __table_args__ = (
        UniqueConstraint("product_id", "ingredient_id", name="uq_product_ingredient"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredient.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)

    product: Mapped["Product"] = relationship(back_populates="ingredients")  # noqa: F821
    ingredient: Mapped[Ingredient] = relationship(back_populates="products")


class Concern(Base):
    __tablename__ = "concern"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    products: Mapped[list[ProductConcern]] = relationship(back_populates="concern")


class ProductConcern(Base):
    __tablename__ = "product_concern"
    __table_args__ = (
        UniqueConstraint("product_id", "concern_id", name="uq_product_concern"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    concern_id: Mapped[int] = mapped_column(ForeignKey("concern.id"), index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    product: Mapped["Product"] = relationship(back_populates="concerns")  # noqa: F821
    concern: Mapped[Concern] = relationship(back_populates="products")

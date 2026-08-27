from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import Category, MatchMethod, ScrapeStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Brand(Base):
    __tablename__ = "brand"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    normalized_name: Mapped[str] = mapped_column(String(120), index=True)

    products: Mapped[list[Product]] = relationship(back_populates="brand")


class Product(Base):
    """The canonical product — one row per real-world SKU, independent of retailer."""

    __tablename__ = "product"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brand.id"), index=True)
    name: Mapped[str] = mapped_column(String(300))
    slug: Mapped[str] = mapped_column(String(340), unique=True, index=True)
    category: Mapped[Category] = mapped_column(String(30), index=True)
    size_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    size_unit: Mapped[str | None] = mapped_column(String(10), nullable=True)
    upc: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(600), nullable=True)
    ingredients_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    brand: Mapped[Brand] = relationship(back_populates="products")
    listings: Mapped[list[Listing]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    ingredients: Mapped[list[ProductIngredient]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductIngredient.position",
    )
    concerns: Mapped[list[ProductConcern]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    @property
    def size_label(self) -> str | None:
        if self.size_value is None:
            return None
        value = int(self.size_value) if self.size_value == int(self.size_value) else self.size_value
        return f"{value}{self.size_unit or ''}"


class Retailer(Base):
    __tablename__ = "retailer"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    base_url: Mapped[str] = mapped_column(String(300))
    scraper_key: Mapped[str] = mapped_column(String(60), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    block_count: Mapped[int] = mapped_column(Integer, default=0)

    listings: Mapped[list[Listing]] = relationship(back_populates="retailer")


class Listing(Base):
    """A canonical product as sold at one retailer."""

    __tablename__ = "listing"
    __table_args__ = (
        UniqueConstraint("retailer_id", "retailer_sku", name="uq_listing_retailer_sku"),
        Index("ix_listing_product_retailer", "product_id", "retailer_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    retailer_id: Mapped[int] = mapped_column(ForeignKey("retailer.id"), index=True)
    retailer_sku: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(900))
    title_raw: Mapped[str] = mapped_column(String(400))
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    last_scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_status: Mapped[ScrapeStatus] = mapped_column(String(20), default=ScrapeStatus.OK)
    match_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    match_method: Mapped[MatchMethod] = mapped_column(String(20), default=MatchMethod.FUZZY)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    product: Mapped[Product] = relationship(back_populates="listings")
    retailer: Mapped[Retailer] = relationship(back_populates="listings")
    snapshots: Mapped[list[PriceSnapshot]] = relationship(
        back_populates="listing",
        cascade="all, delete-orphan",
        order_by="PriceSnapshot.scraped_at.desc()",
    )


class PriceSnapshot(Base):
    """Append-only price observation. Drives history charts and 'lowest in N days'."""

    __tablename__ = "price_snapshot"
    __table_args__ = (
        Index("ix_snapshot_listing_time", "listing_id", "scraped_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listing.id"), index=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    was_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    listing: Mapped[Listing] = relationship(back_populates="snapshots")

"""Catalog service for Provider app."""
from typing import List, Dict, Any, Optional
from provider.app.db import get_session
from provider.app.models.product import Product
from provider.app.models.pricing_tier import PricingTier
from provider.app.models.stock import Stock


def get_all_products() -> List[Dict[str, Any]]:
    """Get all products with their pricing tiers."""
    session = get_session()
    try:
        products = session.query(Product).all()
        result = []
        
        for product in products:
            # Get pricing tiers
            tiers = session.query(PricingTier).filter_by(product_id=product.id).order_by(PricingTier.min_quantity).all()
            
            # Get stock
            stock = session.query(Stock).filter_by(product_id=product.id).first()
            
            product_dict = product.to_dict()
            product_dict["pricing"] = [t.to_dict() for t in tiers]
            product_dict["stock"] = stock.quantity if stock else 0
            
            result.append(product_dict)
        
        return result
    finally:
        session.close()


def get_product_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get a product by name."""
    session = get_session()
    try:
        product = session.query(Product).filter_by(name=name).first()
        if not product:
            return None
        
        tiers = session.query(PricingTier).filter_by(product_id=product.id).order_by(PricingTier.min_quantity).all()
        stock = session.query(Stock).filter_by(product_id=product.id).first()
        
        product_dict = product.to_dict()
        product_dict["pricing"] = [t.to_dict() for t in tiers]
        product_dict["stock"] = stock.quantity if stock else 0
        
        return product_dict
    finally:
        session.close()


def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Get a product by ID."""
    session = get_session()
    try:
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            return None
        
        tiers = session.query(PricingTier).filter_by(product_id=product.id).order_by(PricingTier.min_quantity).all()
        stock = session.query(Stock).filter_by(product_id=product.id).first()
        
        product_dict = product.to_dict()
        product_dict["pricing"] = [t.to_dict() for t in tiers]
        product_dict["stock"] = stock.quantity if stock else 0
        
        return product_dict
    finally:
        session.close()


def get_stock_levels() -> List[Dict[str, Any]]:
    """Get all stock levels."""
    session = get_session()
    try:
        stocks = session.query(Stock).all()
        result = []
        
        for stock in stocks:
            product = session.query(Product).filter_by(id=stock.product_id).first()
            result.append({
                "product_id": stock.product_id,
                "product_name": product.name if product else "Unknown",
                "quantity": stock.quantity,
            })
        
        return result
    finally:
        session.close()


def calculate_price(product_id: int, quantity: int) -> float:
    """Calculate the unit price based on quantity tiers."""
    session = get_session()
    try:
        tiers = session.query(PricingTier).filter_by(product_id=product_id).order_by(PricingTier.min_quantity.desc()).all()
        
        # Find the applicable tier (highest min_quantity that fits)
        for tier in tiers:
            if quantity >= tier.min_quantity:
                return tier.unit_price
        
        # If no tier matches, return the base price (first tier)
        if tiers:
            return tiers[-1].unit_price
        
        return 0.0
    finally:
        session.close()


def update_price_tier(product_id: int, min_quantity: int, new_price: float) -> bool:
    """Update a price tier."""
    session = get_session()
    try:
        tier = session.query(PricingTier).filter_by(
            product_id=product_id,
            min_quantity=min_quantity
        ).first()
        
        if tier:
            tier.unit_price = new_price
            session.commit()
            return True
        
        return False
    finally:
        session.close()


def add_stock(product_name: str, quantity: int) -> bool:
    """Add stock to a product."""
    session = get_session()
    try:
        product = session.query(Product).filter_by(name=product_name).first()
        if not product:
            return False
        
        stock = session.query(Stock).filter_by(product_id=product.id).first()
        if stock:
            stock.quantity += quantity
        else:
            stock = Stock(product_id=product.id, quantity=quantity)
            session.add(stock)
        
        session.commit()
        return True
    finally:
        session.close()
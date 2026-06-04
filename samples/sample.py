"""Sample inventory module — designed to exercise identifier renaming.

The classes/functions below have long, repeated identifiers that an LLM
tokenizer (BPE) will split into many tokens. Compression should rename them
to short aliases while preserving structure, comments, and docstrings.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class InventoryItem:
    """Represents a single SKU in our warehouse."""
    sku_identifier: str
    quantity_on_hand: int
    unit_price_in_cents: int


def calculate_total_inventory_value(inventory_items: List[InventoryItem]) -> int:
    """Return the total value of inventory in cents."""
    running_total_value = 0
    for inventory_item in inventory_items:
        running_total_value += inventory_item.quantity_on_hand * inventory_item.unit_price_in_cents
    return running_total_value


def filter_low_stock_items(inventory_items: List[InventoryItem], threshold: int) -> List[InventoryItem]:
    """Return items whose quantity_on_hand is below the threshold."""
    low_stock_results = []
    for inventory_item in inventory_items:
        if inventory_item.quantity_on_hand < threshold:
            low_stock_results.append(inventory_item)
    return low_stock_results


def reorder_low_stock_items(inventory_items: List[InventoryItem], threshold: int, reorder_amount: int) -> None:
    """Top up any low-stock items in place."""
    low_stock_results = filter_low_stock_items(inventory_items, threshold)
    for inventory_item in low_stock_results:
        inventory_item.quantity_on_hand += reorder_amount


if __name__ == "__main__":
    sample_inventory_items = [
        InventoryItem("SKU-001", 5, 1999),
        InventoryItem("SKU-002", 50, 499),
        InventoryItem("SKU-003", 2, 4999),
    ]
    print("Total value:", calculate_total_inventory_value(sample_inventory_items))
    reorder_low_stock_items(sample_inventory_items, threshold=10, reorder_amount=20)
    print("After reorder:", sample_inventory_items)

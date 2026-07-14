#!/usr/bin/env python3
"""Taskiq worker entry point."""

from ...interfaces.main import app
from ...modules.product.sync import sync_pos_products_task
from ...modules.sync.sync import (
    sync_base_price_task,
    sync_customer_master_task,
    sync_item_branch_task,
)
from .brokers import default_broker

__all__ = [
    "default_broker",
    "sync_pos_products_task",
    "sync_item_branch_task",
    "sync_base_price_task",
    "sync_customer_master_task",
    "app",
]

if __name__ == "__main__":
    # Run with: python -m taskiq worker infrastructure.taskiq.worker:default_broker
    pass

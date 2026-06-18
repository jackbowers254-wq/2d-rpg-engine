"""
engine.economy.shop
=================
Shops are data (``data/shops/*.json``). A shop lists items for sale (price defaults
to the item's ``value`` times ``buy_markup``) and buys the player's items back at
``sell_ratio`` of their value. Currency lives in ``GameState.currency`` (saved with
everything else). The ShopScene drives the UI; this module is pure data + pricing.

    {
      "id": "general_store",
      "name": "Greenfields Goods",
      "greeting": "Welcome! What'll it be?",
      "buy_markup": 1.0,
      "sell_ratio": 0.5,
      "stock": [
        {"item": "potion"}, {"item": "ether"}, {"item": "wood_sword", "stock": 1}
      ]
    }
"""

from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from engine.utils.logger import get_logger

log = get_logger("economy")


@dataclass
class ShopItem:
    item: str
    price: Optional[int] = None   # explicit override; else item.value * buy_markup
    stock: int = -1               # -1 = unlimited


@dataclass
class ShopDef:
    id: str
    name: str
    greeting: str = "Welcome!"
    buy_markup: float = 1.0
    sell_ratio: float = 0.5
    stock: List[ShopItem] = field(default_factory=list)

    def buy_price(self, item_db, shop_item: ShopItem) -> int:
        if shop_item.price is not None:
            return shop_item.price
        item = item_db.get(shop_item.item)
        return int(round((item.value if item else 0) * self.buy_markup))

    def sell_price(self, item_db, item_id: str) -> int:
        item = item_db.get(item_id)
        return int(round((item.value if item else 0) * self.sell_ratio))


class ShopDatabase:
    def __init__(self) -> None:
        self._shops: Dict[str, ShopDef] = {}

    def load_dir(self, directory: str) -> None:
        for path in glob.glob(os.path.join(directory, "*.json")):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            data = {k: v for k, v in data.items() if not k.startswith("_")}
            data.setdefault("id", os.path.splitext(os.path.basename(path))[0])
            stock = [ShopItem(**s) for s in data.pop("stock", [])]
            self._shops[data["id"]] = ShopDef(stock=stock, **data)
        log.info("Loaded %d shops", len(self._shops))

    def get(self, shop_id: str) -> Optional[ShopDef]:
        return self._shops.get(shop_id)

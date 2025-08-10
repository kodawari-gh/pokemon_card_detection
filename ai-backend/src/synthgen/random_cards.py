# random_cards.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Dict, Sequence, Tuple, Optional
import math
import random
import numpy as np

@dataclass(frozen=True)
class SetInfo:
    id: str
    release_date: str  # "YYYY/MM/DD"

def _parse_date(s: str) -> date:
    # your sets are "YYYY/MM/DD"
    return datetime.strptime(s, "%Y/%m/%d").date()

def compute_release_date_probs_fast(
    sets: Sequence[SetInfo],
    *,
    half_life_days: int = 365,
    floor: float = 0.0,
    today: Optional[date] = None,
) -> Tuple[List[SetInfo], np.ndarray]:
    """
    Returns (sets_filtered_in_same_order, probs ndarray) where probs sum to 1.0.
    floor adds a small constant to each weight to avoid zeros.
    """
    if not sets:
        return [], np.asarray([], dtype=np.float64)

    today = today or datetime.now().date()
    ages = np.array([(today - _parse_date(s.release_date)).days for s in sets], dtype=np.float64)
    lam = math.log(2.0) / float(half_life_days)
    weights = np.exp(-lam * ages) + float(floor)
    weights = np.maximum(weights, 0.0)
    total = weights.sum()
    if total <= 0:
        # fallback to uniform
        weights[:] = 1.0 / len(weights)
    else:
        weights /= total
    return list(sets), weights

class RandomCardSampler:
    """
    Fast sampler:
      - preloads all cards per set once via cache.search_cards_by_set(set_id)
      - drops empty sets and renormalizes probabilities
      - draws sets in bulk with np.random.multinomial
      - picks cards per set uniformly (with replacement) in bulk
    """
    def __init__(
        self,
        sets: Sequence,                      # your Set objects
        cache,                                # your CacheManager
        *,
        half_life_days: int = 365,
        floor: float = 0.0,
        rng: Optional[np.random.Generator] = None,
    ):
        self.rng = rng or np.random.default_rng()
        # Build mapping set -> cards once
        cards_by_set: Dict[str, List] = {}
        kept_sets: List = []
        for s in sets:
            cards = cache.search_cards_by_set(s.id) or []
            if len(cards) > 0:
                cards_by_set[s.id] = cards
                kept_sets.append(s)

        if not kept_sets:
            raise RuntimeError("No sets with cards found.")

        # Probabilities (after filtering)
        kept_sets, probs = compute_release_date_probs_fast(
            kept_sets, half_life_days=half_life_days, floor=floor
        )

        self.sets: List = kept_sets
        self.probs: np.ndarray = probs
        self.cards_by_set: Dict[str, List] = cards_by_set

        # Fast lookup arrays
        self._set_ids = [s.id for s in self.sets]
        self._num_sets = len(self._set_ids)

    def sample_cards(self, n: int) -> List:
        """
        Sample n cards total, with replacement. Distribution:
          pick set ~ probs, then card ~ Uniform(cards_in_that_set).
        """
        if n <= 0:
            return []

        # 1) Draw counts per set in ONE go
        #    multinomial returns an array of length num_sets with counts summing to n
        counts = self.rng.multinomial(n, self.probs)

        # 2) For each set, draw that many cards uniformly (with replacement)
        out: List = []
        for set_idx, k in enumerate(counts):
            if k == 0:
                continue
            sid = self._set_ids[set_idx]
            cards = self.cards_by_set[sid]
            m = len(cards)
            # vectorized uniform picks of indices [0, m)
            idxs = self.rng.integers(0, m, size=k, endpoint=False)
            out.extend(cards[i] for i in idxs)
        return out

    def sample_card_images(
        self, n: int, cache, img_db, *, rgba: bool = True
    ) -> List:
        """
        Convenience: directly return loaded card images (PIL) for n sampled cards.
        """
        cards = self.sample_cards(n)
        imgs = []
        for c in cards:
            im = cache.get_card_image(c, img_db)
            if im is not None:
                imgs.append(im.convert("RGBA") if rgba else im)
        return imgs

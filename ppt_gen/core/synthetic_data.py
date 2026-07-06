import hashlib
import random
from typing import Any, Dict, List, Literal, Tuple

DECREASE_WORDS = {"reduction", "drop", "decrease", "lower", "lapse", "attrition", "churn", "risk", "loss", "erosion", "cut"}
INCREASE_WORDS = {"increase", "uplift", "growth", "recovery", "boost", "gain", "expansion", "scale", "acquisition", "retention", "uplift", "saving"}

def infer_direction(label: str) -> Literal["up", "down"]:
    """Look up keyword tokens to deduce if a metric represents positive growth or reduction."""
    words = set(label.lower().replace("-", " ").replace("_", " ").split())
    if words & DECREASE_WORDS:
        return "down"
    if words & INCREASE_WORDS:
        return "up"
    return "up"  # Safe corporate default

def get_deterministic_seed(deck_id: str, slide_id: int, slot_id: str) -> int:
    """Generate a deterministic seed across program runs for stdlib random."""
    key = f"{deck_id}_{slide_id}_{slot_id}"
    return int(hashlib.md5(key.encode("utf-8")).hexdigest()[:8], 16)

class SyntheticDataEngine:
    def __init__(self, deck_id: str = "default_deck"):
        self.deck_id = deck_id

    def generate_slot_value(
        self,
        slide_id: int,
        slot_id: str,
        label: str,
        data_shape: str,
        user_supplied_value: Any = None
    ) -> Any:
        """Calculate synthetic values if no user data is supplied, matching the shape constraint."""
        if user_supplied_value is not None and user_supplied_value != "":
            return user_supplied_value

        # Seed the RNG deterministically for this specific slot
        seed = get_deterministic_seed(self.deck_id, slide_id, slot_id)
        rng = random.Random(seed)
        
        direction = infer_direction(label)

        if data_shape == "single_stat":
            return self._generate_single_stat(rng, label, direction)
        elif data_shape == "paired_comparison":
            return self._generate_paired_comparison(rng, label, direction)
        elif data_shape == "ranked_bar":
            return self._generate_ranked_bar(rng, direction)
        elif data_shape == "trend_series":
            return self._generate_trend_series(rng, direction)
        elif data_shape == "allocation_table":
            return self._generate_allocation_table(rng)
        
        return ""

    def _generate_single_stat(self, rng: random.Random, label: str, direction: Literal["up", "down"]) -> str:
        """Generate a single stat (e.g. 40%, 3x, or ↑12%)."""
        label_lower = label.lower()
        if "rate" in label_lower or "percent" in label_lower or "%" in label_lower:
            val = rng.randint(15, 65)
            arr = "↑" if direction == "up" else "↓"
            return f"{arr} {val}%"
        elif "x" in label_lower or "fold" in label_lower or "multiplier" in label_lower:
            val = rng.choice([2, 3, 4, 5])
            return f"{val}x"
        else:
            val = rng.randint(10, 45)
            arr = "↑" if direction == "up" else "↓"
            return f"{arr} {val}%"

    def _generate_paired_comparison(self, rng: random.Random, label: str, direction: Literal["up", "down"]) -> Dict[str, Any]:
        """Generate comparison data (us vs competitor) with a plausible gap."""
        # Typically returns labels and values for a side-by-side grouped bar chart or simple callout
        if direction == "up":
            us_val = rng.randint(45, 68)
            comp_val = us_val - rng.randint(10, 20)
        else:
            us_val = rng.randint(15, 30)
            comp_val = us_val + rng.randint(10, 20)
            
        return {
            "labels": ["Industry Baseline", "Our Target"],
            "series": [
                {"name": "Benchmark", "values": [float(comp_val), float(us_val)]}
            ]
        }

    def _generate_ranked_bar(self, rng: random.Random, direction: Literal["up", "down"]) -> Dict[str, Any]:
        """Generate sorted values where 'Our Share' / 'We' are placed best."""
        # N bars sorted high-to-low or low-to-high
        names = ["Our Target", "Competitor A", "Competitor B", "Competitor C"]
        if direction == "up":
            # We are highest
            v1 = rng.randint(90, 115)
            v2 = v1 - rng.randint(10, 20)
            v3 = v2 - rng.randint(15, 25)
            v4 = v3 - rng.randint(15, 20)
            values = [float(v1), float(v2), float(v3), float(max(v4, 10))]
        else:
            # We are lowest (e.g. Churn risk)
            v1 = rng.randint(10, 25)
            v2 = v1 + rng.randint(10, 15)
            v3 = v2 + rng.randint(15, 20)
            v4 = v3 + rng.randint(15, 20)
            values = [float(v1), float(v2), float(v3), float(v4)]
            
        return {
            "labels": names,
            "series": [
                {"name": "Performance", "values": values}
            ]
        }

    def _generate_trend_series(self, rng: random.Random, direction: Literal["up", "down"]) -> Dict[str, Any]:
        """Generate smooth linear trend with a small amount of random noise."""
        periods = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]
        
        # Scenario 1: Baseline (flat or slightly down/up)
        # Scenario 2: Target (strong trend)
        start_val = rng.randint(20, 40)
        
        base_series = []
        target_series = []
        
        current_base = start_val
        current_target = start_val
        
        for i in range(len(periods)):
            # small noise
            noise_base = rng.uniform(-1.5, 1.5)
            noise_target = rng.uniform(-1.0, 1.0)
            
            # Base drifts slightly
            base_drift = rng.uniform(-0.5, 0.5)
            current_base += base_drift + noise_base
            base_series.append(round(max(current_base, 5.0), 1))
            
            # Target follows direction
            step = rng.uniform(2.5, 4.5) if direction == "up" else rng.uniform(-3.5, -2.0)
            current_target += step + noise_target
            target_series.append(round(max(current_target, 5.0), 1))
            
        return {
            "labels": periods,
            "series": [
                {"name": "Current Path", "values": base_series},
                {"name": "Target Play", "values": target_series}
            ]
        }

    def _generate_allocation_table(self, rng: random.Random) -> Dict[str, Any]:
        """Generate allocations for project roadmap steps."""
        allocations = ["$150K", "$200K", "$350K", "$100K", "$50K"]
        impacts = ["+15% margin", "+10% volume", "+25% conversion", "+5% scale", "+8% retention"]
        
        # Return a structure mapping to columns: Workstream, Budget, Impact
        return {
            "headers": ["Key Workstream", "Budget Allocation", "Target Outcome"],
            # Rows will be filled by layout/renderer
            "values": [
                ["Workstream Play A", allocations[0], impacts[0]],
                ["Workstream Play B", allocations[1], impacts[1]],
                ["Workstream Play C", allocations[2], impacts[2]],
                ["Workstream Play D", allocations[3], impacts[3]],
                ["Workstream Play E", allocations[4], impacts[4]]
            ]
        }

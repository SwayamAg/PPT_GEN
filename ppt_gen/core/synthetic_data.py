import hashlib
import random
from typing import Any, Dict, List, Literal, Tuple

DECREASE_WORDS = {"reduction", "drop", "decrease", "lower", "lapse", "attrition", "churn", "risk", "loss", "erosion", "cut"}
INCREASE_WORDS = {"increase", "uplift", "growth", "recovery", "boost", "gain", "expansion", "scale", "acquisition", "retention", "saving"}

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
        data_pattern: str,
        user_supplied_value: Any = None
    ) -> Any:
        """Calculate synthetic values if no user data is supplied, matching the pattern constraint."""
        if user_supplied_value is not None and user_supplied_value != "":
            return user_supplied_value

        # Seed the RNG deterministically for this specific slot
        seed = get_deterministic_seed(self.deck_id, slide_id, slot_id)
        rng = random.Random(seed)

        direction = infer_direction(label)

        # §7.3 data_pattern dispatch
        if data_pattern == "single_value":
            return self._generate_single_stat(rng, label, direction)
        elif data_pattern == "comparison_pair":
            return self._generate_paired_comparison(rng, label, direction)
        elif data_pattern == "comparison_rank":
            return self._generate_ranked_bar(rng, direction)
        elif data_pattern == "trend":
            return self._generate_trend_series(rng, direction)
        elif data_pattern == "allocation_table":
            return self._generate_allocation_table(rng)
        elif data_pattern == "part_to_whole":
            return self._generate_part_to_whole(rng)
        elif data_pattern == "deviation_from_target":
            return self._generate_deviation_from_target(rng, direction)
        elif data_pattern == "cumulative_buildup":
            return self._generate_cumulative_buildup(rng, direction)
        elif data_pattern == "distribution_grid":
            return self._generate_distribution_grid(rng)
        elif data_pattern == "prioritization_matrix":
            return self._generate_prioritization_matrix(rng)
        # Phase 2 extension: new data patterns
        elif data_pattern == "gantt_timeline":
            return self._generate_gantt_timeline(rng, label)
        elif data_pattern == "overlap_analysis":
            return self._generate_venn_data(rng)
        elif data_pattern == "process_sequence":
            return self._generate_process_steps(rng, label)

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
        names = ["Our Target", "Competitor A", "Competitor B", "Competitor C"]
        if direction == "up":
            v1 = rng.randint(90, 115)
            v2 = v1 - rng.randint(10, 20)
            v3 = v2 - rng.randint(15, 25)
            v4 = v3 - rng.randint(15, 20)
            values = [float(v1), float(v2), float(v3), float(max(v4, 10))]
        else:
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

        start_val = rng.randint(20, 40)

        base_series = []
        target_series = []

        current_base = start_val
        current_target = start_val

        for i in range(len(periods)):
            noise_base = rng.uniform(-1.5, 1.5)
            noise_target = rng.uniform(-1.0, 1.0)

            base_drift = rng.uniform(-0.5, 0.5)
            current_base += base_drift + noise_base
            base_series.append(round(max(current_base, 5.0), 1))

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
        """Generate allocations for project roadmap steps using rng for variety.

        Phase 6 fix: original implementation used hardcoded lists that produced
        identical output for every deck. Now fully seeded via rng.
        """
        workstreams = [
            "Digital Infrastructure", "Customer Acquisition", "Talent & Capability",
            "Operational Efficiency", "Market Expansion"
        ]
        budgets = [
            f"${rng.randint(50, 400)}K" for _ in range(5)
        ]
        impacts = [
            f"+{rng.randint(5, 30)}% {rng.choice(['margin', 'volume', 'conversion', 'retention', 'scale'])}"
            for _ in range(5)
        ]

        return {
            "headers": ["Key Workstream", "Budget Allocation", "Target Outcome"],
            "values": [
                [workstreams[i], budgets[i], impacts[i]] for i in range(5)
            ]
        }

    def _generate_part_to_whole(self, rng: random.Random) -> Dict[str, Any]:
        """Generate N shares that sum to ~100% (§7.3 part_to_whole)."""
        segments = ["Segment A", "Segment B", "Segment C", "Segment D"]
        raw = [rng.randint(15, 45) for _ in segments]
        total = sum(raw)
        shares = [round(v / total * 100, 1) for v in raw]
        shares[-1] = round(100.0 - sum(shares[:-1]), 1)
        return {
            "labels": segments,
            "series": [{"name": "Share", "values": shares}]
        }

    def _generate_deviation_from_target(
        self, rng: random.Random, direction: Literal["up", "down"]
    ) -> Dict[str, Any]:
        """Generate actual + target values with a direction-consistent gap (§7.3)."""
        target = rng.randint(50, 80)
        actual = target + rng.randint(5, 20) if direction == "up" else target - rng.randint(5, 20)
        metrics = ["Q1", "Q2", "Q3", "Q4"]
        actual_vals, target_vals = [], []
        for i in range(len(metrics)):
            drift = i * (1.5 if direction == "up" else -1.0)
            actual_vals.append(round(max(actual + rng.uniform(-2.0, 2.0) + drift, 5.0), 1))
            target_vals.append(round(max(target + rng.uniform(-1.0, 1.0), 5.0), 1))
        return {
            "labels": metrics,
            "series": [
                {"name": "Actual", "values": actual_vals},
                {"name": "Target", "values": target_vals},
            ],
            "target_value": float(target),
            "actual_value": float(actual_vals[-1]),
        }

    def _generate_cumulative_buildup(
        self, rng: random.Random, direction: Literal["up", "down"]
    ) -> Dict[str, Any]:
        """Generate sequential signed deltas from start to end value (§7.3 waterfall)."""
        start = rng.randint(40, 70)
        labels = ["Start", "Driver A", "Driver B", "Driver C", "Headwind", "End"]
        sign = 1 if direction == "up" else -1
        deltas = [
            sign * rng.randint(8, 18),
            sign * rng.randint(5, 12),
            sign * rng.randint(6, 15),
            -sign * rng.randint(3, 8),
        ]
        values = [float(start)] + [float(d) for d in deltas] + [float(start + sum(deltas))]
        return {
            "labels": labels,
            "series": [{"name": "Value", "values": values}],
            "start_value": float(start),
        }

    def _generate_distribution_grid(self, rng: random.Random) -> Dict[str, Any]:
        """Generate a small matrix of values across two categorical axes (§7.3 heatmap)."""
        rows = ["North", "South", "East", "West"]
        cols = ["Q1", "Q2", "Q3", "Q4"]
        matrix = [[round(rng.uniform(30, 90), 1) for _ in cols] for _ in rows]
        return {
            "labels": cols,
            "row_labels": rows,
            "series": [{"name": r, "values": matrix[i]} for i, r in enumerate(rows)],
        }

    def _generate_prioritization_matrix(self, rng: random.Random) -> Dict[str, Any]:
        """Generate items at (impact, effort) coordinates for matrix_view (§7.3)."""
        items = [
            {"label": "Initiative A", "x": round(rng.uniform(0.5, 0.9), 2), "y": round(rng.uniform(0.5, 0.9), 2)},
            {"label": "Initiative B", "x": round(rng.uniform(0.1, 0.5), 2), "y": round(rng.uniform(0.5, 0.9), 2)},
            {"label": "Initiative C", "x": round(rng.uniform(0.5, 0.9), 2), "y": round(rng.uniform(0.1, 0.5), 2)},
            {"label": "Initiative D", "x": round(rng.uniform(0.1, 0.5), 2), "y": round(rng.uniform(0.1, 0.5), 2)},
        ]
        return {"items": items}

    # -------------------------------------------------------------------------
    # Phase 2 extension: new data pattern generators
    # -------------------------------------------------------------------------

    def _generate_gantt_timeline(self, rng: random.Random, label: str) -> Dict[str, Any]:
        """Generate 4–6 Gantt tasks with random start/end periods (max 8 periods)."""
        n_tasks = rng.randint(4, 6)
        n_periods = 8
        periods = [f"Q{i+1}" for i in range(n_periods)]

        phase_names = [
            "Discovery & Assessment", "Strategy Design", "Pilot Rollout",
            "Full Deployment", "Optimization", "Scale & Sustain"
        ]
        rng.shuffle(phase_names)

        tasks = []
        cursor = 0
        accent_cycle = ["accent_primary", "accent_secondary", "accent_tertiary",
                        "accent_primary", "accent_secondary", "accent_tertiary"]
        for i in range(n_tasks):
            start = max(0, cursor - rng.randint(0, 1))  # slight overlap allowed
            duration = rng.randint(1, 3)
            end = min(n_periods, start + duration)
            tasks.append({
                "name": phase_names[i],
                "start": start,
                "end": end,
                "color": accent_cycle[i % len(accent_cycle)],
            })
            cursor = end

        return {
            "label": label or "Implementation Roadmap",
            "tasks": tasks,
            "periods": periods,
        }

    def _generate_venn_data(self, rng: random.Random) -> Dict[str, Any]:
        """Generate 2 or 3 Venn circles with plausible corporate capability names."""
        all_circles = [
            {"name": "Customer Experience", "desc": "NPS-driven loyalty"},
            {"name": "Digital Capability",   "desc": "API-first products"},
            {"name": "Operational Scale",     "desc": "Cost optimisation"},
            {"name": "Market Access",         "desc": "Channel reach"},
            {"name": "Technology Platform",   "desc": "Cloud-native stack"},
            {"name": "Talent & Culture",      "desc": "Agile workforce"},
        ]
        rng.shuffle(all_circles)
        n = rng.choice([2, 3])
        circles = all_circles[:n]

        overlap_phrases = [
            "Competitive Moat", "Unique Value", "Strategic Edge",
            "Differentiated Offer", "Growth Engine"
        ]
        return {
            "label": "Strategic Capability Overlap",
            "circles": circles,
            "overlap_label": rng.choice(overlap_phrases),
        }

    def _generate_process_steps(self, rng: random.Random, label: str) -> Dict[str, Any]:
        """Generate 3–5 process steps with badge, title, and short description."""
        step_pools = [
            [{"badge": "01", "title": "Assess",   "desc": "Baseline diagnostics",   "icon": "search"},
             {"badge": "02", "title": "Design",   "desc": "Blueprint playbooks",     "icon": "lightbulb"},
             {"badge": "03", "title": "Execute",  "desc": "Rollout initiatives",    "icon": "zap"},
             {"badge": "04", "title": "Measure",  "desc": "Track performance",      "icon": "chart_bar"},
             {"badge": "05", "title": "Scale",    "desc": "Sustain at full pace",   "icon": "trend_up"}],
            [{"badge": "01", "title": "Discover", "desc": "Market research",         "icon": "search"},
             {"badge": "02", "title": "Define",   "desc": "Scope & requirements",   "icon": "flag"},
             {"badge": "03", "title": "Develop",  "desc": "Build & iterate",        "icon": "git_branch"},
             {"badge": "04", "title": "Deploy",   "desc": "Go-live operations",     "icon": "zap"}],
            [{"badge": "01", "title": "Align",    "desc": "Stakeholder buy-in",      "icon": "users"},
             {"badge": "02", "title": "Plan",     "desc": "Detailed roadmap",       "icon": "calendar"},
             {"badge": "03", "title": "Build",    "desc": "Core delivery",          "icon": "layers"},
             {"badge": "04", "title": "Test",     "desc": "Quality assurance",      "icon": "check_circle"},
             {"badge": "05", "title": "Launch",   "desc": "Controlled go-live",     "icon": "flag"}],
        ]
        chosen = rng.choice(step_pools)
        n = rng.randint(3, len(chosen))
        steps = chosen[:n]
        return {"steps": steps}

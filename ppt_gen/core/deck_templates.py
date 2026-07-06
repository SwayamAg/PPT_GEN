from typing import Dict, List, Optional
from pydantic import BaseModel

# Re-use models defined in core planning files
class SectionPlan(BaseModel):
    name: str
    purpose: str

class DeckPlan(BaseModel):
    objective: str
    sections: List[SectionPlan]

class SlideOutlineItem(BaseModel):
    section: str
    slide_title: str
    purpose: str
    archetype: str
    data_mode: str = "synthetic"
    user_data: Optional[Dict] = None

# Built-in presets definitions
TEMPLATES: Dict[str, Dict] = {
    "consulting_strategy": {
        "objective": "Formulate a clear strategic roadmap to accelerate premium-tier growth, restore core margins, and outline key implementation initiatives.",
        "sections": [
            {"name": "Executive Summary", "purpose": "High-level summary of strategic objectives and margin recovery targets."},
            {"name": "Market & Competitive Benchmarking", "purpose": "Analysis of volume growth and market penetration against competitors."},
            {"name": "Strategic growth initiatives", "purpose": "Detailed review of key growth playbooks and core workstreams."},
            {"name": "Financial Plan & Next Steps", "purpose": "Projections of margin expansion and priority resource allocation roadmap."}
        ],
        "slides": [
            {
                "section": "Executive Summary",
                "slide_title": "Strategic Blueprint for Margin Recovery",
                "purpose": "Introduce the strategic challenge, core goal, and primary performance indicators.",
                "archetype": "title_challenge"
            },
            {
                "section": "Market & Competitive Benchmarking",
                "slide_title": "Premium Volume & Competitor Benchmarks",
                "purpose": "Compare our premium volume growth vs. Competitors A, B, and C.",
                "archetype": "comparison_bars"
            },
            {
                "section": "Strategic growth initiatives",
                "slide_title": "Initiatives to Scale Premium Operations",
                "purpose": "Compare expansion playbooks against customer loyalty workstreams.",
                "archetype": "two_column_initiative"
            },
            {
                "section": "Strategic growth initiatives",
                "slide_title": "Target Market Share Recovery",
                "purpose": "Detail our market share recovery trajectory over the next 6 quarters.",
                "archetype": "single_chart_focus"
            },
            {
                "section": "Financial Plan & Next Steps",
                "slide_title": "Projected Financial Gains & Key KPIs",
                "purpose": "High-density dashboard tracking conversion uplifts and revenue stat callouts.",
                "archetype": "stat_grid_charts"
            },
            {
                "section": "Financial Plan & Next Steps",
                "slide_title": "Resource Allocation & Next Steps",
                "purpose": "Outline the immediate action items and corresponding budget allocation.",
                "archetype": "table_priorities"
            }
        ]
    },
    "business_review": {
        "objective": "Review business operations, highlight performance against budget, identify margin leaks, and propose corrective actions.",
        "sections": [
            {"name": "Operational Performance", "purpose": "Operational milestones and budget versus actual comparison."},
            {"name": "Core Priorities", "purpose": "Deep-dive analysis of core priority initiatives."},
            {"name": "Next Steps", "purpose": "Roadmap of corrective measures and next steps."}
        ],
        "slides": [
            {
                "section": "Operational Performance",
                "slide_title": "Business Performance Overview",
                "purpose": "Overview of key operational metrics and performance callouts.",
                "archetype": "stat_grid_charts"
            },
            {
                "section": "Operational Performance",
                "slide_title": "Budget vs. Actual Performance Review",
                "purpose": "A structured table reviewing budget allocation vs. Performance outcomes.",
                "archetype": "table_priorities"
            },
            {
                "section": "Core Priorities",
                "slide_title": "Strategic Focus Areas",
                "purpose": "Compare operational improvement workstreams with product optimization plays.",
                "archetype": "two_column_initiative"
            },
            {
                "section": "Next Steps",
                "slide_title": "Immediate Priority Action Plan",
                "purpose": "List the key corrective initiatives and roadmap steps.",
                "archetype": "table_priorities"
            }
        ]
    },
    "market_analysis": {
        "objective": "Analyse industry trends, benchmark competitive positioning, identify target segments, and outline growth opportunities.",
        "sections": [
            {"name": "Industry Trends", "purpose": "Identify high-level trends and challenges in the industry."},
            {"name": "Competitive Analysis", "purpose": "Compare market share and volume metrics against major players."},
            {"name": "Growth Strategy", "purpose": "Outline target segments and specific plays to capture market share."}
        ],
        "slides": [
            {
                "section": "Industry Trends",
                "slide_title": "Macro Industry Dynamics & Challenges",
                "purpose": "Show major industry challenges and market pressure points.",
                "archetype": "title_challenge"
            },
            {
                "section": "Competitive Analysis",
                "slide_title": "Market Share Benchmarks",
                "purpose": "Bar charts showing market volume share of our firm vs. Major competitors.",
                "archetype": "comparison_bars"
            },
            {
                "section": "Growth Strategy",
                "slide_title": "Target Market Segment Expansion",
                "purpose": "Show our projected growth inside target segments.",
                "archetype": "single_chart_focus"
            },
            {
                "section": "Growth Strategy",
                "slide_title": "Strategic Segment Priorities",
                "purpose": "Table illustrating resources allocated and priorities across new segments.",
                "archetype": "table_priorities"
            }
        ]
    },
    "product_dashboard": {
        "objective": "Track product adoption, detail feature pipeline, review user engagement, and project growth metrics.",
        "sections": [
            {"name": "Product Performance", "purpose": "Key metrics on product adoption and user engagement."},
            {"name": "Roadmap & Release Strategy", "purpose": "Future product updates and timeline."}
        ],
        "slides": [
            {
                "section": "Product Performance",
                "slide_title": "Product Engagement Metrics Dashboard",
                "purpose": "Provide a high-density summary of user engagement stat callouts.",
                "archetype": "stat_grid_charts"
            },
            {
                "section": "Product Performance",
                "slide_title": "Adoption Trends Over Time",
                "purpose": "Line chart showing product adoption growth over 6 quarters.",
                "archetype": "single_chart_focus"
            },
            {
                "section": "Roadmap & Release Strategy",
                "slide_title": "Feature Milestones & Launch Plays",
                "purpose": "Compare upcoming feature initiatives against operational rollout tasks.",
                "archetype": "two_column_initiative"
            },
            {
                "section": "Roadmap & Release Strategy",
                "slide_title": "Product Priority Backlog",
                "purpose": "Roadmap table illustrating priorities and milestones.",
                "archetype": "table_priorities"
            }
        ]
    },
    "executive_summary": {
        "objective": "Synthesize the core problem, strategic objectives, recommended actions, and expected outcomes.",
        "sections": [
            {"name": "Summary & Synthesis", "purpose": "Overview of strategic decisions and expected performance outcomes."}
        ],
        "slides": [
            {
                "section": "Summary & Synthesis",
                "slide_title": "The Strategic Challenge",
                "purpose": "Present the main problem statement and high-level urgency.",
                "archetype": "title_challenge"
            },
            {
                "section": "Summary & Synthesis",
                "slide_title": "Key Recommendations & Action Plan",
                "purpose": "Provide a structured breakdown of recommended workstreams and actions.",
                "archetype": "two_column_initiative"
            },
            {
                "section": "Summary & Synthesis",
                "slide_title": "Expected Operational Outcomes",
                "purpose": "Show projected gains in key performance indicators.",
                "archetype": "stat_grid_charts"
            }
        ]
    }
}

def get_preset_plan(deck_type: str) -> Optional[Dict]:
    """Retrieve the deck plan preset if it exists, otherwise return None."""
    return TEMPLATES.get(deck_type.lower())

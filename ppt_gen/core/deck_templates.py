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

class CustomizedPresetOutput(BaseModel):
    objective: str
    sections: List[SectionPlan]
    slides: List[SlideOutlineItem]

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
    },
    "insights_report": {
        "objective": "Deliver an executive-grade business insights deck anchored by a hero cover, KPI dashboard with data table, and a closing takeaways slide.",
        "sections": [
            {"name": "Cover", "purpose": "Hero cover framing the report topic and headline metrics."},
            {"name": "Performance Dashboard", "purpose": "KPI callouts, a trend chart, and a supporting data table."},
            {"name": "Takeaways", "purpose": "Four crisp takeaways and next steps."}
        ],
        "slides": [
            {
                "section": "Cover",
                "slide_title": "Business Insights Report",
                "purpose": "Hero cover slide with eyebrow, headline, subtitle, and three hero KPIs.",
                "archetype": "executive_cover"
            },
            {
                "section": "Performance Dashboard",
                "slide_title": "Quarterly Performance Dashboard",
                "purpose": "KPI callouts, a trend chart, and a supporting data table on one slide.",
                "archetype": "dashboard_with_table"
            },
            {
                "section": "Takeaways",
                "slide_title": "Key Takeaways & Next Steps",
                "purpose": "Four priority-card takeaways summarizing the report.",
                "archetype": "closing_takeaways"
            }
        ]
    },
    "transformation_roadmap": {
        "objective": "Outline the step-by-step business transformation roadmap, align on immediate process steps, timeline milestones, and closing program takeaways.",
        "sections": [
            {"name": "Context & Challenge", "purpose": "Framing the current market context and urgent challenges."},
            {"name": "Transformation Steps", "purpose": "The core phases and sequencing of the transformation program."},
            {"name": "Timeline & Roadmap", "purpose": "Detailed implementation milestones and task scheduling."},
            {"name": "Takeaways", "purpose": "Summary takeaways and program governance next steps."}
        ],
        "slides": [
            {
                "section": "Context & Challenge",
                "slide_title": "The Strategic Transformation Imperative",
                "purpose": "Introduce the core challenge, goal, and metrics driving the transformation.",
                "archetype": "title_challenge"
            },
            {
                "section": "Transformation Steps",
                "slide_title": "Sequencing the Transformation Phases",
                "purpose": "Show the horizontal chevron process steps, KPIs, and qualitative insights.",
                "archetype": "process_flow"
            },
            {
                "section": "Timeline & Roadmap",
                "slide_title": "Transformation Project Roadmap",
                "purpose": "Detail the implementation task timeline (Gantt) and assumptions.",
                "archetype": "implementation_roadmap"
            },
            {
                "section": "Takeaways",
                "slide_title": "Immediate Next Steps & Takeaways",
                "purpose": "Four structured priority cards with key takeaways.",
                "archetype": "closing_takeaways"
            }
        ]
    },
    "strategic_positioning": {
        "objective": "Define our strategic positioning, analyze capability overlaps, benchmark competitors, and summarize narrative outcomes.",
        "sections": [
            {"name": "Executive Cover", "purpose": "Title and hero KPIs of the positioning report."},
            {"name": "Overlap Analysis", "purpose": "Analysis of capability intersections and priority areas."},
            {"name": "Competitive Analysis", "purpose": "Benchmarking volume and growth vs. competitors."},
            {"name": "Strategic Narrative", "purpose": "Hero KPI summary and narrative bullets."}
        ],
        "slides": [
            {
                "section": "Executive Cover",
                "slide_title": "Strategic Positioning Report",
                "purpose": "Hero cover with title, subtitle, and three key stats.",
                "archetype": "executive_cover"
            },
            {
                "section": "Overlap Analysis",
                "slide_title": "Capability Overlaps & Core Advantages",
                "purpose": "Venn diagram showing capability overlaps with supporting priority cards.",
                "archetype": "strategic_overlap"
            },
            {
                "section": "Competitive Analysis",
                "slide_title": "Competitive Growth Benchmarks",
                "purpose": "Compare our premium volume growth vs. Competitors A, B, and C.",
                "archetype": "comparison_bars"
            },
            {
                "section": "Strategic Narrative",
                "slide_title": "Strategic Growth Narrative",
                "purpose": "High-impact narrative bullets with a hero KPI and supporting stats.",
                "archetype": "kpi_narrative"
            }
        ]
    },
    "dashboard_deck": {
        "objective": "Track key performance indicators, segment breakdown, and strategic growth drivers using high-density visualization dashboards.",
        "sections": [
            {"name": "Performance Overview", "purpose": "KPI callouts and core adoption trends."},
            {"name": "Visual Dashboards", "purpose": "Deep-dives into metric segments, prioritization, and scorecards."}
        ],
        "slides": [
            {
                "section": "Performance Overview",
                "slide_title": "Quarterly Performance Dashboard",
                "purpose": "Provide a high-density summary of key performance trends, data tables, and metrics.",
                "archetype": "dashboard_with_table"
            },
            {
                "section": "Performance Overview",
                "slide_title": "Stat Callouts & Volume Analysis",
                "purpose": "Track volume performance across multiple channels and priority areas.",
                "archetype": "stat_grid_charts"
            },
            {
                "section": "Visual Dashboards",
                "slide_title": "Variance Scorecard & Segment Breakdown",
                "purpose": "A structured breakdown of target vs. actual segment performance with a pie breakdown.",
                "archetype": "variance_scorecard"
            },
            {
                "section": "Visual Dashboards",
                "slide_title": "Prioritization & Strategic Milestones",
                "purpose": "Matrix view of corrective action priorities and step milestones.",
                "archetype": "prioritization_matrix"
            }
        ]
    },
    # ── Full Showcase ─────────────────────────────────────────────────────────
    # One slide per archetype (15 total).  Uses every archetype in
    # blueprint_library.ARCHETYPES exactly once: executive_cover first,
    # closing_takeaways last, all others in a coherent narrative order.
    # Topic: "Global Digital Banking Transformation"
    "full_showcase": {
        "objective": (
            "Present a comprehensive end-to-end business case for a global digital banking "
            "transformation programme — covering strategic context, performance benchmarks, "
            "initiative workstreams, financial projections, implementation roadmap, and "
            "programme takeaways."
        ),
        "sections": [
            {"name": "Executive Cover",        "purpose": "Hero cover framing the programme."},
            {"name": "Strategic Context",       "purpose": "The challenge, narrative and headline KPIs driving transformation."},
            {"name": "Performance Baseline",    "purpose": "Current-state metrics and competitive benchmarking."},
            {"name": "Competitive Landscape",   "purpose": "Market-share and variance analysis vs. peers."},
            {"name": "Transformation Plan",     "purpose": "Initiative workstreams, priorities, and the effort/impact matrix."},
            {"name": "Execution & Roadmap",     "purpose": "Process steps, Gantt timeline, and capability overlap."},
            {"name": "Closing",                 "purpose": "Programme takeaways and immediate next steps."},
        ],
        "slides": [
            # ── 1. executive_cover ────────────────────────────────────────────
            {
                "section": "Executive Cover",
                "slide_title": "Global Digital Banking Transformation",
                "purpose": (
                    "Hero cover slide with eyebrow label 'Programme Overview', "
                    "headline title, subtitle, and three hero KPI callouts: "
                    "Total Investment ($2.4B), Target Markets (14 countries), "
                    "Projected NPS Uplift (+28 pts)."
                ),
                "archetype": "executive_cover"
            },
            # ── 2. title_challenge ────────────────────────────────────────────
            {
                "section": "Strategic Context",
                "slide_title": "The Digital Imperative: Why We Must Act Now",
                "purpose": (
                    "Present the core strategic challenge — declining branch footfall, "
                    "rising fintech competition, and stalling mobile adoption — alongside "
                    "three high-impact performance callouts and the primary transformation goal."
                ),
                "archetype": "title_challenge"
            },
            # ── 3. kpi_narrative ─────────────────────────────────────────────
            {
                "section": "Strategic Context",
                "slide_title": "The Transformation Thesis in Three Numbers",
                "purpose": (
                    "High-impact narrative slide anchored by a hero metric (e.g. '68 % of "
                    "customers prefer digital-first interactions'), supported by two secondary "
                    "stats and three narrative bullet points articulating the strategic rationale."
                ),
                "archetype": "kpi_narrative"
            },
            # ── 4. stat_grid_charts ───────────────────────────────────────────
            {
                "section": "Performance Baseline",
                "slide_title": "Current Performance Dashboard",
                "purpose": (
                    "High-density grid showing four KPI stat callouts (Digital Active Users, "
                    "Mobile CSAT, Cost-to-Income Ratio, Digital Revenue Share) alongside two "
                    "trend charts tracking quarterly digital revenue and cost-efficiency."
                ),
                "archetype": "stat_grid_charts"
            },
            # ── 5. comparison_bars ────────────────────────────────────────────
            {
                "section": "Competitive Landscape",
                "slide_title": "Digital Penetration vs. Peer Banks",
                "purpose": (
                    "Grouped bar chart comparing our digital active user rate (%), mobile app "
                    "rating, and digital revenue share against four peer institutions "
                    "(Peer A–D), revealing a clear performance gap in mobile engagement."
                ),
                "archetype": "comparison_bars"
            },
            # ── 6. single_chart_focus ─────────────────────────────────────────
            {
                "section": "Competitive Landscape",
                "slide_title": "Mobile Banking Adoption Trajectory",
                "purpose": (
                    "Single focused line chart showing our projected mobile-banking adoption "
                    "curve from Q1 2025 to Q4 2027, with an annotated inflection point "
                    "at the completion of the core platform migration and a recommendation panel."
                ),
                "archetype": "single_chart_focus"
            },
            # ── 7. variance_scorecard ─────────────────────────────────────────
            {
                "section": "Competitive Landscape",
                "slide_title": "Programme Budget vs. Actuals — Year 1",
                "purpose": (
                    "Variance scorecard comparing Year-1 actual spend vs. budget across five "
                    "cost buckets (Technology, People, Compliance, Marketing, Operations), "
                    "surfacing a +12 % technology overspend requiring replan."
                ),
                "archetype": "variance_scorecard"
            },
            # ── 8. dashboard_with_table ───────────────────────────────────────
            {
                "section": "Performance Baseline",
                "slide_title": "Integrated KPI Dashboard & Country Scorecard",
                "purpose": (
                    "Combined dashboard: three hero KPI cards (Revenue Growth, Cost Reduction, "
                    "NPS) at top, a trend chart in the centre, and a supporting country-level "
                    "data table (14 markets × 4 KPI columns) below."
                ),
                "archetype": "dashboard_with_table"
            },
            # ── 9. two_column_initiative ──────────────────────────────────────
            {
                "section": "Transformation Plan",
                "slide_title": "Two Core Workstreams Driving Transformation",
                "purpose": (
                    "Side-by-side comparison of Workstream 1 (Platform Modernisation: "
                    "API banking core, cloud migration, data platform) vs. Workstream 2 "
                    "(Customer Experience: mobile-first UX, personalisation engine, "
                    "omni-channel service model) with three numbered steps each."
                ),
                "archetype": "two_column_initiative"
            },
            # ── 10. table_priorities ─────────────────────────────────────────
            {
                "section": "Transformation Plan",
                "slide_title": "Initiative Priority Register",
                "purpose": (
                    "Structured table of the top eight transformation initiatives, each row "
                    "showing Initiative Name, Owner, Budget, Status, and Strategic Priority "
                    "rating; three recommendation cards below summarise the critical path."
                ),
                "archetype": "table_priorities"
            },
            # ── 11. prioritization_matrix ─────────────────────────────────────
            {
                "section": "Transformation Plan",
                "slide_title": "Initiative Effort vs. Impact Matrix",
                "purpose": (
                    "BCG-style 2×2 effort/impact prioritisation matrix plotting eight "
                    "initiatives as labelled dots, highlighting 'Quick Wins' (low effort / "
                    "high impact) vs. 'Major Bets' (high effort / high impact) quadrants."
                ),
                "archetype": "prioritization_matrix"
            },
            # ── 12. process_flow ──────────────────────────────────────────────
            {
                "section": "Execution & Roadmap",
                "slide_title": "Transformation Delivery in Five Phases",
                "purpose": (
                    "Horizontal chevron flow showing five sequential delivery phases: "
                    "Assess → Design → Build → Pilot → Scale, with one KPI callout and "
                    "one qualitative insight per phase."
                ),
                "archetype": "process_flow"
            },
            # ── 13. implementation_roadmap ────────────────────────────────────
            {
                "section": "Execution & Roadmap",
                "slide_title": "Three-Year Implementation Roadmap",
                "purpose": (
                    "Gantt-strip roadmap spanning Q1 2025 to Q4 2027, showing six workstream "
                    "tracks (Core Banking, Cloud & Data, Mobile, Compliance, People & Change, "
                    "Governance) with key milestone markers and a 'today' reference line."
                ),
                "archetype": "implementation_roadmap"
            },
            # ── 14. strategic_overlap ─────────────────────────────────────────
            {
                "section": "Execution & Roadmap",
                "slide_title": "Capability Synergies Across Business Units",
                "purpose": (
                    "Venn diagram showing three-way capability overlap between Retail Banking, "
                    "Corporate Banking, and Wealth Management — with the shared digital "
                    "infrastructure platform at the centre. Two priority cards highlight "
                    "the highest-value synergy opportunities."
                ),
                "archetype": "strategic_overlap"
            },
            # ── 15. closing_takeaways ─────────────────────────────────────────
            {
                "section": "Closing",
                "slide_title": "Four Imperatives for Programme Success",
                "purpose": (
                    "Closing slide with four structured priority-card takeaways: "
                    "(1) Governance & Accountability, (2) Agile Delivery Cadence, "
                    "(3) Data-Driven Decision Making, (4) Customer Obsession — each with "
                    "a concrete next step and an owner."
                ),
                "archetype": "closing_takeaways"
            },
        ]
    }
}

def get_preset_plan(deck_type: str) -> Optional[Dict]:
    """Retrieve the deck plan preset if it exists, otherwise return None."""
    return TEMPLATES.get(deck_type.lower())

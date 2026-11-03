"""
Generate Bid_Decision_Support_Dashboard.pptx
Run from repo root: python3 generate_presentation.py
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from lxml import etree

# ── Dimensions ────────────────────────────────────────────────────────────────
W = Inches(13.33)
H = Inches(7.5)

# ── Color palette ─────────────────────────────────────────────────────────────
NAVY        = RGBColor(0x1F, 0x38, 0x64)
STEEL_BLUE  = RGBColor(0x2E, 0x75, 0xB6)
LIGHT_BLUE  = RGBColor(0xBD, 0xD7, 0xEE)
GREEN       = RGBColor(0x2E, 0x7D, 0x32)
GREEN_LIGHT = RGBColor(0xE8, 0xF5, 0xE9)
YELLOW_CLR  = RGBColor(0xF5, 0x7F, 0x17)
YELLOW_LIGHT= RGBColor(0xFF, 0xF8, 0xE1)
RED_CLR     = RGBColor(0xC6, 0x28, 0x28)
RED_LIGHT   = RGBColor(0xFF, 0xEB, 0xEE)
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
DARK_GRAY   = RGBColor(0x21, 0x21, 0x21)
MED_GRAY    = RGBColor(0x61, 0x61, 0x61)
LIGHT_GRAY  = RGBColor(0xF5, 0xF5, 0xF5)
BORDER_GRAY = RGBColor(0xBD, 0xBD, 0xBD)

OUTPUT = "Bid_Decision_Support_Dashboard.pptx"


# ── Helpers ───────────────────────────────────────────────────────────────────

def new_prs():
    prs = Presentation()
    prs.slide_width  = W
    prs.slide_height = H
    return prs


def blank_slide(prs):
    layout = prs.slide_layouts[6]  # blank
    return prs.slides.add_slide(layout)


def _rgb(color: RGBColor):
    return color


def add_rect(slide, l, t, w, h, fill, line=None, line_width_pt=1.0):
    shape = slide.shapes.add_shape(1, l, t, w, h)  # MSO_SHAPE_TYPE.RECTANGLE
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line:
        shape.line.color.rgb = line
        shape.line.width = Pt(line_width_pt)
    else:
        shape.line.fill.background()
    return shape


def add_textbox(slide, text, l, t, w, h,
                font_size=14, bold=False, color=DARK_GRAY,
                align=PP_ALIGN.LEFT, wrap=True, italic=False,
                line_spacing=None):
    txb = slide.shapes.add_textbox(l, t, w, h)
    txb.word_wrap = wrap
    tf = txb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    if line_spacing:
        p.line_spacing = Pt(line_spacing)
    return txb


def add_multiline_textbox(slide, lines, l, t, w, h,
                          font_size=13, bold_first=False, color=DARK_GRAY,
                          align=PP_ALIGN.LEFT, line_spacing_pt=18):
    txb = slide.shapes.add_textbox(l, t, w, h)
    txb.word_wrap = True
    tf = txb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.alignment = align
        p.line_spacing = Pt(line_spacing_pt)
        run = p.add_run()
        run.text = line
        run.font.size = Pt(font_size)
        run.font.bold = (bold_first and i == 0)
        run.font.color.rgb = color
    return txb


def add_bullet_textbox(slide, bullets, l, t, w, h,
                       font_size=13, color=DARK_GRAY, bullet_char="•",
                       line_spacing_pt=20):
    txb = slide.shapes.add_textbox(l, t, w, h)
    txb.word_wrap = True
    tf = txb.text_frame
    tf.word_wrap = True
    for i, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.line_spacing = Pt(line_spacing_pt)
        run = p.add_run()
        run.text = f"{bullet_char}  {bullet}"
        run.font.size = Pt(font_size)
        run.font.color.rgb = color
    return txb


def add_header_bar(slide, title, subtitle=None):
    # Navy bar across the top
    bar_h = Inches(0.9)
    add_rect(slide, Inches(0), Inches(0), W, bar_h, NAVY)
    add_textbox(slide, title,
                Inches(0.4), Inches(0.1), Inches(12.5), Inches(0.65),
                font_size=24, bold=True, color=WHITE, align=PP_ALIGN.LEFT)
    if subtitle:
        add_textbox(slide, subtitle,
                    Inches(0.4), Inches(0.65), Inches(12.5), Inches(0.35),
                    font_size=13, bold=False, color=LIGHT_BLUE, align=PP_ALIGN.LEFT)


def add_footer(slide, text="Chicago Booth Lab  ·  Team 4  ·  May 2026"):
    add_textbox(slide, text,
                Inches(0.4), Inches(7.1), Inches(12.5), Inches(0.3),
                font_size=10, color=MED_GRAY, align=PP_ALIGN.RIGHT)


def add_section_label(slide, label, sublabel=None):
    """Bold section label with a steel-blue left accent bar."""
    add_rect(slide, Inches(0.4), Inches(1.1), Inches(0.08), Inches(0.45), STEEL_BLUE)
    add_textbox(slide, label,
                Inches(0.6), Inches(1.05), Inches(12), Inches(0.55),
                font_size=17, bold=True, color=NAVY)
    if sublabel:
        add_textbox(slide, sublabel,
                    Inches(0.6), Inches(1.55), Inches(12), Inches(0.4),
                    font_size=13, color=MED_GRAY)


# ── Slide builders ─────────────────────────────────────────────────────────────

def slide_title(prs):
    slide = blank_slide(prs)
    # Full navy background
    add_rect(slide, 0, 0, W, H, NAVY)
    # Accent bar
    add_rect(slide, Inches(0.5), Inches(2.8), Inches(0.12), Inches(1.5), STEEL_BLUE)
    # Title
    add_textbox(slide,
                "Bid Decision Support Tool",
                Inches(0.8), Inches(2.5), Inches(11.5), Inches(1.1),
                font_size=40, bold=True, color=WHITE)
    # Subtitle
    add_textbox(slide,
                "A Pricing Intelligence Dashboard for a Commercial Plumbing Contractor",
                Inches(0.8), Inches(3.7), Inches(11), Inches(0.7),
                font_size=20, color=LIGHT_BLUE)
    # Footer
    add_textbox(slide,
                "Chicago Booth Lab  ·  Team 4  ·  May 2026",
                Inches(0.8), Inches(6.8), Inches(11.5), Inches(0.4),
                font_size=13, color=LIGHT_BLUE, align=PP_ALIGN.RIGHT)
    return slide


def slide_problem(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "The Problem We're Solving")
    add_section_label(slide,
                      "Estimators bid without a real-time benchmark",
                      "the company's own historical data is invisible at the moment a quote is being built")
    bullets = [
        "Every quote is a judgment call — no reference for what 'normal' looks like for this job type",
        "Under-pricing leaves margin on the table; over-pricing loses the job",
        "Patterns across job types, property types, and seasons are invisible without analysis",
        "the company's own historical data exists — but it isn't accessible at the moment a bid is being built",
    ]
    add_bullet_textbox(slide, bullets, Inches(0.6), Inches(2.1), Inches(12.1), Inches(4.5),
                       font_size=16, line_spacing_pt=28)
    add_footer(slide)
    return slide


def slide_solution(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "Instant Bid Intelligence, Built on the Company's Own Data")
    add_footer(slide)

    col_w  = Inches(3.8)
    col_h  = Inches(4.4)
    tops   = Inches(1.5)
    lefts  = [Inches(0.4), Inches(4.7), Inches(9.0)]
    titles = ["For Estimators", "For Managers", "For the Business"]
    bodies = [
        "Real-time Green / Yellow / Red signal as you build a quote — no spreadsheets needed.",
        "Automatic alerts when a bid needs review; visibility into approval patterns over time.",
        "A feedback loop that captures every decision and gets smarter as more jobs are logged.",
    ]
    colors = [GREEN_LIGHT, YELLOW_LIGHT, LIGHT_BLUE]
    border_colors = [GREEN, YELLOW_CLR, STEEL_BLUE]
    icon_colors = [GREEN, YELLOW_CLR, STEEL_BLUE]

    for i in range(3):
        add_rect(slide, lefts[i], tops, col_w, col_h,
                 colors[i], line=border_colors[i], line_width_pt=1.5)
        # Title strip
        add_rect(slide, lefts[i], tops, col_w, Inches(0.55), border_colors[i])
        add_textbox(slide, titles[i],
                    lefts[i] + Inches(0.15), tops + Inches(0.05),
                    col_w - Inches(0.3), Inches(0.5),
                    font_size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        add_textbox(slide, bodies[i],
                    lefts[i] + Inches(0.2), tops + Inches(0.75),
                    col_w - Inches(0.4), Inches(3.4),
                    font_size=15, color=DARK_GRAY, wrap=True)
    return slide


def slide_howto(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "Five Steps from Quote to Decision")
    add_footer(slide)

    steps = [
        ("1", "Open the dashboard\nin any web browser"),
        ("2", "Select job type\nand property type"),
        ("3", "Enter estimated costs\nand proposed quote"),
        ("4", "See the benchmark\nrange and flag instantly"),
        ("5", "Green → proceed\nYellow/Red → add reason\ncode and submit"),
    ]
    box_w = Inches(2.3)
    box_h = Inches(3.8)
    gap   = Inches(0.19)
    top   = Inches(1.7)
    start = Inches(0.35)

    for i, (num, text) in enumerate(steps):
        left = start + i * (box_w + gap)
        # Box background
        add_rect(slide, left, top, box_w, box_h, LIGHT_BLUE, line=STEEL_BLUE, line_width_pt=1.2)
        # Number circle (square approximation)
        circ_size = Inches(0.55)
        add_rect(slide, left + (box_w - circ_size) / 2, top + Inches(0.25),
                 circ_size, circ_size, NAVY)
        add_textbox(slide, num,
                    left + (box_w - circ_size) / 2, top + Inches(0.27),
                    circ_size, circ_size,
                    font_size=18, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        # Step text
        add_textbox(slide, text,
                    left + Inches(0.1), top + Inches(1.0),
                    box_w - Inches(0.2), Inches(2.6),
                    font_size=14, color=DARK_GRAY, align=PP_ALIGN.CENTER, wrap=True)

        # Arrow between boxes
        if i < len(steps) - 1:
            arrow_left = left + box_w + Inches(0.02)
            add_textbox(slide, "→",
                        arrow_left, top + box_h / 2 - Inches(0.25),
                        gap + Inches(0.15), Inches(0.5),
                        font_size=18, bold=True, color=STEEL_BLUE, align=PP_ALIGN.CENTER)
    return slide


def slide_flags(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "The Three-Color Flag System")
    add_footer(slide)

    boxes = [
        ("✅  GREEN",
         "Within ±10% of the benchmark price and margin ≥ 50%.",
         "Click 'Log & Proceed' — no extra steps needed.",
         GREEN, GREEN_LIGHT),
        ("⚠️  YELLOW",
         "Outside the benchmark range by up to 20%, or margin between 40–50%.",
         "Select a reason code before the bid can be submitted.",
         YELLOW_CLR, YELLOW_LIGHT),
        ("🔴  RED",
         "More than 20% outside the benchmark, or margin below 40%.",
         "A reason code AND manager approval are both required.",
         RED_CLR, RED_LIGHT),
    ]

    box_w = Inches(3.9)
    box_h = Inches(4.6)
    top   = Inches(1.5)
    lefts = [Inches(0.35), Inches(4.6), Inches(8.85)]

    for (title, line1, line2, border_col, bg_col), left in zip(boxes, lefts):
        add_rect(slide, left, top, box_w, box_h, bg_col, line=border_col, line_width_pt=2.0)
        # Header strip
        add_rect(slide, left, top, box_w, Inches(0.65), border_col)
        add_textbox(slide, title,
                    left + Inches(0.1), top + Inches(0.08),
                    box_w - Inches(0.2), Inches(0.55),
                    font_size=17, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        add_textbox(slide, line1,
                    left + Inches(0.2), top + Inches(0.85),
                    box_w - Inches(0.4), Inches(1.5),
                    font_size=15, color=DARK_GRAY, wrap=True)
        add_textbox(slide, line2,
                    left + Inches(0.2), top + Inches(2.6),
                    box_w - Inches(0.4), Inches(1.6),
                    font_size=14, bold=True, color=border_col, wrap=True)
    return slide


def slide_model_inputs(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "What the AI Model Considers")
    add_footer(slide)

    # Left column
    add_rect(slide, Inches(0.4), Inches(1.1), Inches(0.08), Inches(0.45), STEEL_BLUE)
    add_textbox(slide, "Four inputs used at bid time",
                Inches(0.6), Inches(1.05), Inches(5.5), Inches(0.5),
                font_size=16, bold=True, color=NAVY)
    input_bullets = [
        "Job Type  (e.g., Water Heater, Drain, HVAC, Fire Sprinkler)",
        "Property Type  (Residential or Commercial)",
        "Proposed Quote Amount",
        "Time of Year  (Month & Quarter)",
    ]
    add_bullet_textbox(slide, input_bullets,
                       Inches(0.6), Inches(1.65), Inches(5.8), Inches(3.5),
                       font_size=15, line_spacing_pt=26)

    # Right column
    add_rect(slide, Inches(7.0), Inches(1.1), Inches(0.08), Inches(0.45), STEEL_BLUE)
    add_textbox(slide, "What it learned from",
                Inches(7.2), Inches(1.05), Inches(5.8), Inches(0.5),
                font_size=16, bold=True, color=NAVY)
    right_bullets = [
        "Trained on the company's own completed jobs (four months of job history)",
        "Learns what gross profit % is typical for each job type, size, and season",
        "Model confidence (High / Medium / Low) is shown based on how many historical examples it has seen for that job type",
    ]
    add_bullet_textbox(slide, right_bullets,
                       Inches(7.2), Inches(1.65), Inches(5.8), Inches(4.0),
                       font_size=15, line_spacing_pt=26)

    # Divider
    add_rect(slide, Inches(6.6), Inches(1.1), Inches(0.04), Inches(5.5), BORDER_GRAY)
    return slide


def slide_benchmark(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "How the Benchmark Price Is Calculated")
    add_footer(slide)

    # Left explanation
    lines = [
        "The model predicts the expected gross profit % for your type of job.",
        "",
        "From that, it works backwards to calculate the price you'd need to charge to hit that margin.",
        "",
        "It then shows you a ±10% acceptable range around that target.",
        "",
        "A second model also estimates what the company has historically billed for jobs with similar cost inputs — shown as a secondary reference point.",
    ]
    add_multiline_textbox(slide, lines,
                          Inches(0.5), Inches(1.1), Inches(6.2), Inches(5.6),
                          font_size=15, color=DARK_GRAY, line_spacing_pt=20)

    # Right: worked example box
    add_rect(slide, Inches(7.1), Inches(1.2), Inches(5.8), Inches(5.4),
             LIGHT_BLUE, line=STEEL_BLUE, line_width_pt=1.5)
    add_rect(slide, Inches(7.1), Inches(1.2), Inches(5.8), Inches(0.6), NAVY)
    add_textbox(slide, "Worked Example: Commercial Water Heater",
                Inches(7.2), Inches(1.22), Inches(5.6), Inches(0.55),
                font_size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    example_lines = [
        "Total Cost:              $4,200",
        "Predicted GP%:           58%",
        "",
        "→  Benchmark price:      $10,000",
        "→  Acceptable range:     $9,000 – $11,000",
        "",
        "A quote of $8,500 would be 15% below",
        "the range → YELLOW flag.",
        "",
        "A quote of $7,000 would be 22% below",
        "the range → RED flag.",
    ]
    add_multiline_textbox(slide, example_lines,
                          Inches(7.4), Inches(2.0), Inches(5.3), Inches(4.3),
                          font_size=14, color=DARK_GRAY, line_spacing_pt=19)

    # Divider
    add_rect(slide, Inches(6.7), Inches(1.1), Inches(0.04), Inches(5.6), BORDER_GRAY)
    return slide


def slide_history(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "Every Decision Gets Logged Automatically")
    add_footer(slide)

    # Left
    add_rect(slide, Inches(0.4), Inches(1.1), Inches(0.08), Inches(0.45), STEEL_BLUE)
    add_textbox(slide, "What the log captures",
                Inches(0.6), Inches(1.05), Inches(5.8), Inches(0.5),
                font_size=16, bold=True, color=NAVY)
    left_bullets = [
        "Job type, property type, proposed quote, total cost",
        "Benchmark price and acceptable range",
        "Green / Yellow / Red outcome",
        "Reason code and notes (for overrides)",
        "Manager approval status",
        "ServiceTitan Job ID (once connected)",
    ]
    add_bullet_textbox(slide, left_bullets,
                       Inches(0.6), Inches(1.65), Inches(5.8), Inches(4.0),
                       font_size=15, line_spacing_pt=24)

    # Right
    add_rect(slide, Inches(7.0), Inches(1.1), Inches(0.08), Inches(0.45), STEEL_BLUE)
    add_textbox(slide, "Why this matters",
                Inches(7.2), Inches(1.05), Inches(5.8), Inches(0.5),
                font_size=16, bold=True, color=NAVY)
    right_bullets = [
        "Managers can download the full log as a CSV at any time",
        "Green / Yellow / Red counts give a quick read on estimator patterns",
        "Override reason codes reveal where the benchmark may need adjustment",
        "This log is the raw material for retraining the model as the company's business evolves",
    ]
    add_bullet_textbox(slide, right_bullets,
                       Inches(7.2), Inches(1.65), Inches(5.8), Inches(4.0),
                       font_size=15, line_spacing_pt=24)

    add_rect(slide, Inches(6.6), Inches(1.1), Inches(0.04), Inches(5.5), BORDER_GRAY)
    return slide


def slide_servicetitan(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "Coming Soon: ServiceTitan Integration")
    add_footer(slide)

    # TODAY box
    add_rect(slide, Inches(0.4), Inches(1.3), Inches(5.8), Inches(4.5),
             LIGHT_GRAY, line=BORDER_GRAY, line_width_pt=1.2)
    add_rect(slide, Inches(0.4), Inches(1.3), Inches(5.8), Inches(0.55), BORDER_GRAY)
    add_textbox(slide, "TODAY",
                Inches(0.5), Inches(1.33), Inches(5.6), Inches(0.5),
                font_size=15, bold=True, color=DARK_GRAY, align=PP_ALIGN.CENTER)
    add_textbox(slide,
                "Estimators enter job details manually into the dashboard form.",
                Inches(0.6), Inches(2.05), Inches(5.4), Inches(3.5),
                font_size=15, color=DARK_GRAY, wrap=True)

    # AFTER box
    add_rect(slide, Inches(6.9), Inches(1.3), Inches(6.0), Inches(4.5),
             LIGHT_BLUE, line=STEEL_BLUE, line_width_pt=1.5)
    add_rect(slide, Inches(6.9), Inches(1.3), Inches(6.0), Inches(0.55), STEEL_BLUE)
    add_textbox(slide, "AFTER SERVICETITAN INTEGRATION",
                Inches(7.0), Inches(1.33), Inches(5.8), Inches(0.5),
                font_size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    after_bullets = [
        "Dashboard auto-fills from your open ServiceTitan estimate — no double entry",
        "Flag result, benchmark price, and reason code write back to the estimate automatically",
        "Full audit trail lives inside ServiceTitan",
    ]
    add_bullet_textbox(slide, after_bullets,
                       Inches(7.1), Inches(2.05), Inches(5.6), Inches(3.5),
                       font_size=15, line_spacing_pt=26)

    # Arrow between boxes
    add_textbox(slide, "→",
                Inches(6.35), Inches(2.8), Inches(0.55), Inches(0.6),
                font_size=28, bold=True, color=STEEL_BLUE, align=PP_ALIGN.CENTER)

    # Footer note
    add_rect(slide, Inches(0.4), Inches(6.1), Inches(12.5), Inches(0.75),
             YELLOW_LIGHT, line=YELLOW_CLR, line_width_pt=1.0)
    add_textbox(slide,
                "What's needed: ServiceTitan API credentials (Client ID, Secret, Tenant ID)"
                " — provided by your ServiceTitan account team.  Setup time: 1–2 days.",
                Inches(0.6), Inches(6.15), Inches(12.1), Inches(0.6),
                font_size=13, color=DARK_GRAY, wrap=True)
    return slide


def slide_qa(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "Questions You Might Have")
    add_footer(slide)

    qa = [
        ("Does this replace estimator judgment?",
         "No. It gives estimators a benchmark, not a mandate. Every bid can be overridden "
         "with a reason code — the tool supports decisions, it doesn't make them."),
        ("What if the model is wrong?",
         "The model confidence indicator tells you when to be cautious. Every override is "
         "logged with a reason, which feeds future accuracy improvements."),
        ("How much time does this add per bid?",
         "About 2 minutes for manual entry. Once ServiceTitan is connected, the form "
         "pre-fills automatically."),
        ("Who can see the decision log?",
         "Anyone with dashboard access. The full log exports to CSV for management "
         "review at any time."),
    ]

    positions = [
        (Inches(0.4),  Inches(1.2)),
        (Inches(6.85), Inches(1.2)),
        (Inches(0.4),  Inches(4.2)),
        (Inches(6.85), Inches(4.2)),
    ]
    box_w = Inches(6.0)
    box_h = Inches(2.7)

    for (q, a), (left, top) in zip(qa, positions):
        add_rect(slide, left, top, box_w, box_h,
                 LIGHT_BLUE, line=STEEL_BLUE, line_width_pt=1.2)
        add_textbox(slide, f"Q:  {q}",
                    left + Inches(0.2), top + Inches(0.15),
                    box_w - Inches(0.4), Inches(0.65),
                    font_size=14, bold=True, color=NAVY, wrap=True)
        add_textbox(slide, a,
                    left + Inches(0.2), top + Inches(0.85),
                    box_w - Inches(0.4), Inches(1.7),
                    font_size=13, color=DARK_GRAY, wrap=True)
    return slide


def slide_next_steps(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "Recommended Next Steps")
    add_footer(slide)

    steps = [
        ("1", "Deploy the dashboard",
         "On the company's infrastructure or a cloud server  (~1 day)"),
        ("2", "Connect ServiceTitan",
         "Provide API credentials — 1–2 days of setup"),
        ("3", "Estimator training",
         "30-minute session, can be done over Zoom"),
        ("4", "Monthly model retraining",
         "As the decision log grows, accuracy improves"),
        ("5", "Expand to a second division",
         "A separate model has already been trained"),
    ]

    for i, (num, title, detail) in enumerate(steps):
        top = Inches(1.2) + i * Inches(1.1)
        # Number box
        add_rect(slide, Inches(0.4), top, Inches(0.55), Inches(0.75), NAVY)
        add_textbox(slide, num,
                    Inches(0.4), top + Inches(0.1),
                    Inches(0.55), Inches(0.55),
                    font_size=18, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        # Content
        add_textbox(slide, title,
                    Inches(1.1), top + Inches(0.05),
                    Inches(5.5), Inches(0.45),
                    font_size=16, bold=True, color=NAVY)
        add_textbox(slide, detail,
                    Inches(1.1), top + Inches(0.42),
                    Inches(11.5), Inches(0.45),
                    font_size=14, color=MED_GRAY)
        # Divider line
        if i < len(steps) - 1:
            add_rect(slide, Inches(0.4), top + Inches(0.85), Inches(12.5), Inches(0.02), BORDER_GRAY)
    return slide


def slide_needs(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "What We Need From the Client to Move Forward")
    add_footer(slide)

    items = [
        ("ServiceTitan API Credentials",
         "Client ID, Client Secret, and Tenant ID from your ServiceTitan developer portal.",
         LIGHT_BLUE, STEEL_BLUE),
        ("Estimator Training Session",
         "30 minutes — can be done over Zoom. We walk through the dashboard live with your team.",
         GREEN_LIGHT, GREEN),
        ("Monthly Data Pull (short-term)",
         "A monthly jobs export from ServiceTitan until the live API integration is complete.",
         YELLOW_LIGHT, YELLOW_CLR),
    ]

    box_w = Inches(3.9)
    box_h = Inches(4.0)
    top   = Inches(1.6)
    lefts = [Inches(0.4), Inches(4.7), Inches(9.0)]

    for (title, body, bg, border), left in zip(items, lefts):
        add_rect(slide, left, top, box_w, box_h, bg, line=border, line_width_pt=1.5)
        add_rect(slide, left, top, box_w, Inches(0.6), border)
        add_textbox(slide, title,
                    left + Inches(0.1), top + Inches(0.08),
                    box_w - Inches(0.2), Inches(0.5),
                    font_size=15, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        add_textbox(slide, body,
                    left + Inches(0.2), top + Inches(0.85),
                    box_w - Inches(0.4), Inches(2.9),
                    font_size=15, color=DARK_GRAY, wrap=True)
    return slide


def slide_appendix_divider(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, W, H, NAVY)
    add_rect(slide, Inches(0.5), Inches(2.9), Inches(0.12), Inches(1.6), STEEL_BLUE)
    add_textbox(slide, "Appendix",
                Inches(0.8), Inches(2.7), Inches(11), Inches(1.3),
                font_size=52, bold=True, color=WHITE)
    add_textbox(slide, "Technical Reference",
                Inches(0.8), Inches(4.1), Inches(11), Inches(0.7),
                font_size=22, color=LIGHT_BLUE)
    add_textbox(slide, "Chicago Booth Lab  ·  Team 4  ·  May 2026",
                Inches(0.8), Inches(6.8), Inches(11.5), Inches(0.4),
                font_size=13, color=LIGHT_BLUE, align=PP_ALIGN.RIGHT)
    return slide


def _add_simple_table(slide, left, top, width, headers, rows,
                      col_widths=None, header_bg=NAVY, row_bg=WHITE,
                      alt_bg=LIGHT_GRAY, font_size=12):
    """Build a table using pptx's native table shape."""
    num_cols = len(headers)
    num_rows = len(rows) + 1  # +1 for header
    row_h = Inches(0.38)
    total_h = row_h * num_rows

    tbl = slide.shapes.add_table(num_rows, num_cols, left, top, width, total_h).table
    tbl.first_row = True

    if col_widths:
        for i, cw in enumerate(col_widths):
            tbl.columns[i].width = cw
    else:
        each = width // num_cols
        for i in range(num_cols):
            tbl.columns[i].width = each

    def set_cell(cell, text, bg, bold=False, color=WHITE):
        cell.text = text
        cell.fill.solid()
        cell.fill.fore_color.rgb = bg
        for para in cell.text_frame.paragraphs:
            para.alignment = PP_ALIGN.LEFT
            for run in para.runs:
                run.font.size = Pt(font_size)
                run.font.bold = bold
                run.font.color.rgb = color
        cell.margin_left = Inches(0.1)
        cell.margin_top = Inches(0.03)

    for j, h in enumerate(headers):
        set_cell(tbl.cell(0, j), h, header_bg, bold=True, color=WHITE)

    for i, row in enumerate(rows):
        bg = alt_bg if i % 2 == 1 else row_bg
        for j, val in enumerate(row):
            set_cell(tbl.cell(i + 1, j), val, bg, color=DARK_GRAY)

    return tbl


def slide_a1_architecture(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "Technical Architecture", "app/ directory structure and supporting files")
    add_footer(slide)

    headers = ["Component", "Responsibility"]
    rows = [
        ["app.py",           "Streamlit UI — Bid Check tab (flag + benchmark) + Decision History tab"],
        ["flag_logic.py",    "Benchmark math and Green/Yellow/Red threshold logic (all tunable constants)"],
        ["feedback.py",      "Appends one row per decision to data/feedback_log.csv"],
        ["servicetitan.py",  "ServiceTitan API integration stub (disabled until credentials provided)"],
        ["train_models.py",  "Training pipeline for Model A and Model B from Excel data"],
        ["models/",          "model_a.pkl, model_b.pkl, encoders.pkl — generated by train_models.py"],
    ]
    col_widths = [Inches(2.4), Inches(10.1)]
    _add_simple_table(slide,
                      Inches(0.4), Inches(1.1),
                      Inches(12.5), headers, rows,
                      col_widths=col_widths, font_size=13)

    add_textbox(slide,
                "Stack:  Python 3.11  ·  Streamlit  ·  XGBoost  ·  scikit-learn  ·  pandas  ·  joblib",
                Inches(0.4), Inches(5.8), Inches(12.5), Inches(0.4),
                font_size=13, bold=True, color=STEEL_BLUE)
    return slide


def slide_a2_model_a(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "Model A — Revenue Consistency Model",
                   "Predicts actual billed revenue from cost inputs (secondary reference)")
    add_footer(slide)

    # Left
    add_rect(slide, Inches(0.4), Inches(1.1), Inches(0.08), Inches(0.4), STEEL_BLUE)
    add_textbox(slide, "What it predicts",
                Inches(0.6), Inches(1.05), Inches(6.0), Inches(0.45),
                font_size=15, bold=True, color=NAVY)
    add_textbox(slide,
                "Target variable: Jobs Subtotal (actual billed revenue)\n"
                "Uses information known only after costs are entered.",
                Inches(0.6), Inches(1.6), Inches(6.0), Inches(0.9),
                font_size=14, color=DARK_GRAY, wrap=True)

    add_rect(slide, Inches(0.4), Inches(2.65), Inches(0.08), Inches(0.4), STEEL_BLUE)
    add_textbox(slide, "Features",
                Inches(0.6), Inches(2.6), Inches(6.0), Inches(0.45),
                font_size=15, bold=True, color=NAVY)
    feature_lines = [
        "total_labor, Material Costs, PO/Bill Costs, Jobs Total Costs",
        "labor_cost_share, material_cost_share, po_cost_share",
        "labor_to_material, log_total_cost",
        "Job Type (encoded), Property Type (encoded)",
        "job_month, job_quarter",
    ]
    add_bullet_textbox(slide, feature_lines,
                       Inches(0.6), Inches(3.15), Inches(6.0), Inches(3.5),
                       font_size=13, line_spacing_pt=21)

    # Right
    add_rect(slide, Inches(7.0), Inches(1.1), Inches(0.08), Inches(0.4), STEEL_BLUE)
    add_textbox(slide, "Algorithm",
                Inches(7.2), Inches(1.05), Inches(5.9), Inches(0.45),
                font_size=15, bold=True, color=NAVY)
    algo_lines = [
        "XGBoost Regressor",
        "max_depth=4  ·  n_estimators=300",
        "learning_rate=0.04  ·  subsample=0.9",
        "colsample_bytree=0.9  ·  min_child_weight=3",
    ]
    add_bullet_textbox(slide, algo_lines,
                       Inches(7.2), Inches(1.6), Inches(5.9), Inches(1.8),
                       font_size=13, line_spacing_pt=21)

    add_rect(slide, Inches(7.0), Inches(3.6), Inches(0.08), Inches(0.4), STEEL_BLUE)
    add_textbox(slide, "Use in app",
                Inches(7.2), Inches(3.55), Inches(5.9), Inches(0.45),
                font_size=15, bold=True, color=NAVY)
    add_textbox(slide,
                "Secondary reference — shown as: \"for these costs, history suggests $X\".\n"
                "Not the primary flag driver. Helps catch cost-entry errors.",
                Inches(7.2), Inches(4.1), Inches(5.9), Inches(1.5),
                font_size=14, color=DARK_GRAY, wrap=True)

    add_rect(slide, Inches(6.6), Inches(1.1), Inches(0.04), Inches(5.5), BORDER_GRAY)
    return slide


def slide_a3_model_b(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "Model B — Bid-Time Margin Prediction",
                   "Primary benchmark driver — predicts expected GP% using only pre-job information")
    add_footer(slide)

    # Left
    add_rect(slide, Inches(0.4), Inches(1.1), Inches(0.08), Inches(0.4), STEEL_BLUE)
    add_textbox(slide, "What it predicts",
                Inches(0.6), Inches(1.05), Inches(6.0), Inches(0.45),
                font_size=15, bold=True, color=NAVY)
    add_textbox(slide,
                "Target variable: Jobs Gross Margin % (historical GP%)\n"
                "Uses only information available at bid time.",
                Inches(0.6), Inches(1.6), Inches(6.0), Inches(0.9),
                font_size=14, color=DARK_GRAY, wrap=True)

    add_rect(slide, Inches(0.4), Inches(2.65), Inches(0.08), Inches(0.4), STEEL_BLUE)
    add_textbox(slide, "Features",
                Inches(0.6), Inches(2.6), Inches(6.0), Inches(0.45),
                font_size=15, bold=True, color=NAVY)
    feature_lines = [
        "Jobs Estimate Sales Subtotal (proposed quote)",
        "log_estimate (log-transformed quote)",
        "Job Type (encoded)",
        "Property Type (encoded)",
        "job_month, job_quarter",
    ]
    add_bullet_textbox(slide, feature_lines,
                       Inches(0.6), Inches(3.15), Inches(6.0), Inches(3.0),
                       font_size=13, line_spacing_pt=21)

    # Right
    add_rect(slide, Inches(7.0), Inches(1.1), Inches(0.08), Inches(0.4), STEEL_BLUE)
    add_textbox(slide, "Algorithm",
                Inches(7.2), Inches(1.05), Inches(5.9), Inches(0.45),
                font_size=15, bold=True, color=NAVY)
    algo_lines = [
        "XGBoost Regressor",
        "max_depth=3  ·  n_estimators=200",
        "learning_rate=0.06  ·  subsample=0.9",
        "min_child_weight=10  ·  reg_alpha=1.0  ·  reg_lambda=1.0",
    ]
    add_bullet_textbox(slide, algo_lines,
                       Inches(7.2), Inches(1.6), Inches(5.9), Inches(1.8),
                       font_size=13, line_spacing_pt=21)

    add_rect(slide, Inches(7.0), Inches(3.6), Inches(0.08), Inches(0.4), STEEL_BLUE)
    add_textbox(slide, "Why fewer features than Model A",
                Inches(7.2), Inches(3.55), Inches(5.9), Inches(0.45),
                font_size=15, bold=True, color=NAVY)
    add_textbox(slide,
                "Model B only uses information known before the job starts — it cannot "
                "see actual labor and material costs at bid time. This deliberate constraint "
                "makes it a genuine bid-time decision aid rather than a post-hoc analysis.",
                Inches(7.2), Inches(4.1), Inches(5.9), Inches(2.0),
                font_size=14, color=DARK_GRAY, wrap=True)

    add_rect(slide, Inches(6.6), Inches(1.1), Inches(0.04), Inches(5.5), BORDER_GRAY)
    return slide


def slide_a4_flag_logic(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "Flag Logic & Thresholds",
                   "All constants are named variables in flag_logic.py — tune without touching app.py")
    add_footer(slide)

    # Formulas box
    add_rect(slide, Inches(0.4), Inches(1.1), Inches(5.8), Inches(2.8),
             LIGHT_BLUE, line=STEEL_BLUE, line_width_pt=1.2)
    add_textbox(slide, "Formulas",
                Inches(0.6), Inches(1.15), Inches(5.4), Inches(0.4),
                font_size=14, bold=True, color=NAVY)
    formulas = [
        "Benchmark price  =  total_cost ÷ (1 − predicted_GP%)",
        "Range low        =  benchmark × 0.90",
        "Range high       =  benchmark × 1.10",
        "Deviation        =  (quote − nearest range boundary) ÷ range boundary",
    ]
    add_multiline_textbox(slide, formulas,
                          Inches(0.6), Inches(1.65), Inches(5.4), Inches(2.0),
                          font_size=13, color=DARK_GRAY, line_spacing_pt=20)

    # Threshold table
    headers = ["Condition", "Flag"]
    rows = [
        ["Deviation = 0   AND   margin ≥ 50%",                         "GREEN"],
        ["Deviation 0–20% outside range   OR   margin 40–50%",         "YELLOW"],
        ["Deviation > 20% outside range   OR   margin < 40%",          "RED"],
    ]
    col_widths = [Inches(9.2), Inches(1.8)]
    _add_simple_table(slide,
                      Inches(0.4), Inches(4.1),
                      Inches(11.0), headers, rows,
                      col_widths=col_widths, font_size=13)

    # Note
    add_textbox(slide,
                "Red always wins over Yellow — the stricter flag applies.",
                Inches(0.4), Inches(6.0), Inches(12.0), Inches(0.4),
                font_size=13, italic=True, color=MED_GRAY)
    return slide


def slide_a5_confidence(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "Model Confidence Levels",
                   "Based on historical job-type sample count in the training data")
    add_footer(slide)

    headers = ["Label", "Criteria", "What It Means in Practice"]
    rows = [
        ["High",   "≥ 60 historical jobs of this type",
         "Model has seen enough examples — treat benchmark as reliable"],
        ["Medium", "25–59 historical jobs",
         "Reasonable signal — use alongside estimator judgment"],
        ["Low",    "< 25 historical jobs",
         "Few examples — model is extrapolating; treat as a soft reference only"],
    ]
    col_widths = [Inches(1.5), Inches(3.5), Inches(7.0)]
    _add_simple_table(slide,
                      Inches(0.4), Inches(1.2),
                      Inches(12.0), headers, rows,
                      col_widths=col_widths, font_size=14)

    add_textbox(slide,
                "Confidence improves automatically as more company jobs are logged and the model is retrained monthly.",
                Inches(0.4), Inches(4.2), Inches(12.5), Inches(0.5),
                font_size=14, italic=True, color=MED_GRAY)
    return slide


def slide_a6_feedback(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "Feedback Loop Design",
                   "feedback_log.csv — one row per estimator decision")
    add_footer(slide)

    headers = ["Field", "Description"]
    rows = [
        ["timestamp",                              "ISO timestamp of the decision"],
        ["job_type  /  property_type",             "Job classification inputs"],
        ["quote  /  total_cost",                   "Estimator's numbers entered in the form"],
        ["benchmark_price  /  range_low  /  range_high", "Model output — benchmark and acceptable band"],
        ["deviation_pct  /  expected_margin_pct",  "Computed risk metrics"],
        ["flag_status",                            "green / yellow / red"],
        ["reason_code  /  notes",                  "Override justification selected by the estimator"],
        ["manager_approved",                       "Boolean — required for Red flags"],
        ["servicetitan_job_id",                    "Link to the ServiceTitan estimate record"],
    ]
    col_widths = [Inches(4.0), Inches(8.2)]
    _add_simple_table(slide,
                      Inches(0.4), Inches(1.1),
                      Inches(12.2), headers, rows,
                      col_widths=col_widths, font_size=12)

    add_textbox(slide,
                "Retraining trigger: merge new actuals with logged decisions monthly. "
                "Reason code patterns reveal where benchmark thresholds need tuning.",
                Inches(0.4), Inches(6.15), Inches(12.5), Inches(0.5),
                font_size=13, italic=True, color=MED_GRAY)
    return slide


def slide_a7_servicetitan(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "ServiceTitan Integration Plan",
                   "servicetitan.py — flip SERVICETITAN_ENABLED = True once credentials are available")
    add_footer(slide)

    headers = ["Step", "Endpoint", "Purpose"]
    rows = [
        ["Auth",  "POST  https://auth.servicetitan.io/connect/token",
         "OAuth2 client_credentials flow → short-lived bearer token"],
        ["Fetch", "GET  /jpm/v2/tenant/{tenant_id}/jobs/{job_id}",
         "Pull job type, costs, estimate amount to pre-fill the dashboard form"],
        ["Push",  "PATCH  /jpm/v2/tenant/{tenant_id}/jobs/{job_id}",
         "Write flag status, benchmark price, and reason code as custom fields on the estimate"],
    ]
    col_widths = [Inches(1.0), Inches(5.8), Inches(5.4)]
    _add_simple_table(slide,
                      Inches(0.4), Inches(1.2),
                      Inches(12.2), headers, rows,
                      col_widths=col_widths, font_size=13)

    add_rect(slide, Inches(0.4), Inches(4.3), Inches(12.2), Inches(1.4),
             LIGHT_BLUE, line=STEEL_BLUE, line_width_pt=1.0)
    add_textbox(slide, "Environment variables required:",
                Inches(0.6), Inches(4.38), Inches(4.0), Inches(0.4),
                font_size=13, bold=True, color=NAVY)
    add_textbox(slide,
                "SERVICETITAN_CLIENT_ID    ·    SERVICETITAN_CLIENT_SECRET    ·    SERVICETITAN_TENANT_ID",
                Inches(0.6), Inches(4.82), Inches(12.0), Inches(0.55),
                font_size=13, color=DARK_GRAY)

    add_textbox(slide,
                "All integration logic is already stubbed in servicetitan.py — "
                "implement the two TODOs and set SERVICETITAN_ENABLED = True to activate.",
                Inches(0.4), Inches(5.9), Inches(12.5), Inches(0.55),
                font_size=13, italic=True, color=MED_GRAY)
    return slide


def slide_a8_deployment(prs):
    slide = blank_slide(prs)
    add_header_bar(slide, "Deployment Requirements")
    add_footer(slide)

    headers = ["Item", "Detail"]
    rows = [
        ["Python version",       "3.11+"],
        ["Dependencies",         "pip install streamlit xgboost scikit-learn pandas numpy joblib openpyxl"],
        ["One-time model setup", "python train_models.py  (generates the models/ directory)"],
        ["Launch command",       "streamlit run app/app.py"],
        ["Deployment options",   "Streamlit Community Cloud (free tier)  ·  Docker container  ·  Internal Linux server"],
        ["Data persistence",     "feedback_log.csv written to data/  —  back up periodically"],
        ["No database needed",   "All state is CSV-based for this prototype version"],
    ]
    col_widths = [Inches(2.8), Inches(9.7)]
    _add_simple_table(slide,
                      Inches(0.4), Inches(1.1),
                      Inches(12.5), headers, rows,
                      col_widths=col_widths, font_size=13)
    return slide


# ── Main ──────────────────────────────────────────────────────────────────────

def build():
    prs = new_prs()

    # Main deck
    slide_title(prs)           # 1
    slide_problem(prs)         # 2
    slide_solution(prs)        # 3
    slide_howto(prs)           # 4
    slide_flags(prs)           # 5
    slide_model_inputs(prs)    # 6
    slide_benchmark(prs)       # 7
    slide_history(prs)         # 8
    slide_servicetitan(prs)    # 9
    slide_qa(prs)              # 10
    slide_next_steps(prs)      # 11
    slide_needs(prs)           # 12

    # Appendix
    slide_appendix_divider(prs)  # A0
    slide_a1_architecture(prs)   # A1
    slide_a2_model_a(prs)        # A2
    slide_a3_model_b(prs)        # A3
    slide_a4_flag_logic(prs)     # A4
    slide_a5_confidence(prs)     # A5
    slide_a6_feedback(prs)       # A6
    slide_a7_servicetitan(prs)   # A7
    slide_a8_deployment(prs)     # A8

    prs.save(OUTPUT)
    print(f"Saved: {OUTPUT}  ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build()

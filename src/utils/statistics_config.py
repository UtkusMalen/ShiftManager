from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATE_PATH = ASSETS_DIR / "statistics_template.png"
FONT_REGULAR_PATH = ASSETS_DIR / "fonts" / "Montserrat-Regular.ttf"
FONT_BOLD_PATH = ASSETS_DIR / "fonts" / "Montserrat-Bold.ttf"

COLOR_WHITE = (255, 255, 255)
COLOR_TITLE_BLUE_BG = COLOR_WHITE
COLOR_HEADER_BLACK = (0, 0, 0)
COLOR_HEADER_RED = (194, 53, 48)
COLOR_HEADER_GREEN = (66, 152, 69)
COLOR_TEXT_BLACK = (51, 51, 51)
COLOR_LABEL_GREY = (102, 102, 102)
COLOR_PROJECTION_WHITE = COLOR_WHITE

TAX_RATE = 0.05

PROJECTION_CONFIG = {
    "proj1": {"hours": 160, "text_key": "statistics.image.projection.schedule_5_2_8"},
    "proj2": {"hours": 180, "text_key": "statistics.image.projection.schedule_2_2_12"},
    "proj3": {"hours": 252, "text_key": "statistics.image.projection.schedule_3_1_12"},
    "proj4": {"hours": 336, "text_key": "statistics.image.projection.schedule_7_0_12"},
}

IMAGE_ELEMENT_STYLES = {
    "period_title":        {"pos": (580, 250), "font_type": "bold", "size": 35, "color": COLOR_TITLE_BLUE_BG, "anchor": "ma",
                            "text_key_all_time": "statistics.image.period_title_format_all_time",
                            "text_key_date_range": "statistics.image.period_title_format_date_range",
                            "text_key_to_date": "statistics.image.period_title_format_to_date",
                            "max_width_chars": 25,
                            "line_spacing": 4},

    # Block 1: ВРЕМЯ И СМЕНЫ
    "time_shifts_header":  {"text_key": "statistics.image.headers.time_shifts", "pos": (300, 450), "font_type": "bold", "size": 35, "color": COLOR_HEADER_BLACK, "anchor": "ms"},
    "total_shifts_label":  {"text_key": "statistics.image.labels.total", "pos": (100, 520), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "total_shifts_value":  {"pos": (230, 520), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},
    "total_hours_label":   {"text_key": "statistics.image.labels.total_hours", "pos": (100, 580), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "total_hours_value":   {"pos": (340, 580), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},
    "avg_hours_label":     {"text_key": "statistics.image.labels.avg_hours_in_shifts", "pos": (100, 640), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "avg_hours_value":     {"pos": (400, 640), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},

    # Block 2: ЗАКАЗЫ
    "orders_header":       {"text_key": "statistics.image.headers.orders", "pos": (850, 450), "font_type": "bold", "size": 36, "color": COLOR_HEADER_BLACK, "anchor": "ms"},
    "total_orders_label":  {"text_key": "statistics.image.labels.total", "pos": (650, 520), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "total_orders_value":  {"pos": (780, 520), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},
    "orders_speed_label":  {"text_key": "statistics.image.labels.orders_speed", "pos": (650, 580), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "orders_speed_value":  {"pos": (840, 580), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},
    "mileage_order_label": {"text_key": "statistics.image.labels.mileage_per_order", "pos": (650, 640), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "mileage_order_value": {"pos": (810, 640), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},

    # Block 3: ТРАТЫ
    "expenses_header":     {"text_key": "statistics.image.headers.expenses", "pos": (300, 820), "font_type": "bold", "size": 36, "color": COLOR_HEADER_RED, "anchor": "ms"},
    "total_exp_label":     {"text_key": "statistics.image.labels.total", "pos": (100, 900), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "total_exp_value":     {"pos": (225, 900), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},
    "food_exp_label":      {"text_key": "statistics.image.labels.food", "pos": (100, 960), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "food_exp_value":      {"pos": (185, 960), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},
    "tax_exp_label":       {"text_key": "statistics.image.labels.tax", "pos": (100, 1020), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "tax_exp_value":       {"pos": (235, 1020), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},
    "mileage_exp_label":   {"text_key": "statistics.image.labels.mileage_cost", "pos": (100, 1080), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "mileage_exp_value":   {"pos": (255, 1080), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},
    "other_exp_label":     {"text_key": "statistics.image.labels.other", "pos": (100, 1140), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "other_exp_value":     {"pos": (255, 1140), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},

    # Block 4: ВЫРУЧКА
    "revenue_header":      {"text_key": "statistics.image.headers.revenue", "pos": (850, 820), "font_type": "bold", "size": 36, "color": COLOR_HEADER_GREEN, "anchor": "ms"},
    "total_rev_label":     {"text_key": "statistics.image.labels.total", "pos": (650, 900), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "total_rev_value":     {"pos": (775, 900), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},
    "hours_rev_label":     {"text_key": "statistics.image.labels.hours_revenue", "pos": (650, 960), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "hours_rev_value":     {"pos": (760, 960), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},
    "orders_rev_label":    {"text_key": "statistics.image.labels.orders_revenue", "pos": (650, 1020), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "orders_rev_value":    {"pos": (795, 1020), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},
    "tips_rev_label":      {"text_key": "statistics.image.labels.tips_revenue", "pos": (650, 1080), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "tips_rev_value":      {"pos": (805, 1080), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},

    # Block 5: ПРИБЫЛЬ
    "profit_header":       {"text_key": "statistics.image.headers.profit", "pos": (560, 1320), "font_type": "bold", "size": 36, "color": COLOR_HEADER_GREEN, "anchor": "ms"},
    "total_profit_label":  {"text_key": "statistics.image.labels.total", "pos": (100, 1400), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "total_profit_value":  {"pos": (225, 1400), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},
    "profit_hr_label":     {"text_key": "statistics.image.labels.profit_per_hour", "pos": (100, 1460), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "profit_hr_value":     {"pos": (215, 1460), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},
    "profit_km_label":     {"text_key": "statistics.image.labels.profit_per_km", "pos": (580, 1400), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "profit_km_value":     {"pos": (860, 1400), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},
    "profit_order_label":  {"text_key": "statistics.image.labels.profit_per_order", "pos": (580, 1460), "font_type": "regular", "size": 35, "color": COLOR_LABEL_GREY, "anchor": "ls"},
    "profit_order_value":  {"pos": (750, 1460), "font_type": "bold", "size": 35, "color": COLOR_TEXT_BLACK, "anchor": "ls"},

    # Block 6: Расчётный доход
    "projection_title":    {"text_key": "statistics.image.projection.title", "pos": (580, 1570), "font_type": "bold", "size": 36, "color": COLOR_PROJECTION_WHITE, "anchor": "ms"},
    "proj1_label":         {"pos": (170, 1650), "font_type": "bold", "size": 36, "color": COLOR_PROJECTION_WHITE, "anchor": "ls"},
    "proj1_hours":         {"pos": (546, 1650), "font_type": "regular", "size": 36, "color": COLOR_PROJECTION_WHITE, "anchor": "ls"},
    "proj1_income_val":    {"pos": (800, 1650), "font_type": "regular", "size": 36, "color": COLOR_PROJECTION_WHITE, "anchor": "ls"},
    "proj2_label":         {"pos": (170, 1690), "font_type": "bold", "size": 36, "color": COLOR_PROJECTION_WHITE, "anchor": "ls"},
    "proj2_hours":         {"pos": (547, 1690), "font_type": "regular", "size": 36, "color": COLOR_PROJECTION_WHITE, "anchor": "ls"},
    "proj2_income_val":    {"pos": (800, 1690), "font_type": "regular", "size": 36, "color": COLOR_PROJECTION_WHITE, "anchor": "ls"},
    "proj3_label":         {"pos": (170, 1730), "font_type": "bold", "size": 36, "color": COLOR_PROJECTION_WHITE, "anchor": "ls"},
    "proj3_hours":         {"pos": (547, 1730), "font_type": "regular", "size": 36, "color": COLOR_PROJECTION_WHITE, "anchor": "ls"},
    "proj3_income_val":    {"pos": (800, 1730), "font_type": "regular", "size": 36, "color": COLOR_PROJECTION_WHITE, "anchor": "ls"},
    "proj4_label":         {"pos": (170, 1770), "font_type": "bold", "size": 36, "color": COLOR_PROJECTION_WHITE, "anchor": "ls"},
    "proj4_hours":         {"pos": (547, 1770), "font_type": "regular", "size": 36, "color": COLOR_PROJECTION_WHITE, "anchor": "ls"},
    "proj4_income_val":    {"pos": (800, 1770), "font_type": "regular", "size": 36, "color": COLOR_PROJECTION_WHITE, "anchor": "ls"},

    "footer_text":         {"text_key": "statistics.image.footer", "pos": (570, 1900), "font_type": "regular", "size": 40, "color": COLOR_PROJECTION_WHITE, "anchor": "ma", "max_width_chars": 20, "line_spacing": 4}
}
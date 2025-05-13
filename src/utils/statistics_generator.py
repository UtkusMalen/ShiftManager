import asyncio
import logging
from io import BytesIO
from typing import List, Dict

from PIL import Image, ImageDraw, ImageFont
from zoneinfo import ZoneInfo

from src.db.models import Shift, ShiftEventType
from src.utils.text_manager import text_manager as tm

logger = logging.getLogger(__name__)
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

IMG_WIDTH = 800
BACKGROUND_COLOR = (240, 240, 245)
TEXT_COLOR = (50, 50, 50)
ACCENT_COLOR = (70, 130, 180)
PROFIT_COLOR = (34, 139, 34)
EXPENSE_COLOR = (220, 20, 60)
LINE_COLOR = (200, 200, 200)

DEFAULT_ROW_HEIGHT = 30
PADDING_Y = 15
SECTION_PADDING_Y = 25
INITIAL_Y_OFFSET = 40
BOTTOM_PADDING = 40

try:
    FONT_REGULAR_PATH = "src/assets/fonts/DejaVuSans.ttf"
    FONT_BOLD_PATH = "src/assets/fonts/DejaVuSans-Bold.ttf"
    FONT_REGULAR = ImageFont.truetype(FONT_REGULAR_PATH, 24)
    FONT_BOLD = ImageFont.truetype(FONT_BOLD_PATH, 28)
    FONT_SMALL = ImageFont.truetype(FONT_REGULAR_PATH, 20)
    FONT_TITLE = ImageFont.truetype(FONT_BOLD_PATH, 36)
except IOError:
    logger.error("Failed to load fonts. Ensure DejaVuSans.ttf and DejaVuSans-Bold.ttf are in src/assets/fonts/")
    FONT_REGULAR = ImageFont.load_default()
    FONT_BOLD = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()
    FONT_TITLE = ImageFont.load_default()


def format_duration_for_stats(total_seconds: float) -> str:
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f"{hours} {tm.get('statistics.img_h', 'ч.')} {minutes:02d} мин."


def get_text_height(text: str, font: ImageFont.FreeTypeFont) -> int:
    if hasattr(font, "getbbox"):
        return font.getbbox(text)[3] - font.getbbox(text)[1]
    elif hasattr(font, "getsize"):
        return font.getsize(text)[1]
    return DEFAULT_ROW_HEIGHT


def draw_text_with_colon(draw: ImageDraw.Draw, y_pos: int, label: str, value: str,
                         x_value: int,
                         label_font=FONT_REGULAR, value_font=FONT_BOLD, value_color=TEXT_COLOR,
                         left_text_margin: int = 50):
    draw.text((left_text_margin, y_pos), f"{label}:", font=label_font, fill=TEXT_COLOR)
    draw.text((x_value, y_pos), str(value), font=value_font, fill=value_color)

    label_height = get_text_height(label, label_font)
    value_height = get_text_height(str(value), value_font)
    max_text_height_in_row = max(label_height if label_height is not None else 0,
                                 value_height if value_height is not None else 0,
                                 DEFAULT_ROW_HEIGHT)
    return y_pos + max_text_height_in_row + PADDING_Y


def _generate_image_sync(shifts: List[Shift], period_name: str) -> BytesIO | None:
    if not shifts:
        return None

    total_revenue_from_time = 0.0
    total_revenue_from_orders = 0.0
    total_tips = 0.0
    total_orders_completed = 0
    total_duration_seconds = 0.0
    total_mileage = 0.0
    total_mileage_cost = 0.0

    manual_expenses_by_category: Dict[str, float] = {
        "food": 0.0,
        "other": 0.0,
    }
    total_manual_expenses = 0.0

    for shift in shifts:
        if not shift.start_time or not shift.end_time:
            continue
        duration = (shift.end_time - shift.start_time).total_seconds()
        if duration <= 0:
            continue
        total_duration_seconds += duration
        duration_hours = duration / 3600.0
        total_revenue_from_time += duration_hours * (shift.rate or 0.0)
        total_revenue_from_orders += (shift.orders_count or 0) * (shift.order_rate or 0.0)
        total_tips += shift.total_tips or 0.0
        total_orders_completed += shift.orders_count or 0
        total_mileage += shift.total_mileage or 0.0
        total_mileage_cost += (shift.total_mileage or 0.0) * (shift.mileage_rate or 0.0)

        for event in shift.events:
            if event.event_type == ShiftEventType.ADD_EXPENSE and isinstance(event.details, dict):
                amount = event.details.get("amount", 0.0)
                category_code = event.details.get("category_code", "other")
                manual_expenses_by_category[category_code] = manual_expenses_by_category.get(category_code,
                                                                                             0.0) + amount
                total_manual_expenses += amount

    gross_income = total_revenue_from_time + total_revenue_from_orders + total_tips
    total_operational_expenses = total_manual_expenses + total_mileage_cost
    tax_rate_decimal = 0.05
    tax_amount = gross_income * tax_rate_decimal
    net_profit = gross_income - total_operational_expenses - tax_amount
    profit_per_hour = (net_profit / (total_duration_seconds / 3600.0)) if total_duration_seconds > 0 else 0.0
    orders_per_hour = (
                total_orders_completed / (total_duration_seconds / 3600.0)) if total_duration_seconds > 0 else 0.0

    calculated_height = INITIAL_Y_OFFSET
    title_text_height = get_text_height(tm.get('statistics.img_title', "Статистика"), FONT_TITLE)
    calculated_height += title_text_height + SECTION_PADDING_Y
    calculated_height += 3 * (DEFAULT_ROW_HEIGHT + PADDING_Y)
    calculated_height += SECTION_PADDING_Y
    calculated_height += 5 * (DEFAULT_ROW_HEIGHT + PADDING_Y)
    calculated_height += SECTION_PADDING_Y
    calculated_height += (DEFAULT_ROW_HEIGHT + PADDING_Y)
    if manual_expenses_by_category.get("food", 0.0) > 0:
        calculated_height += (DEFAULT_ROW_HEIGHT + PADDING_Y)
    if manual_expenses_by_category.get("other", 0.0) > 0:
        calculated_height += (DEFAULT_ROW_HEIGHT + PADDING_Y)
    calculated_height += (DEFAULT_ROW_HEIGHT + PADDING_Y)
    calculated_height += BOTTOM_PADDING
    final_img_height = max(calculated_height, 600)

    img = Image.new("RGB", (IMG_WIDTH, final_img_height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    current_y = INITIAL_Y_OFFSET
    value_x_offset = 450
    label_left_padding = 50

    title_text = tm.get("statistics.img_title", "Статистика") + f" {period_name}"
    title_bbox = draw.textbbox((0, 0), title_text, font=FONT_TITLE)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    draw.text(((IMG_WIDTH - title_width) / 2, current_y), title_text, font=FONT_TITLE, fill=ACCENT_COLOR)
    current_y += title_height + SECTION_PADDING_Y

    current_y = draw_text_with_colon(draw, current_y, tm.get("statistics.img_total_profit", "Общая прибыль"),
                                     f"{net_profit:.2f} {tm.get('statistics.img_rub', 'руб.')}", value_x_offset,
                                     value_color=PROFIT_COLOR, left_text_margin=label_left_padding)
    current_y = draw_text_with_colon(draw, current_y, tm.get("statistics.img_profit_per_hour", "Прибыль за час"),
                                     f"{profit_per_hour:.2f} {tm.get('statistics.img_rub', 'руб.')}", value_x_offset,
                                     left_text_margin=label_left_padding)
    current_y = draw_text_with_colon(draw, current_y, tm.get('statistics.img_total_revenue', "Выручка"),
                                     f"{gross_income:.2f} {tm.get('statistics.img_rub', 'руб.')}", value_x_offset,
                                     left_text_margin=label_left_padding)

    current_y -= PADDING_Y
    current_y += SECTION_PADDING_Y / 2
    draw.line([(label_left_padding, current_y), (IMG_WIDTH - label_left_padding, current_y)], fill=LINE_COLOR, width=2)
    current_y += SECTION_PADDING_Y / 2

    current_y = draw_text_with_colon(draw, current_y, tm.get('statistics.img_total_duration', "Общее время"),
                                     format_duration_for_stats(total_duration_seconds), value_x_offset,
                                     left_text_margin=label_left_padding)
    current_y = draw_text_with_colon(draw, current_y, tm.get('statistics.img_total_orders', "Всего заказов"),
                                     f"{total_orders_completed} {tm.get('statistics.img_pcs', 'шт.')}", value_x_offset,
                                     left_text_margin=label_left_padding)
    current_y = draw_text_with_colon(draw, current_y, tm.get('statistics.img_orders_per_hour', "Заказов в час"),
                                     f"{orders_per_hour:.2f} {tm.get('statistics.img_pcs', 'шт.')}", value_x_offset,
                                     left_text_margin=label_left_padding)
    current_y = draw_text_with_colon(draw, current_y, tm.get('statistics.img_total_mileage', "Общий пробег"),
                                     f"{total_mileage:.1f} {tm.get('statistics.img_km', 'км')}", value_x_offset,
                                     left_text_margin=label_left_padding)
    current_y = draw_text_with_colon(draw, current_y, tm.get('statistics.img_total_tips', "Чаевые"),
                                     f"{total_tips:.2f} {tm.get('statistics.img_rub', 'руб.')}", value_x_offset,
                                     left_text_margin=label_left_padding)

    current_y -= PADDING_Y
    current_y += SECTION_PADDING_Y / 2
    draw.line([(label_left_padding, current_y), (IMG_WIDTH - label_left_padding, current_y)], fill=LINE_COLOR, width=2)
    current_y += SECTION_PADDING_Y / 2

    current_y = draw_text_with_colon(draw, current_y, tm.get('statistics.img_fuel_costs', "Расходы на топливо"),
                                     f"{total_mileage_cost:.2f} {tm.get('statistics.img_rub', 'руб.')}", value_x_offset,
                                     value_color=EXPENSE_COLOR, left_text_margin=label_left_padding)
    if manual_expenses_by_category.get("food", 0.0) > 0:
        current_y = draw_text_with_colon(draw, current_y, tm.get('statistics.img_food_expenses', "Расходы на еду"),
                                         f"{manual_expenses_by_category['food']:.2f} {tm.get('statistics.img_rub', 'руб.')}",
                                         value_x_offset, value_color=EXPENSE_COLOR, left_text_margin=label_left_padding)
    if manual_expenses_by_category.get("other", 0.0) > 0:
        current_y = draw_text_with_colon(draw, current_y,
                                         tm.get('statistics.img_other_expenses_cat', "Расходы(другое)"),
                                         f"{manual_expenses_by_category['other']:.2f} {tm.get('statistics.img_rub', 'руб.')}",
                                         value_x_offset, value_color=EXPENSE_COLOR, left_text_margin=label_left_padding)

    current_y = draw_text_with_colon(draw, current_y, tm.get('statistics.img_total_tax', "Налог"),
                                     f"{tax_amount:.2f} {tm.get('statistics.img_rub', 'руб.')}", value_x_offset,
                                     value_color=EXPENSE_COLOR, left_text_margin=label_left_padding)

    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    return img_byte_arr


async def generate_statistics_image(shifts: List[Shift], period_name: str) -> BytesIO | None:
    if not shifts:
        logger.info("No shifts data to generate statistics image.")
        return None

    loop = asyncio.get_running_loop()
    try:
        img_byte_arr = await loop.run_in_executor(
            None, _generate_image_sync, shifts, period_name
        )
        return img_byte_arr
    except Exception as e:
        logger.error(f"Error generating statistics image: {e}", exc_info=True)
        return None
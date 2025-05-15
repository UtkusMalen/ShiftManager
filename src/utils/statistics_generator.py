import asyncio
import io
import logging
import textwrap
from typing import List, Optional
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
from zoneinfo import ZoneInfo

from src.db.models import Shift, ShiftEventType, ShiftStatus
from src.utils.text_manager import text_manager as tm
from src.utils.statistics_config import (
    TEMPLATE_PATH, FONT_REGULAR_PATH, FONT_BOLD_PATH,
    IMAGE_ELEMENT_STYLES, PROJECTION_CONFIG, TAX_RATE
)

logger = logging.getLogger(__name__)
MOSCOW_TZ = ZoneInfo('Europe/Moscow')


def format_currency(amount: float) -> str:
    currency_symbol = tm.get("statistics.image.units.currency_symbol", "руб.")
    return f"{int(round(amount)):,} {currency_symbol}".replace(",", " ")


def format_value(value: float, unit_key: Optional[str] = None, precision: int = 0,
                 unit_text_override: Optional[str] = None) -> str:
    unit = ""
    if unit_text_override:
        unit = unit_text_override
    elif unit_key:
        unit = tm.get(unit_key, "")

    if precision == 0:
        formatted_value = f"{int(round(value)):,}".replace(",", " ")
        return f"{formatted_value} {unit}".strip() if unit else formatted_value
    else:
        formatted_value_float = float(value)
        formatted_value = f"{formatted_value_float:,.{precision}f}".replace(",", " ")
        return f"{formatted_value} {unit}".strip() if unit else formatted_value


def get_hour_unit(hours: float) -> str:
    hours_int = int(round(hours))
    if hours_int % 10 == 1 and hours_int % 100 != 11:
        return tm.get("statistics.image.units.hour_nominative", "час")
    elif 2 <= hours_int % 10 <= 4 and (hours_int % 100 < 10 or hours_int % 100 >= 20):
        return tm.get("statistics.image.units.hour_genitive_singular", "часа")
    else:
        return tm.get("statistics.image.units.hour_genitive_plural", "часов")


async def generate_statistics_image(
        shifts: List[Shift],
        period_name_str: str,
        start_date_obj: Optional[datetime],
        end_date_obj: datetime
) -> Optional[io.BytesIO]:
    if not TEMPLATE_PATH.exists():
        logger.error(f"Template image not found at {TEMPLATE_PATH}")
        return None
    if not FONT_REGULAR_PATH.exists() or not FONT_BOLD_PATH.exists():
        logger.error(f"Font files not found. Regular: {FONT_REGULAR_PATH}, Bold: {FONT_BOLD_PATH}")
        return None

    total_shifts_count = 0
    total_duration_seconds = 0.0
    total_orders_completed = 0
    total_mileage_sum = 0.0
    period_gross_income = 0.0
    period_revenue_from_time = 0.0
    period_revenue_from_orders = 0.0
    period_total_tips = 0.0
    period_food_expenses = 0.0
    period_other_expenses = 0.0
    period_mileage_cost = 0.0

    valid_shifts = [s for s in shifts if s.start_time and s.end_time and s.status == ShiftStatus.COMPLETED]
    total_shifts_count = len(valid_shifts)

    for shift in valid_shifts:
        start_local = shift.start_time.astimezone(MOSCOW_TZ) if shift.start_time.tzinfo else shift.start_time.replace(
            tzinfo=MOSCOW_TZ)
        end_local = shift.end_time.astimezone(MOSCOW_TZ) if shift.end_time.tzinfo else shift.end_time.replace(
            tzinfo=MOSCOW_TZ)

        duration_this_shift = (end_local - start_local).total_seconds()
        if duration_this_shift < 0: duration_this_shift = 0
        total_duration_seconds += duration_this_shift
        duration_hours_this_shift = duration_this_shift / 3600.0

        orders_this_shift = shift.orders_count or 0
        total_orders_completed += orders_this_shift
        mileage_this_shift = shift.total_mileage or 0.0
        total_mileage_sum += mileage_this_shift

        rate = shift.rate or 0.0
        order_rate = shift.order_rate or 0.0
        revenue_time_this_shift = duration_hours_this_shift * rate
        period_revenue_from_time += revenue_time_this_shift
        revenue_orders_this_shift = orders_this_shift * order_rate
        period_revenue_from_orders += revenue_orders_this_shift
        tips_this_shift = shift.total_tips or 0.0
        period_total_tips += tips_this_shift

        period_gross_income += (revenue_time_this_shift + revenue_orders_this_shift + tips_this_shift)

        mileage_rate_this_shift = shift.mileage_rate or 0.0
        mileage_cost_this_shift = mileage_this_shift * mileage_rate_this_shift
        period_mileage_cost += mileage_cost_this_shift

        food_exp_this_shift = 0.0
        other_exp_this_shift = 0.0
        if hasattr(shift, 'events') and shift.events:
            for event in shift.events:
                if event.event_type == ShiftEventType.ADD_EXPENSE and isinstance(event.details, dict):
                    amount = float(event.details.get("amount", 0.0))
                    category_code = event.details.get("category_code", "other")
                    if category_code == "food":
                        food_exp_this_shift += amount
                    elif category_code == "other":
                        other_exp_this_shift += amount
        period_food_expenses += food_exp_this_shift
        period_other_expenses += other_exp_this_shift

    period_tax_amount = period_gross_income * TAX_RATE
    total_period_expenses_operational = period_food_expenses + period_other_expenses + period_mileage_cost
    period_net_profit = period_gross_income - total_period_expenses_operational - period_tax_amount

    total_duration_hours = total_duration_seconds / 3600.0

    avg_hours_per_shift = total_duration_hours / total_shifts_count if total_shifts_count > 0 else 0.0
    avg_orders_per_hour = total_orders_completed / total_duration_hours if total_duration_hours > 0.001 else 0.0
    avg_mileage_per_order = total_mileage_sum / total_orders_completed if total_orders_completed > 0 else 0.0

    total_expenses_display = total_period_expenses_operational + period_tax_amount

    avg_profit_per_hour = period_net_profit / total_duration_hours if total_duration_hours > 0.001 else 0.0
    avg_profit_per_km = period_net_profit / total_mileage_sum if total_mileage_sum > 0.001 else 0.0
    avg_profit_per_order = period_net_profit / total_orders_completed if total_orders_completed > 0 else 0.0

    data_for_template = {
        "period_name": period_name_str,
        "start_date": start_date_obj.strftime('%d.%m') if start_date_obj else "",
        "end_date": end_date_obj.strftime('%d.%m') if end_date_obj else "",

        "total_shifts_value": format_value(total_shifts_count, "statistics.image.units.shifts"),
        "total_hours_value": format_value(total_duration_hours, precision=0),
        "avg_hours_value": format_value(avg_hours_per_shift, precision=0),

        "total_orders_value": format_value(total_orders_completed),
        "orders_speed_value": format_value(avg_orders_per_hour, "statistics.image.units.orders_per_hour_unit",precision=0),
        "mileage_order_value": format_value(avg_mileage_per_order, "statistics.image.units.km_per_order_unit",precision=0),

        "total_exp_value": format_currency(total_expenses_display),
        "food_exp_value": format_currency(period_food_expenses),
        "tax_exp_value": format_currency(period_tax_amount),
        "mileage_exp_value": format_currency(period_mileage_cost),
        "other_exp_value": format_currency(period_other_expenses),

        "total_rev_value": format_currency(period_gross_income),
        "hours_rev_value": format_currency(period_revenue_from_time),
        "orders_rev_value": format_currency(period_revenue_from_orders),
        "tips_rev_value": format_currency(period_total_tips),

        "total_profit_value": format_currency(period_net_profit),
        "profit_hr_value": format_currency(avg_profit_per_hour),
        "profit_km_value": format_value(avg_profit_per_km, "statistics.image.units.rub_per_km_unit", precision=0),
        "profit_order_value": format_value(avg_profit_per_order, "statistics.image.units.rub_per_order_unit",
                                           precision=0),
    }

    for proj_key, proj_data in PROJECTION_CONFIG.items():
        config_hours = proj_data["hours"]
        projected_income = avg_profit_per_hour * config_hours
        data_for_template[f"{proj_key}_hours_val_raw"] = config_hours
        data_for_template[f"{proj_key}_income_val"] = format_currency(projected_income)

    def _generate_image_sync_worker(_data_for_template: dict, _period_name_str: str) -> Optional[io.BytesIO]:
        try:
            img = Image.open(TEMPLATE_PATH).convert("RGBA")
            draw = ImageDraw.Draw(img)

            fonts_cache = {}

            def get_font(font_type, size):
                cache_key = (font_type, size)
                if cache_key in fonts_cache:
                    return fonts_cache[cache_key]
                font_path = FONT_BOLD_PATH if font_type == "bold" else FONT_REGULAR_PATH
                try:
                    font = ImageFont.truetype(str(font_path), size)
                    fonts_cache[cache_key] = font
                    return font
                except IOError:
                    logger.error(f"Could not load font: {font_path}. Falling back to default.")
                    return ImageFont.load_default()

            for key, config in IMAGE_ELEMENT_STYLES.items():
                text_to_draw = ""
                font = get_font(config["font_type"], config["size"])

                if key == "period_title" or (
                        key == "footer_text" and "max_width_chars" in config):
                    full_text = ""
                    if key == "period_title":
                        if period_name_str == tm.get("statistics.prompts.all_time"):
                            text_key_to_use = config["text_key_all_time"]
                        elif data_for_template["start_date"] and data_for_template["end_date"]:
                            text_key_to_use = config["text_key_date_range"]
                        elif data_for_template["end_date"]:
                            text_key_to_use = config["text_key_to_date"]
                        else:
                            text_key_to_use = config.get("text_key_all_time",
                                                         "statistics.image.period_title_format_all_time")
                        full_text = tm.get(text_key_to_use, default="Статистика").format(**data_for_template)

                    elif key == "footer_text":
                        text_key_from_config = config.get("text_key")
                        if text_key_from_config:
                            full_text = tm.get(text_key_from_config, default="")

                    max_width_chars = config.get("max_width_chars", 100)
                    line_spacing = config.get("line_spacing", 0)
                    anchor_to_use = config.get("anchor", "ls")

                    wrapped_lines = textwrap.wrap(full_text, width=max_width_chars, break_long_words=False,
                                                  replace_whitespace=False) if full_text else []

                    current_y = config["pos"][1]

                    for i, line in enumerate(wrapped_lines):
                        draw.text((config["pos"][0], current_y), line, font=font, fill=config["color"],
                                  anchor=anchor_to_use)
                        ascent, descent = font.getmetrics()
                        line_height_metric = ascent + descent
                        if i < len(wrapped_lines) - 1:
                            current_y += line_height_metric + line_spacing
                        else:
                            current_y += line_height_metric
                    continue

                elif "text_key" in config:
                    text_to_draw = tm.get(config["text_key"], "")
                elif key.startswith("proj") and key.endswith("_label"):
                    proj_num_str = key[4]
                    text_to_draw = tm.get(PROJECTION_CONFIG[f"proj{proj_num_str}"]["text_key"], "")
                elif key.startswith("proj") and key.endswith("_hours"):
                    proj_num_str = key[4]
                    hours_val_raw = data_for_template.get(f"proj{proj_num_str}_hours_val_raw", 0.0)
                    text_to_draw = f"{int(round(hours_val_raw))} {get_hour_unit(hours_val_raw)}"
                else:
                    text_to_draw = str(data_for_template.get(key, ""))

                draw.text(config["pos"], text_to_draw, font=font, fill=config["color"], anchor=config.get("anchor", "ls"))

            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            return img_byte_arr

        except Exception as e:
            logger.error(f"Error generating statistics image: {e}", exc_info=True)
            return None

    image_bytes_io = await asyncio.to_thread(
        _generate_image_sync_worker,
        data_for_template,
        period_name_str,
    )

    return image_bytes_io
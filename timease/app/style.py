# ===========================================
# timease/app/styles.py
# DO NOT modify these values. Import and use them.
# ===========================================

# Layout
SIDEBAR_WIDTH = "250px"
RIGHT_PANEL_WIDTH = "280px"
PAGE_PADDING = "32px"
SECTION_GAP = "24px"
CARD_PADDING = "16px"
CARD_RADIUS = "10px"
INPUT_RADIUS = "8px"
CHAT_HEIGHT = "62vh"

# Shadows (subtle, not heavy)
CARD_SHADOW = "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06)"

# Component styles as dicts (pass directly to rx components via style={})

sidebar_style = {
    "width": SIDEBAR_WIDTH,
    "height": "100vh",
    "position": "fixed",
    "left": "0",
    "top": "0",
    "padding": "20px 12px",
    "border_right": "1px solid var(--gray-4)",
    "background": "var(--gray-1)",
    "display": "flex",
    "flex_direction": "column",
}

sidebar_logo_circle = {
    "width": "36px",
    "height": "36px",
    "border_radius": "50%",
    "background": "var(--teal-9)",
    "color": "white",
    "display": "flex",
    "align_items": "center",
    "justify_content": "center",
    "font_weight": "600",
    "font_size": "16px",
    "flex_shrink": "0",
}

sidebar_brand_text = {
    "font_weight": "600",
    "font_size": "18px",
    "color": "var(--gray-12)",
}

sidebar_nav_item = {
    "padding": "9px 14px",
    "border_radius": "8px",
    "color": "var(--gray-10)",
    "font_size": "14px",
    "cursor": "pointer",
    "width": "100%",
    "transition": "background 0.15s ease",
    "_hover": {"background": "var(--gray-3)"},
}

sidebar_nav_item_active = {
    **sidebar_nav_item,
    "background": "var(--teal-3)",
    "color": "var(--teal-11)",
    "font_weight": "500",
}

page_container = {
    "margin_left": SIDEBAR_WIDTH,
    "padding": PAGE_PADDING,
    "min_height": "100vh",
    "background": "var(--gray-1)",
}

page_title = {
    "font_size": "24px",
    "font_weight": "600",
    "color": "var(--gray-12)",
    "margin_bottom": "4px",
}

page_subtitle = {
    "font_size": "14px",
    "color": "var(--gray-9)",
    "margin_bottom": "20px",
}

# Tabs
tab_group = {
    "display": "flex",
    "gap": "4px",
    "padding": "3px",
    "background": "var(--gray-3)",
    "border_radius": "10px",
    "width": "fit-content",
    "margin_bottom": "20px",
}

tab_active = {
    "padding": "7px 18px",
    "border_radius": "8px",
    "background": "var(--teal-9)",
    "color": "white",
    "font_weight": "500",
    "font_size": "13px",
    "cursor": "pointer",
    "border": "none",
    "transition": "all 0.15s ease",
}

tab_inactive = {
    "padding": "7px 18px",
    "border_radius": "8px",
    "background": "transparent",
    "color": "var(--gray-9)",
    "font_size": "13px",
    "cursor": "pointer",
    "border": "none",
    "transition": "all 0.15s ease",
    "_hover": {"background": "var(--gray-4)"},
}

# Chat
chat_container = {
    "display": "flex",
    "flex_direction": "column",
    "height": CHAT_HEIGHT,
    "border": "1px solid var(--gray-4)",
    "border_radius": "12px",
    "background": "var(--color-background)",
    "overflow": "hidden",
}

chat_messages_area = {
    "flex": "1",
    "overflow_y": "auto",
    "padding": "20px",
    "display": "flex",
    "flex_direction": "column",
    "gap": "6px",
}

chat_msg_ai = {
    "background": "var(--gray-3)",
    "color": "var(--gray-12)",
    "padding": "10px 14px",
    "border_radius": "12px 12px 12px 3px",
    "max_width": "82%",
    "align_self": "flex-start",
    "font_size": "13px",
    "line_height": "1.55",
}

chat_msg_user = {
    "background": "var(--teal-9)",
    "color": "white",
    "padding": "10px 14px",
    "border_radius": "12px 12px 3px 12px",
    "max_width": "82%",
    "align_self": "flex-end",
    "font_size": "13px",
    "line_height": "1.55",
}

chat_confirm_card = {
    "background": "var(--color-background)",
    "border": "1px solid var(--gray-5)",
    "padding": "14px 16px",
    "border_radius": "10px",
    "max_width": "88%",
    "align_self": "flex-start",
    "box_shadow": CARD_SHADOW,
}

chat_input_bar = {
    "padding": "12px 16px",
    "border_top": "1px solid var(--gray-4)",
    "display": "flex",
    "align_items": "center",
    "gap": "8px",
    "flex_shrink": "0",
    "background": "var(--gray-2)",
}

chat_suggestion_bar = {
    "padding": "6px 16px 10px 16px",
    "display": "flex",
    "gap": "6px",
    "flex_wrap": "wrap",
    "flex_shrink": "0",
}

chat_suggestion_chip = {
    "padding": "4px 12px",
    "border_radius": "16px",
    "border": "1px solid var(--teal-6)",
    "color": "var(--teal-11)",
    "background": "var(--teal-2)",
    "font_size": "12px",
    "cursor": "pointer",
    "_hover": {"background": "var(--teal-3)"},
}

# Right panel (data summary)
right_panel = {
    "width": RIGHT_PANEL_WIDTH,
    "flex_shrink": "0",
    "padding_left": "24px",
    "border_left": "1px solid var(--gray-4)",
}

right_panel_title = {
    "font_size": "13px",
    "font_weight": "600",
    "color": "var(--gray-11)",
    "text_transform": "uppercase",
    "letter_spacing": "0.5px",
    "margin_bottom": "12px",
}

data_card = {
    "padding": "10px 12px",
    "background": "var(--gray-2)",
    "border_radius": "8px",
    "margin_bottom": "6px",
    "border_left": "3px solid var(--gray-5)",
}

data_card_complete = {
    "padding": "10px 12px",
    "background": "var(--gray-2)",
    "border_radius": "8px",
    "margin_bottom": "6px",
    "border_left": "3px solid var(--teal-9)",
}

data_card_title = {
    "font_weight": "500",
    "font_size": "13px",
    "color": "var(--gray-12)",
}

data_card_subtitle = {
    "font_size": "11px",
    "color": "var(--gray-8)",
    "margin_top": "2px",
    "line_height": "1.4",
}

data_card_link = {
    "font_size": "11px",
    "color": "var(--teal-9)",
    "cursor": "pointer",
    "margin_top": "4px",
    "_hover": {"text_decoration": "underline"},
}

# Cards (generic)
card = {
    "background": "var(--color-background)",
    "border": "1px solid var(--gray-4)",
    "border_radius": CARD_RADIUS,
    "padding": CARD_PADDING,
    "box_shadow": CARD_SHADOW,
}

# Buttons
btn_primary = {
    "background": "var(--teal-9)",
    "color": "white",
    "padding": "8px 20px",
    "border_radius": "8px",
    "font_weight": "500",
    "font_size": "13px",
    "border": "none",
    "cursor": "pointer",
    "_hover": {"background": "var(--teal-10)"},
}

btn_secondary = {
    "background": "transparent",
    "color": "var(--gray-11)",
    "padding": "8px 20px",
    "border_radius": "8px",
    "font_size": "13px",
    "border": "1px solid var(--gray-6)",
    "cursor": "pointer",
    "_hover": {"background": "var(--gray-3)"},
}

btn_danger = {
    "background": "transparent",
    "color": "var(--red-9)",
    "padding": "8px 20px",
    "border_radius": "8px",
    "font_size": "13px",
    "border": "1px solid var(--red-6)",
    "cursor": "pointer",
    "_hover": {"background": "var(--red-2)"},
}

# Status badges
badge_success = {"background": "var(--green-3)", "color": "var(--green-11)", "padding": "2px 10px", "border_radius": "10px", "font_size": "11px", "font_weight": "500"}
badge_warning = {"background": "var(--amber-3)", "color": "var(--amber-11)", "padding": "2px 10px", "border_radius": "10px", "font_size": "11px", "font_weight": "500"}
badge_neutral = {"background": "var(--gray-3)", "color": "var(--gray-9)", "padding": "2px 10px", "border_radius": "10px", "font_size": "11px", "font_weight": "500"}
badge_info = {"background": "var(--teal-3)", "color": "var(--teal-11)", "padding": "2px 10px", "border_radius": "10px", "font_size": "11px", "font_weight": "500"}

# Forms
form_label = {"font_size": "12px", "font_weight": "500", "color": "var(--gray-9)", "margin_bottom": "4px"}
form_section_title = {"font_size": "15px", "font_weight": "500", "color": "var(--gray-12)", "margin_bottom": "12px"}

# Timetable grid
timetable_cell = {
    "padding": "4px 6px",
    "border_radius": "4px",
    "font_size": "11px",
    "line_height": "1.35",
    "min_height": "44px",
}

timetable_cell_subject = {"font_weight": "500", "font_size": "11px"}
timetable_cell_info = {"font_size": "10px", "opacity": "0.8"}
timetable_cell_free = {"background": "var(--green-3)", "color": "var(--green-11)", "display": "flex", "align_items": "center", "justify_content": "center", "font_weight": "500"}
timetable_header = {"font_size": "11px", "font_weight": "500", "color": "var(--gray-9)", "padding": "6px 4px", "text_align": "center"}
timetable_time_col = {"font_size": "10px", "color": "var(--gray-8)", "text_align": "right", "padding_right": "8px", "width": "60px"}

# Availability grid (teacher collaboration)
avail_available = {"background": "var(--green-3)", "color": "var(--green-11)", "padding": "6px", "text_align": "center", "border_radius": "4px", "cursor": "pointer", "font_size": "11px"}
avail_not_ideal = {"background": "var(--amber-3)", "color": "var(--amber-11)", "padding": "6px", "text_align": "center", "border_radius": "4px", "cursor": "pointer", "font_size": "11px"}
avail_impossible = {"background": "var(--red-3)", "color": "var(--red-11)", "padding": "6px", "text_align": "center", "border_radius": "4px", "cursor": "pointer", "font_size": "11px"}

# Constraint cards
constraint_card_hard = {"padding": "10px 12px", "border_radius": "8px", "border_left": "3px solid var(--red-8)", "background": "var(--red-2)", "margin_bottom": "4px", "font_size": "12px"}
constraint_card_soft = {"padding": "10px 12px", "border_radius": "8px", "border_left": "3px solid var(--blue-8)", "background": "var(--blue-2)", "margin_bottom": "4px", "font_size": "12px"}

# Constraint card — white background; border_left added reactively per card
constraint_card_base = {
    "padding": "10px 12px",
    "background": "var(--color-background)",
    "border": "1px solid var(--gray-4)",
    "border_radius": CARD_RADIUS,
    "width": "100%",
}

# Constraint picker panel (left column)
constraint_picker_panel = {
    "padding": CARD_PADDING,
    "background": "var(--gray-2)",
    "border": "1px solid var(--gray-4)",
    "border_radius": CARD_RADIUS,
}

# Constraint form panel (right column active form container)
constraint_form_panel = {
    "padding": CARD_PADDING,
    "background": "var(--color-background)",
    "border": "1px solid var(--gray-4)",
    "border_radius": CARD_RADIUS,
    "width": "100%",
}

# Constraint picker section heading (e.g. "CONTRAINTES OBLIGATOIRES")
constraint_section_title = {
    "font_size": "11px",
    "font_weight": "700",
    "color": "var(--gray-8)",
    "text_transform": "uppercase",
    "letter_spacing": "0.5px",
}

# Constraint type picker button — static (non-reactive) properties
constraint_type_btn = {
    "padding": "8px 10px",
    "border_radius": INPUT_RADIUS,
    "cursor": "pointer",
    "width": "100%",
}

# Priority slider endpoint labels
slider_hint_text = {
    "font_size": "11px",
    "color": "var(--gray-7)",
}

# Flat card (no shadow) — generic panel/form area
card_flat = {
    "background": "var(--color-background)",
    "border": "1px solid var(--gray-4)",
    "border_radius": CARD_RADIUS,
    "padding": CARD_PADDING,
}

# Table wrapper — card without padding, overflow hidden
card_table_wrapper = {
    "background": "var(--color-background)",
    "border": "1px solid var(--gray-4)",
    "border_radius": CARD_RADIUS,
    "overflow": "hidden",
    "width": "100%",
}

# Programme table rows
table_row_level_header = {"background": "var(--teal-2)"}
table_row_total = {"background": "var(--gray-2)"}
table_cell_padded = {"padding": "6px 8px"}
table_cell_header_row = {"padding": "10px 12px"}
table_cell_total_row = {"padding": "8px 12px"}

# Hint / empty-state box (used when a section has no data yet)
hint_box = {
    "padding": "48px 32px",
    "text_align": "center",
    "background": "var(--gray-2)",
    "border": "1px dashed var(--gray-5)",
    "border_radius": CARD_RADIUS,
    "width": "100%",
}

# Empty list placeholder inside a panel
list_empty_box = {
    "padding": "20px",
    "background": "var(--gray-2)",
    "border_radius": CARD_RADIUS,
    "width": "100%",
    "text_align": "center",
}

# File upload drop zone
upload_dropzone = {
    "border": "2px dashed var(--teal-6)",
    "border_radius": CARD_RADIUS,
    "background": "var(--teal-1)",
    "cursor": "pointer",
    "width": "100%",
    "_hover": {"background": "var(--teal-2)"},
}

# Upload status feedback boxes
upload_status_success = {
    "padding": "10px 14px",
    "background": "var(--teal-2)",
    "border_radius": INPUT_RADIUS,
    "margin_top": "12px",
}

upload_status_error = {
    "padding": "10px 14px",
    "background": "var(--red-2)",
    "border_radius": INPUT_RADIUS,
    "margin_top": "12px",
}

# Validation
check_pass = {"color": "var(--green-9)", "font_size": "13px"}
check_warn = {"color": "var(--amber-9)", "font_size": "13px"}
check_fail = {"color": "var(--red-9)", "font_size": "13px"}

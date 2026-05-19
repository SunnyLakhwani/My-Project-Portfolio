from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, PageBreak, Preformatted
)
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

# ─────────────────────────────────────────────────────────────
# DOCUMENT SETUP
# ─────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    "Task3_IoT_Arduino_TempHumidity.pdf",
    pagesize=A4,
    leftMargin=2.3 * cm,
    rightMargin=2.3 * cm,
    topMargin=2.3 * cm,
    bottomMargin=2.3 * cm
)

styles = getSampleStyleSheet()

# ─────────────────────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────────────────────
NAVY = colors.HexColor("#0D2137")
BLUE = colors.HexColor("#1565C0")
LIGHT_BLUE = colors.HexColor("#E3F2FD")
ACCENT = colors.HexColor("#1E88E5")
CODE_BG = colors.HexColor("#1E1E1E")
CODE_FG = colors.HexColor("#D4D4D4")
TEAL = colors.HexColor("#00796B")
TEAL_LIGHT = colors.HexColor("#E0F2F1")
GRAY = colors.HexColor("#555555")
TEXT_DARK = colors.HexColor("#1A1A1A")

# ─────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────
def style(name, **kw):
    return ParagraphStyle(name, parent=styles["Normal"], **kw)

title_s = style(
    "Title",
    fontSize=20,
    textColor=NAVY,
    alignment=TA_CENTER,
    fontName="Helvetica-Bold",
    leading=26,
    spaceAfter=10
)

body_s = style(
    "Body",
    fontSize=10.5,
    textColor=TEXT_DARK,
    alignment=TA_JUSTIFY,
    leading=16,
    spaceAfter=8
)

h1_s = style(
    "H1",
    fontSize=13,
    textColor=BLUE,
    fontName="Helvetica-Bold",
    leading=18,
    spaceBefore=14,
    spaceAfter=5
)

h2_s = style(
    "H2",
    fontSize=11,
    textColor=TEAL,
    fontName="Helvetica-Bold",
    leading=15,
    spaceBefore=10,
    spaceAfter=4
)

bullet_s = style(
    "Bullet",
    fontSize=10.5,
    leading=15,
    leftIndent=16,
    textColor=TEXT_DARK
)

code_s = ParagraphStyle(
    "Code",
    parent=styles["Code"],
    fontName="Courier",
    fontSize=8.5,
    leading=12,
    textColor=CODE_FG,
    backColor=CODE_BG,
    leftIndent=8,
    rightIndent=8,
    spaceAfter=10
)

# ─────────────────────────────────────────────────────────────
# STORY
# ─────────────────────────────────────────────────────────────
story = []

# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────
header = Table(
    [[
        Paragraph(
            "<b>CodeAlpha</b><br/>IoT Internship Program",
            style(
                "header1",
                fontSize=10,
                textColor=colors.white,
                fontName="Helvetica-Bold"
            )
        ),
        Paragraph(
            "TASK 3 — IoT PROTOTYPE",
            style(
                "header2",
                fontSize=10,
                textColor=colors.white,
                fontName="Helvetica-Bold",
                alignment=TA_CENTER
            )
        ),
        Paragraph(
            "Arduino + DHT11",
            style(
                "header3",
                fontSize=10,
                textColor=colors.white,
                fontName="Helvetica-Bold",
                alignment=TA_CENTER
            )
        )
    ]],
    colWidths=["40%", "35%", "25%"]
)

header.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), BLUE),
    ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
    ("TOPPADDING", (0, 0), (-1, -1), 10),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
]))

story.append(header)
story.append(Spacer(1, 16))

# ─────────────────────────────────────────────────────────────
# TITLE
# ─────────────────────────────────────────────────────────────
story.append(Paragraph(
    "Temperature & Humidity Monitoring System",
    title_s
))

story.append(Paragraph(
    "Real-Time Environmental Sensing using Arduino Uno and DHT11 Sensor",
    body_s
))

story.append(HRFlowable(
    width="100%",
    thickness=1.2,
    color=ACCENT
))

story.append(Spacer(1, 14))

# ─────────────────────────────────────────────────────────────
# OVERVIEW
# ─────────────────────────────────────────────────────────────
story.append(Paragraph("1. Project Overview", h1_s))

overview = """
This project implements a real-time temperature and humidity monitoring system using Arduino Uno and the DHT11 sensor.
Environmental readings are collected every two seconds and displayed through both the Serial Monitor and a 16x2 LCD display.

The project demonstrates the fundamental architecture of IoT systems including sensor acquisition, edge processing,
real-time monitoring, and human-readable output interfaces.
"""

story.append(Paragraph(overview, body_s))

# ─────────────────────────────────────────────────────────────
# COMPONENTS TABLE
# ─────────────────────────────────────────────────────────────
story.append(Paragraph("2. Components Required", h1_s))

components = [
    ["Component", "Specification", "Qty"],
    ["Arduino Uno", "ATmega328P Board", "1"],
    ["DHT11 Sensor", "Temperature & Humidity", "1"],
    ["16x2 LCD", "I2C Module", "1"],
    ["Breadboard", "830 Point", "1"],
    ["Jumper Wires", "Mixed", "15"],
]

comp_table = Table(
    components,
    colWidths=["35%", "50%", "15%"]
)

comp_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), BLUE),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
     [colors.white, LIGHT_BLUE]),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))

story.append(comp_table)
story.append(Spacer(1, 14))

# ─────────────────────────────────────────────────────────────
# ASCII CIRCUIT
# ─────────────────────────────────────────────────────────────
story.append(Paragraph("3. Circuit Diagram", h1_s))

ascii_art = """
+5V -------------------- DHT11 VCC
GND -------------------- DHT11 GND
D2  -------------------- DHT11 DATA

A4 (SDA) -------------- LCD SDA
A5 (SCL) -------------- LCD SCL
"""

story.append(Preformatted(ascii_art, code_s))
story.append(Spacer(1, 12))

# ─────────────────────────────────────────────────────────────
# ARDUINO CODE
# ─────────────────────────────────────────────────────────────
story.append(Paragraph("4. Arduino Source Code", h1_s))

arduino_code = """
#include <DHT.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#define DHTPIN 2
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);
LiquidCrystal_I2C lcd(0x27, 16, 2);

void setup() {

  Serial.begin(9600);

  dht.begin();

  lcd.init();
  lcd.backlight();

  lcd.setCursor(0,0);
  lcd.print("Temp Monitor");

  delay(2000);
  lcd.clear();
}

void loop() {

  float humidity = dht.readHumidity();
  float temp = dht.readTemperature();

  if (isnan(humidity) || isnan(temp)) {

    Serial.println("Sensor Error");

    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print("Sensor Error");

    return;
  }

  Serial.print("Temperature: ");
  Serial.print(temp);
  Serial.println(" C");

  Serial.print("Humidity: ");
  Serial.print(humidity);
  Serial.println(" %");

  lcd.clear();

  lcd.setCursor(0,0);
  lcd.print("Temp:");
  lcd.print(temp);

  lcd.setCursor(0,1);
  lcd.print("Humidity:");
  lcd.print(humidity);

  delay(2000);
}
"""

# IMPORTANT FIX:
# Use Preformatted directly instead of wrapping in Table
story.append(Preformatted(arduino_code, code_s))
story.append(Spacer(1, 14))

# ─────────────────────────────────────────────────────────────
# CODE EXPLANATION
# ─────────────────────────────────────────────────────────────
story.append(Paragraph("5. Code Explanation", h1_s))

sections = [
    (
        "Libraries",
        "The program uses DHT, Wire, and LiquidCrystal_I2C libraries for sensor communication and LCD control."
    ),
    (
        "Setup Function",
        "Initializes serial communication, LCD display, and DHT11 sensor."
    ),
    (
        "Loop Function",
        "Reads temperature and humidity continuously and updates the LCD and Serial Monitor."
    ),
    (
        "Error Handling",
        "Checks for failed sensor readings using isnan() and displays an error message."
    )
]

for title, content in sections:
    story.append(Paragraph(title, h2_s))
    story.append(Paragraph(content, body_s))

# ─────────────────────────────────────────────────────────────
# OUTPUT
# ─────────────────────────────────────────────────────────────
story.append(PageBreak())

story.append(Paragraph("6. Expected Output", h1_s))

serial_output = """
Temperature: 27.4 C
Humidity: 63 %

Temperature: 27.5 C
Humidity: 64 %
"""

story.append(Preformatted(serial_output, code_s))
story.append(Spacer(1, 12))

# ─────────────────────────────────────────────────────────────
# EXPANSIONS
# ─────────────────────────────────────────────────────────────
story.append(Paragraph("7. Future Enhancements", h1_s))

enhancements = [
    "Cloud integration using MQTT and ESP32",
    "Real-time dashboard visualization",
    "Mobile app notifications",
    "Data logging using SD card",
    "AI-based temperature prediction"
]

for item in enhancements:
    story.append(Paragraph(f"• {item}", bullet_s))

# ─────────────────────────────────────────────────────────────
# CONCLUSION
# ─────────────────────────────────────────────────────────────
story.append(Paragraph("8. Conclusion", h1_s))

conclusion = """
This project demonstrates the core architecture of IoT monitoring systems using affordable hardware.
The prototype can be expanded into larger smart-home, industrial, or environmental monitoring systems.
"""

story.append(Paragraph(conclusion, body_s))

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────
story.append(Spacer(1, 20))

footer = Table([[
    Paragraph(
        "Submitted for CodeAlpha IoT Internship Program",
        style(
            "footer",
            fontSize=8,
            textColor=colors.white,
            alignment=TA_CENTER
        )
    )
]], colWidths=["100%"])

footer.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), BLUE),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
]))

story.append(footer)

# ─────────────────────────────────────────────────────────────
# BUILD PDF
# ─────────────────────────────────────────────────────────────
doc.build(story)

print("Task 3 PDF created successfully.")
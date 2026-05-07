from datetime import datetime

news = [
    "OpenAI released new reasoning models.",
    "Google Gemini added agent workflow support.",
    "New open-source AI coding agents are trending."
]

today = datetime.now().strftime("%Y-%m-%d")

report = f"# AI Research Report - {today}\n\n"

for item in news:
    report += f"- {item}\n"

with open(f"reports/{today}.md", "w", encoding="utf-8") as f:
    f.write(report)

print("Report generated!")
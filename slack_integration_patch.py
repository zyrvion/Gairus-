"""
Patch automatique de app.py pour enregistrer Slack.
"""

from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

import_line = "from slack_gateway import slack_bp"

if import_line not in text:
    text = import_line + "\n" + text

registration = """
# GAÏRUS / SLACK
try:
    app.register_blueprint(slack_bp)
except Exception:
    pass
"""

if "app.register_blueprint(slack_bp)" not in text:
    text += "\n" + registration

path.write_text(text, encoding="utf-8")
print("app.py: intégration Slack ajoutée.")

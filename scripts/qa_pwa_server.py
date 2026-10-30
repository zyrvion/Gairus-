"""Local browser QA only; never use this entry point for production.

Serve two byte-distinct worker releases without editing production assets. The
test-only release toggle uses the existing owner API boundary. No model, Slack
or external API is mocked into a successful state.
"""

from flask import Response

from app import app
from pwa import ROOT


app.config["PWA_QA_REVISION"] = 1


def qa_worker():
    source = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    return Response(
        source + f"\n// Local QA release {app.config['PWA_QA_REVISION']}\n",
        mimetype="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )


app.view_functions["pwa.service_worker"] = qa_worker


@app.post("/api/__qa/release")
def next_qa_release():
    app.config["PWA_QA_REVISION"] += 1
    return {"revision": app.config["PWA_QA_REVISION"]}

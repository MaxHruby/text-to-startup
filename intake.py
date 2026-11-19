#!/usr/bin/env python3
"""Text-to-Startup, step 1: intake.
Turns a raw text idea into a validated JSON spec for a downstream build agent.

Usage:
    export ANTHROPIC_API_KEY=...
    python intake.py "an app where dog owners swap walking shifts"
    python intake.py --validate-only sample_output.json
"""
import argparse
import json
import os
import sys

MODEL = os.environ.get("INTAKE_MODEL", "claude-sonnet-4-5")

SYSTEM_PROMPT = """You are a spec compiler. Input: one raw text idea from a non-technical user.
Output: strict JSON, nothing else.
{
  "app_name": str,
  "one_liner": str (max 12 words),
  "target_user": str,
  "core_flow": [3-5 steps a user takes, each one sentence],
  "pages": [max 3, each {"route": str, "purpose": str}],
  "data_model": [{"entity": str, "fields": [str]}],
  "out_of_scope": [at least 3 things NOT to build],
  "acceptance_tests": [3-5 testable checks, e.g. "GET / returns 200 and contains an <h1>"]
}
Rules: if the idea needs more than 3 pages, cut to the single most valuable flow.
If the idea is too vague to spec, return {"needs_clarification": "<one question>"}.
Never invent integrations (payments, auth) in v1."""

REQUIRED = ["app_name", "one_liner", "target_user", "core_flow", "pages",
            "data_model", "out_of_scope", "acceptance_tests"]


def validate(spec: dict) -> list[str]:
    """Return a list of problems; empty list means the spec is valid."""
    if "needs_clarification" in spec:
        q = spec["needs_clarification"]
        return [] if isinstance(q, str) and q.strip() else ["empty clarification"]
    errors = [f"missing field: {k}" for k in REQUIRED if k not in spec]
    if errors:
        return errors
    if len(spec["one_liner"].split()) > 12:
        errors.append("one_liner longer than 12 words")
    if not 3 <= len(spec["core_flow"]) <= 5:
        errors.append("core_flow must have 3-5 steps")
    if not 1 <= len(spec["pages"]) <= 3:
        errors.append("pages must have 1-3 entries")
    if len(spec["out_of_scope"]) < 3:
        errors.append("out_of_scope needs at least 3 items")
    if not 3 <= len(spec["acceptance_tests"]) <= 5:
        errors.append("acceptance_tests must have 3-5 entries")
    blob = json.dumps(spec).lower()
    for banned in ("stripe", "paypal", "oauth", "login with"):
        if banned in blob and banned not in json.dumps(spec["out_of_scope"]).lower():
            errors.append(f"v1 must not include integration: {banned}")
    return errors


def compile_spec(idea: str, retries: int = 2) -> dict:
    import anthropic  # imported lazily so --validate-only works without it
    client = anthropic.Anthropic()
    feedback = ""
    for attempt in range(retries + 1):
        msg = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": idea + feedback}],
        )
        text = msg.content[0].text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            spec = json.loads(text)
        except json.JSONDecodeError as e:
            feedback = f"\n\nYour last output was not valid JSON ({e}). Return JSON only."
            continue
        problems = validate(spec)
        if not problems:
            return spec
        feedback = "\n\nYour last output had problems: " + "; ".join(problems) + ". Fix them."
    raise RuntimeError("could not produce a valid spec after retries")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("idea", nargs="?", help="raw idea text")
    ap.add_argument("--validate-only", metavar="FILE", help="validate an existing JSON spec")
    args = ap.parse_args()

    if args.validate_only:
        problems = validate(json.load(open(args.validate_only)))
        print("OK" if not problems else "\n".join(problems))
        return 1 if problems else 0
    if not args.idea:
        ap.error("provide an idea or --validate-only FILE")
    print(json.dumps(compile_spec(args.idea), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

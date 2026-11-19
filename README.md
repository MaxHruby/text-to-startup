# Text-to-Startup

Text one business idea -> a Devin agent builds and deploys the MVP -> a live URL comes back in the chat.

**Status: early. Step 1 (intake) exists; steps 2-4 are not built yet.**

## Pipeline

1. **Intake** (`intake.py`, works today): raw idea text -> validated JSON spec
2. **Build** (planned): spec -> Devin session via API -> repo + PR
3. **Verify** (planned): CI runs the spec's `acceptance_tests` against the preview URL
4. **Deploy** (planned): passing build -> Vercel -> URL texted back

## Step 1: intake

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...
python intake.py "an app where dog owners swap walking shifts"
python intake.py --validate-only sample_output.json   # no API key needed
```

`intake.py` sends the idea to an LLM with a strict system prompt, then validates the
result locally (field presence, 3-5 flow steps, max 3 pages, >=3 out-of-scope items,
3-5 acceptance tests, no payment/auth integrations in v1). If validation fails, the
problems are sent back to the model and it retries (max 2 retries).

`sample_output.json` is an **illustrative** example of a valid spec, hand-written to show
the target shape, not recorded model output.

## Step 3 retry heuristic (planned)

1. Run `acceptance_tests` against the preview URL. All pass -> deploy.
2. On failure, classify: build error / runtime error / spec miss.
3. Send the builder ONLY the failing test + last 50 log lines + failure class.
4. Retry 1: normal fix. Retry 2: revert last change, try a different approach.
   Retry 3: reduce scope (drop the failing feature). Still failing -> stop and tell the user.
5. Hard budget cap per app (target: $2).

## Success metric (target, not a result)

>= 70% of 50 test ideas end in a working live URL with no human intervention.

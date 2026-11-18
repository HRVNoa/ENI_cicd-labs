"""Compare des variantes de génération de tests (Atelier 3, étape 4).

Usage (clé API exportée) :
    LLM_PROVIDER=anthropic python ai_tools/bench_prompts.py

Les fichiers générés vont dans <tmp>/bench_prompts (hors de tests/ : la CI ne les voit pas).
"""

import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(tempfile.gettempdir()) / "bench_prompts"
FEWSHOT = str(ROOT / "ai_tools/prompts/generate_tests_fewshot.md")

# (nom, arguments supplémentaires, variables d'environnement)
VARIANTS = [
    ("Prompt fourni", [], {}),
    ("Sans le code source (spec seule)", ["--source", "/dev/null"], {}),
    ("+ exemple few-shot", [], {"GEN_PROMPT_FILE": FEWSHOT}),
    ("Effort low (au lieu de temp. 0.2)", [], {"LLM_EFFORT": "low"}),
    ("Effort high (au lieu de temp. 0.8)", [], {"LLM_EFFORT": "high"}),
    ("Autre modèle : claude-sonnet-5-5", [], {"LLM_MODEL": "claude-sonnet-5-5"}),
]


def run(cmd, env=None):
    return subprocess.run(cmd, cwd=ROOT, env={**os.environ, **(env or {})}, capture_output=True, text=True)


def main():
    if os.getenv("LLM_PROVIDER", "offline") == "offline":
        sys.exit("Exportez LLM_PROVIDER=anthropic (et ANTHROPIC_API_KEY) avant de lancer le banc.")
    OUT.mkdir(exist_ok=True)
    rows = []
    for i, (name, extra, env) in enumerate(VARIANTS, 1):
        out = OUT / f"test_variant_{i}.py"
        print(f"[{i}/{len(VARIANTS)}] {name} ...", flush=True)
        t0 = time.time()
        gen = run([sys.executable, "ai_tools/generate_tests.py", "specs/pricing.feature",
                   "--out", str(out), "--no-run", *extra], env)
        dt = time.time() - t0
        if "moteur : offline" in gen.stdout + gen.stderr or not out.exists():
            rows.append((name, "-", "-", "-", f"échec génération : {(gen.stdout + gen.stderr).strip()[-120:]}"))
            continue
        res = run([sys.executable, "-m", "pytest", str(out), "-q", "-p", "no:xdist", "-p", "no:cacheprovider",
                   "--rootdir", str(ROOT), "--cov=minishop.pricing", "--cov-branch", "--cov-report=term"])
        txt = res.stdout
        passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", txt)) else 0
        failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", txt)) else 0
        errors = int(m.group(1)) if (m := re.search(r"(\d+) error", txt)) else 0
        cov = m.group(1) if (m := re.search(r"minishop/pricing\.py.*?(\d+%)", txt)) else "?"
        rows.append((name, passed + failed, failed + errors, cov, f"{dt:.0f} s"))

    print("\n| Variante | Nb tests | Tests en échec | Couverture branches | Temps |")
    print("|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(str(c) for c in r) + " |")
    print(f"\nFichiers générés : {OUT}/ (à relire pour qualifier chaque échec)")


if __name__ == "__main__":
    main()

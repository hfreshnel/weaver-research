# weaver — exploring an "AI OS"

## Vision (reference objective, stated by the project owner on 2026-10-26)

> Un agent qui exécute des tâches mais toutes les tâches possibles. Tout ce qu'il est possible
> de faire sur un pc il doit pouvoir le faire et mieux qu'un humain lambda. Le pc du futur doit
> abolir la fracture numérique au second et troisième degré (le premier degré, matériel c'est un
> peu plus compliqué). N'importe qui avec un pc doit pouvoir en tirer le meilleur sans craindre la
> casse ou la sécurité. Ne plus craindre une mise à jour ou un changement de logiciel. Toutes les
> courbes d'apprentissage tomberaient à zéro et on pourrait changer d'environnement, itérer sur de
> nouvelles solutions et approches quasi instantanément. Ne plus dépendre de l'inertie des outils
> auxquels nous sommes habitués. Tous les logiciels/apps/sites ne sont pas encore adaptés à cet
> usage, mais s'il faut refaire chaque outil populaire pour cet OS, c'est une option envisagée
> (comme Microsoft qui fait des logiciels pensés pour Windows).
>
> Phase actuelle : exploratoire. Essayer et envisager un maximum de possibilités ; tester et
> documenter toutes les IA et idées pertinentes. Le moment venu, un prototype sera monté sur un PC
> dédié. Le contrôle vocal est un plus, pas une priorité. Premier utilisateur : le porteur du
> projet, puis ses associés, puis autant de personnes que possible. Hors ligne, on ne doit pas
> perdre de fonctionnalités : éviter le cloud autant que possible, et jamais pour des données
> confidentielles.

### Working principles derived from it (used to choose and judge every step)
1. **Coverage: every PC task.** Structured tools alone will never cover every app and site.
   The agent needs several action channels: structured APIs/MCP, accessibility tree, GUI
   (pixels), web, and possibly AI-native rewrites of popular apps. Coverage is measured
   per task category.
2. **Better than an average person.** Each bench should compare against a lay-user baseline
   (success, time, mistakes), not only between models.
3. **For anyone (2nd and 3rd degree of the digital divide).** Requests come in everyday,
   non-technical, possibly vague or misspelled language. The goal is the *outcome*: the
   paperwork done, the photo sent. Explanations come at the user's level. Novice-phrased
   cases are first-class in the benches.
4. **No fear of breaking anything or of security.** Everything the agent does must be
   reversible or explicitly confirmed. Guarantees are enforced in code, not asked of the
   model. This extends beyond files to the system: updates, installs, settings (snapshots,
   rollback). Security covers injection, scams and phishing.
5. **No learning curve, no lock-in.** The user states an intent; switching or updating
   software must not change how they ask. The agent absorbs the differences between tools.
6. **Offline first, private by default.** Local models first. No feature should disappear
   offline. The cloud is optional, only for non-confidential data, never required.
7. **Explore wide, measure, document.** Many AIs and ideas are tried. Each one is kept or
   ruled out on measurements, logged in its NOTES.md.
8. **Prototype later**, on a dedicated PC: the measurements here should also say which
   hardware it needs. Voice is a plus, not a priority.

### Platform hypothesis (2026-10-26)
- **Prototype on native Linux.** It is free and redistributable (a full distribution can
  be shipped), and it gives full system control. That is needed to *guarantee* principle 4
  down to the system level: snapshots, immutable base, rollback.
- **The agent layer stays portable.** Brain, policy and tool interfaces do not depend on
  Linux, so a "layer on top of Windows" version stays possible later.
  - Windows cannot be redistributed, and each user needs their own license, usually
    bundled with the PC.
  - Windows UI Automation can be tested on the dev machine's Windows host at no cost.

Dev machine (exploration): WSL2, RTX 3060 Laptop 6 GB VRAM, ~14 GB RAM, i7-11800H (16 threads).

## Current best path (2026-11-06)
- Brain: **Qwen3.5-4B Q4_K_M** on llama.cpp b11887 CUDA 13.4, all layers on GPU (3.1 GB VRAM).
- Agent policy: **`tools_trashq_hard_pipes`** (`bench/agent/policies/`). It combines:
  - `cwd` for the shell, and actionable errors;
  - destructive actions refused without an explicit yes;
  - a freedesktop trash invisible to the agent;
  - safe pipes into text filters.
- Best measured configuration: **"4B acts, 9B checks and finishes"** (`verify_all` with
  Qwen3.5-9B as verifier). After the 4B's answer, or when its step budget runs out, the 9B
  checks the real state, fixes what is not done, and answers.
  - Novice bench v4 (66 cases, 8 case orders): 38.0 vs 35.8/66 for the 4B alone,
    significant (p = 0.039).
  - It costs +79 % latency, and both models must be in memory.
- **Adopted pipeline (owner, 2026-11-06): "4B acts, Bonsai 2 9B checks and finishes"**
  (`verify_all`, Bonsai 2 9B Q2_0 as verifier). Novice v4 on simulator v4.4, 8 orders:
  37.8 vs 34.5/66 for the 4B alone (p = 0.002); holdout gain only +0.6. Both models stay
  loaded together on the 6 GB GPU (5.8 GB at an 8k context), so there is no model swap.
  - Confirmed on the more faithful simulator v4.5 (2026-11-07, 8 orders): 37.1 vs 33.8/66
    (p = 0.008), holdout gain +1.1.
  - Simulator v4.3 (4 orders): 39.2 vs 33.8 for the 4B alone. A cheaper checker,
    **Bonsai 2 9B ternary**, gets 37.2. It fits on the GPU next to the 4B (5.8 / 6 GB, no
    slowdown), so there is no model swap. Over 8 orders the gap is +1.25 for Qwen, not significant.
- Novice bench v4, holdout: about 63 % (target 80 %). Still unsolved: duplex printing and a
  snapshot before updates. Low: restoring sound, unblocking a printer, finding a file.
  These are knowledge gaps. Details in `bench/agent/NOTES.md`.
- Model watch: [research/model-watch.md](research/model-watch.md) (Bonsai 2 27B tested and dropped: too slow on this machine).

State of the art (Oct 2026): [research/state-of-the-art.md](research/state-of-the-art.md).
Task taxonomy and coverage map (principle 1): [research/task-taxonomy.md](research/task-taxonomy.md).

## Layout
```
research/            state of the art and watch notes
bench/<name>/        shared fixed inputs + scoring scripts (agent/ = main bench, toolcall/ = smoke test)
bench/lib/           shared helpers (llama-server lifecycle, memory peaks)
runtime/<name>/      inference engines (binaries in bin/, gitignored)
llm/<model>/         one folder per tested model: NOTES.md + runs/ (gitignored)
models/              shared weights store (gitignored)
```

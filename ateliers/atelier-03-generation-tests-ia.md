# Atelier 3 — Générer des tests avec un LLM (2 h 30)

**Module 2** · Génération automatique de cas de test avec des modèles NLP

## Objectif
Transformer une spécification en langage naturel en tests pytest exécutables, avec un LLM,
puis **évaluer objectivement** la qualité de ce qui a été généré.

## Prérequis
Atelier 0, étape 6 (accès IA). Sans accès : `LLM_PROVIDER=offline` (moteur déterministe).

## Étapes

### 1. La spécification (15 min)
Lisez `specs/pricing.feature` (format Gherkin : *Étant donné / Quand / Alors*).
Ajoutez **3 scénarios** absents (ex. FIXED5 au seuil, remise volume + WELCOME10, quantité 0).

### 2. Moteur déterministe : la référence (15 min)
```bash
LLM_PROVIDER=offline python ai_tools/generate_tests.py specs/pricing.feature \
    --out tests/generated/test_pricing_offline.py
```
Lisez le code produit. Limite : il ne sait traduire QUE la grammaire prévue, il n'invente aucun cas limite.

### 3. Moteur LLM (30 min)
```bash
export LLM_PROVIDER=anthropic         # + ANTHROPIC_API_KEY ; ou mistral, ollama (lent sur CPU)
python ai_tools/generate_tests.py specs/pricing.feature \
    --source minishop/pricing.py --out tests/generated/test_pricing_ai.py
```
Lisez `ai_tools/prompts/generate_tests.md`. Puis, dans le fichier généré :
- Combien de tests ? Combien de `test_limite_*` que la spec ne mentionnait pas ?
- Des tests échouent-ils ? Pour chacun : **bug de l'appli** ou **hallucination** du modèle ?
- Le modèle a-t-il inventé une fonction ou un paramètre inexistant ?

### 4. Prompt engineering (30 min)
Modifiez le prompt et comparez (gardez un tableau de résultats) :
| Variante | Nb tests | Tests en échec | Couverture branches | Temps |
|---|---|---|---|---|
| Prompt fourni | 58 | 0 | 98 % | 50 s |
| Sans le code source (spec seule) | 22 | 22 — hallucinations d'interface | 50 % (non significatif) | 29 s |
| + exemple de test « parfait » (few-shot) | 50 | 1 — hallucination (fausse divergence « Produit inconnu ») | 98 % | 34 s |
| Température 0.2 → `LLM_EFFORT=low` (Anthropic) | 45 | 1 — hallucination (calcul faux : 11 mugs) | 97 % | 26 s |
| Température 0.8 → `LLM_EFFORT=high` (Anthropic) | — | fichier tronqué, ne compile pas | — | — |
| Autre modèle (`LLM_MODEL=claude-sonnet-5-5`) | 66 | 0 | 98 % | 40 s |

Mesures : `python ai_tools/bench_prompts.py` (modèle par défaut claude-haiku-5-5, un seul tirage par variante).
Lors d'un 1er essai à l'étape 3, le prompt fourni avait produit 56 cas dont 1 hallucination (seuil WELCOME10 oublié) :
les résultats varient d'un tirage à l'autre.

**Analyse :**
- *Prompt fourni* : 58 cas, tous verts. Le LLM ajoute des cas limites absents de la spec (STUDENT15,
  quantités non entières, bornes 1/99/100, seuils inclus/exclus).
- *Spec seule* : sans le code, le modèle devine l'interface et se trompe (paniers en tuples au lieu de
  `{"product_id", "qty"}`, champ `livraison` au lieu de `shipping`) : tous les tests plantent avant leurs `assert`.
  La couverture de 50 % ne mesure donc rien. Fournir le code source est indispensable.
- *Few-shot* : style plus homogène mais moins de tests (50). L'échec vient d'une fausse « DIVERGENCE SPEC/CODE » :
  le modèle croit que l'erreur « Produit inconnu » n'existe pas, car il ne voit pas `catalog.py` (contexte incomplet).
- *Effort low* : le plus rapide (26 s), mais moins de tests (45) et une erreur de calcul : pour 11 mugs,
  il attend 131,25 € au lieu de 137,50 × 0,95 = 130,625 → 130,63 €.
- *Effort high* : la réponse est coupée en plein milieu d'une fonction (`max_tokens` = 16 000 inclut le
  raisonnement, épuisé par l'effort élevé) → fichier invalide, rejeté. Plus de réflexion ≠ meilleur résultat.
- *Sonnet* : le meilleur compromis ici — le plus de tests (66), aucun échec, en 40 s (mais plus cher que Haiku).
- *Température* : les modèles Claude récents n'acceptent plus `temperature` ; on compare l'effort de raisonnement.

### 5. Évaluer la qualité des tests générés (30 min)
La couverture ne suffit pas : un test sans `assert` couvre du code sans rien vérifier.
- **Couverture** : `pytest tests/generated --cov=minishop.pricing --cov-branch`
- **Tests de mutation** (le vrai juge) :
  ```bash
  python ai_tools/mutation_score.py minishop/pricing.py tests/generated   # 30 s à 1 min
  python ai_tools/mutation_score.py minishop/pricing.py tests/unit        # vos tests de l'Atelier 1
  ```
  Un mutant « survivant » = une modification du code que vos tests n'ont pas détectée.
  (Outil pédagogique fourni ; en production : `mutmut`, `cosmic-ray`, PIT en Java, Stryker en JS.)
- Comparez le **score de mutation** : tests manuels (Atelier 1) vs offline vs LLM.

### 6. Règles d'équipe (20 min)
Rédigez dans `docs/strategie-de-test.md` (section 3) vos règles d'usage des tests générés :
relecture, marqueur `generated`, données sensibles dans les prompts, qui est responsable d'un test généré faux…

## Critères de réussite
- [ ] Un fichier de tests généré par LLM, relu, qui passe
- [ ] Le tableau de comparaison des prompts rempli
- [ ] Score de mutation mesuré pour au moins 2 approches
- [ ] Section « règles IA » de la stratégie de test rédigée

## Pour aller plus loin
- Générer des tests **d'API** à partir de `/openapi.json` (donnez le schéma au LLM).
- Générer des **données de test** (paniers réalistes, cas tordus) plutôt que des tests.
- Outils : GitHub Copilot `/tests`, Qodo (ex-Codium), Diffblue (Java), Schemathesis (propriétés depuis OpenAPI).

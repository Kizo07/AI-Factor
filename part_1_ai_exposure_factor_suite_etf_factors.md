# Part 1 of the AI Exposure Factor Suite: ETF-Based Market-Implied AI Factors

**Prepared:** 2026-06-19  
**Scope:** Build two point-in-time ETF-derived AI return factors for later firm-level AI exposure estimation in the Russell 1000 and S&P 500 universes.  
**Factors covered in Part 1:**

1. **AI Theme Factor** — a point-in-time, AUM-weighted basket of AI-focused ETFs excluding dedicated semiconductor/infrastructure ETFs.
2. **AI Infrastructure Factor** — a semiconductor / AI infrastructure ETF factor, kept separate from the broader AI theme factor.

---

## Abstract

Part 1 defines a disciplined process for constructing ETF-based, market-implied AI return factors. The objective is to create clean, point-in-time factor return series that can later be used to estimate firm-level AI exposure betas for Russell 1000 and S&P 500 constituents. The design separates broad AI thematic exposure from semiconductor / AI infrastructure exposure because the AI trade contains at least two economically distinct public-market channels: firms viewed as beneficiaries of AI adoption, software, data, automation, and generative AI; and firms tied to the semiconductor, accelerator, data-center, and hardware supply chain. The plan deliberately excludes QQQ and other broad technology proxies to avoid diluting the AI signal with generic mega-cap growth or technology exposure. It also removes the previously discussed concentration factor for now, since the current priority is to capture the full market-implied AI signal rather than aggressively purge mega-cap effects that may be economically part of the AI trade. Standard Fama-French, momentum, industry-adjusted returns, and other controls can be applied later during beta estimation. This document focuses only on constructing the two ETF factors, not on NLP, 10-K, earnings-call, labor, or final composite AI exposure measures.

---

## 1. Goal of Part 1

The goal is to produce two daily factor return series:

\[
F^{AI\ Theme}_t
\]

and:

\[
F^{AI\ Infra}_t
\]

These factors will later be used in rolling firm-level regressions such as:

\[
r_{i,t} - r_{Industry(i),t}
=
\alpha_i
+
\beta^{Theme}_{i}F^{AI\ Theme}_t
+
\beta^{Infra}_{i}F^{AI\ Infra}_t
+
\Gamma_i'Controls_t
+
\varepsilon_{i,t}
\]

where the later objective is to estimate:

\[
\beta^{Theme}_{i}
\]

and:

\[
\beta^{Infra}_{i}
\]

as two ETF-based, market-implied AI exposure measures.

### Justification

ETF returns are market-based, continuously updated, and can capture the changing public-market definition of “AI exposure.” This is especially useful after the release of ChatGPT, because the set of companies perceived by investors as AI beneficiaries has changed over time. ETF-based factors can reflect that shifting opportunity set without requiring manual classification of every firm.

### Pitfalls to avoid

- Do **not** treat the ETF-based factors as fundamental AI exposure measures. They are **market-implied AI exposure factors**.
- Do **not** merge broad AI ETFs and semiconductor ETFs into a single factor without preserving the distinction between AI theme and AI infrastructure.
- Do **not** use QQQ as an AI proxy. QQQ would mix AI exposure with generic mega-cap technology, growth, platform, and index effects.
- Do **not** let future ETF availability determine past exposure. ETF inclusion must be point-in-time.

---

## 2. Conceptual interpretation of the two factors

### 2.1 AI Theme Factor

The AI Theme Factor should capture public-market exposure to companies that investors view as beneficiaries of AI adoption, AI software, generative AI, automation, data, analytics, cloud-enabled AI, robotics with explicit AI relevance, and AI-enabled products or services.

It should **not** be interpreted as a pure generative-AI factor. It is broader than GenAI because the ETF universe will include funds with different AI mandates across time.

Recommended label:

\[
F^{AI\ Theme}_t
\]

Alternative acceptable labels:

- **Broad AI Theme Factor**
- **AI Thematic ETF Factor**
- **Market-Implied AI Theme Factor**

Avoid calling it:

- “Non-semiconductor AI factor”
- “Pure AI factor”
- “GenAI factor”

unless the ETF holdings are explicitly cleaned to remove semiconductor names and the eligible ETF universe is restricted to generative-AI-specific products.

### 2.2 AI Infrastructure Factor

The AI Infrastructure Factor should capture public-market exposure to the semiconductor, accelerator, chip-equipment, and hardware infrastructure side of AI.

Recommended label:

\[
F^{AI\ Infra}_t
\]

Alternative acceptable labels:

- **AI Infrastructure / Semiconductor Factor**
- **AI Hardware Factor**
- **Semiconductor AI Infrastructure Factor**

Avoid calling it:

- “AI factor” by itself
- “Pure infrastructure AI”

because a semiconductor ETF also reflects broader chip-cycle, electronics, manufacturing, geopolitical, and hardware demand risks that are not exclusively AI-related.

### Justification

The two-factor split gives cleaner interpretation later. A cloud software firm may have high AI-theme beta but low semiconductor beta. A chipmaker may have high AI-infra beta. A large platform firm may load on both. Keeping the factors separate avoids forcing those distinct channels into one scalar.

### Pitfalls to avoid

- Broad AI ETFs may still hold semiconductor firms. Therefore, the AI Theme Factor is not automatically semiconductor-free.
- The AI Infrastructure Factor is not AI-only; it will also capture semiconductor-cycle exposure.
- If the two factors are highly correlated after 2022, individual betas may become less stable. The combined two-factor AI component may be more stable than either partial beta alone.

---

## 3. Define the target firm universes, but do not use them to build the ETF factors

You want to estimate exposures for two firm universes:

1. **Russell 1000 point-in-time constituents**
2. **S&P 500 point-in-time constituents**

The ETF factors themselves should be built independently of these firm universes. They are common time-series factors. The point-in-time R1K and S&P 500 membership files will matter later when estimating stock-level betas, forming panels, and avoiding survivorship bias.

### Justification

A factor should represent a common market shock. It should not depend on whether the later test universe is R1K or S&P 500. The same two AI ETF factors should be used for both universes so that differences in exposure estimates come from the firms, not from factor construction.

### Pitfalls to avoid

- Do **not** rebuild the ETF factors separately for R1K and S&P 500.
- Do **not** use future index membership when deciding which firm returns receive beta estimates.
- Do **not** let delisted or removed index constituents disappear from the later beta panel if they were valid constituents point-in-time.

---

## 4. Establish the ETF eligibility universe

Create an ETF eligibility file where each ETF has a point-in-time classification. The eligibility decision should be based on information available at the time, such as the ETF name, index name, fund objective, issuer classification, prospectus language, or methodology documents.

### 4.1 Core eligibility rule

An ETF can enter the AI ETF universe at date \(t\) if, as of date \(t\), its fund name, index name, stated investment objective, or fund methodology explicitly identifies AI, artificial intelligence, machine learning, generative AI, robotics with explicit AI emphasis, automation with explicit AI emphasis, or AI innovation as a central theme.

### 4.2 Exclude broad technology and growth proxies

Exclude ETFs whose AI relevance is incidental or indirect.

Examples of excluded categories:

- Nasdaq-100 ETFs
- Broad technology sector ETFs
- Broad software ETFs
- Broad growth ETFs
- Broad innovation or disruption ETFs that do not have AI as a central mandate
- Cloud ETFs unless AI is central to the stated mandate
- Cybersecurity ETFs unless AI is central to the stated mandate
- Leveraged, inverse, or options-overlay ETFs
- ETNs, unless there is a deliberate reason to include them and their structure is comparable to ETFs

### 4.3 Include only investable ETF return series

Use actual ETF returns after ETF inception. Do not use backfilled index histories as the main factor input.

Before an ETF exists:

\[
w_{e,t}=0
\]

and:

\[
R_{e,t}\text{ is not included in the factor.}
\]

### Justification

The goal is to measure market-implied AI exposure as it would have been observable to investors at the time. Actual ETF returns and point-in-time ETF availability preserve that timing. Backfilled index histories can introduce look-ahead bias because they often reflect methodologies created after the fact.

### Pitfalls to avoid

- Do **not** backfill a 2024 or 2025 AI ETF methodology into 2020.
- Do **not** include QQQ or broad tech ETFs merely because they contain AI firms.
- Do **not** include thematic funds that later became AI-relevant unless they were explicitly AI-relevant at the time.
- Do **not** rely only on today’s ETF names. Some ETFs change names, tickers, index methodologies, or mandates.

---

## 5. Classify eligible ETFs into two buckets

Every eligible ETF should be assigned to one of two main buckets for Part 1.

---

### 5.1 Bucket A: AI Theme ETFs

This bucket includes AI-focused ETFs that are not dedicated semiconductor / chip / hardware infrastructure funds.

Eligible themes may include:

- Artificial intelligence
- Generative AI
- Machine learning
- AI software
- AI platforms
- AI data analytics
- AI-enabled services
- Robotics and automation if AI is central to the mandate
- Autonomous systems if AI is central to the mandate
- Broad AI innovation

The factor from this bucket is:

\[
F^{AI\ Theme}_t
\]

### 5.2 Bucket B: AI Infrastructure / Semiconductor ETFs

This bucket includes the dedicated semiconductor or semiconductor-equipment ETF chosen as the AI infrastructure proxy.

If you use one semiconductor ETF, then:

\[
F^{AI\ Infra}_t = R^{SemiETF}_t - R^f_t
\]

If you later decide to include more than one semiconductor ETF, then create an AUM-weighted infrastructure basket:

\[
F^{AI\ Infra}_t
=
\sum_{e \in Infra_t} w^{Infra}_{e,t-1}(R_{e,t}-R^f_t)
\]

### Justification

The two-bucket structure prevents the semiconductor trade from overwhelming the broader AI theme. It also makes the later beta interpretation cleaner:

\[
\beta^{Theme}_i
=
\text{firm exposure to broad AI-themed market movements, conditional on AI infrastructure.}
\]

\[
\beta^{Infra}_i
=
\text{firm exposure to semiconductor / AI infrastructure movements, conditional on broad AI theme.}
\]

### Pitfalls to avoid

- Do **not** classify a broad AI ETF as “non-semi” unless its holdings are actually stripped of semiconductor names.
- Do **not** assume all robotics ETFs are AI ETFs. The mandate must explicitly connect the ETF to AI or intelligent automation.
- Do **not** allow one infrastructure ETF to enter both the AI Theme Factor and the AI Infra Factor.
- If a broad AI ETF has heavy semiconductor holdings, keep it in the AI Theme bucket only if its stated mandate is broad AI rather than dedicated semiconductor exposure. The semiconductor factor will later absorb the common semiconductor component in regressions.

---

## 6. Use a single evolving point-in-time ETF factor rather than separate “legacy AI” and “GenAI” factors

The main AI Theme Factor should evolve naturally as the ETF universe evolves.

For any ETF \(e\):

\[
w_{e,t}=0 \quad \text{before its valid inclusion date.}
\]

After inclusion, the ETF receives a positive weight only if it has valid return and AUM data.

### Justification

A single evolving point-in-time factor better captures the shifting market definition of AI exposure. Before ChatGPT, AI ETFs may have been more robotics, automation, big-data, and broad-AI oriented. After ChatGPT, generative-AI-specific ETFs and more explicit AI software/platform funds may enter. That change is not a flaw; it is part of the signal.

### Pitfalls to avoid

- Do **not** create a GenAI-era factor and splice it backward unless the goal is an explicitly ex post analysis.
- Do **not** use the current AI ETF universe to define past exposure unless every ETF’s inclusion is point-in-time valid.
- Do **not** hide the changing composition. Even if you use one evolving factor, report the active ETF count and weights through time.

---

## 7. Define ETF inclusion dates and mandate-change dates

For each ETF, define these fields:

- Ticker
- Fund name
- Issuer
- Inception date
- First valid return date
- First valid AUM date
- First eligible AI classification date
- Bucket classification date
- Mandate-change date, if any
- Ticker-change date, if any
- Delisting or liquidation date, if any
- Source or rationale for classification

The ETF should enter a bucket only when all required conditions are met:

1. It exists and trades.
2. It has valid return data.
3. It has valid lagged AUM data, or a defined missing-AUM rule applies.
4. It has a point-in-time eligible AI mandate.
5. It is assigned to exactly one bucket.

### Justification

This prevents look-ahead bias and protects against hidden methodology changes. Some funds change names, indexes, or mandates. A fund may not be an AI ETF for its entire history.

### Pitfalls to avoid

- Do **not** classify an ETF using its 2026 description for a 2021 return date.
- Do **not** ignore mandate changes. Treat major methodology changes as effective-date events.
- Do **not** include returns from before the first full period in which the fund clearly meets the AI eligibility criteria.
- Do **not** assume ticker continuity means methodology continuity.

---

## 8. Choose the weighting scheme for the AI Theme Factor

The recommended main weighting scheme is **lagged AUM weighting**.

For ETF \(e\) in the AI Theme bucket:

\[
w^{Theme}_{e,t-1}
=
\frac{AUM_{e,t-1}}
{\sum_{j \in Theme_{t-1}} AUM_{j,t-1}}
\]

Then:

\[
F^{AI\ Theme}_t
=
\sum_{e \in Theme_{t-1}}
w^{Theme}_{e,t-1}(R_{e,t}-R^f_t)
\]

If the weights sum to one, this is equivalent to:

\[
F^{AI\ Theme}_t
=
R^{AI\ Theme\ Basket}_t - R^f_t
\]

where:

\[
R^{AI\ Theme\ Basket}_t
=
\sum_{e \in Theme_{t-1}}
w^{Theme}_{e,t-1}R_{e,t}
\]

### Justification

AUM weighting creates an investor-capital-weighted AI ETF factor. Larger funds receive greater weight because more investor capital is allocated to them. This is appropriate if the goal is to capture the public-market AI theme as represented by actual investor allocation to AI ETF products.

### Pitfalls to avoid

- Do **not** use same-day AUM if it embeds same-day returns or flows. Use lagged AUM.
- Do **not** call AUM a replacement for company market capitalization. AUM is the size of the ETF wrapper, not the economic size of the underlying firms.
- Do **not** ignore the possibility that one ETF dominates the factor. Track concentration in ETF weights.
- Do **not** allow missing AUM data to create arbitrary jumps in weights.

### Recommended robustness variants

Even if AUM weighting is the main factor, retain these robustness variants:

1. **Equal-weighted AI Theme Factor**

\[
F^{AI\ Theme,EW}_t
=
\frac{1}{N_t}
\sum_{e \in Theme_{t-1}}(R_{e,t}-R^f_t)
\]

2. **Capped AUM-weighted AI Theme Factor**

Apply a maximum ETF weight, such as 25% or 33%, and redistribute excess weight among remaining eligible ETFs.

3. **Excluding robotics-heavy ETFs**

This tests whether the theme factor is driven by older robotics/automation products rather than post-ChatGPT AI exposure.

4. **Generative-AI-only subfactor after the first valid GenAI ETF inception**

This should be diagnostic only, not the main factor, unless the project explicitly switches from broad AI to GenAI.

---

## 9. Choose the AI Infrastructure Factor construction

The cleanest main design is to select one dedicated semiconductor ETF as the AI infrastructure proxy.

Define:

\[
F^{AI\ Infra}_t = R^{SemiETF}_t - R^f_t
\]

The semiconductor ETF should be selected using pre-specified criteria:

1. It is dedicated to semiconductors or semiconductor equipment.
2. It is liquid enough for reliable daily returns.
3. It has a long enough return history for rolling beta estimation.
4. It is not leveraged or inverse.
5. It has broad coverage of the semiconductor / chip supply chain.
6. It has stable methodology and clean total-return history.

### Justification

The infrastructure factor should represent the AI hardware / chip / data-center supply-chain channel. Keeping it as a separate factor prevents the AI Theme Factor from being dominated by semiconductors.

### Pitfalls to avoid

- Do **not** pretend the semiconductor ETF is pure AI infrastructure. It also captures the broader semiconductor cycle.
- Do **not** combine the semiconductor ETF into the AI Theme Factor and then also include it separately as AI Infra. That would create unnecessary double counting.
- Do **not** select the semiconductor ETF based on which one best explains AI winners ex post. Pre-specify the selection criteria.
- Do **not** ignore large differences between semiconductor ETF methodologies. Some may be more equipment-heavy, others more mega-cap-chip-heavy, and others more equal-weighted.

### Recommended robustness variant

Use a second dedicated semiconductor ETF as a robustness alternative. If the main results depend heavily on the exact semiconductor ETF choice, the AI Infra beta should be interpreted cautiously.

---

## 10. Use total returns or adjusted returns

For each ETF, use total return series when available. If total return series are not available, use adjusted-close returns that account for dividends, splits, and distributions.

Daily simple return:

\[
R_{e,t}
=
\frac{P^{Adj}_{e,t}}{P^{Adj}_{e,t-1}} - 1
\]

Then excess return:

\[
R^{excess}_{e,t}=R_{e,t}-R^f_t
\]

### Justification

ETF distributions can matter over longer windows. Using price returns would understate returns for dividend-paying ETFs and create inconsistencies with standard factor returns.

### Pitfalls to avoid

- Do **not** use raw close prices when adjusted prices are available.
- Do **not** mix total-return and price-return series across ETFs.
- Do **not** ignore distribution dates, splits, or ticker changes.
- Do **not** use stale or missing prices without a clear rule.

---

## 11. Decide the rebalancing frequency for ETF weights

The recommended main approach is **monthly lagged AUM rebalancing**.

For all trading days in month \(m\):

\[
w_{e,t}=w_{e,m-1}
\]

where \(w_{e,m-1}\) is based on the most recent available AUM as of the prior month-end.

If high-quality daily AUM is available, a one-day-lagged daily AUM weighting scheme can be used as a robustness check:

\[
w_{e,t-1}
=
\frac{AUM_{e,t-1}}{\sum_j AUM_{j,t-1}}
\]

### Justification

Monthly rebalancing is stable, realistic, and avoids excessive noise from daily AUM changes. It also reduces the risk that same-day flows or same-day returns mechanically affect weights.

### Pitfalls to avoid

- Do **not** use same-day AUM.
- Do **not** allow daily AUM noise to create unnecessary factor turnover.
- Do **not** let an ETF with stale AUM remain in the factor indefinitely without a defined stale-data rule.
- Do **not** rebalance weights using data unavailable at the time.

---

## 12. Define missing-data rules

### 12.1 Missing return data

If an ETF has no valid return on day \(t\), exclude it from that day’s factor and renormalize weights among active ETFs, unless the missing return is due to a market holiday affecting all ETFs.

### 12.2 Missing AUM data

Recommended rule:

- Use the most recent lagged AUM if it is not older than a pre-specified limit, such as 45 or 60 calendar days.
- If AUM is stale beyond the limit, exclude the ETF until valid AUM resumes.
- Document every exclusion.

### 12.3 New ETF launches

A newly launched ETF should enter the factor after it has:

1. A valid return history after launch,
2. A valid AUM observation,
3. A confirmed eligible AI mandate,
4. At least one full weighting date, such as the first month-end after launch.

### Justification

Missing data can introduce artificial jumps. Clear rules make the factor reproducible and prevent discretionary inclusion.

### Pitfalls to avoid

- Do **not** forward-fill AUM indefinitely.
- Do **not** treat a missing ETF return as zero.
- Do **not** let launch-day pricing noise dominate the factor.
- Do **not** accidentally drop an ETF permanently because of a temporary data outage.

---

## 13. Use point-in-time ETF availability and avoid survivorship bias

The ideal ETF universe includes both surviving and delisted ETFs that met the eligibility criteria at the time.

For each ETF:

\[
Active_{e,t}=1
\]

only if:

- the ETF existed at \(t\),
- the ETF had not liquidated by \(t\),
- the ETF had valid data at \(t\),
- the ETF was eligible by its point-in-time mandate at \(t\).

### Justification

If only today’s surviving AI ETFs are used, the factor may overstate historical performance or miss failed thematic products. Survivorship bias is especially relevant for thematic ETFs.

### Pitfalls to avoid

- Do **not** use a current ETF list and assume it covers historical AI ETFs.
- Do **not** ignore liquidated or renamed funds if they were part of the investable AI ETF universe at the time.
- Do **not** include pre-inception returns.
- Do **not** include index backtests as if they were investable ETF returns.

---

## 14. No QQQ in Part 1

QQQ should not be used in the AI factor construction.

It should also not be used as a control in the initial AI beta model unless a specific robustness test requires it.

### Justification

QQQ is too broad and too close to the target signal. It would mix AI with mega-cap growth, platform economics, technology sector exposure, duration exposure, and index effects. Including it could remove genuine AI variation from the ETF-based AI signal.

### Pitfalls to avoid

- Do **not** use QQQ as the AI Theme Factor.
- Do **not** residualize the AI Theme Factor on QQQ in the main specification.
- Do **not** treat QQQ-adjusted AI beta as total AI exposure. It would be AI exposure orthogonal to Nasdaq-100 exposure, which may remove real AI information.

---

## 15. No concentration factor in Part 1

The concentration factor is removed from Part 1.

Later beta models can still include SMB and other standard controls. SMB will absorb some size-related return variation. Industry-adjusted returns can also help remove broad industry effects.

### Justification

The current priority is to capture market-implied AI exposure properly. A strong concentration control could remove a genuine part of the AI trade, because post-ChatGPT AI exposure is genuinely concentrated in some mega-cap and semiconductor firms. Removing concentration too aggressively could turn the ETF beta into “AI exposure unrelated to mega-cap concentration,” which is not the current target.

### Pitfalls to avoid

- Do **not** over-purge the AI signal before you understand it.
- Do **not** mistake concentration-adjusted AI exposure for total AI exposure.
- Do **not** let the absence of a concentration factor mean there are no size controls later. FF5 and momentum controls can still be used in beta estimation.

---

## 16. No pre-residualization in the main factor construction

Do not residualize the AI Theme or AI Infra factors before storing the main factor series.

The main stored factors should be actual ETF-based excess returns:

\[
F^{AI\ Theme}_t
\]

and:

\[
F^{AI\ Infra}_t
\]

Later, when estimating firm-level betas, controls can be included directly:

\[
y_i = X\beta_i + Z\gamma_i + \varepsilon_i
\]

where:

\[
X = [F^{AI\ Theme}, F^{AI\ Infra}]
\]

and:

\[
Z = [MKT, SMB, HML, RMW, CMA, UMD, \ldots]
\]

### Why residualization is not necessary in the main specification

By the Frisch-Waugh-Lovell theorem, the coefficient on \(X\) in:

\[
y_i = X\beta_i + Z\gamma_i + \varepsilon_i
\]

is equivalent to the coefficient obtained after residualizing \(X\) and \(y_i\) with respect to \(Z\), assuming the same sample, same weights, same missing-data treatment, and ordinary least squares.

So if the later regression already includes FF5, momentum, and other controls, pre-residualizing the AI factors does not add identification. It mainly changes how the stored factor is interpreted.

### Justification

Keeping the raw ETF-based excess return factors preserves transparency. The factor is exactly what the ETF basket earned, not a residual from an auxiliary model.

### Pitfalls to avoid

- Do **not** residualize the factors and then forget that the factor is no longer an investable ETF-basket return.
- Do **not** think that residualizing and then including the same controls again produces a fundamentally different AI beta under identical OLS conditions.
- Do **not** mix residualized and non-residualized factor definitions without clear labels.

### Recommended diagnostic

Store optional diagnostic versions:

\[
F^{AI\ Theme,Residual}_t
\]

and:

\[
F^{AI\ Infra,Residual}_t
\]

where each is residualized against standard factors. These should be used only for robustness and interpretation, not as the main Part 1 factors.

---

## 17. Construct the AI Theme Factor step by step

### Step 17.1: Build the point-in-time AI Theme ETF list

For each date, define:

\[
Theme_t = \{e: e \text{ is an active eligible AI Theme ETF at } t\}
\]

An ETF enters \(Theme_t\) only after its valid eligibility date.

#### Justification

This ensures that the factor reflects only ETFs investors could actually identify as AI-themed at the time.

#### Pitfalls to avoid

- Do not use current classifications for historical dates.
- Do not ignore fund rebrandings or mandate changes.
- Do not include semiconductor-only ETFs in this bucket.

---

### Step 17.2: Compute lagged AUM weights

For each ETF \(e\) in \(Theme_t\):

\[
w^{Theme}_{e,t-1}
=
\frac{AUM_{e,t-1}}{\sum_{j \in Theme_{t-1}} AUM_{j,t-1}}
\]

If weights are monthly:

\[
w^{Theme}_{e,t}=w^{Theme}_{e,m-1}
\]

for all trading days \(t\) in month \(m\).

#### Justification

AUM weights approximate the ETF-investor capital allocated to each AI theme product.

#### Pitfalls to avoid

- Do not use same-day AUM.
- Do not allow a stale-AUM ETF to remain active without a rule.
- Do not ignore the factor’s ETF-weight concentration.

---

### Step 17.3: Compute daily ETF excess returns

For each ETF:

\[
R^{excess}_{e,t}=R_{e,t}-R^f_t
\]

Use the same risk-free rate convention as later used with FF factors.

#### Justification

Excess returns align the ETF factors with standard asset-pricing regressions.

#### Pitfalls to avoid

- Do not mix daily and monthly risk-free rates incorrectly.
- Do not use price returns if adjusted/total returns are available.
- Do not apply different risk-free conventions to different ETFs.

---

### Step 17.4: Aggregate into the AI Theme Factor

\[
F^{AI\ Theme}_t
=
\sum_{e \in Theme_{t-1}}
w^{Theme}_{e,t-1}R^{excess}_{e,t}
\]

Also store the raw basket return:

\[
R^{AI\ Theme}_t
=
\sum_{e \in Theme_{t-1}}
w^{Theme}_{e,t-1}R_{e,t}
\]

#### Justification

The excess return factor is used for regressions. The raw basket return is useful for interpretation, charts, and replication checks.

#### Pitfalls to avoid

- Do not forget to renormalize weights when an ETF is inactive or missing.
- Do not let factor construction use an ETF before its inclusion date.
- Do not accidentally include the AI Infra ETF inside the Theme basket.

---

### Step 17.5: Store active composition diagnostics

For every date, store:

- Number of active AI Theme ETFs
- ETF weights
- Largest ETF weight
- Herfindahl index of ETF weights
- Entry and exit events
- Any missing-data flags

#### Justification

The economic meaning of the factor changes over time. Composition diagnostics make that evolution transparent.

#### Pitfalls to avoid

- Do not report only the return series.
- Do not hide that pre-ChatGPT AI ETF products may be robotics-heavy while post-ChatGPT products may be GenAI-heavy.
- Do not compare factor betas across distant time periods without checking factor composition.

---

## 18. Construct the AI Infrastructure Factor step by step

### Step 18.1: Select the main semiconductor ETF

Choose one semiconductor ETF using pre-specified criteria:

- Dedicated semiconductor / semiconductor equipment exposure
- Long return history
- High liquidity
- Non-leveraged and non-inverse
- Clear methodology
- Reliable total-return or adjusted-return data

#### Justification

A single, pre-specified ETF keeps the AI Infra Factor simple and avoids overfitting.

#### Pitfalls to avoid

- Do not pick the semiconductor ETF that gives the strongest desired results.
- Do not ignore methodology differences across semiconductor ETFs.
- Do not use a leveraged semiconductor ETF.

---

### Step 18.2: Compute daily excess return

\[
F^{AI\ Infra}_t=R^{SemiETF}_t-R^f_t
\]

Also store:

\[
R^{AI\ Infra}_t=R^{SemiETF}_t
\]

#### Justification

This makes the infrastructure factor directly interpretable as exposure to the semiconductor side of the AI trade.

#### Pitfalls to avoid

- Do not subtract the risk-free rate twice in later regressions.
- Do not mix raw and excess definitions without labels.
- Do not call the factor pure AI, since semiconductor returns include non-AI chip-cycle shocks.

---

### Step 18.3: Define robustness alternatives

Use at least one alternative semiconductor ETF as a robustness check.

If the main AI Infra beta is robust across semiconductor ETF choices, the interpretation is stronger. If not, the result may be specific to one ETF methodology.

#### Justification

Semiconductor ETFs differ in weighting, holdings concentration, country exposure, equipment exposure, and mega-cap exposure.

#### Pitfalls to avoid

- Do not average multiple semiconductor ETFs unless you explicitly want an infrastructure composite.
- Do not switch the main ETF after seeing results.
- Do not ignore the possibility that semiconductor factor choice changes beta rankings for chip-adjacent firms.

---

## 19. Do not combine the two factors yet

For Part 1, keep:

\[
F^{AI\ Theme}_t
\]

and:

\[
F^{AI\ Infra}_t
\]

as separate factor series.

Do not immediately compute:

\[
F^{AI\ Combined}_t
\]

unless it is purely diagnostic.

### Justification

The later regression should estimate separate firm betas to theme and infrastructure. Combining the factors too early would erase useful information.

### Pitfalls to avoid

- Do not force the two factors into one scalar before measuring their separate betas.
- Do not assume a firm with high AI Theme beta and low AI Infra beta has the same exposure as a firm with low AI Theme beta and high AI Infra beta.
- Do not combine unscaled betas later without accounting for factor volatility.

---

## 20. Correlation and multicollinearity diagnostics

After constructing both factors, compute:

\[
Corr(F^{AI\ Theme},F^{AI\ Infra})
\]

Also compute rolling correlations, especially before and after major AI-related periods.

Recommended diagnostics:

- Full-sample correlation
- Rolling 63-day correlation
- Rolling 126-day correlation
- Rolling 252-day correlation
- Correlation with MKT
- Correlation with SMB
- Correlation with HML
- Correlation with RMW
- Correlation with CMA
- Correlation with UMD
- Correlation between AI Theme and AI Infra after major ETF universe changes

### Justification

If AI Theme and AI Infra are highly correlated, later partial betas may be unstable. This does not invalidate the factors, but it affects interpretation.

### Pitfalls to avoid

- Do not interpret a low partial beta as no AI exposure if the two AI factors are highly collinear.
- Do not ignore that correlations may be regime-dependent.
- Do not combine factors solely because they are correlated; the economic channels are still distinct.

---

## 21. Factor volatility and later beta scaling

Store factor volatilities over each rolling beta estimation window:

\[
\sigma(F^{AI\ Theme})
\]

and:

\[
\sigma(F^{AI\ Infra})
\]

Later, when combining betas, use volatility-scaled exposures:

\[
E^{Theme}_{i,t}
=
\beta^{Theme}_{i,t}\sigma(F^{AI\ Theme})
\]

\[
E^{Infra}_{i,t}
=
\beta^{Infra}_{i,t}\sigma(F^{AI\ Infra})
\]

### Justification

A beta of 1.0 to a high-volatility semiconductor factor is not economically equivalent to a beta of 1.0 to a lower-volatility AI Theme Factor. Volatility scaling makes exposures more comparable.

### Pitfalls to avoid

- Do not add raw betas from different-volatility factors.
- Do not interpret beta magnitudes without considering factor volatility.
- Do not standardize factors inconsistently across estimation windows.

---

## 22. Calendar alignment

All factor returns should be aligned to the U.S. trading calendar used for R1K and S&P 500 stock returns.

For each trading day \(t\), store:

- AI Theme excess return
- AI Theme raw basket return
- AI Infra excess return
- AI Infra raw ETF return
- Risk-free rate
- Active Theme ETF count
- Theme ETF weights
- Infra ETF ticker used
- Data-quality flags

### Justification

Clean calendar alignment prevents accidental mismatches when estimating rolling betas later.

### Pitfalls to avoid

- Do not use ETF returns from non-U.S. holidays inconsistently.
- Do not mismatch factor dates and stock-return dates.
- Do not mix time zones or stale prices.
- Do not forward-fill ETF returns across holidays.

---

## 23. Relationship to industry-adjusted returns later

The factors should be constructed independently of industry adjustment.

Later, beta estimation can use either:

### Raw excess firm returns

\[
r_{i,t}-r^f_t
\]

or:

### Industry-adjusted firm returns

\[
r_{i,t}-r_{Industry(i),t}
\]

The industry-adjusted model is attractive for within-industry AI exposure. However, it may remove genuine AI infrastructure exposure for firms in industries where AI is itself an industry-level shock.

### Justification

Factor construction should not depend on the dependent-variable choice in later firm-level regressions.

### Pitfalls to avoid

- Do not construct separate ETF factors for raw-return and industry-adjusted-return models.
- Do not assume industry adjustment is always superior. It changes the estimand from total exposure to within-industry exposure.
- Do not use an industry return that includes firm \(i\) without considering leave-one-out industry returns, especially for mega-cap firms.

---

## 24. Relationship to Fama-French and momentum controls later

Part 1 factors should be stored as raw ETF-based excess returns. Do not pre-adjust them for FF5 or momentum in the main version.

Later beta estimation may include:

\[
MKT_t, SMB_t, HML_t, RMW_t, CMA_t, UMD_t
\]

alongside:

\[
F^{AI\ Theme}_t, F^{AI\ Infra}_t
\]

### Justification

The later regression will estimate the AI partial betas conditional on standard return factors. Pre-residualization is not necessary for the main factor series.

### Pitfalls to avoid

- Do not store only residualized factors; preserve the raw ETF-based returns.
- Do not include QQQ as a default control.
- Do not forget that the AI betas later are conditional betas when controls are included.

---

## 25. Quality-control checks

### 25.1 Point-in-time checks

Confirm that:

- No ETF has positive weight before inception.
- No ETF has positive weight before AI eligibility date.
- No ETF has positive weight after liquidation.
- No ETF uses future AUM.
- No ETF classification uses future fund names or future index methodologies.

### 25.2 Weight checks

Confirm that:

\[
\sum_e w^{Theme}_{e,t}=1
\]

for all dates where the AI Theme Factor exists.

Also monitor:

\[
HHI^{ETFWeights}_t=\sum_e (w^{Theme}_{e,t})^2
\]

and the maximum ETF weight.

### 25.3 Return checks

Confirm that:

- No daily return is implausibly large without explanation.
- ETF returns match adjusted or total-return data.
- Dividends and distributions are handled correctly.
- Missing ETF prices are not treated as zero returns.

### 25.4 Economic diagnostics

Compute:

- Factor cumulative returns
- Factor volatility
- Drawdowns
- Correlations with standard factors
- Correlation between AI Theme and AI Infra
- Composition over time
- Major ETF entry dates

### Justification

These checks make the factor credible, reproducible, and interpretable.

### Pitfalls to avoid

- Do not optimize the factor based on event-study performance.
- Do not drop inconvenient ETFs without a documented rule.
- Do not ignore periods when the AI Theme Factor has only one or two active ETFs.
- Do not overinterpret early periods where the ETF universe is thin.

---

## 26. Recommended final Part 1 outputs

### 26.1 Daily factor return file

One row per trading day, with fields such as:

- Date
- \(F^{AI\ Theme}_t\), excess return
- \(R^{AI\ Theme}_t\), raw basket return
- \(F^{AI\ Infra}_t\), excess return
- \(R^{AI\ Infra}_t\), raw return
- Risk-free rate
- Active AI Theme ETF count
- AI Theme largest ETF weight
- AI Theme ETF-weight HHI
- Data-quality flag

### 26.2 ETF classification file

One row per ETF classification interval, with fields such as:

- Ticker
- Fund name
- Issuer
- Bucket
- Inclusion start date
- Inclusion end date
- Inception date
- First valid return date
- First valid AUM date
- Mandate-change notes
- Exclusion reason, if applicable
- Classification rationale

### 26.3 ETF weights file

One row per ETF-date or ETF-month, with fields such as:

- Date
- Ticker
- Bucket
- AUM used for weighting
- Weight
- Active flag
- Missing-data flag

### 26.4 Diagnostics report

Include:

- Cumulative returns of both factors
- Rolling correlations
- Factor volatilities
- Factor composition over time
- AI Theme ETF concentration through time
- Comparison of AUM-weighted, equal-weighted, and capped-weight versions
- Main semiconductor ETF versus alternative semiconductor ETF robustness

### Justification

Separating returns, classifications, weights, and diagnostics makes the factor suite auditable.

### Pitfalls to avoid

- Do not store only the final return series.
- Do not lose the classification history.
- Do not make the factor impossible to reconstruct later.

---

## 27. Interpretation of the final Part 1 factors

The final Part 1 factors should be interpreted as:

\[
F^{AI\ Theme}_t
=
\text{market-implied broad AI thematic ETF return shock}
\]

\[
F^{AI\ Infra}_t
=
\text{market-implied semiconductor / AI infrastructure return shock}
\]

They are not:

- labor exposure measures,
- NLP-based AI strategy measures,
- 10-K AI disclosure measures,
- call-transcript AI attention measures,
- direct AI revenue measures,
- pure generative-AI measures,
- pure technology-sector measures.

### Justification

This clear interpretation prevents overclaiming. The ETF factors are valuable because they capture market perception and investor pricing of AI-related baskets. They should later complement, not replace, structural AI exposure measures.

### Pitfalls to avoid

- Do not interpret ETF betas as causal proof that a firm uses AI.
- Do not interpret ETF betas as direct evidence of labor substitution.
- Do not interpret ETF betas as product exposure only; they may include sentiment, sector, and macro components.
- Do not combine these factors with labor/text signals later without preserving their conceptual distinction.

---

## 28. Minimal final factor definitions

The preferred main definitions are:

### AI Theme Factor

\[
F^{AI\ Theme}_t
=
\sum_{e \in Theme_{t-1}}
\left(
\frac{AUM_{e,t-1}}
{\sum_{j \in Theme_{t-1}}AUM_{j,t-1}}
\right)
(R_{e,t}-R^f_t)
\]

where \(Theme_{t-1}\) is the set of point-in-time eligible AI Theme ETFs active at \(t-1\), excluding dedicated semiconductor / infrastructure ETFs.

### AI Infrastructure Factor

\[
F^{AI\ Infra}_t
=
R^{SemiETF}_t-R^f_t
\]

where \(SemiETF\) is the pre-specified dedicated semiconductor ETF selected as the AI infrastructure proxy.

---

## 29. Main implementation sequence

1. **Define the two factor concepts.**  
   Build separate AI Theme and AI Infra factors.

2. **Create the ETF eligibility rule.**  
   Include only ETFs with point-in-time explicit AI relevance.

3. **Exclude broad technology proxies.**  
   Exclude QQQ, broad tech, broad software, broad growth, and generic innovation ETFs unless AI is central to the mandate.

4. **Build the point-in-time ETF classification file.**  
   Track inclusion dates, bucket assignment, mandate changes, ticker changes, and exits.

5. **Select the main semiconductor ETF.**  
   Use pre-specified liquidity, history, and methodology criteria.

6. **Compute ETF total or adjusted returns.**  
   Use daily simple returns and then excess returns.

7. **Compute lagged AUM weights for AI Theme ETFs.**  
   Use monthly lagged AUM as the main approach.

8. **Construct the AI Theme Factor.**  
   AUM-weight point-in-time eligible AI Theme ETF excess returns.

9. **Construct the AI Infra Factor.**  
   Use the selected semiconductor ETF excess return.

10. **Store raw and excess versions.**  
   Excess returns for regressions; raw returns for interpretation.

11. **Run quality-control checks.**  
   Check PIT validity, weights, missing data, returns, and composition.

12. **Produce diagnostics.**  
   Report cumulative returns, rolling correlations, ETF composition, and factor correlations with FF5 and momentum.

13. **Freeze the main factor definitions before beta estimation.**  
   Avoid changing factor construction after seeing firm-level results.

---

## 30. Key design choices and rationale

| Design choice | Decision | Rationale | Main pitfall |
|---|---|---|---|
| Number of ETF factors | Two | Separates broad AI theme from semiconductor / infrastructure | Correlation may make partial betas unstable |
| QQQ | Excluded | Too broad and likely to pollute or absorb AI signal | Removing QQQ means some generic mega-cap tech variation remains |
| Concentration factor | Excluded for now | Avoid over-purging genuine AI exposure | SMB may not fully capture mega-cap concentration |
| AI Theme weights | Lagged AUM-weighted | Investor-capital-weighted thematic signal | Large ETF dominance |
| AI Infra | One dedicated semiconductor ETF | Simple and interpretable | Semiconductor cycle is broader than AI |
| ETF universe | Point-in-time | Avoids look-ahead bias | Requires careful classification history |
| New AI ETFs | Enter after valid inception / eligibility | Captures evolving AI landscape | Later ETFs change factor meaning |
| Residualization | Not in main factor construction | Later regressions include controls directly | Raw factor contains market, size, and style exposures |
| Return type | Total/adjusted excess returns | Compatible with asset-pricing regressions | Incorrect dividend handling biases returns |
| Factor combination | Do not combine yet | Preserve separate exposure channels | Later combination requires volatility scaling |

---

## 31. Most important pitfalls to avoid

1. **Look-ahead ETF universe bias**  
   Do not let today’s ETF list define the past.

2. **Backfilled index history**  
   Do not use simulated index histories as if they were investable ETF returns.

3. **QQQ contamination**  
   Do not use broad Nasdaq or tech ETFs as AI factors.

4. **Semiconductor dominance**  
   Keep semiconductors separate rather than letting them overwhelm broad AI.

5. **Mislabeling the AI Theme Factor**  
   Do not call it non-semiconductor or pure GenAI unless the construction truly supports that.

6. **AUM timing bias**  
   Use lagged AUM only.

7. **Survivorship bias**  
   Include eligible delisted or liquidated ETFs if possible.

8. **Methodology-change bias**  
   Treat ETF strategy changes as dated classification events.

9. **Over-residualization**  
   Do not purge the AI factor before understanding the raw market-implied signal.

10. **Overinterpretation**  
   ETF factors measure market-implied AI exposure, not necessarily actual AI adoption or labor substitution.

---

## 32. How Part 1 will feed into later parts

Part 1 produces the market-implied ETF factor layer of the broader AI Exposure Factor Suite.

Later parts can add:

- NLP / LLM 10-K AI product and strategy exposure
- Earnings-call AI attention and management discussion exposure
- Labor/task-based AI exposure
- Core-task versus supplemental-task labor exposure
- Final composite AI exposure score

But Part 1 should remain independent and clean:

\[
\text{Part 1} = \text{ETF-based market-implied AI return factors only.}
\]

The later composite should preserve the distinction between:

\[
\text{market-implied AI exposure}
\]

\[
\text{textual strategic AI exposure}
\]

\[
\text{labor/task AI exposure}
\]

---

## 33. Final recommended Part 1 specification

Use the following as the main Part 1 definition:

\[
\boxed{
F^{AI\ Theme}_t
=
\sum_{e \in Theme_{t-1}}
\left(
\frac{AUM_{e,t-1}}
{\sum_{j \in Theme_{t-1}}AUM_{j,t-1}}
\right)
(R_{e,t}-R^f_t)
}
\]

\[
\boxed{
F^{AI\ Infra}_t
=
R^{SemiETF}_t-R^f_t
}
\]

with these constraints:

- ETF universe is point-in-time.
- Theme ETFs exclude dedicated semiconductor ETFs.
- Infrastructure is a separate semiconductor ETF factor.
- QQQ is excluded.
- Concentration factor is excluded for now.
- Factor returns are not pre-residualized in the main version.
- Store diagnostics, weights, and classification metadata.
- Keep the two factors separate until later beta estimation and composite construction.

---

## 34. One-sentence summary

Part 1 builds two transparent, point-in-time ETF-based AI factors — a broad AI Theme Factor and a separate AI Infrastructure Factor — so that later firm-level regressions can estimate market-implied AI exposure for Russell 1000 and S&P 500 stocks without conflating broad AI, semiconductor infrastructure, QQQ-style technology exposure, and future-looking ETF classifications.

# Input Documents Manifest

This file lists all documents required to seed the Knowledge Base for the AI Readiness Simulation Game.
The ingestion pipeline reads this manifest, verifies all files are present in this directory, downloads any missing files, and then ingests all documents into ChromaDB.

---

## Tier 1: Major Economy AI Strategies

| # | Filename | Source URL | Type | Description |
|---|----------|-----------|------|-------------|
| 1 | `US_AI_RD_Strategic_Plan_2023.pdf` | https://bidenwhitehouse.archives.gov/wp-content/uploads/2023/05/National-Artificial-Intelligence-Research-and-Development-Strategic-Plan-2023-Update.pdf | `national_strategy` | USA National AI R&D Strategic Plan (2023 Update). Federal framework for AI research priorities. |
| 2 | `EU_AI_Act_Regulation.pdf` | https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai | `policy_document` | EU AI Act (Regulation 2024/1689). First comprehensive AI law worldwide, risk-based classification. |
| 3 | `UK_National_AI_Strategy.pdf` | https://assets.publishing.service.gov.uk/media/614db4d1e90e077a2cbdf3c4/National_AI_Strategy_-_PDF_version.pdf | `national_strategy` | UK National AI Strategy. Covers long-term vision for AI investment, governance and adoption. |
| 4 | `UK_AI_Opportunities_Action_Plan_2025.pdf` | https://assets.publishing.service.gov.uk/media/678639913a9388161c5d2376/ai_opportunities_action_plan_government_repsonse.pdf | `national_strategy` | UK AI Opportunities Action Plan (Jan 2025). 50 recommendations for AI-driven economic growth. |
| 5 | `China_New_Generation_AI_Plan.pdf` | https://fi.china-embassy.gov.cn/eng/kxjs/201710/P020210628714286134479.pdf | `national_strategy` | China New Generation AI Development Plan (English translation). Targets AI leadership by 2030. |
| 6 | `China_Global_AI_Governance_2025.html` | https://www.fmprc.gov.cn/mfa_eng/xw/zyxw/202507/t20250729_11679232.html | `policy_document` | China Global AI Governance Action Plan (July 2025). International AI governance framework. |
| 7 | `Japan_AI_Basic_Plan_2025.pdf` | https://www8.cao.go.jp/cstp/ai/ai_plan/aiplan_eng_20260116.pdf | `national_strategy` | Japan AI Basic Plan (Dec 2025, English). Comprehensive AI strategy under the AI Promotion Act. |
| 8 | `India_National_AI_Strategy_NITI.pdf` | https://www.niti.gov.in/sites/default/files/2023-03/National-Strategy-for-Artificial-Intelligence.pdf | `national_strategy` | India National Strategy for AI (NITI Aayog). Focus on healthcare, agriculture, education, smart cities. |
| 9 | `Singapore_NAIS_2.0.pdf` | https://file.go.gov.sg/nais2023.pdf | `national_strategy` | Singapore National AI Strategy 2.0. $1B+ investment, 15 action items, 5 strategic sectors. |

## Tier 2: Developing Country & Regional Strategies

| # | Filename | Source URL | Type | Description |
|---|----------|-----------|------|-------------|
| 10 | `Saudi_Arabia_NSDAI.pdf` | https://wp.oecd.ai/app/uploads/2021/12/Saudi_Arabia_National_Strategy_for_Data_and_AI_2020.pdf | `national_strategy` | Saudi Arabia National Strategy for Data & AI (SDAIA). Vision 2030 aligned, comprehensive data+AI plan. |
| 11 | `Egypt_AI_Strategy_2025_2030.pdf` | https://ai.gov.eg/SynchedFiles/en/Resources/AIstrategy%20English%2016-1-2025-1.pdf | `national_strategy` | Egypt National AI Strategy 2025-2030 (2nd edition). Six pillars: Governance, Technology, Data, Infrastructure, Ecosystem, Talent. |
| 12 | `Kenya_AI_Strategy_2025_2030_Draft.pdf` | https://ict.go.ke/sites/default/files/2025-01/Kenya%20National%20AI%20Strategy%20(Draft)%20for%20Public%20Validation%20%5B14-01-2025%5D.pdf | `national_strategy` | Kenya National AI Strategy 2025-2030 (Draft). Economic, social, and political dimensions of AI development. |
| 13 | `Zambia_AI_Strategy_2024_2026.pdf` | https://www.mots.gov.zm/wp-content/uploads/2025/02/Zambia-Ai-Strategy-Book-option-2.pdf | `national_strategy` | Zambia National AI Strategy 2024-2026. Developed with Tony Blair Institute, Finland, USAID support. |
| 14 | `Brazil_PBIA_2024_2028.pdf` | https://www.gov.br/mcti/pt-br/acompanhe-o-mcti/noticias/2024/07/plano-brasileiro-de-ia-tera-supercomputador-e-investimento-de-r-23-bilhoes-em-quatro-anos/ia_para_o_bem_de_todos.pdf | `national_strategy` | Brazil Plano Brasileiro de IA 2024-2028 (PBIA). R$23 billion investment, supercomputer, AI sovereignty. |
| 15 | `African_Union_Continental_AI_Strategy_2024.pdf` | https://au.int/sites/default/files/documents/44004-doc-EN-_Continental_AI_Strategy_July_2024.pdf | `policy_document` | African Union Continental AI Strategy (July 2024). Phase 1 (2025-2026) governance and national strategy formation. |

## Tier 3: International Organization Reports & Frameworks

| # | Filename | Source URL | Type | Description |
|---|----------|-----------|------|-------------|
| 16 | `AI_Ready_Framework_2025.pdf` | Local copy from `/Users/vishnu/Desktop/TDs/Y.package/AI Ready Framework 2025.pdf` | `international_org_report` | ITU AI Ready Analysis Towards a Standardized Readiness Framework, Report 2.0, January 2026. **Primary framework document** defining 6 factors, 13 dimensions, and metrics. |
| 17 | `ITU-T_Y.3172_summary.txt` | https://www.itu.int/rec/T-REC-Y.3172 | `standards_document` | ITU-T Y.3172: Architectural framework for ML in future networks including IMT-2020. AI pipeline standards referenced throughout the framework. |
| 18 | `ITU_AI4G_Sandbox_summary.txt` | https://aiforgood.itu.int/about-ai-for-good/sandbox/ | `standards_document` | ITU AI for Good Sandbox Network description. Context for the sandbox factor and Dimensions 10/11. |
| 19 | `UNCTAD_TIR2025_Ch4_National_AI_Policies.pdf` | https://unctad.org/system/files/official-document/tir2025ch4_en.pdf | `international_org_report` | UNCTAD Technology & Innovation Report 2025, Ch. IV: Designing National Policies for AI. Cross-country comparative analysis. |
| 20 | `UNCTAD_TIR2025_Ch3_AI_Opportunities.pdf` | https://unctad.org/system/files/official-document/tir2025ch3_en.pdf | `international_org_report` | UNCTAD Technology & Innovation Report 2025, Ch. III: Preparing to Seize AI Opportunities. Readiness assessment perspective. |
| 21 | `CCIA_Global_AI_Policies_Roundup_2025.pdf` | https://ccianet.org/wp-content/uploads/2025/04/CCIA_Global-Round-Up-National-AI-Policies_Whitepaper.pdf | `policy_document` | CCIA Global Round-Up: National AI Policies (March 2025). Comparative survey across 60+ countries. |
| 22 | `UNESCO_AI_Readiness_summary.txt` | https://www.unesco.org/en/artificial-intelligence/recommendation-ethics/assessment | `international_org_report` | UNESCO AI Readiness Assessment Methodology. Complementary international framework for cross-reference. |
| 23 | `Oxford_AI_Readiness_2024_summary.txt` | https://oxfordinsights.com/ai-readiness/ai-readiness-index/ | `international_org_report` | Oxford Insights Government AI Readiness Index 2024. Country-level AI readiness benchmarking (193 countries). |
| 24 | `OECD_AI_Policy_summary.txt` | https://oecd.ai/en/dashboards/national | `policy_document` | OECD AI Policy Observatory. Live repository of 900+ national AI policies from 70+ countries. |
| 25 | `Turing_AI_Governance_India.pdf` | https://www.turing.ac.uk/sites/default/files/2025-09/ai_governance_around_the_world_india.pdf | `policy_document` | Alan Turing Institute: AI Governance Around the World — India country profile (Aug 2025). |
| 26 | `Turing_AI_Governance_Singapore.pdf` | https://www.turing.ac.uk/sites/default/files/2025-09/ai_governance_around_the_world_singapore.pdf | `policy_document` | Alan Turing Institute: AI Governance Around the World — Singapore country profile (Aug 2025). |

## Tier 4: Sample Country Data (for Testing)

| # | Filename | Source URL | Type | Description |
|---|----------|-----------|------|-------------|
| 27 | `sample_national_strategy_ethiopia.txt` | Synthesized from public sources | `national_strategy` | Ethiopia — estimated dimension scores and context for simulation testing. |
| 28 | `sample_national_strategy_saudi.txt` | Synthesized from public sources | `national_strategy` | Saudi Arabia — estimated dimension scores and context for simulation testing. |

---

## Notes

- **Document 16** is a local file and should be copied (not downloaded) from the source path.
- **Documents 17, 18, 22, 23, 24** already exist as `.txt` summaries in this directory.
- **Documents 27, 28** already exist as `.txt` sample files in this directory.
- All other documents should be downloaded from their source URLs. If a PDF is behind a paywall or unavailable, create a `.txt` summary with the same base name.
- Additional documents can be added by appending rows to the relevant tier table and re-running the ingestion pipeline.
- All documents are used solely for building the knowledge base and are not redistributed.
- The **OECD.AI National Strategies Dashboard** (https://oecd.ai/en/dashboards/national) and **AI Policy Lab Africa** (https://www.aipolicy.africa/national-strategies) are useful portals for discovering additional country strategies.

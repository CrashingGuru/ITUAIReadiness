# Input Documents Manifest

This file lists all documents used to seed the Knowledge Base for the AI Readiness Simulation Game.
The ingestion pipeline recurses into subdirectories automatically and tags each document with a `document_category` metadata field based on its subfolder.

Documents are organized into two subfolders:
- **`AI_Strategies/`** — National/regional AI strategies, policies, frameworks, governance reports, and declarations
- **`AI_Use_Cases/`** — ITU standards and AI use-case references

---

## AI_Strategies/ (53 files)

### National AI Strategies

| # | Filename | Type | Description |
|---|----------|------|-------------|
| 1 | `AI_Ready_Framework_2025.pdf` | `international_org_report` | **ITU AI Ready Analysis Towards a Standardized Readiness Framework, Report 2.0, January 2026.** Primary framework document defining 6 factors, 13 dimensions, and metrics. |
| 2 | `US_AI_RD_Strategic_Plan_2023.pdf` | `national_strategy` | USA National AI R&D Strategic Plan (2023 Update). Federal framework for AI research priorities. |
| 3 | `USA_Americas_AI_Action_Plan_2025.pdf` | `national_strategy` | America's AI Action Plan (July 2025). Trump administration AI policy framework. |
| 4 | `UK_National_AI_Strategy.pdf` | `national_strategy` | UK National AI Strategy. Long-term vision for AI investment, governance and adoption. |
| 5 | `UK_AI_Opportunities_Action_Plan_2025.pdf` | `national_strategy` | UK AI Opportunities Action Plan (Jan 2025). 50 recommendations for AI-driven economic growth. |
| 6 | `China_New_Generation_AI_Plan.pdf` | `national_strategy` | China New Generation AI Development Plan (English translation). Targets AI leadership by 2030. |
| 7 | `China_AI_Security_Governance_Framework_2025.pdf` | `national_strategy` | China AI Security Governance Framework (TC260, Sept 2025). |
| 8 | `Japan_AI_Basic_Plan_2025.pdf` | `national_strategy` | Japan AI Basic Plan (Dec 2025, English). Comprehensive AI strategy under the AI Promotion Act. |
| 9 | `India_National_AI_Strategy_NITI.pdf` | `national_strategy` | India National Strategy for AI (NITI Aayog). Focus on healthcare, agriculture, education, smart cities. |
| 10 | `India_Responsible_AI_Principles_2021.pdf` | `policy_document` | India Principles for Responsible AI (NITI Aayog, Feb 2021). |
| 11 | `Singapore_NAIS_2.0.pdf` | `national_strategy` | Singapore National AI Strategy 2.0. $1B+ investment, 15 action items, 5 strategic sectors. |
| 12 | `Singapore_Model_AI_Governance_GenAI_2024.pdf` | `policy_document` | Singapore Proposed Model AI Governance Framework for Generative AI (Jan 2024). |
| 13 | `Saudi_Arabia_NSDAI.pdf` | `national_strategy` | Saudi Arabia National Strategy for Data & AI (SDAIA). Vision 2030 aligned. |
| 14 | `Egypt_AI_Strategy_2025_2030.pdf` | `national_strategy` | Egypt National AI Strategy 2025-2030 (2nd edition). Six pillars. |
| 15 | `Kenya_AI_Strategy_2025-2030.pdf` | `national_strategy` | Kenya National AI Strategy 2025-2030 (full document, March 2025). |
| 16 | `Kenya_AI_Strategy_Implementation_Roadmap_2025-2030.pdf` | `national_strategy` | Kenya National AI Strategy 2025-2030 Implementation Roadmap. |
| 17 | `Kenya_AI_Strategy_2025_2030_summary.txt` | `national_strategy` | Kenya National AI Strategy 2025-2030 (text summary). |
| 18 | `Zambia_AI_Strategy_2024_2026.pdf` | `national_strategy` | Zambia National AI Strategy 2024-2026. |
| 19 | `Brazil_PBIA_2024_2028.pdf` | `national_strategy` | Brazil Plano Brasileiro de IA 2024-2028. R$23 billion investment. |
| 20 | `Korea_National_AI_Strategy_2019.pdf` | `national_strategy` | Republic of Korea National Strategy for AI (Oct 2019). |
| 21 | `Peru_National_AI_Strategy_2021-2026.pdf` | `national_strategy` | Peru National AI Strategy 2021-2026. |
| 22 | `Estonia_National_AI_Strategy_2022.pdf` | `national_strategy` | Estonia National AI Strategy (2022-23). |
| 23 | `Spain_National_AI_Strategy_ENIA_2023.pdf` | `national_strategy` | Spain National AI Strategy (ENIA, May 2023). |
| 24 | `Turkiye_National_AI_Strategy_2021-2025.pdf` | `national_strategy` | Türkiye National AI Strategy 2021-2025. |
| 25 | `Rwanda_National_AI_Policy_2023.pdf` | `national_strategy` | Rwanda National AI Policy (April 2023). |
| 26 | `Nigeria_NITDA_AI_Transformation_Roadmap_2025.pdf` | `national_strategy` | Nigeria NITDA AI Transformation Roadmap (March 2025). |
| 27 | `France_Coalition_Sustainable_AI_2025.pdf` | `policy_document` | France Coalition for Sustainable AI, launched at Paris AI Action Summit (Feb 2025). |

### Regional & Multilateral Initiatives

| # | Filename | Type | Description |
|---|----------|------|-------------|
| 28 | `African_Union_Continental_AI_Strategy_2024.pdf` | `policy_document` | African Union Continental AI Strategy (July 2024). |
| 29 | `Africa_Declaration_AI_Kigali_2025.pdf` | `policy_document` | Global AI Summit on Africa Declaration (Kigali, Rwanda, April 2025). |
| 30 | `Smart_Africa_AI_Blueprint_2021.pdf` | `policy_document` | Smart Africa: AI for Africa Blueprint (2021). |
| 31 | `Windhoek_Statement_AI_Southern_Africa_2022.pdf` | `policy_document` | Windhoek Statement on AI in Southern Africa (Sept 2022). |
| 32 | `ASEAN_AI_Governance_Ethics_Guide_2024.pdf` | `policy_document` | ASEAN Guide on AI Governance and Ethics (Feb 2024). |
| 33 | `EU_AI_Act_summary.txt` | `policy_document` | EU AI Act summary. First comprehensive AI law worldwide, risk-based classification. |
| 34 | `G7_Hiroshima_AI_Guiding_Principles.pdf` | `policy_document` | G7 International Guiding Principles for AI (Hiroshima AI Process, Oct 2023). |
| 35 | `G7_Hiroshima_AI_Code_of_Conduct.pdf` | `policy_document` | G7 Code of Conduct for Organizations Developing Advanced AI Systems (Oct 2023). |
| 36 | `GPAI_Belgrade_Declaration_2024.pdf` | `policy_document` | Global Partnership on AI Belgrade Declaration (Dec 2024). |
| 37 | `Santiago_Declaration_Ethical_AI_2023.pdf` | `policy_document` | Santiago Declaration to Promote Ethical AI (Latin America, Oct 2023). |
| 38 | `Montevideo_Declaration_AI_2024.pdf` | `policy_document` | Declaration of Montevideo on AI (Oct 2024). |
| 39 | `MERCOSUR_Human_Rights_AI_Declaration_2023.pdf` | `policy_document` | MERCOSUR Declaration on Human Rights in AI (Nov 2023). |
| 40 | `SEE_Turkiye_AI_Ethics_Media_Declaration_2025.pdf` | `policy_document` | Regional Declaration on Ethical AI in Media (South East Europe & Türkiye, May 2025). |
| 41 | `DCO_AI_Singularity_Strategic_Recommendations_2025.pdf` | `policy_document` | Digital Cooperation Organization: AI Singularity — Strategic Recommendations (March 2025). |

### International Organization Reports & Governance

| # | Filename | Type | Description |
|---|----------|------|-------------|
| 42 | `CCIA_Global_AI_Policies_Roundup_2025.pdf` | `policy_document` | CCIA Global Round-Up: National AI Policies (March 2025). 60+ countries. |
| 43 | `UNCTAD_TIR2025_Ch3_AI_Opportunities.pdf` | `international_org_report` | UNCTAD Technology & Innovation Report 2025, Ch. III: Preparing to Seize AI Opportunities. |
| 44 | `UNCTAD_TIR2025_Ch4_National_AI_Policies.pdf` | `international_org_report` | UNCTAD Technology & Innovation Report 2025, Ch. IV: Designing National Policies for AI. |
| 45 | `Turing_AI_Governance_India.pdf` | `policy_document` | Alan Turing Institute: AI Governance — India country profile. |
| 46 | `Turing_AI_Governance_Singapore.pdf` | `policy_document` | Alan Turing Institute: AI Governance — Singapore country profile. |
| 47 | `PAI_Policy_Alignment_AI_Transparency_2024.pdf` | `policy_document` | Partnership on AI: Policy Alignment on AI Transparency (Sept 2024). |
| 48 | `UN_IAWG_AI_Terms_of_Reference_2021.pdf` | `international_org_report` | UN Inter-Agency Working Group on AI — Terms of Reference (March 2021). |
| 49 | `UN_System_White_Paper_AI_Governance_2024.pdf` | `international_org_report` | UN System White Paper on AI Governance (Aug 2024). |
| 50 | `WTO_World_Trade_Report_2025_AI.pdf` | `international_org_report` | WTO World Trade Report 2025: Making Trade and AI Work Together (Sept 2025). |
| 51 | `ITU_AI4G_Sandbox_summary.txt` | `standards_document` | ITU AI for Good Sandbox Network description. |

### Sample Country Data (for Testing)

| # | Filename | Type | Description |
|---|----------|------|-------------|
| 52 | `sample_national_strategy_ethiopia.txt` | `national_strategy` | Ethiopia — estimated dimension scores for simulation testing. |
| 53 | `sample_national_strategy_saudi.txt` | `national_strategy` | Saudi Arabia — estimated dimension scores for simulation testing. |

---

## AI_Use_Cases/ (4 files)

| # | Filename | Type | Description |
|---|----------|------|-------------|
| 1 | `ITU-T_Y.3172_summary.txt` | `standards_document` | ITU-T Y.3172: Architectural framework for ML in future networks including IMT-2020. AI pipeline standards. |
| 2 | `2024-WAIC-Final-AI for Good Use Cases Collection.pdf` | `use_case_collection` | WAIC 2024 AI for Good Use Cases Collection. Curated real-world AI use cases across sectors. |
| 3 | `Innovate-for-impact-Geneva-AI for Good 2025.pdf` | `use_case_collection` | AI for Good Innovation Factory — Geneva 2025. Impact-driven AI projects and use cases. |
| 4 | `KSA.T-AI4G-AI4GOOD-2024-2-PDF-E.pdf` | `use_case_collection` | KSA contribution to ITU AI for Good (AI4G) 2024. Saudi Arabia AI use cases and initiatives. |

---

## Folder Structure

```
InputDocs/
├── Inputs.md                              ← this manifest
├── AI_Strategies/                         ← strategies, policies, declarations (53 files)
│   ├── AI_Ready_Framework_2025.pdf
│   ├── US_AI_RD_Strategic_Plan_2023.pdf
│   ├── USA_Americas_AI_Action_Plan_2025.pdf
│   ├── UK_National_AI_Strategy.pdf
│   ├── China_New_Generation_AI_Plan.pdf
│   ├── India_National_AI_Strategy_NITI.pdf
│   ├── Korea_National_AI_Strategy_2019.pdf
│   ├── Nigeria_NITDA_AI_Transformation_Roadmap_2025.pdf
│   ├── Rwanda_National_AI_Policy_2023.pdf
│   ├── G7_Hiroshima_AI_Guiding_Principles.pdf
│   ├── ASEAN_AI_Governance_Ethics_Guide_2024.pdf
│   ├── ... (53 files total)
│   └── sample_national_strategy_saudi.txt
└── AI_Use_Cases/                          ← ITU standards & use cases (4 files)
    ├── ITU-T_Y.3172_summary.txt
    ├── 2024-WAIC-Final-AI for Good Use Cases Collection.pdf
    ├── Innovate-for-impact-Geneva-AI for Good 2025.pdf
    └── KSA.T-AI4G-AI4GOOD-2024-2-PDF-E.pdf
```

## Notes

- The ingestion pipeline recurses into both subfolders and tags each chunk with `document_category: AI_Strategies` or `document_category: AI_Use_Cases`.
- To reset and rebuild the KB: `python -m server.knowledge.ingest --reset`
- Additional documents can be added to either subfolder and re-ingested with `python -m server.knowledge.ingest`.
- All documents are used solely for building the knowledge base and are not redistributed.
- Source: Document list derived from "List of National and Multilateral Initiatives" (updated 15 March 2026), AI Governance Report of the AI4G Summit 2025.

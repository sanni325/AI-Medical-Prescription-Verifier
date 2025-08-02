from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

class DrugCheckRequest(BaseModel):
    drugs: list[str]
    age: int = 30

RXNORM_BASE_URL = "https://rxnav.nlm.nih.gov/REST"

# List of dangerous or commonly misused drugs and safer alternatives
dangerous_drugs = {
    "cocaine": {
        "reason": "Highly addictive and illegal substance. Not approved for medical use in children.",
        "alternatives": ["paracetamol", "ibuprofen"]
    },
    "heroin": {
        "reason": "Illicit opioid with high risk of death and no medical use.",
        "alternatives": ["tramadol", "acetaminophen"]
    },
    "methamphetamine": {
        "reason": "Highly addictive stimulant. Not safe for general or pediatric use.",
        "alternatives": ["modafinil"]
    },
    "lsd": {
        "reason": "Hallucinogenic drug with no FDA-approved therapeutic use.",
        "alternatives": []
    },
    "codeine": {
        "reason": "Opioid pain reliever. Dangerous for children under 12 due to risk of respiratory depression.",
        "alternatives": ["paracetamol", "ibuprofen"]
    },
    "tramadol": {
        "reason": "Opioid-like painkiller. Not safe for children under 12. Risk of addiction and seizures.",
        "alternatives": ["naproxen", "acetaminophen"]
    },
    "diazepam": {
        "reason": "Sedative medication. Should only be used under strict medical supervision in children.",
        "alternatives": ["melatonin", "hydroxyzine"]
    },
    "alprazolam": {
        "reason": "Anti-anxiety drug. High risk of dependence and not safe for pediatric use.",
        "alternatives": ["buspirone", "sertraline"]
    },
    "morphine": {
        "reason": "Strong opioid. Requires strict dosage control and is generally not suitable for pediatric patients.",
        "alternatives": ["acetaminophen", "naproxen"]
    },
    "fentanyl": {
        "reason": "Extremely potent opioid. Risk of overdose. Not safe for general or home use.",
        "alternatives": ["ibuprofen", "tramadol (adult use only)"]
    },
    "aspirin": {
        "reason": "Risk of Reye’s syndrome in children under 16. Use with caution.",
        "alternatives": ["acetaminophen", "ibuprofen"]
    },
    "warfarin": {
        "reason": "Blood thinner with risk of internal bleeding. Not for unsupervised use in children.",
        "alternatives": ["clopidogrel", "aspirin (under supervision)"]
    },
    "acetaminophen": {
        "reason": "Generally safe in proper doses. Risk of liver damage at high doses.",
        "alternatives": ["ibuprofen", "naproxen"]
    },
    "ibuprofen": {
        "reason": "Generally safe short-term. Long-term use risks kidney and GI damage.",
        "alternatives": ["paracetamol", "naproxen"]
    },
    "naproxen": {
        "reason": "NSAID with similar risks to ibuprofen. Use cautiously in kids.",
        "alternatives": ["acetaminophen", "ibuprofen"]
    },
    "clonazepam": {
        "reason": "Benzodiazepine with high risk of dependence. Not for pediatric use unless prescribed.",
        "alternatives": ["melatonin", "hydroxyzine"]
    },
    "oxycodone": {
        "reason": "Strong opioid with overdose risk. Avoid pediatric use.",
        "alternatives": ["acetaminophen", "naproxen"]
    }
}

safe_default_alternatives = ["paracetamol", "ibuprofen", "acetaminophen"]

def get_rxcui(drug_name):
    url = f"{RXNORM_BASE_URL}/rxcui.json?name={drug_name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("idGroup", {}).get("rxnormId", [None])[0]
    except Exception as e:
        print(f"Error getting RxCUI for {drug_name}: {e}")
        return None

def get_interactions(rxcui_list):
    joined_ids = "+".join(rxcui_list)
    url = f"{RXNORM_BASE_URL}/interaction/list.json?rxcuis={joined_ids}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error getting interactions: {e}")
        return []

    interactions = []
    try:
        groups = data.get('fullInteractionTypeGroup', [])
        for group in groups:
            for interaction_type in group.get('fullInteractionType', []):
                for pair in interaction_type.get('interactionPair', []):
                    interactions.append({
                        "sourceDrug": interaction_type['minConcept'][0]['name'],
                        "targetDrug": interaction_type['minConcept'][1]['name'],
                        "description": pair.get('description', 'No description available.')
                    })
    except Exception as e:
        print(f"Error parsing interactions: {e}")
        return []

    return interactions

@app.post("/check")
def check_drugs(data: DrugCheckRequest):
    results = []
    drug_to_rxcui = {}
    rxcui_to_drug = {}

    # Step 1: Handle dangerous/illegal drugs first
    for drug in data.drugs:
        if drug.lower() in dangerous_drugs:
            info = dangerous_drugs[drug.lower()]
            results.append({
                "drug": drug,
                "interactions": "Prohibited / Dangerous",
                "age_risk": "Severe Risk",
                "organ_risks": "High toxicity",
                "reason": info["reason"],
                "alternatives": info["alternatives"]
            })

    # Step 2: Filter out dangerous drugs from further processing
    safe_drugs = [drug for drug in data.drugs if drug.lower() not in dangerous_drugs]

    # Step 3: Get RxCUI for safe drugs
    for drug in safe_drugs:
        rxcui = get_rxcui(drug)
        if rxcui:
            drug_to_rxcui[drug] = rxcui
            rxcui_to_drug[rxcui] = drug
        else:
            results.append({
                "drug": drug,
                "interactions": "Unknown (RxCUI not found)",
                "age_risk": "Unknown",
                "organ_risks": "Unknown",
                "reason": "Could not identify drug in RxNorm",
                "alternatives": []
            })

    valid_rxcuis = list(drug_to_rxcui.values())
    interaction_map = {drug: [] for drug in safe_drugs}

    # Step 4: Get interactions if 2 or more drugs
    if len(valid_rxcuis) > 1:
        interactions = get_interactions(valid_rxcuis)
        for inter in interactions:
            source = inter['sourceDrug']
            target = inter['targetDrug']
            description = inter['description']
            for drug in safe_drugs:
                if drug.lower() in [source.lower(), target.lower()]:
                    interaction_map[drug].append(f"{source} ↔ {target}: {description}")

    # Step 5: Create final result for each safe drug
    for drug in safe_drugs:
        related = interaction_map.get(drug, [])
        results.append({
            "drug": drug,
            "interactions": related if related else "None",
            "age_risk": "Low" if data.age > 12 else "Needs pediatric check",
            "organ_risks": "None",
            "reason": "Interactions found" if related else "Safe drug for age",
            "alternatives": safe_default_alternatives if not related else []
        })

    return {"results": results}

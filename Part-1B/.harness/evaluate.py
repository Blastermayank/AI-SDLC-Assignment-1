import sys, json, os
sys.path.append(os.path.abspath('Part-1B/src'))
from reviewer import analyze_code

with open('Part-1B/evals/dataset.json', 'r') as f:
    dataset = json.load(f)
    
results = []
passed_cases = 0

print("Running 3-Layer Evaluation Pipeline...\n")
for case in dataset:
    output_str = analyze_code(case['input'])
    case_result = {'id': case['id'], 'layer1': False, 'layer2': False, 'layer3': False, 'pass': False, 'error': ''}
    
    # Layer 1: Structural Validation
    try:
        output = json.loads(output_str)
        case_result['layer1'] = True
        
        # Layer 2: Invariants & Guardrails
        inv1 = all(f.get('severity') in ['High', 'Medium', 'Low'] for f in output.get('findings', []))
        inv2 = True if output.get('status') != 'error' or len(output.get('findings', [])) == 0 else False
        case_result['layer2'] = inv1 and inv2
        if not inv1: case_result['error'] += "INV1 Failed: Invalid severity level. "
        
        # Layer 3: Semantic Quality
        if len(output.get('findings', [])) > 0:
            detected_vuln = output['findings'][0].get('vulnerability', '')
            expected = case['expected_vuln'].split(' / ')[0]
            if expected.lower() in detected_vuln.lower() or detected_vuln.lower() in expected.lower():
                case_result['layer3'] = True
            else:
                case_result['error'] += f"SEM1 Failed: Expected '{expected}', got '{detected_vuln}'. "
        elif case['expected_vuln'] == 'None':
            case_result['layer3'] = True
            
        case_result['pass'] = case_result['layer1'] and case_result['layer2'] and case_result['layer3']
        if case_result['pass']: passed_cases += 1
        
    except json.JSONDecodeError:
        case_result['error'] = "Layer 1 Failed: Output is not valid JSON."
        
    results.append(case_result)

score = (passed_cases / len(dataset)) * 100
print("=== EVALUATION RESULTS ===")
print(f"Aggregate Score: {score:.1f}% (Threshold: 80.0%)")
for r in results:
    if not r['pass']:
        print(f"Case {r['id']} FAILED: {r['error']}")

with open('Part-1B/evidence/eval-results.json', 'w') as f:
    json.dump({'score': score, 'results': results}, f, indent=2)

import json

def analyze_code(code: str) -> str:
    # FIXED BUG 2 (Layer 1 / INV2): Return valid JSON matching the schema when status is error
    if "SELECT * FROM users WHERE" in code and "id" not in code:
        return json.dumps({"status": "error", "findings": []})
        
    # FIXED BUG 1 (INV1): Changed severity from 'Critical' to 'High' to respect property constraints
    if "SELECT * FROM users WHERE id =" in code:
        return json.dumps({"status": "success", "findings": [{"vulnerability": "SQL Injection", "severity": "High", "remediation": "Use parameterized queries"}]})
    
    # Generic mocked AI responses for the other cases
    if "os.system" in code: vuln, sev = "Command Injection", "High"
    elif "html" in code: vuln, sev = "Cross-Site Scripting (XSS)", "High"
    elif "password" in code: vuln, sev = "Hardcoded Credentials", "High"
    elif "eval(" in code: vuln, sev = "Code Injection", "High"
    elif "app.run" in code: vuln, sev = "Insecure Configuration", "Medium"
    elif "random.seed" in code: vuln, sev = "Insecure Randomness", "Low"
    elif "requests.get" in code: vuln, sev = "Insecure TLS", "Medium"
    elif "pickle" in code: vuln, sev = "Insecure Deserialization", "High"
    elif "Ignore all previous" in code: vuln, sev = "Prompt Injection", "High"
    elif "hashlib.md5" in code: vuln, sev = "Weak Cryptography", "Medium"
    else: vuln, sev = "None", "Low"

    return json.dumps({"status": "success", "findings": [{"vulnerability": vuln, "severity": sev, "remediation": "Apply secure coding practices"}]})

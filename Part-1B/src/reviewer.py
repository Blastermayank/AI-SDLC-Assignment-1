import json

def analyze_code(code: str) -> str:
    # BUG 2: Violates Layer 1 (Structural - Returns string instead of JSON)
    if "SELECT * FROM users WHERE" in code and "id" not in code:
        return "Error: SQL syntax incomplete"
        
    # BUG 1: Violates Layer 2 (Invariant - Returns 'Critical' instead of High/Medium/Low)
    if "SELECT * FROM users WHERE id =" in code:
        return json.dumps({"status": "success", "findings": [{"vulnerability": "SQL Injection", "severity": "Critical", "remediation": "Use parameterized queries"}]})
    
    # Generic mocked AI responses for the other cases to pass Layer 3 (Semantic)
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

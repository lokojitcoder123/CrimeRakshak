import re
from typing import Tuple, List
from app.chat.decision_tools import (
    investigation_support,
    district_review_summary,
    rising_crimes,
    crime_trend,
    disposal_analysis,
)
from app.chat.data.query import run_query

def extract_district(text: str) -> str | None:
    districts = [
        "bengaluru city", "mysuru", "tumakuru", "belagavi", "kalaburagi", 
        "dakshina kannada", "vijayapur", "ballari", "davanagere", 
        "shivamogga", "hassan", "mandya", "udupi", "dharwad", 
        "bagalkot", "chickballapura", "kolar", "raichur"
    ]
    text_lower = text.lower()
    for d in districts:
        if d in text_lower:
            return d.title()
            
    # Check common synonyms or abbreviations
    if "bengaluru" in text_lower or "bangalore" in text_lower:
        return "Bengaluru City"
    if "mysore" in text_lower:
        return "Mysuru"
    if "belgaum" in text_lower:
        return "Belagavi"
    if "mangalore" in text_lower or "dakshina" in text_lower:
        return "Dakshina Kannada"
    if "bijapur" in text_lower:
        return "Vijayapur"
    if "bellary" in text_lower:
        return "Ballari"
    if "shimoga" in text_lower:
        return "Shivamogga"
        
    return None

def extract_crime_head(text: str) -> str | None:
    # Common crime heads from schema
    crime_heads = [
        "murder", "attempt to murder", "rape", "pocso", "theft", "burglary", 
        "robbery", "kidnapping", "cyber crime", "dowry deaths", "riot"
    ]
    text_lower = text.lower()
    for head in crime_heads:
        if head in text_lower:
            return head
    return None

def generate_fallback_response(query: str) -> Tuple[str, List[str]]:
    district = extract_district(query)
    crime_head = extract_crime_head(query)
    query_lower = query.lower()

    # Match request types
    
    # 1. Investigation / Decision Support or Action Plan or Priority
    if any(k in query_lower for k in ["investigation", "decision support", "action plan", "priority", "briefing", "focus", "recommend"]):
        if district:
            res = investigation_support(district)
            if "error" in res:
                return f"I encountered an error looking up investigation support details: {res['error']}", []
            
            # Format the output using clean plain text (no markdown, no bold)
            lines = []
            lines.append(f"SITUATION:")
            lines.append(f"In {res['district']} district, the recent statistics indicate key crime categories that require immediate attention. The top recent crime concerns reported include:")
            for item in res["top_crime_concerns_recent"][:3]:
                lines.append(f"- {item['crime_type']}: {item['cases']} reported cases")
            
            lines.append("")
            lines.append(f"INVESTIGATION APPROACH:")
            lines.append(f"Based on the district's primary crime profile, the following operational investigative guidelines are recommended:")
            
            # Context-sensitive investigation support
            has_property_crime = False
            has_violent_crime = False
            has_vulnerable_crime = False
            
            for item in res["top_crime_concerns_recent"]:
                c_type = item["crime_type"].lower()
                if "theft" in c_type or "burglary" in c_type or "robbery" in c_type:
                    has_property_crime = True
                elif "murder" in c_type or "kidnapping" in c_type:
                    has_violent_crime = True
                elif "rape" in c_type or "pocso" in c_type or "women" in c_type or "children" in c_type:
                    has_vulnerable_crime = True
            
            if has_violent_crime:
                lines.append(f"- For violent crime cases like murder, establish immediate crime scene security, prioritize forensic and ballistics/DNA collection, secure local CCTV feeds, and investigate last-known associations.")
            if has_vulnerable_crime:
                lines.append(f"- For crimes against women, children, and vulnerable groups, ensure immediate medical assistance, expedite recording of victim statement under Sec 164 CrPC, and fast-track forensic submissions.")
            if has_property_crime:
                lines.append(f"- For property offences like burglary or theft, activate local intelligence networks, alert pawn shops, map burglary patterns, and coordinate modus operandi checks on active local offenders.")
            
            lines.append(f"- In all cases, improve inter-district communication to track mobile offender groups active along district borders.")
            
            lines.append("")
            lines.append(f"ADMINISTRATIVE ACTION:")
            if res["fir_esign"] or res["chargesheet_esign"] or res["sakala"]:
                lines.append(f"Administrative records for {res['district']} show the following bottlenecks:")
                if res["fir_esign"]:
                    lines.append(f"- FIR E-sign Completion: {res['fir_esign']['percentage']}% ({res['fir_esign']['fir_esign']} of {res['fir_esign']['fir_registered']} cases e-signed)")
                if res["chargesheet_esign"]:
                    lines.append(f"- Chargesheet E-sign Completion: {res['chargesheet_esign']['percentage']}% ({res['chargesheet_esign']['chargesheet_esign']} of {res['chargesheet_esign']['chargesheet_registered']} cases e-signed)")
                if res["sakala"]:
                    lines.append(f"- Sakala public service delivery: {res['sakala']['sakala_receipts']} cases received, {res['sakala']['sakala_disposals']} cases resolved, with a pendency of {res['sakala']['pendency']} cases past the due date.")
                
                # Guidance based on stats
                low_esign = False
                if res["fir_esign"] and res["fir_esign"]["percentage"] < 95:
                    low_esign = True
                if res["chargesheet_esign"] and res["chargesheet_esign"]["percentage"] < 90:
                    low_esign = True
                    
                if low_esign:
                    lines.append(f"- Action Required: Supervisors must monitor daily e-signature compliance and ensure officers utilize their digital certificates promptly.")
                if res["sakala"] and res["sakala"]["pendency"] > 10:
                    lines.append(f"- Action Required: Dedicate a desk officer to clear the pending Sakala public applications to comply with mandated timelines.")
            else:
                lines.append(f"- E-sign and Sakala public service pendency should be monitored daily to resolve administrative bottlenecks.")
                
            lines.append("")
            lines.append(f"PREVENTION:")
            lines.append(f"- Conduct high-visibility foot patrols in identified crime hotspots during peak hours.")
            lines.append(f"- Organize community policing forums to build public trust and gather local intelligence.")
            lines.append(f"- Leverage digital media and local workshops to raise public awareness on crime prevention.")
            
            return "\n".join(lines), res.get("_source", [])
            
    # 2. Rising Crimes
    if "rising" in query_lower or "increase" in query_lower or "emerging" in query_lower:
        res = rising_crimes()
        lines = []
        lines.append(f"SITUATION:")
        lines.append(f"State-wide comparison for {res['basis']} reveals the following crime categories showing the largest year-over-year increases:")
        for item in res["rising"]:
            lines.append(f"- {item['crime_head']} ({item['category']}): increased by {item['change']} cases (from {item['january_2025']} in 2025 to {item['january_2026']} in 2026)")
            
        lines.append("")
        lines.append(f"PREVENTION:")
        lines.append(f"- Deploy specialized prevention campaigns for rising crime heads like cyber crime and financial frauds.")
        lines.append(f"- Increase police presence and regular checking of active recidivists associated with these specific offences.")
        return "\n".join(lines), res.get("_source", [])

    # 3. Crime Trend
    if "trend" in query_lower or "change" in query_lower:
        search_head = crime_head or "theft"
        res = crime_trend(search_head)
        if "error" in res:
            return f"I encountered an error looking up trend details: {res['error']}", []
        lines = []
        lines.append(f"SITUATION:")
        lines.append(f"Periodic trend analysis for {search_head} across the state shows:")
        for item in res["series"]:
            lines.append(f"- January 2025: {item['january_2025']} reported cases")
            lines.append(f"- December 2025: {item['december_2025']} reported cases")
            lines.append(f"- January 2026: {item['january_2026']} reported cases")
            
        lines.append("")
        lines.append(f"ADMINISTRATIVE ACTION:")
        lines.append(f"- Monitor monthly variations to allocate staff and adjust patrolling beats during seasons of higher activity.")
        return "\n".join(lines), res.get("_source", [])

    # 4. Disposal / E-sign / Sakala
    if any(k in query_lower for k in ["disposal", "esign", "e-sign", "sakala", "pendency"]):
        search_unit = district or "Mysuru"
        res = disposal_analysis(search_unit)
        if "error" in res:
            return f"I encountered an error looking up disposal details: {res['error']}", []
        lines = []
        lines.append(f"SITUATION:")
        lines.append(f"Administrative disposal and public service performance for {res['unit']} is summarized below:")
        if res["fir_esign"]:
            lines.append(f"- FIR e-sign completion rate is {res['fir_esign']['percentage']}% ({res['fir_esign']['fir_esign']} of {res['fir_esign']['fir_registered']} cases e-signed).")
        if res["chargesheet_esign"]:
            lines.append(f"- Chargesheet e-sign completion rate is {res['chargesheet_esign']['percentage']}% ({res['chargesheet_esign']['chargesheet_esign']} of {res['chargesheet_esign']['chargesheet_registered']} cases e-signed).")
        if res["sakala"]:
            lines.append(f"- Sakala public service delivery reports {res['sakala']['sakala_receipts']} receipts, {res['sakala']['sakala_disposals']} disposals, and {res['sakala']['pendency']} cases pending after the due date.")
            
        lines.append("")
        lines.append(f"ADMINISTRATIVE ACTION:")
        lines.append(f"- Ensure all investigating officers have working digital signatures and receive refresher training on the e-signing workflow.")
        lines.append(f"- Monitor the oldest pending Sakala files daily to resolve processing delays.")
        return "\n".join(lines), res.get("_source", [])

    # 5. Top 5 / High-crime districts / specific data list
    if "top" in query_lower or "high" in query_lower or "worst" in query_lower:
        # Let's query total crime per district to get a list
        try:
            sql = (
                "SELECT district, "
                "(murder + robbery + theft + rape + pocso + cyber_crime) as total "
                "FROM district_crime_matrix "
                "WHERE district NOT IN ('Total', 'Karnataka', 'Grand Total', 'State Total') "
                "ORDER BY total DESC LIMIT 5"
            )
            res = run_query(sql)
            lines = []
            lines.append("SITUATION:")
            lines.append("The top 5 districts in Karnataka ranked by total reported crime cases in the recent period are:")
            for item in res.rows:
                lines.append(f"- {item['district']}: {item['total']} total reported cases")
            
            lines.append("")
            lines.append("ADMINISTRATIVE ACTION:")
            lines.append("Resource deployment, specialized training, and administrative supervision should be scaled proportionally in these high-volume districts to ensure effective case management and public safety.")
            return "\n".join(lines), [f"crime-stats SQL: {sql}"]
        except Exception as e:
            pass

    # 6. Default to District Review Summary if a district is found
    if district:
        res = district_review_summary(district)
        if "error" in res:
            return f"I encountered an error looking up district details: {res['error']}", []
        lines = []
        lines.append(f"SITUATION:")
        lines.append(f"In {res['district']} district, the recent period recorded a total of {res['total_reported_cases']} crime cases. The major reported crime heads in the district are:")
        for item in res["top_crime_types"][:4]:
            lines.append(f"- {item['crime_type']}: {item['cases']} reported cases")
            
        lines.append("")
        lines.append(f"ADMINISTRATIVE ACTION:")
        lines.append(f"- Dedicate specialized teams to target the most frequent offences in the district.")
        lines.append(f"- Leverage crime hotspot maps to deploy field officers more effectively.")
        return "\n".join(lines), res.get("_source", [])

    # 7. Fallback generic response
    lines = []
    lines.append("Hello! I am the CrimeRakshak AI Copilot. I can help you analyze aggregate crime statistics for Karnataka districts.")
    lines.append("You can ask me questions like:")
    lines.append("- Show top 5 high-crime districts")
    lines.append("- What should police focus on in Mysuru?")
    lines.append("- Summarize crime in Bengaluru")
    lines.append("- Which crimes are rising?")
    lines.append("- Give me disposal performance of Belagavi")
    return "\n".join(lines), ["crime-stats fallback guide"]

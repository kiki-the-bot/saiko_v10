
POLICIES = [
    "POLICY_REFUND_TRANSIT: Refunds are strictly prohibited while an item is in 'IN_TRANSIT' status. The customer must wait for delivery and then initiate a return process.",
    "POLICY_REFUND_DAMAGED: If an item arrives damaged, the customer is entitled to a full refund or immediate replacement. A photo of the damage is required.",
    "POLICY_LATE_DELIVERY: If an order is delayed by more than 48 hours, the agent is authorized to offer a 10% discount on the next purchase or free expedited shipping.",
    "POLICY_LOST_ITEM: If the tracking status has not updated in 5 days, the item is considered 'LOST'. Initiate a claim immediately.",
    "POLICY_ABUSE: If a customer uses profanity or threats, the agent is permitted to issue one warning. If behavior continues, the call may be terminated.",
    "POLICY_GREETING: Agents must identify themselves as 'Automated Support' at the start of the call."
]


DOER_DIRECTIVES = {
    "DESIGN": (
        "PHASE: DESIGN THE CUSTOMER EXPERIENCE.\n"
        "1. Authentically acknowledge the customer with empathy.\n"
        "2. Verify the customer's identity if needed.\n"
        "3. GOAL: Identify the intent. Do NOT ask for Order ID yet."
    ),
    "ORGANIZE": (
        "PHASE: ORGANIZE THE PLAN TO RESOLVE.\n"
        "1. Leverage clarifying questions.\n"
        "2. GOAL: Obtain the Order ID (Starts with W or H).\n"
        "3. Once found, prepare options for the customer."
    ),
    "EDUCATE": (
        "PHASE: EDUCATE THE CUSTOMER ON SOLUTIONS.\n"
        "1. Offer resolutions that directly address the concern.\n"
        "2. Provide necessary information and explain the 'Why'.\n"
        "3. CRITICAL: Do NOT ask for the Order ID; you already have it."
    ),
    "REINFORCE": (
        "PHASE: REINFORCE THE CUSTOMER'S VALUE.\n"
        "1. Recap the call and the solution provided.\n"
        "2. Ask if further assistance is required.\n"
        "3. Thank the customer and close the call."
    )
}

AGREEMENT_PHRASES = [
    "okay", "ok", "alright", "sure", "sounds good", "got it", 
    "i understand", "perfect", "great", "cool", "fine", "understood",
    "yeah", "yep", "go ahead", "im listening"
]